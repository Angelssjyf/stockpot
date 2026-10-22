// Módulo de reportes y estadísticas (RF-11.1 a RF-11.6).
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, pintarSuave } from './ui.js';

await exigirSesion('reportes.ver'); // solo el ADMINISTRADOR

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
  const ancho = 640;
  const alto = 220;
  const margen = { arriba: 16, abajo: 40, izquierda: 28 }; // a los lados caben las etiquetas
  const maximo = Math.max(...datos.map((d) => d.valor), 1);
  const paso = (ancho - margen.izquierda * 2) / datos.length;
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${ancho} ${alto}`);
  svg.setAttribute('class', 'grafica');
  svg.setAttribute('role', 'img');
  const cada = Math.ceil(datos.length / 12); // no más de 12 etiquetas abajo

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
    if (i % cada === 0) {
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
    barra.style.width = `${Math.max(2, (valor / maximo) * 100)}%`;
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
          tarjeta('receipt_long', 'Ventas por día', String(i.ventas_por_dia), `${i.ventas} ventas`),
          tarjeta('shopping_bag', 'Ticket promedio', formato.dinero(i.ticket_promedio)),
          tarjeta('star', 'Producto estrella', i.producto_estrella ?? '—'),
          tarjeta('event', 'Día de más ventas', i.dia_mas_ventas ?? '—'),
          tarjeta('schedule', 'Hora pico', i.hora_pico ?? '—'),
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
        panel('Detalle por día', tabla('ventas-por-dia', [
          { titulo: 'Fecha', valor: (f) => f.fecha },
          { titulo: 'Ventas', valor: (f) => f.ventas, numero: true },
          { titulo: 'Total', valor: (f) => formato.dinero(f.total), numero: true },
          { titulo: 'Ganancia', valor: (f) => formato.dinero(f.ganancia), numero: true },
        ], r.por_dia)),
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
};

const NOMBRES_PESTANA = {
  estadisticas: 'Estadísticas', ventas: 'Ventas', inventario: 'Inventario',
  consumo: 'Consumo', productos: 'Más vendidos', historico: 'Histórico',
};

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

$('atajos').replaceChildren(...Object.entries(ATAJOS).map(([texto, aplicar]) => {
  const boton = crear('button', { type: 'button', className: 'chip filtro', texto });
  boton.addEventListener('click', () => {
    aplicar();
    generar();
  });
  return boton;
}));

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
