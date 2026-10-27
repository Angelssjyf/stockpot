// Módulo de caja y pagos (RF-09.1 a RF-09.7) y venta de mostrador (RF-10.1).
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, pintarSuave } from './ui.js';

const yo = await exigirSesion('pagos.ver'); // sin el permiso vuelve al menú
const puedeCobrar = yo.permisos.includes('pagos.gestionar');

const $ = (id) => document.getElementById(id);

const METODOS = { EFECTIVO: 'Efectivo', TARJETA: 'Tarjeta', TRANSFERENCIA: 'Transferencia' };
const TIPOS = { DOMICILIO: 'Domicilio', MESA: 'Mesa', LLEVAR: 'Para llevar' };
const ESTADOS_PAGO = { PENDIENTE: 'Pendiente', PARCIAL: 'Pago parcial', PAGADO: 'Pagado' };

function fechaHora(iso) {
  return new Date(iso).toLocaleString('es-CO', {
    day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  });
}

function abrirComprobante(ordenId) {
  window.open(`comprobante.html?orden=${ordenId}`, '_blank');
}

function tarjetaResumen(icono, titulo, valor) {
  return crear('div', { className: 'tarjeta-resumen' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
  ]);
}

// =====================================================================
//  Formulario de pago (RF-09.2 método, monto, efectivo recibido y cambio)
//  Se usa en la cuenta de una orden y en la venta de mostrador.
// =====================================================================

/**
 * Pinta el formulario de pago dentro del contenedor.
 * montoFijo: función que devuelve el total a cobrar (mostrador), o null si el monto se edita.
 */
function formularioDePago(contenedor, { montoInicial = 0, montoFijo = null } = {}) {
  let metodo = 'EFECTIVO';
  const botones = crear('div', { className: 'categorias', role: 'group', 'aria-label': 'Método de pago' });
  const monto = crear('input', { type: 'number', min: '0', step: 'any', 'aria-label': 'Monto' });
  monto.value = montoInicial;
  const recibido = crear('input', { type: 'number', min: '0', step: 'any', 'aria-label': 'Efectivo recibido' });
  const referencia = crear('input', { autocomplete: 'off', maxlength: '60', 'aria-label': 'Referencia' });
  const cambio = crear('p', { className: 'cambio' });

  const bloqueMonto = crear('div', {}, [
    crear('label', { className: 'etiqueta', texto: 'Monto a pagar ($)' }), crear('div', { className: 'campo' }, [monto]),
  ]);
  const bloqueRecibido = crear('div', {}, [
    crear('label', { className: 'etiqueta', texto: 'Efectivo recibido ($)' }), crear('div', { className: 'campo' }, [recibido]),
  ]);
  const bloqueReferencia = crear('div', {}, [
    crear('label', { className: 'etiqueta', texto: 'Referencia (n.º de aprobación)' }),
    crear('div', { className: 'campo' }, [referencia]),
  ]);
  bloqueMonto.hidden = Boolean(montoFijo);

  const valorMonto = () => (montoFijo ? montoFijo() : Number(monto.value) || 0);

  function actualizar() {
    for (const boton of botones.children) {
      boton.setAttribute('aria-pressed', String(boton.dataset.metodo === metodo));
    }
    bloqueRecibido.hidden = metodo !== 'EFECTIVO';
    bloqueReferencia.hidden = metodo === 'EFECTIVO';
    const diferencia = (Number(recibido.value) || 0) - valorMonto();
    cambio.hidden = metodo !== 'EFECTIVO' || !recibido.value;
    cambio.textContent = diferencia >= 0 ? `Cambio: ${formato.dinero(diferencia)}`
      : `Faltan ${formato.dinero(-diferencia)}`;
    cambio.classList.toggle('falta', diferencia < 0);
  }

  for (const [valor, texto] of Object.entries(METODOS)) {
    const boton = crear('button', { type: 'button', className: 'chip filtro', texto });
    boton.dataset.metodo = valor;
    boton.addEventListener('click', () => {
      metodo = valor;
      actualizar();
    });
    botones.appendChild(boton);
  }
  for (const campo of [monto, recibido]) campo.addEventListener('input', actualizar);

  contenedor.replaceChildren(botones, crear('div', { className: 'dos-columnas' }, [bloqueMonto, bloqueRecibido, bloqueReferencia]), cambio);
  actualizar();

  return {
    actualizar,
    /** Devuelve los datos para la API, o un texto con el error. */
    leer() {
      const datos = { metodo, monto: valorMonto() };
      if (!(datos.monto > 0)) return 'Escribe un monto mayor que cero';
      if (metodo === 'EFECTIVO' && recibido.value) {
        datos.recibido = Number(recibido.value);
        if (datos.recibido < datos.monto) return 'El efectivo recibido no alcanza';
      }
      if (metodo !== 'EFECTIVO') datos.referencia = referencia.value.trim();
      return datos;
    },
  };
}

// =====================================================================
//  Pestañas
// =====================================================================

const vistas = { cobrar: cargarPorCobrar, mostrador: prepararMostrador, pagos: cargarPagos };

function mostrarPestana(nombre) {
  for (const clave of Object.keys(vistas)) {
    $(`tab-${clave}`).setAttribute('aria-selected', String(clave === nombre));
    $(`vista-${clave}`).hidden = clave !== nombre;
  }
  vistas[nombre]();
}

for (const clave of Object.keys(vistas)) {
  $(`tab-${clave}`).addEventListener('click', () => mostrarPestana(clave));
}
$('tab-mostrador').hidden = !puedeCobrar;

// =====================================================================
//  RF-09.4 Órdenes por cobrar
// =====================================================================

async function cargarPorCobrar() {
  try {
    const ordenes = await api('GET', '/ordenes/por-cobrar');
    $('estado-cobrar').hidden = ordenes.length > 0;
    $('estado-cobrar').textContent = 'No hay órdenes pendientes de pago';
    pintarSuave($('lista-cobrar'), ...ordenes.map((orden) => {
      const chips = [crear('span', { className: 'chip', texto: `Saldo ${formato.dinero(orden.saldo)}` })];
      if (orden.pagado > 0) chips.unshift(crear('span', { className: 'chip estado-PARCIAL', texto: 'Pago parcial' }));
      const tipo = orden.mesa ? `Mesa ${orden.mesa}` : TIPOS[orden.tipo];
      const detalle = [tipo, orden.cliente, fechaHora(orden.fecha)].filter(Boolean).join(' · ');
      const fila = crear('li', { className: 'fila editable' }, [
        crear('div', { className: 'avatar' }, [crear('span', { className: 'icono', texto: 'receipt_long', 'aria-hidden': 'true' })]),
        crear('div', { className: 'datos' }, [
          crear('div', { className: 'nombre', texto: `${orden.codigo} · ${formato.dinero(orden.total)}` }),
          crear('div', { className: 'correo', texto: detalle }),
        ]),
        crear('div', { className: 'chips' }, chips),
      ]);
      fila.addEventListener('click', () => abrirCuenta(orden.orden_id));
      return fila;
    }));
  } catch (error) {
    $('estado-cobrar').hidden = false;
    $('estado-cobrar').textContent = error.message;
  }
}

// =====================================================================
//  RF-09.3 Cuenta, RF-09.1 Registrar pago y RF-09.4 Anular
// =====================================================================

const dialogoCuenta = $('dialogo-cuenta');
let cuentaAbierta = null;
let pagoCuenta = null;

async function abrirCuenta(ordenId) {
  try {
    pintarCuenta(await api('GET', `/ordenes/${ordenId}/cuenta`));
    if (!dialogoCuenta.open) dialogoCuenta.showModal();
  } catch (error) {
    mostrarAviso(error.message, 'error');
  }
}

function pintarCuenta(cuenta) {
  cuentaAbierta = cuenta;
  $('error-cuenta').hidden = true;
  $('cuenta-titulo').replaceChildren(
    crear('span', { texto: `${cuenta.codigo} ` }),
    crear('span', { className: `chip estado-${cuenta.estado_pago}`, texto: ESTADOS_PAGO[cuenta.estado_pago] }),
  );
  $('cuenta-cliente').textContent = [TIPOS[cuenta.tipo], cuenta.cliente?.nombre].filter(Boolean).join(' · ');
  pintarSuave($('cuenta-lineas'), ...cuenta.productos.map((d) => crear('li', {}, [
    crear('span', { texto: `${d.cantidad} × ${d.producto}` }),
    crear('span', { texto: formato.dinero(d.subtotal) }),
  ])));

  const filas = [['Subtotal', formato.dinero(cuenta.subtotal)]];
  if (cuenta.costo_envio) filas.push(['Envío', formato.dinero(cuenta.costo_envio)]);
  filas.push(
    ['Total', formato.dinero(cuenta.total)],
    ['Impoconsumo incluido (8 %)', formato.dinero(cuenta.impoconsumo_incluido)],
    ['Pagado', formato.dinero(cuenta.pagado)],
    ['Saldo', formato.dinero(cuenta.saldo)],
  );
  pintarSuave($('cuenta-totales'), ...filas.flatMap(([titulo, valor]) => [
    crear('dt', { texto: titulo }), crear('dd', { texto: valor }),
  ]));

  // Pagos ya hechos, con opción de anular mientras la orden siga abierta
  $('bloque-pagos-hechos').hidden = cuenta.pagos.length === 0;
  pintarSuave($('cuenta-pagos'), ...cuenta.pagos.map((pago) => {
    const texto = `${METODOS[pago.metodo]} · ${formato.dinero(pago.monto)}`
      + (pago.cambio ? ` (cambio ${formato.dinero(pago.cambio)})` : '')
      + (pago.referencia ? ` · ref. ${pago.referencia}` : '');
    const partes = [crear('span', { texto }), crear('span', { className: 'nota', texto: fechaHora(pago.fecha) })];
    if (pago.estado === 'ANULADO') {
      partes.push(crear('span', { className: 'chip estado-CANCELADO', texto: 'Anulado' }));
    } else if (puedeCobrar && cuenta.estado_orden === 'ABIERTA') {
      const anular = crear('button', { type: 'button', className: 'boton-texto', texto: 'Anular' });
      anular.addEventListener('click', () => anularPago(pago));
      partes.push(anular);
    }
    return crear('li', {}, partes);
  }));

  const puedePagar = puedeCobrar && cuenta.estado_orden === 'ABIERTA' && cuenta.saldo > 0;
  $('bloque-nuevo-pago').hidden = !puedePagar;
  if (puedePagar) pagoCuenta = formularioDePago($('c-pago'), { montoInicial: cuenta.saldo });

  const cerrar = crear('button', { type: 'button', className: 'boton-texto', texto: 'Cerrar' });
  cerrar.addEventListener('click', () => dialogoCuenta.close());
  const botones = [cerrar];
  if (cuenta.estado_pago !== 'PENDIENTE') {
    const comprobante = crear('button', { type: 'button', className: 'boton-texto', texto: 'Comprobante' });
    comprobante.addEventListener('click', () => abrirComprobante(cuenta.orden_id));
    botones.push(comprobante);
  }
  if (puedePagar) {
    const pagar = crear('button', { type: 'button', className: 'boton-principal' }, [
      crear('span', { className: 'icono', texto: 'payments', 'aria-hidden': 'true' }),
      document.createTextNode(' Registrar pago'),
    ]);
    pagar.addEventListener('click', () => registrarPago(pagar));
    botones.push(pagar);
  }
  $('cuenta-acciones').replaceChildren(...botones);
}

function mostrarErrorCuenta(mensaje) {
  $('error-cuenta').textContent = mensaje;
  $('error-cuenta').hidden = false;
}

async function registrarPago(boton) {
  const datos = pagoCuenta.leer();
  if (typeof datos === 'string') {
    mostrarErrorCuenta(datos);
    return;
  }
  boton.disabled = true;
  try {
    const { cuenta } = await api('POST', `/ordenes/${cuentaAbierta.orden_id}/pagos`, datos); // RF-09.1
    mostrarAviso(cuenta.venta ? `Pagado. Venta ${cuenta.venta} registrada` : 'Abono registrado', 'exito');
    pintarCuenta(cuenta);
    cargarPorCobrar();
  } catch (error) {
    mostrarErrorCuenta(error.message); // por ejemplo "El monto supera el saldo pendiente"
    boton.disabled = false;
  }
}

async function anularPago(pago) {
  if (!confirm(`¿Anular el pago de ${formato.dinero(pago.monto)}?`)) return;
  try {
    const { cuenta } = await api('PATCH', `/pagos/${pago.id}/anular`);
    mostrarAviso('Pago anulado', 'exito');
    pintarCuenta(cuenta);
    cargarPorCobrar();
  } catch (error) {
    mostrarErrorCuenta(error.message);
  }
}

// =====================================================================
//  RF-10.1 Venta de mostrador
// =====================================================================

let carta = [];
let lineas = []; // [{producto_id, nombre, precio, cantidad}]
let pagoMostrador = null;
const totalMostrador = () => lineas.reduce((total, l) => total + l.precio * l.cantidad, 0);

async function prepararMostrador() {
  if (!pagoMostrador) pagoMostrador = formularioDePago($('m-pago'), { montoFijo: totalMostrador });
  try {
    carta = await api('GET', '/productos?disponible=true');
    $('m-producto').replaceChildren(
      crear('option', { value: '', texto: 'Elige un producto…' }),
      ...carta.map((p) => crear('option', { value: p.id, texto: `${p.nombre} · ${formato.dinero(p.precio_venta)}` })),
    );
  } catch (error) {
    mostrarErrorMostrador(error.message);
  }
  pintarLineas();
}

function pintarLineas() {
  const filas = lineas.map((linea, posicion) => {
    const quitar = crear('button', { type: 'button', className: 'boton-icono', title: 'Quitar' }, [
      crear('span', { className: 'icono', texto: 'delete', 'aria-hidden': 'true' }),
    ]);
    quitar.addEventListener('click', () => {
      lineas.splice(posicion, 1);
      pintarLineas();
    });
    return crear('div', { className: 'linea con-cantidad' }, [
      crear('span', { className: 'texto-linea', texto: linea.nombre }),
      crear('span', { className: 'texto-linea', texto: `× ${linea.cantidad}` }),
      crear('span', { className: 'texto-linea', texto: formato.dinero(linea.precio * linea.cantidad) }),
      quitar,
    ]);
  });
  if (filas.length === 0) filas.push(crear('p', { className: 'nota', texto: 'Agrega lo que lleva el cliente.' }));
  pintarSuave($('m-lineas'), ...filas);
  $('m-total').textContent = `Total: ${formato.dinero(totalMostrador())}`;
  pagoMostrador?.actualizar();
}

/** Pasa a la venta el producto elegido. Devuelve false si falta algo. */
function agregarProducto() {
  const producto = carta.find((p) => p.id === Number($('m-producto').value));
  const cantidad = Number($('m-cantidad').value);
  if (!producto || !Number.isInteger(cantidad) || cantidad < 1) {
    $('error-m-productos').textContent = producto ? 'La cantidad debe ser un número entero' : 'Elige un producto';
    return false;
  }
  $('error-m-productos').textContent = '';
  const existente = lineas.find((l) => l.producto_id === producto.id);
  if (existente) existente.cantidad += cantidad;
  else lineas.push({ producto_id: producto.id, nombre: producto.nombre, precio: producto.precio_venta, cantidad });
  $('m-producto').value = '';
  $('m-cantidad').value = '1';
  pintarLineas();
  return true;
}

$('m-agregar').addEventListener('click', agregarProducto);

function mostrarErrorMostrador(mensaje) {
  $('error-mostrador').textContent = mensaje;
  $('error-mostrador').hidden = false;
}

$('m-cobrar').addEventListener('click', async () => {
  $('error-mostrador').hidden = true;
  if ($('m-producto').value && !agregarProducto()) return; // lo elegido sin tocar ⊕ se agrega solo
  if (lineas.length === 0) {
    $('error-m-productos').textContent = 'Agrega al menos un producto';
    return;
  }
  const pago = pagoMostrador.leer();
  if (typeof pago === 'string') {
    mostrarErrorMostrador(pago);
    return;
  }
  $('m-cobrar').disabled = true;
  try {
    const { venta, pago: registrado } = await api('POST', '/ventas', {
      items: lineas.map((l) => ({ producto_id: l.producto_id, cantidad: l.cantidad })),
      metodo: pago.metodo, recibido: pago.recibido, referencia: pago.referencia,
    });
    mostrarAviso(`Venta ${venta.codigo}` + (registrado.cambio ? ` · cambio ${formato.dinero(registrado.cambio)}` : ''), 'exito');
    lineas = [];
    pagoMostrador = formularioDePago($('m-pago'), { montoFijo: totalMostrador });
    pintarLineas();
    abrirComprobante(venta.orden_id);
  } catch (error) {
    mostrarErrorMostrador(error.message);
  } finally {
    $('m-cobrar').disabled = false;
  }
});

// =====================================================================
//  RF-09.7 Historial de pagos
// =====================================================================

const hoy = new Date().toLocaleDateString('en-CA'); // AAAA-MM-DD en hora local
$('p-desde').value = hoy;
$('p-hasta').value = hoy;

async function cargarPagos() {
  if (empezarCarga($('lista-pagos'))) {
    $('estado-pagos').hidden = false;
    $('estado-pagos').textContent = 'Cargando…';
  }
  try {
    const parametros = new URLSearchParams({ desde: $('p-desde').value, hasta: $('p-hasta').value });
    const { resumen, pagos } = await api('GET', `/pagos?${parametros}`);
    pintarSuave($('resumen-pagos'),
      tarjetaResumen('payments', 'Total recibido', formato.dinero(resumen.total)),
      tarjetaResumen('money', 'Efectivo', formato.dinero(resumen.por_metodo.EFECTIVO)),
      tarjetaResumen('credit_card', 'Tarjeta', formato.dinero(resumen.por_metodo.TARJETA)),
      tarjetaResumen('swap_horiz', 'Transferencia', formato.dinero(resumen.por_metodo.TRANSFERENCIA)),
    );
    $('estado-pagos').hidden = pagos.length > 0;
    $('estado-pagos').textContent = 'No hay pagos en esas fechas';
    pintarSuave($('lista-pagos'), ...pagos.map((pago) => {
      const chips = [crear('span', { className: 'chip', texto: formato.dinero(pago.monto) })];
      if (pago.estado === 'ANULADO') chips.unshift(crear('span', { className: 'chip estado-CANCELADO', texto: 'Anulado' }));
      const fila = crear('li', { className: 'fila editable' }, [
        crear('div', { className: 'avatar' }, [crear('span', { className: 'icono', texto: 'payments', 'aria-hidden': 'true' })]),
        crear('div', { className: 'datos' }, [
          crear('div', { className: 'nombre', texto: `${pago.orden} · ${METODOS[pago.metodo]}` }),
          crear('div', { className: 'correo', texto: `${fechaHora(pago.fecha)} · ${pago.usuario}` }),
        ]),
        crear('div', { className: 'chips' }, chips),
      ]);
      fila.addEventListener('click', () => abrirCuenta(pago.orden_id));
      return fila;
    }));
  } catch (error) {
    $('estado-pagos').textContent = error.message;
  }
}

$('form-pagos').addEventListener('submit', (evento) => {
  evento.preventDefault();
  cargarPagos();
});

mostrarPestana('cobrar');
