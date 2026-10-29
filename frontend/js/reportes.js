// Módulo de reportes y estadísticas (RF-11.1 a RF-11.7).
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, pintarSuave } from './ui.js';

const yo = await exigirSesion('reportes.ver'); // solo el ADMINISTRADOR
const puedeVerIncidencias = yo.permisos.includes('incidencias.ver'); // RF-12.4
const puedeGestionarCodigos = yo.permisos.includes('incidencias.gestionar'); // RF-12.1

const $ = (id) => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';

const ESTADOS = { OK: 'OK', BAJO: 'En el mínimo', AGOTADO: 'Agotado' };
const TIPOS = { DOMICILIO: 'Domicilio', LLEVAR: 'Para llevar', MESA: 'Mesa' };
const METODOS = { EFECTIVO: 'Efectivo', TARJETA: 'Tarjeta', TRANSFERENCIA: 'Transferencia' };

// Tabla visible del reporte actual: se usa para descargar el CSV
let tablaActual = { nombre: 'reporte', columnas: [], filas: [] };

// =====================================================================
//  Piezas de pantalla: tarjetas, tablas y gráficas
// =====================================================================

function tarjeta(icono, titulo, valor, detalle) {
  return crear('div', { className: 'tarjeta-resumen' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
    ...(detalle ? [crear('small', { className: 'nota', texto: detalle })] : []),
  ]);
}

/**
 * Tabla a partir de columnas [{titulo, valor: fila => texto, numero?}] y filas.
 * También la guarda como la tabla a descargar.
 */
function tabla(nombre, columnas, filas) {
  tablaActual = { nombre, columnas, filas };
  if (filas.length === 0) return crear('p', { className: 'nota', texto: 'No hay datos en este periodo.' });
  const encabezado = crear('tr', {}, columnas.map((c) => crear('th', { className: c.numero ? 'numero' : '', texto: c.titulo })));
  const cuerpo = filas.map((fila) => crear('tr', {}, columnas.map((c) => crear('td', {
    className: c.numero ? 'numero' : '', texto: String(c.valor(fila) ?? ''),
  }))));
  return crear('div', { className: 'tabla-contenedor' }, [
    crear('table', { className: 'tabla' }, [crear('thead', {}, [encabezado]), crear('tbody', {}, cuerpo)]),
  ]);
}

/** Gráfica de barras en SVG: datos [{etiqueta, valor}]. */
function graficaBarras(datos, formatoValor = formato.dinero) {
  if (!datos.some((d) => d.valor > 0)) return crear('p', { className: 'nota', texto: 'No hay ventas en este periodo.' });
  // En el celular el lienzo es más angosto para que las letras no se encojan al escalar
  const celular = window.innerWidth < 600;
  const ancho = celular ? 360 : 640;
  const alto = celular ? 240 : 220;
  const margen = { arriba: 28, abajo: 40, izquierda: 20 }; // a los lados caben las etiquetas
  const maximo = Math.max(...datos.map((d) => d.valor), 1);
  const paso = (ancho - margen.izquierda * 2) / datos.length;
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${ancho} ${alto}`);
  svg.setAttribute('class', celular ? 'grafica movil' : 'grafica');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', `Máximo del periodo: ${formatoValor(maximo)}`);
  const cada = Math.ceil(datos.length / (celular ? 4 : 10)); // pocas etiquetas abajo para que se lean

  // Línea base y valor máximo como referencia
  const base = document.createElementNS(NS, 'line');
  base.setAttribute('x1', margen.izquierda);
  base.setAttribute('x2', ancho - margen.izquierda);
  base.setAttribute('y1', alto - margen.abajo);
  base.setAttribute('y2', alto - margen.abajo);
  base.setAttribute('class', 'base');
  svg.appendChild(base);
  const tope = document.createElementNS(NS, 'text');
  tope.setAttribute('x', margen.izquierda);
  tope.setAttribute('y', 16);
  tope.setAttribute('class', 'tope');
  tope.textContent = `Máx. ${formatoValor(maximo)}`;
  svg.appendChild(tope);

  datos.forEach((d, i) => {
    const altura = ((alto - margen.arriba - margen.abajo) * d.valor) / maximo;
    const x = margen.izquierda + i * paso + paso * 0.15;
    const rect = document.createElementNS(NS, 'rect');
    rect.setAttribute('x', x);
    rect.setAttribute('y', alto - margen.abajo - altura);
    rect.setAttribute('width', paso * 0.7);
    rect.setAttribute('height', Math.max(altura, d.valor > 0 ? 2 : 0));
    rect.setAttribute('rx', 3);
    const titulo = document.createElementNS(NS, 'title');
    titulo.textContent = `${d.etiqueta}: ${formatoValor(d.valor)}`; // se ve al pasar el mouse
    rect.appendChild(titulo);
    svg.appendChild(rect);
    if ((i - Math.floor(cada / 2)) % cada === 0) { // etiquetas centradas, ninguna pegada al borde
      const texto = document.createElementNS(NS, 'text');
      texto.setAttribute('x', x + paso * 0.35);
      texto.setAttribute('y', alto - margen.abajo + 16);
      texto.setAttribute('text-anchor', 'middle');
      texto.textContent = d.etiqueta;
      svg.appendChild(texto);
    }
  });
  return svg;
}

/** Barras horizontales simples (por método, por tipo...). */
function barrasHorizontales(pares) {
  const maximo = Math.max(...pares.map(([, v]) => v), 1);
  return crear('ul', { className: 'barras' }, pares.map(([texto, valor]) => {
    const barra = crear('div', { className: 'barra-progreso' });
    barra.style.width = valor > 0 ? `${Math.max(2, (valor / maximo) * 100)}%` : '0'; // en $0 no se dibuja
    return crear('li', {}, [
      crear('div', { className: 'barra-texto' }, [crear('span', { texto }), crear('span', { texto: formato.dinero(valor) })]),
      barra,
    ]);
  }));
}

function panel(titulo, ...hijos) {
  return crear('section', { className: 'panel' }, [crear('h3', { texto: titulo }), ...hijos]);
}

const diaCorto = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
const porcentaje = (v) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${v} %`);

// =====================================================================
//  Los 6 reportes
// =====================================================================

const REPORTES = {
  // RF-11.6 Estadísticas para la toma de decisiones
  estadisticas: {
    titulo: 'Estadísticas para tomar decisiones',
    async pintar(p) {
      const r = await api('GET', `/reportes/estadisticas?${p}`);
      const i = r.indicadores;
      const recomendaciones = crear('ul', { className: 'recomendaciones' },
        r.recomendaciones.map((texto) => crear('li', { texto })));
      return [
        crear('div', { className: 'resumen' }, [
          tarjeta('payments', 'Total vendido', formato.dinero(i.total), `${porcentaje(i.variacion_total)} vs. periodo anterior`),
          tarjeta('receipt_long', 'Ventas por día', formato.cantidad(i.ventas_por_dia), `${i.ventas} ${i.ventas === 1 ? 'venta' : 'ventas'}`),
          tarjeta('shopping_bag', 'Ticket promedio', formato.dinero(i.ticket_promedio)),
          tarjeta('star', 'Producto estrella', i.producto_estrella ?? '—'),
          tarjeta('event', 'Día de más ventas', i.dia_mas_ventas ?? '—'),
          tarjeta('schedule', 'Hora pico', i.hora_pico?.replace(' - ', '–') ?? '—'),
        ]),
        panel('Recomendaciones', recomendaciones),
        panel('Cobertura del inventario (días que alcanza al ritmo actual)', tabla('cobertura', [
          { titulo: 'Insumo', valor: (f) => f.insumo },
          { titulo: 'Stock', valor: (f) => `${formato.cantidad(f.stock_actual)} ${f.unidad_medida}`, numero: true },
          { titulo: 'Consumo diario', valor: (f) => formato.cantidad(f.consumo_diario), numero: true },
          { titulo: 'Días', valor: (f) => formato.cantidad(f.dias), numero: true },
        ], r.cobertura)),
      ];
    },
  },

  // RF-11.2 Reporte de ventas
  ventas: {
    titulo: 'Reporte de ventas',
    async pintar(p) {
      const r = await api('GET', `/reportes/ventas?${p}`);
      const s = r.resumen;
      return [
        crear('div', { className: 'resumen' }, [
          tarjeta('receipt_long', 'Ventas', String(s.ventas)),
          tarjeta('payments', 'Total vendido', formato.dinero(s.total)),
          tarjeta('trending_up', 'Ganancia', formato.dinero(s.ganancia), `Margen ${s.margen} %`),
          tarjeta('shopping_bag', 'Ticket promedio', formato.dinero(s.ticket_promedio)),
        ]),
        panel('Ventas por día', graficaBarras(r.por_dia.map((d) => ({ etiqueta: diaCorto(d.fecha), valor: d.total })))),
        crear('div', { className: 'dos-columnas paneles' }, [
          panel('Por método de pago', barrasHorizontales(Object.entries(r.por_metodo).map(([m, v]) => [METODOS[m], v]))),
          panel('Por tipo de pedido', barrasHorizontales(Object.entries(r.por_tipo).map(([t, d]) => [`${TIPOS[t]} (${d.ventas})`, d.total]))),
        ]),
        panel('Detalle por día', crear('p', { className: 'nota', texto: 'Solo los días con ventas.' }), tabla('ventas-por-dia', [
          { titulo: 'Fecha', valor: (f) => f.fecha },
          { titulo: 'Ventas', valor: (f) => f.ventas, numero: true },
          { titulo: 'Total', valor: (f) => formato.dinero(f.total), numero: true },
          { titulo: 'Ganancia', valor: (f) => formato.dinero(f.ganancia), numero: true },
        ], r.por_dia.filter((d) => d.ventas > 0))),
      ];
    },
  },

  // RF-11.1 Reporte de inventario
  inventario: {
    titulo: 'Reporte de inventario',
    async pintar(p) {
      const r = await api('GET', `/reportes/inventario?${p}`);
      const s = r.resumen;
      return [
        crear('div', { className: 'resumen' }, [
          tarjeta('inventory_2', 'Insumos activos', String(s.insumos)),
          tarjeta('payments', 'Valor del inventario', formato.dinero(s.valor_total)),
          tarjeta('trending_down', 'En el mínimo', String(s.bajos)),
          tarjeta('block', 'Agotados', String(s.agotados)),
        ]),
        tabla('inventario', [
          { titulo: 'Código', valor: (f) => f.codigo },
          { titulo: 'Insumo', valor: (f) => f.insumo },
          { titulo: 'Stock', valor: (f) => `${formato.cantidad(f.stock_actual)} ${f.unidad_medida}`, numero: true },
          { titulo: 'Mínimo', valor: (f) => formato.cantidad(f.stock_minimo), numero: true },
          { titulo: 'Estado', valor: (f) => ESTADOS[f.estado_stock] },
          { titulo: 'Valor', valor: (f) => formato.dinero(f.valor), numero: true },
          { titulo: 'Entradas', valor: (f) => formato.cantidad(f.entradas), numero: true },
          { titulo: 'Consumo', valor: (f) => formato.cantidad(f.consumo), numero: true },
          { titulo: 'Merma', valor: (f) => formato.cantidad(f.merma), numero: true },
        ], r.insumos),
      ];
    },
  },

  // RF-11.3 Reporte de consumo
  consumo: {
    titulo: 'Reporte de consumo de insumos',
    async pintar(p) {
      const r = await api('GET', `/reportes/consumo?${p}`);
      return [
        crear('div', { className: 'resumen' }, [
          tarjeta('restaurant', 'Costo del consumo en ventas', formato.dinero(r.resumen.costo_consumo)),
          tarjeta('delete', 'Costo de las mermas', formato.dinero(r.resumen.costo_merma)),
        ]),
        tabla('consumo', [
          { titulo: 'Insumo', valor: (f) => f.insumo },
          { titulo: 'Consumo', valor: (f) => `${formato.cantidad(f.consumo)} ${f.unidad_medida}`, numero: true },
          { titulo: 'Costo consumo', valor: (f) => formato.dinero(f.costo_consumo), numero: true },
          { titulo: 'Merma', valor: (f) => `${formato.cantidad(f.merma)} ${f.unidad_medida}`, numero: true },
          { titulo: 'Costo merma', valor: (f) => formato.dinero(f.costo_merma), numero: true },
        ], r.insumos),
      ];
    },
  },

  // RF-11.4 Productos más vendidos
  productos: {
    titulo: 'Productos más vendidos',
    async pintar(p) {
      const r = await api('GET', `/reportes/productos?${p}`);
      const partes = [
        panel('Unidades vendidas', graficaBarras(r.vendidos.slice(0, 10).map((v) => ({ etiqueta: v.producto.slice(0, 12), valor: v.cantidad })),
          (n) => `${n} und.`)),
        tabla('productos-mas-vendidos', [
          { titulo: 'Producto', valor: (f) => f.producto },
          { titulo: 'Unidades', valor: (f) => f.cantidad, numero: true },
          { titulo: 'Ingresos', valor: (f) => formato.dinero(f.total), numero: true },
          { titulo: 'Margen', valor: (f) => `${f.margen} %`, numero: true },
        ], r.vendidos),
      ];
      if (r.sin_ventas.length) {
        partes.push(panel('Productos de la carta sin ventas en el periodo',
          crear('p', { texto: r.sin_ventas.join(' · ') })));
      }
      return partes;
    },
  },

  // RF-11.5 Información histórica
  historico: {
    titulo: 'Información histórica (últimos 12 meses)',
    sinFechas: true,
    async pintar() {
      const meses = await api('GET', '/reportes/historico?meses=12');
      return [
        panel('Ventas por mes', graficaBarras(meses.map((m) => ({ etiqueta: m.mes.split(' ')[0], valor: m.total })))),
        tabla('historico', [
          { titulo: 'Mes', valor: (f) => f.mes },
          { titulo: 'Ventas', valor: (f) => f.ventas, numero: true },
          { titulo: 'Total', valor: (f) => formato.dinero(f.total), numero: true },
          { titulo: 'Ganancia', valor: (f) => formato.dinero(f.ganancia), numero: true },
          { titulo: 'Compras recibidas', valor: (f) => formato.dinero(f.compras), numero: true },
          { titulo: 'Domicilios entregados', valor: (f) => f.domicilios, numero: true },
        ], meses),
      ];
    },
  },

  // RF-11.7 Domicilios por domiciliario: cuántos hizo cada uno y cuáles fueron
  domicilios: {
    titulo: 'Domicilios por domiciliario',
    async pintar(p) {
      if (filtroDomiciliario.id !== '') p.set('domiciliario_id', filtroDomiciliario.id);
      const { resumen: r, por_domiciliario: personas, domicilios } = await api('GET', `/reportes/domicilios?${p}`);
      const lider = personas.find((f) => f.domiciliario_id !== 0 && f.entregados > 0);
      const quitar = filtroDomiciliario.id === '' ? [] : [(() => {
        const boton = crear('button', { type: 'button', className: 'chip filtro', 'aria-pressed': 'true', title: 'Quitar este filtro' }, [
          crear('span', { texto: filtroDomiciliario.nombre }), crear('span', { className: 'icono', texto: 'close', 'aria-hidden': 'true' }),
        ]);
        boton.addEventListener('click', () => { Object.assign(filtroDomiciliario, { id: '', nombre: '' }); generar(); });
        return crear('div', { className: 'categorias' }, [boton]);
      })()];
      const barras = personas.length === 0 ? crear('p', { className: 'nota', texto: 'Sin domicilios en este periodo.' })
        : crear('ul', { className: 'barras' }, personas.map((f) => {
          const maximo = Math.max(...personas.map((x) => x.total), 1);
          const barra = crear('div', { className: 'barra-progreso' });
          barra.style.width = `${Math.max(4, (f.total / maximo) * 100)}%`;
          const plural = (n, palabra) => `${n} ${palabra}${n === 1 ? '' : 's'}`;
          const detalle = `${plural(f.entregados, 'entregado')} · ${f.en_curso} en curso` + (f.cancelados ? ` · ${plural(f.cancelados, 'cancelado')}` : '');
          const fila = crear('li', { className: 'barra-filtrable', tabindex: '0', title: 'Ver solo sus domicilios' }, [
            crear('div', { className: 'barra-texto' }, [crear('span', { texto: f.nombre }), crear('span', { texto: detalle })]),
            barra,
          ]);
          const elegir = () => { Object.assign(filtroDomiciliario, { id: String(f.domiciliario_id), nombre: f.nombre }); generar(); };
          fila.addEventListener('click', elegir);
          fila.addEventListener('keydown', (e) => { if (e.key === 'Enter') elegir(); });
          return fila;
        }));
      return [
        ...quitar,
        crear('div', { className: 'resumen' }, [
          tarjeta('delivery_dining', 'Domicilios', String(r.total), `${r.en_curso} en curso · ${r.cancelados} cancelados`),
          tarjeta('task_alt', 'Entregados', String(r.entregados), formato.dinero(r.valor_entregado)),
          tarjeta('timer', 'Tiempo promedio de entrega', r.minutos_promedio === null ? '—' : r.minutos_promedio < 1 ? 'menos de 1 min' : `${r.minutos_promedio} min`, 'De la salida a la entrega'),
          tarjeta('emoji_events', 'Más entregas', lider ? lider.nombre : '—', lider ? `${lider.entregados} ${lider.entregados === 1 ? 'entregado' : 'entregados'}` : ''),
        ]),
        panel('Domicilios por domiciliario', barras),
        panel('Cuáles fueron', tabla('domicilios', [
          { titulo: 'Fecha', valor: (f) => fechaHora(f.fecha) },
          { titulo: 'Pedido', valor: (f) => f.codigo },
          { titulo: 'Domiciliario', valor: (f) => f.domiciliario ?? 'Sin asignar' },
          { titulo: 'Cliente', valor: (f) => f.cliente.nombre },
          { titulo: 'Dirección', valor: (f) => [f.direccion, f.barrio].filter(Boolean).join(' · ') },
          { titulo: 'Estado', valor: (f) => ESTADOS_DOMICILIO[f.estado] ?? f.estado },
          { titulo: 'Total', valor: (f) => formato.dinero(f.total), numero: true },
          { titulo: 'Recibió', valor: (f) => f.recibido_por ?? '—' },
        ], domicilios)),
      ];
    },
  },

  // RF-12.4 Bitácora de incidencias: errores reportados desde inventario, ventas y compras
  incidencias: {
    titulo: 'Incidencias: errores registrados',
    async pintar(p) {
      if (filtroIncidencias.modulo) p.set('modulo', filtroIncidencias.modulo);
      if (filtroIncidencias.campo) p.set(filtroIncidencias.campo, filtroIncidencias.valor);
      const [{ incidencias, resumen: r }, codigos] = await Promise.all([
        api('GET', `/incidencias?${p}`),
        api('GET', '/codigos-incidencia?todos=true'),
      ]);
      const tipo = r.por_tipo[0];
      const quien = r.por_usuario[0];
      return [
        filtrosIncidencias(),
        crear('div', { className: 'resumen' }, [
          tarjeta('report', 'Incidencias', String(r.total)),
          tarjeta('build', 'Corregidas en inventario', String(r.corregidas)),
          tarjeta('category', 'Error más común', tipo ? tipo.codigo : '—', tipo ? `${tipo.nombre} · ${tipo.total}` : ''),
          tarjeta('person', 'Comete más errores', quien ? quien.nombre : '—',
            quien ? `${quien.total} ${quien.total === 1 ? 'incidencia' : 'incidencias'}` : ''),
        ]),
        crear('div', { className: 'dos-columnas paneles' }, [
          panel('Quién comete más errores', barrasFiltrables(r.por_usuario, 'responsable_id', (u) => u.usuario_id, (u) => u.nombre)),
          panel('Errores más comunes', barrasFiltrables(r.por_tipo, 'codigo_id',
            (t) => codigos.find((c) => c.codigo === t.codigo)?.id ?? '', (t) => `${t.codigo} · ${t.nombre}`)),
        ]),
        panel('Todas las incidencias',
          crear('p', { className: 'nota', texto: 'Se reportan con «Reportar un error» en el historial de cada insumo, el detalle de una venta o el de una orden de compra.' }),
          tabla('incidencias', [
            { titulo: 'Fecha', valor: (f) => fechaHora(f.fecha) },
            { titulo: 'Error', valor: (f) => `${f.tipo.codigo} · ${f.tipo.nombre}` },
            { titulo: 'Observación', valor: (f) => f.observacion },
            { titulo: 'Registro', valor: (f) => f.registro },
            { titulo: 'Responsable', valor: (f) => f.responsable },
            { titulo: 'Reportó', valor: (f) => f.reportado_por },
            { titulo: 'Ajuste', valor: (f) => (f.ajuste ? `${f.ajuste.tipo === 'ENTRADA' ? '+' : '−'}${formato.cantidad(f.ajuste.cantidad)}` : '—'), numero: true },
            { titulo: 'Incidencia', valor: (f) => f.codigo },
          ], incidencias)),
        ...(puedeGestionarCodigos ? [catalogoCodigos(codigos)] : []),
      ];
    },
  },
};

const NOMBRES_PESTANA = {
  estadisticas: 'Estadísticas', ventas: 'Ventas', inventario: 'Inventario',
  consumo: 'Consumo', productos: 'Más vendidos', domicilios: 'Domicilios', historico: 'Histórico',
  ...(puedeVerIncidencias ? { incidencias: 'Incidencias' } : {}),
};

// =====================================================================
//  RF-12.4 Incidencias: filtros, barras que filtran y RF-12.1 catálogo de códigos
// =====================================================================

// RF-11.7 Filtro por domiciliario y nombres de los estados del domicilio
const filtroDomiciliario = { id: '', nombre: '' };
const ESTADOS_DOMICILIO = {
  RECIBIDO: 'Recibido', EN_PREPARACION: 'En preparación', LISTO: 'Listo',
  EN_CAMINO: 'En camino', ENTREGADO: 'Entregado', CANCELADO: 'Cancelado',
};

const MODULOS_INCIDENCIA = { INVENTARIO: 'Inventario', VENTAS: 'Ventas', COMPRAS: 'Compras', OTRO: 'Otro' };
const filtroIncidencias = { modulo: '', campo: '', valor: '', texto: '' };
let catalogoAbierto = false;
const fechaHora = (texto) => new Date(texto).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

/** Chips por módulo y, si se tocó una barra, el filtro activo con su X para quitarlo. */
function filtrosIncidencias() {
  const chips = [['', 'Todos'], ...Object.entries(MODULOS_INCIDENCIA)].map(([valor, texto]) => {
    const boton = crear('button', { type: 'button', className: 'chip filtro', texto, 'aria-pressed': String(valor === filtroIncidencias.modulo) });
    boton.addEventListener('click', () => { filtroIncidencias.modulo = valor; generar(); });
    return boton;
  });
  if (filtroIncidencias.campo) {
    const quitar = crear('button', { type: 'button', className: 'chip filtro', 'aria-pressed': 'true', title: 'Quitar este filtro' }, [
      crear('span', { texto: filtroIncidencias.texto }), crear('span', { className: 'icono', texto: 'close', 'aria-hidden': 'true' }),
    ]);
    quitar.addEventListener('click', () => { Object.assign(filtroIncidencias, { campo: '', valor: '', texto: '' }); generar(); });
    chips.push(quitar);
  }
  return crear('div', { className: 'categorias', role: 'group', 'aria-label': 'Filtrar incidencias' }, chips);
}

/** Barras proporcionales; tocar una deja la bitácora solo con ese responsable o ese tipo de error. */
function barrasFiltrables(lista, campo, valor, texto) {
  if (lista.length === 0) return crear('p', { className: 'nota', texto: 'Sin incidencias en este periodo.' });
  const maximo = lista[0].total;
  return crear('ul', { className: 'barras' }, lista.map((item) => {
    const barra = crear('div', { className: 'barra-progreso' });
    barra.style.width = `${Math.max(4, (item.total / maximo) * 100)}%`;
    const fila = crear('li', { className: 'barra-filtrable', tabindex: '0', title: 'Ver solo estas incidencias' }, [
      crear('div', { className: 'barra-texto' }, [crear('span', { texto: texto(item) }), crear('span', { texto: String(item.total) })]),
      barra,
    ]);
    const elegir = () => { Object.assign(filtroIncidencias, { campo, valor: valor(item), texto: texto(item) }); generar(); };
    fila.addEventListener('click', elegir);
    fila.addEventListener('keydown', (e) => { if (e.key === 'Enter') elegir(); });
    return fila;
  }));
}

/** RF-12.1 Catálogo de códigos: activar o desactivar y agregar nuevos (plegable, al final de la pestaña). */
function catalogoCodigos(codigos) {
  const lista = crear('ul', { className: 'mini-lista' }, codigos.map((c) => {
    const interruptor = crear('input', { type: 'checkbox', 'aria-label': `Código ${c.codigo} activo` });
    interruptor.checked = c.activo;
    interruptor.addEventListener('change', async () => {
      try {
        await api('PUT', `/codigos-incidencia/${c.id}`, { activo: interruptor.checked });
        mostrarAviso(`${c.codigo} ${interruptor.checked ? 'activado' : 'desactivado'}`, 'exito');
      } catch (error) {
        interruptor.checked = !interruptor.checked;
        mostrarAviso(error.message, 'error');
      }
    });
    return crear('li', {}, [
      crear('span', { texto: `${c.codigo} · ${c.nombre}` }),
      crear('label', { className: 'interruptor compacto' }, [crear('span', { className: 'nota', texto: MODULOS_INCIDENCIA[c.modulo] }), interruptor]),
    ]);
  }));
  const codigo = crear('input', { id: 'c-codigo', placeholder: 'INV-05', maxlength: '6', 'aria-label': 'Código', autocomplete: 'off' });
  const nombre = crear('input', { id: 'c-nombre', placeholder: 'Nombre del error', maxlength: '120', 'aria-label': 'Nombre del error', autocomplete: 'off' });
  const modulo = crear('select', { id: 'c-modulo', 'aria-label': 'Módulo' },
    Object.entries(MODULOS_INCIDENCIA).map(([valor, texto]) => crear('option', { value: valor, texto })));
  const error = crear('div', { className: 'alerta-error', role: 'alert', hidden: '' });
  const formulario = crear('form', { className: 'nuevo-codigo', novalidate: '' }, [
    crear('div', { className: 'campo' }, [codigo]),
    crear('div', { className: 'campo' }, [nombre]),
    crear('div', { className: 'campo' }, [modulo]),
    crear('button', { type: 'submit', className: 'boton-principal' }, [
      crear('span', { className: 'icono', texto: 'add', 'aria-hidden': 'true' }), document.createTextNode(' Agregar'),
    ]),
  ]);
  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    error.hidden = true;
    try {
      const nuevo = await api('POST', '/codigos-incidencia', { codigo: codigo.value.trim(), nombre: nombre.value.trim(), modulo: modulo.value });
      mostrarAviso(`Código ${nuevo.codigo} agregado`, 'exito');
      generar();
    } catch (excepcion) {
      error.textContent = excepcion.message;
      error.hidden = false;
    }
  });
  const plegable = crear('details', { className: 'panel catalogo' }, [
    crear('summary', {}, [crear('span', { className: 'icono', texto: 'tune', 'aria-hidden': 'true' }), document.createTextNode(' Catálogo de códigos de error')]),
    lista, formulario, error,
  ]);
  plegable.open = catalogoAbierto;
  plegable.addEventListener('toggle', () => { catalogoAbierto = plegable.open; });
  return plegable;
}

// =====================================================================
//  Periodo, pestañas, descarga e impresión
// =====================================================================

const iso = (fecha) => fecha.toLocaleDateString('en-CA'); // AAAA-MM-DD en hora local
const haceDias = (n) => new Date(Date.now() - n * 24 * 3600 * 1000);

function ponerPeriodo(desde, hasta) {
  $('desde').value = iso(desde);
  $('hasta').value = iso(hasta);
}

const ATAJOS = {
  Hoy: () => ponerPeriodo(new Date(), new Date()),
  '7 días': () => ponerPeriodo(haceDias(6), new Date()),
  '30 días': () => ponerPeriodo(haceDias(29), new Date()),
  'Este mes': () => {
    const hoy = new Date();
    ponerPeriodo(new Date(hoy.getFullYear(), hoy.getMonth(), 1), hoy);
  },
};

/** Marca el atajo que coincide con las fechas elegidas (recomendación de la docente: que se vea cuál está activo). */
function marcarAtajo() {
  const actual = `${$('desde').value}|${$('hasta').value}`;
  for (const boton of $('atajos').children) {
    const desde = $('desde').value;
    const hasta = $('hasta').value;
    ATAJOS[boton.textContent]();
    boton.setAttribute('aria-pressed', String(`${$('desde').value}|${$('hasta').value}` === actual));
    $('desde').value = desde;
    $('hasta').value = hasta;
  }
}

$('atajos').replaceChildren(...Object.entries(ATAJOS).map(([texto, aplicar]) => {
  const boton = crear('button', { type: 'button', className: 'chip filtro', texto, 'aria-pressed': 'false' });
  boton.addEventListener('click', () => {
    aplicar();
    generar();
  });
  return boton;
}));
$('desde').addEventListener('change', marcarAtajo);
$('hasta').addEventListener('change', marcarAtajo);

let reporteActual = 'estadisticas';

$('pestanas').replaceChildren(...Object.entries(NOMBRES_PESTANA).map(([clave, texto]) => {
  const boton = crear('button', { type: 'button', role: 'tab', texto, 'aria-selected': String(clave === reporteActual) });
  boton.addEventListener('click', () => {
    reporteActual = clave;
    for (const otro of $('pestanas').children) otro.setAttribute('aria-selected', String(otro === boton));
    generar();
  });
  return boton;
}));

async function generar() {
  const reporte = REPORTES[reporteActual];
  marcarAtajo();
  const parametros = new URLSearchParams({ desde: $('desde').value, hasta: $('hasta').value });
  $('titulo-reporte').textContent = reporte.titulo;
  $('periodo').textContent = reporte.sinFechas ? ''
    : `Del ${formato.fecha($('desde').value)} al ${formato.fecha($('hasta').value)}`;
  $('error').hidden = true;
  if (empezarCarga($('contenido-reporte'))) {
    pintarSuave($('contenido-reporte'), crear('p', { className: 'nota', texto: 'Generando…' }));
  }
  tablaActual = { nombre: reporteActual, columnas: [], filas: [] };
  try {
    pintarSuave($('contenido-reporte'), ...await reporte.pintar(parametros));
  } catch (error) {
    pintarSuave($('contenido-reporte'));
    $('error').textContent = error.message;
    $('error').hidden = false;
  }
  $('descargar').hidden = tablaActual.filas.length === 0;
}

/** Descarga la tabla del reporte como CSV (se abre en Excel). */
$('descargar').addEventListener('click', () => {
  const { nombre, columnas, filas } = tablaActual;
  const celda = (valor) => `"${String(valor ?? '').replace(/"/g, '""')}"`;
  const lineas = [columnas.map((c) => celda(c.titulo)).join(';'),
    ...filas.map((f) => columnas.map((c) => celda(c.valor(f))).join(';'))];
  // El BOM (\uFEFF) hace que Excel lea bien las tildes; ";" es el separador en Excel en español
  const archivo = new Blob([`\uFEFF${lineas.join('\r\n')}`], { type: 'text/csv;charset=utf-8' });
  const enlace = crear('a', { href: URL.createObjectURL(archivo), download: `stockpot-${nombre}-${$('desde').value}.csv` });
  enlace.click();
  URL.revokeObjectURL(enlace.href);
});

$('imprimir').addEventListener('click', () => window.print());
$('form-fechas').addEventListener('submit', (evento) => {
  evento.preventDefault();
  generar();
});

ponerPeriodo(haceDias(29), new Date());
generar();
