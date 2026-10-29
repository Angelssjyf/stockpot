// Módulo de incidencias: RF-12.4 Bitácora del administrador y RF-12.1 Catálogo de códigos.
// Los errores se reportan desde inventario, ventas y compras (js/reportar.js).
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, mostrarEstado, pintarSuave } from './ui.js';

const yo = await exigirSesion('incidencias.ver'); // solo el ADMINISTRADOR
const puedeGestionar = yo.permisos.includes('incidencias.gestionar');

const $ = (id) => document.getElementById(id);
const MODULOS = { INVENTARIO: 'Inventario', VENTAS: 'Ventas', COMPRAS: 'Compras', OTRO: 'Otro' };
const ICONOS = { INVENTARIO: 'inventory_2', VENTAS: 'point_of_sale', COMPRAS: 'shopping_cart', OTRO: 'report' };

// Filtros: fechas (últimos 30 días), módulo y, al tocar una barra, un responsable o un tipo de error
const hoy = new Date();
const hace30 = new Date(hoy.getTime() - 29 * 86400000);
const iso = (fecha) => fecha.toLocaleDateString('en-CA'); // AAAA-MM-DD en la hora local
$('desde').value = iso(hace30);
$('hasta').value = iso(hoy);
let moduloElegido = '';
let filtro = null; // { campo: 'responsable_id' | 'codigo_id', valor, texto }
let codigos = [];

const fechaHora = (texto) => new Date(texto).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

function pintarModulos() {
  const opciones = [['', 'Todos'], ...Object.entries(MODULOS)];
  $('modulos').replaceChildren(...opciones.map(([valor, texto]) => {
    const boton = crear('button', { type: 'button', className: 'chip filtro', texto, 'aria-pressed': String(valor === moduloElegido) });
    boton.addEventListener('click', () => { moduloElegido = valor; pintarModulos(); cargar(); });
    return boton;
  }));
}

function pintarFiltroActivo() {
  $('filtro-activo').hidden = !filtro;
  if (!filtro) return;
  const quitar = crear('button', { type: 'button', className: 'chip filtro', 'aria-pressed': 'true' }, [
    crear('span', { texto: filtro.texto }), crear('span', { className: 'icono', texto: 'close', 'aria-hidden': 'true' }),
  ]);
  quitar.addEventListener('click', () => { filtro = null; pintarFiltroActivo(); cargar(); });
  $('filtro-activo').replaceChildren(quitar);
}

async function cargar() {
  if (empezarCarga($('lista'))) mostrarEstado('Cargando…', { cargando: true });
  const parametros = new URLSearchParams({ desde: $('desde').value, hasta: $('hasta').value, modulo: moduloElegido });
  if (filtro) parametros.set(filtro.campo, filtro.valor);
  try {
    const { incidencias, resumen } = await api('GET', `/incidencias?${parametros}`);
    pintarResumen(resumen);
    pintarBarras(resumen);
    if (incidencias.length === 0) {
      mostrarEstado(filtro || moduloElegido ? 'No hay incidencias con esos filtros' : 'No hay incidencias en estas fechas', {
        icono: 'task_alt',
        detalle: 'Los errores se reportan desde el historial de cada insumo, el detalle de una venta o una orden de compra.',
      });
      pintarSuave($('lista'));
    } else {
      $('estado').hidden = true;
      pintarSuave($('lista'), ...incidencias.map(filaDeIncidencia));
    }
  } catch (error) {
    mostrarEstado(error.message, { reintentar: true });
  }
}

function tarjeta(icono, titulo, valor, detalle) {
  return crear('div', { className: 'tarjeta-resumen' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
    ...(detalle ? [crear('small', { className: 'nota', texto: detalle })] : []),
  ]);
}

function pintarResumen(r) {
  const tipo = r.por_tipo[0];
  const quien = r.por_usuario[0];
  pintarSuave($('resumen'),
    tarjeta('report', 'Incidencias', String(r.total)),
    tarjeta('build', 'Corregidas en inventario', String(r.corregidas)),
    tarjeta('category', 'Error más común', tipo ? tipo.codigo : '—', tipo ? `${tipo.nombre} · ${tipo.total}` : ''),
    tarjeta('person', 'Comete más errores', quien ? quien.nombre : '—', quien ? `${quien.total} ${quien.total === 1 ? 'incidencia' : 'incidencias'}` : ''));
}

/** Barras proporcionales; tocar una filtra la lista por ese responsable o ese tipo de error. */
function barras(lista, campo, valor, texto) {
  if (lista.length === 0) return [crear('li', { className: 'nota', texto: 'Sin incidencias' })];
  const maximo = lista[0].total;
  return lista.map((item) => {
    const barra = crear('div', { className: 'barra-progreso' });
    barra.style.width = `${Math.max(4, (item.total / maximo) * 100)}%`;
    const fila = crear('li', { className: 'barra-filtrable', tabindex: '0', title: 'Ver solo estas incidencias' }, [
      crear('div', { className: 'barra-texto' }, [crear('span', { texto: texto(item) }), crear('span', { texto: String(item.total) })]),
      barra,
    ]);
    const elegir = () => { filtro = { campo, valor: valor(item), texto: texto(item) }; pintarFiltroActivo(); cargar(); };
    fila.addEventListener('click', elegir);
    fila.addEventListener('keydown', (e) => { if (e.key === 'Enter') elegir(); });
    return fila;
  });
}

function pintarBarras(r) {
  pintarSuave($('por-usuario'), ...barras(r.por_usuario, 'responsable_id', (u) => u.usuario_id, (u) => u.nombre));
  pintarSuave($('por-tipo'), ...barras(r.por_tipo, 'codigo_id',
    (t) => codigos.find((c) => c.codigo === t.codigo)?.id ?? '', (t) => `${t.codigo} · ${t.nombre}`));
}

function filaDeIncidencia(i) {
  const chips = [crear('span', { className: 'chip', texto: MODULOS[i.tipo.modulo] })];
  if (i.ajuste) {
    const signo = i.ajuste.tipo === 'ENTRADA' ? '+' : '−';
    chips.push(crear('span', { className: 'chip estado-OK', texto: `Corregida ${signo}${formato.cantidad(i.ajuste.cantidad)}` }));
  }
  return crear('li', { className: 'fila incidencia', 'data-clave': i.id }, [
    crear('div', { className: 'avatar' }, [crear('span', { className: 'icono', texto: ICONOS[i.tipo.modulo], 'aria-hidden': 'true' })]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: `${i.tipo.codigo} · ${i.tipo.nombre}` }),
      crear('div', { className: 'correo', texto: `${i.codigo} · ${i.registro}` }),
      crear('p', { className: 'observacion', texto: `«${i.observacion}»` }),
      crear('small', { className: 'nota', texto: `Responsable: ${i.responsable} · Reportó: ${i.reportado_por} · ${fechaHora(i.fecha)}` }),
    ]),
    crear('div', { className: 'chips' }, chips),
  ]);
}

$('form-fechas').addEventListener('submit', (evento) => { evento.preventDefault(); cargar(); });
$('reintentar').addEventListener('click', cargar);

// =====================================================================
//  RF-12.1 Catálogo de códigos
// =====================================================================

async function cargarCodigos() {
  codigos = await api('GET', '/codigos-incidencia?todos=true');
  if (!puedeGestionar) return;
  pintarSuave($('lista-codigos'), ...codigos.map((c) => {
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
    return crear('li', { 'data-clave': c.codigo }, [
      crear('span', { texto: `${c.codigo} · ${c.nombre}` }),
      crear('label', { className: 'interruptor compacto' }, [crear('span', { className: 'nota', texto: MODULOS[c.modulo] }), interruptor]),
    ]);
  }));
}

if (puedeGestionar) {
  $('catalogo').hidden = false;
  $('form-codigo').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    $('error-codigo').hidden = true;
    try {
      const nuevo = await api('POST', '/codigos-incidencia', {
        codigo: $('c-codigo').value.trim(), nombre: $('c-nombre').value.trim(), modulo: $('c-modulo').value,
      });
      $('form-codigo').reset();
      mostrarAviso(`Código ${nuevo.codigo} agregado`, 'exito');
      cargarCodigos();
    } catch (error) {
      $('error-codigo').textContent = error.message;
      $('error-codigo').hidden = false;
    }
  });
}

pintarModulos();
await cargarCodigos();
cargar();
