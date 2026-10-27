// Módulo de ventas y consumo (RF-10.2 a RF-10.6).
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, pintarSuave } from './ui.js';

const yo = await exigirSesion('ventas.ver'); // sin el permiso vuelve al menú
const puedeVerComprobantes = yo.permisos.includes('pagos.ver');

const $ = (id) => document.getElementById(id);
const TIPOS = { DOMICILIO: 'Domicilio', MESA: 'Mesa', LLEVAR: 'Para llevar' };

function fechaHora(iso) {
  return new Date(iso).toLocaleString('es-CO', {
    day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  });
}

function tarjetaResumen(icono, titulo, valor) {
  return crear('div', { className: 'tarjeta-resumen' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
  ]);
}

// Por defecto: los últimos 7 días
const iso = (fecha) => fecha.toLocaleDateString('en-CA'); // AAAA-MM-DD en hora local
$('desde').value = iso(new Date(Date.now() - 6 * 24 * 3600 * 1000));
$('hasta').value = iso(new Date());

async function cargar() {
  const parametros = new URLSearchParams({ desde: $('desde').value, hasta: $('hasta').value });
  if (empezarCarga($('lista'))) {
    $('estado').hidden = false;
    $('estado').textContent = 'Cargando…';
  }
  try {
    const [{ resumen, ventas }, masVendidos, consumo] = await Promise.all([
      api('GET', `/ventas?${parametros}`),
      api('GET', `/ventas/mas-vendidos?${parametros}`),
      api('GET', `/ventas/consumo?${parametros}`),
    ]);
    pintarResumen(resumen);
    pintarMasVendidos(masVendidos);
    pintarConsumo(consumo);
    pintarVentas(ventas);
  } catch (error) {
    $('estado').textContent = error.message;
  }
}

// RF-10.2 Totales del periodo
function pintarResumen(r) {
  pintarSuave($('resumen'),
    tarjetaResumen('receipt_long', 'Ventas', String(r.ventas)),
    tarjetaResumen('payments', 'Total vendido', formato.dinero(r.total)),
    tarjetaResumen('shopping_bag', 'Ticket promedio', formato.dinero(r.ticket_promedio)),
    tarjetaResumen('trending_up', 'Ganancia (sin insumos)', formato.dinero(r.ganancia)),
  );
}

// RF-10.5 Más vendidos: barras proporcionales al más vendido
function pintarMasVendidos(lista) {
  if (lista.length === 0) {
    pintarSuave($('mas-vendidos'), crear('li', { className: 'nota', texto: 'Sin ventas en el periodo' }));
    return;
  }
  const maximo = lista[0].cantidad;
  pintarSuave($('mas-vendidos'), ...lista.map((p) => {
    const barra = crear('div', { className: 'barra-progreso' });
    barra.style.width = `${Math.max(4, (p.cantidad / maximo) * 100)}%`;
    return crear('li', {}, [
      crear('div', { className: 'barra-texto' }, [
        crear('span', { texto: p.producto }),
        crear('span', { texto: `${p.cantidad} · ${formato.dinero(p.total)}` }),
      ]),
      barra,
    ]);
  }));
}

// RF-10.6 Consumo de insumos del periodo
function pintarConsumo({ insumos, costo_total: costoTotal }) {
  pintarSuave($('consumo'), ...(insumos.length ? insumos.map((i) => crear('li', {}, [
    crear('span', { texto: `${i.insumo} · ${formato.cantidad(i.cantidad)} ${i.unidad_medida}` }),
    crear('span', { texto: formato.dinero(i.costo) }),
  ])) : [crear('li', { className: 'nota', texto: 'Sin consumo en el periodo' })]));
  $('consumo-total').textContent = insumos.length ? `Costo total: ${formato.dinero(costoTotal)}` : '';
}

function pintarVentas(ventas) {
  $('estado').hidden = ventas.length > 0;
  $('estado').textContent = 'No hay ventas en esas fechas';
  pintarSuave($('lista'), ...ventas.map((venta) => {
    const detalle = [venta.orden, TIPOS[venta.tipo], venta.cliente, fechaHora(venta.fecha)].filter(Boolean).join(' · ');
    const fila = crear('li', { className: 'fila editable' }, [
      crear('div', { className: 'avatar' }, [crear('span', { className: 'icono', texto: 'point_of_sale', 'aria-hidden': 'true' })]),
      crear('div', { className: 'datos' }, [
        crear('div', { className: 'nombre', texto: venta.codigo }),
        crear('div', { className: 'correo', texto: detalle }),
      ]),
      crear('div', { className: 'chips' }, [crear('span', { className: 'chip', texto: formato.dinero(venta.total) })]),
    ]);
    fila.addEventListener('click', () => abrirVenta(venta.id));
    return fila;
  }));
}

$('form-fechas').addEventListener('submit', (evento) => {
  evento.preventDefault();
  cargar();
});

// =====================================================================
//  RF-10.4 Detalle de la venta (productos) y RF-10.3 su consumo
// =====================================================================

const dialogo = $('dialogo-venta');
let ventaAbierta = null;

async function abrirVenta(id) {
  try {
    const venta = await api('GET', `/ventas/${id}`);
    ventaAbierta = venta;
    $('venta-titulo').textContent = `${venta.codigo} · ${formato.dinero(venta.total)}`;
    const datos = [
      ['Pedido', `${venta.orden} (${TIPOS[venta.tipo]})`],
      ['Fecha', fechaHora(venta.fecha)],
      ['Cliente', venta.cliente],
      ['Cobró', venta.usuario],
      ['Pagos', venta.pagos.map((p) => `${p.metodo.toLowerCase()} ${formato.dinero(p.monto)}`).join(' + ')],
      ['Costo de insumos', formato.dinero(venta.costo_insumos)],
      ['Ganancia', formato.dinero(venta.ganancia)],
    ].filter(([, valor]) => valor);
    pintarSuave($('venta-datos'), ...datos.flatMap(([t, v]) => [crear('dt', { texto: t }), crear('dd', { texto: v })]));
    pintarSuave($('venta-productos'), ...venta.productos.map((d) => crear('li', {}, [
      crear('span', { texto: `${d.cantidad} × ${d.producto}` }), crear('span', { texto: formato.dinero(d.subtotal) }),
    ])));
    pintarSuave($('venta-consumos'), ...(venta.consumos.length ? venta.consumos.map((c) => crear('li', {}, [
      crear('span', { texto: `${c.insumo} · ${formato.cantidad(c.cantidad)} ${c.unidad_medida}` }),
      crear('span', { texto: formato.dinero(c.costo) }),
    ])) : [crear('li', { className: 'nota', texto: 'Sus productos no tienen receta' })]));
    $('ver-comprobante').hidden = !puedeVerComprobantes;
    dialogo.showModal();
  } catch (error) {
    mostrarAviso(error.message);
  }
}

$('cerrar-venta').addEventListener('click', () => dialogo.close());
$('ver-comprobante').addEventListener('click', () => {
  window.open(`comprobante.html?orden=${ventaAbierta.orden_id}`, '_blank');
});

cargar();
