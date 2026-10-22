// Módulo de pedidos en mesa (RF-05.1 a RF-05.9): mesas, pedidos, cocina y estado.
import { api, exigirSesion } from './api.js';
import { crear, formato, mostrarAviso } from './ui.js';

const yo = await exigirSesion('pedidos.ver'); // sin el permiso vuelve al menú
const puedeGestionar = yo.permisos.includes('pedidos.gestionar'); // MESERO, CAJERO, ADMINISTRADOR

const $ = (id) => document.getElementById(id);

const NOMBRES_ESTADO = {
  REGISTRADO: 'Registrado', CONFIRMADO: 'Confirmado', EN_COCINA: 'En cocina',
  EN_PREPARACION: 'En preparación', LISTO: 'Listo', ENTREGADO: 'Entregado', CANCELADO: 'Cancelado',
};

function chipEstado(estado) {
  return crear('span', { className: `chip estado-${estado}`, texto: NOMBRES_ESTADO[estado] });
}

/** "hace 12 min", "hace 1 h 5 min": cuánto lleva la mesa esperando. */
function espera(iso) {
  const minutos = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
  if (minutos < 60) return `hace ${minutos} min`;
  return `hace ${Math.floor(minutos / 60)} h ${minutos % 60} min`;
}

function fechaHora(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
}

function hora(iso) {
  return new Date(iso).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
}

function botonPrincipal(texto, icono, accion) {
  const boton = crear('button', { type: 'button', className: 'boton-principal' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    document.createTextNode(` ${texto}`),
  ]);
  boton.addEventListener('click', async () => {
    boton.disabled = true;
    await accion();
    boton.disabled = false;
  });
  return boton;
}

function botonTexto(texto, accion) {
  const boton = crear('button', { type: 'button', className: 'boton-texto', texto });
  boton.addEventListener('click', accion);
  return boton;
}

function tarjetaResumen(icono, titulo, valor) {
  return crear('div', { className: 'tarjeta-resumen' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
  ]);
}

// =====================================================================
//  Pestañas
// =====================================================================

const VISTAS = { mesas: cargarMesas, activos: cargarActivos, historial: cargarHistorial };
let vistaActual = 'mesas';

function mostrarVista(vista) {
  vistaActual = vista;
  for (const nombre of Object.keys(VISTAS)) {
    $(`tab-${nombre}`).setAttribute('aria-selected', String(nombre === vista));
    $(`vista-${nombre}`).hidden = nombre !== vista;
  }
  $('boton-nuevo').hidden = !puedeGestionar || vista === 'historial';
  VISTAS[vista]();
}

for (const nombre of Object.keys(VISTAS)) {
  $(`tab-${nombre}`).addEventListener('click', () => mostrarVista(nombre));
}

/** Vuelve a pintar lo que se está viendo (después de guardar algo). */
function refrescar() {
  VISTAS[vistaActual]();
}

// Se actualiza sola cada 30 segundos, si no hay una ventana abierta
setInterval(() => {
  if (!document.querySelector('dialog[open]') && vistaActual !== 'historial') refrescar();
}, 30000);

// =====================================================================
//  RF-05.2 Mesas del salón
// =====================================================================

let mesas = [];

async function cargarMesas() {
  try {
    mesas = await api('GET', '/mesas');
    pintarMesas();
  } catch (error) {
    $('estado-mesas').hidden = false;
    $('estado-mesas').textContent = error.message;
  }
}

function pintarMesas() {
  const ocupadas = mesas.filter((m) => m.ocupada);
  const porCobrar = ocupadas.reduce((total, m) => total + m.pedido.total, 0);
  $('resumen-mesas').replaceChildren(
    tarjetaResumen('event_available', 'Mesas libres', String(mesas.length - ocupadas.length)),
    tarjetaResumen('groups', 'Mesas ocupadas', String(ocupadas.length)),
    tarjetaResumen('payments', 'En mesas sin cobrar', formato.dinero(porCobrar)),
  );
  $('estado-mesas').hidden = mesas.length > 0;
  $('estado-mesas').textContent = puedeGestionar
    ? 'Todavía no hay mesas. Créalas con «Administrar mesas».' : 'Todavía no hay mesas registradas.';
  $('mesas').replaceChildren(...mesas.map(tarjetaMesa));
}

function tarjetaMesa(mesa) {
  const partes = [
    crear('span', { className: 'numero-mesa', texto: `Mesa ${mesa.numero}` }),
    crear('span', { className: 'detalle-mesa', texto: [`${mesa.capacidad} personas`, mesa.ubicacion].filter(Boolean).join(' · ') }),
  ];
  if (mesa.ocupada) {
    const p = mesa.pedido;
    partes.push(
      crear('span', { className: 'estado-mesa', texto: `${p.codigo} · ${formato.dinero(p.total)}` }),
      chipEstado(p.estado),
      crear('span', { className: 'detalle-mesa', texto: `${p.productos} producto${p.productos === 1 ? '' : 's'} · ${espera(p.fecha)}` }),
    );
  } else {
    partes.push(crear('span', { className: 'estado-mesa', texto: 'Libre' }));
  }
  const tarjeta = crear('button', {
    type: 'button', className: `mesa${mesa.ocupada ? ' ocupada' : ''}`,
    'aria-label': `Mesa ${mesa.numero}, ${mesa.ocupada ? 'ocupada' : 'libre'}`,
  }, partes);
  tarjeta.addEventListener('click', () => {
    if (mesa.ocupada) abrirDetalle(mesa.pedido.id);
    else if (puedeGestionar) abrirFormulario(null, mesa.id);
    else mostrarAviso(`La mesa ${mesa.numero} está libre`);
  });
  return tarjeta;
}

// =====================================================================
//  RF-05.5 Consultar pedidos activos e historial
// =====================================================================

let activos = [];
let estadoElegido = '';

function filaDePedido(pedido, conEspera) {
  const fila = crear('li', { className: 'fila editable' }, [
    crear('div', { className: 'avatar' }, [
      crear('span', { className: 'icono', texto: 'table_restaurant', 'aria-hidden': 'true' }),
    ]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: `${pedido.codigo} · Mesa ${pedido.mesa.numero}` }),
      crear('div', { className: 'correo', texto: `${pedido.comensales} comensales · ${pedido.mesero}` }),
      crear('div', { className: 'correo', texto: conEspera ? espera(pedido.fecha) : fechaHora(pedido.fecha) }),
    ]),
    crear('div', { className: 'chips' }, [
      chipEstado(pedido.estado),
      crear('span', { className: 'chip', texto: formato.dinero(pedido.total) }),
    ]),
  ]);
  fila.addEventListener('click', () => abrirDetalle(pedido.id));
  return fila;
}

async function cargarActivos() {
  try {
    activos = await api('GET', '/pedidos');
    pintarActivos();
  } catch (error) {
    $('estado-activos').hidden = false;
    $('estado-activos').textContent = error.message;
  }
}

function pintarActivos() {
  const opciones = ['', 'REGISTRADO', 'CONFIRMADO', 'EN_COCINA', 'EN_PREPARACION', 'LISTO', 'ENTREGADO'];
  $('filtro-estados').replaceChildren(...opciones
    .filter((valor) => !valor || activos.some((p) => p.estado === valor) || valor === estadoElegido)
    .map((valor) => {
      const cuantos = valor ? activos.filter((p) => p.estado === valor).length : activos.length;
      const boton = crear('button', {
        type: 'button', className: 'chip filtro',
        texto: `${valor ? NOMBRES_ESTADO[valor] : 'Todos'} (${cuantos})`,
        'aria-pressed': String(valor === estadoElegido),
      });
      boton.addEventListener('click', () => {
        estadoElegido = valor;
        pintarActivos();
      });
      return boton;
    }));
  const visibles = activos.filter((p) => !estadoElegido || p.estado === estadoElegido);
  $('estado-activos').hidden = visibles.length > 0;
  $('estado-activos').textContent = 'No hay pedidos activos';
  $('lista-activos').replaceChildren(...visibles.map((p) => filaDePedido(p, true)));
}

const iso = (fecha) => fecha.toLocaleDateString('en-CA'); // AAAA-MM-DD en hora local
$('h-desde').value = iso(new Date(Date.now() - 7 * 24 * 3600 * 1000));
$('h-hasta').value = iso(new Date());

async function cargarHistorial() {
  $('estado-historial').hidden = false;
  $('estado-historial').textContent = 'Cargando…';
  try {
    const parametros = new URLSearchParams({ vista: 'historial', desde: $('h-desde').value, hasta: $('h-hasta').value });
    if ($('h-codigo').value.trim()) parametros.set('q', $('h-codigo').value.trim());
    const lista = await api('GET', `/pedidos?${parametros}`);
    $('estado-historial').hidden = lista.length > 0;
    $('estado-historial').textContent = 'No hay pedidos en esas fechas';
    $('lista-historial').replaceChildren(...lista.map((p) => filaDePedido(p, false)));
  } catch (error) {
    $('estado-historial').textContent = error.message;
  }
}

$('form-historial').addEventListener('submit', (evento) => {
  evento.preventDefault();
  cargarHistorial();
});

// =====================================================================
//  RF-05.1 Registrar / RF-05.4 Modificar, con RF-05.6 disponibilidad
// =====================================================================

const dialogoPedido = $('dialogo-pedido');
let carta = []; // productos disponibles hoy
let lineas = []; // [{producto_id, nombre, precio, cantidad, observacion}]
let pedidoEditado = null; // null = pedido nuevo

if (puedeGestionar) $('boton-nuevo').addEventListener('click', () => abrirFormulario(null));

async function cargarCarta() {
  carta = await api('GET', '/productos?disponible=true');
  pintarOpcionesCarta('');
}

/** Llena la lista de productos, filtrada por lo que se escribe en el buscador. */
function pintarOpcionesCarta(texto) {
  const buscar = texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const visibles = carta.filter((p) => p.nombre.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().includes(buscar));
  const opciones = visibles.map((p) => crear('option', { value: p.id, texto: `${p.nombre} · ${formato.dinero(p.precio_venta)}` }));
  $('p-producto').replaceChildren(crear('option', { value: '', texto: visibles.length ? 'Elige un producto…' : 'Sin resultados' }), ...opciones);
  if (visibles.length === 1 && buscar) $('p-producto').value = visibles[0].id; // un solo resultado: queda elegido
}

$('p-buscar').addEventListener('input', () => pintarOpcionesCarta($('p-buscar').value));

/** pedido: el pedido a modificar, o null para uno nuevo. mesaId: mesa elegida al tocar una mesa libre. */
async function abrirFormulario(pedido, mesaId = null) {
  pedidoEditado = pedido;
  $('form-pedido').reset();
  for (const campo of ['mesa', 'comensales', 'productos']) marcarCampo(campo, '');
  $('error-pedido').hidden = true;
  $('disponibilidad').hidden = true;
  $('titulo-pedido').textContent = pedido ? `Modificar ${pedido.codigo}` : 'Nuevo pedido';
  $('texto-guardar').textContent = pedido ? 'Guardar cambios' : 'Registrar pedido';
  lineas = pedido ? pedido.detalles.map((d) => ({
    producto_id: d.producto_id, nombre: d.producto, precio: d.precio_unitario, cantidad: d.cantidad, observacion: d.observacion,
  })) : [];
  dialogoPedido.showModal();
  try {
    const [listaMesas] = await Promise.all([api('GET', '/mesas'), cargarCarta()]);
    // Se pueden elegir las mesas libres y, si se modifica, la mesa actual del pedido
    const elegibles = listaMesas.filter((m) => !m.ocupada || (pedido && m.id === pedido.mesa.id));
    $('p-mesa').replaceChildren(
      crear('option', { value: '', texto: elegibles.length ? 'Elige la mesa…' : 'No hay mesas libres' }),
      ...elegibles.map((m) => crear('option', { value: m.id, texto: `Mesa ${m.numero} · ${m.capacidad} personas${m.ubicacion ? ` · ${m.ubicacion}` : ''}` })),
    );
    $('p-mesa').value = pedido ? pedido.mesa.id : (mesaId ?? '');
    $('p-comensales').value = pedido ? pedido.comensales : 2;
    $('p-observaciones').value = pedido?.observaciones ?? '';
    pintarLineas();
    $('p-buscar').focus();
  } catch (error) {
    mostrarErrorPedido(error.message);
  }
}

function pintarLineas() {
  const filas = lineas.map((linea, posicion) => {
    const cantidad = crear('input', { type: 'number', min: '1', step: '1', 'aria-label': `Cantidad de ${linea.nombre}` });
    cantidad.value = linea.cantidad;
    cantidad.addEventListener('input', () => {
      linea.cantidad = Number(cantidad.value);
      subtotal.textContent = formato.dinero(linea.precio * (linea.cantidad || 0));
      pintarTotal();
      revisarDisponibilidad();
    });
    const subtotal = crear('span', { className: 'texto-linea', texto: formato.dinero(linea.precio * linea.cantidad) });
    const quitar = crear('button', { type: 'button', className: 'boton-icono', title: 'Quitar' }, [
      crear('span', { className: 'icono', texto: 'delete', 'aria-hidden': 'true' }),
    ]);
    quitar.addEventListener('click', () => {
      lineas.splice(posicion, 1);
      pintarLineas();
    });
    const nombre = linea.observacion ? `${linea.nombre} (${linea.observacion})` : linea.nombre;
    return crear('div', { className: 'linea con-cantidad' }, [
      crear('span', { className: 'texto-linea', texto: nombre }), crear('div', { className: 'campo' }, [cantidad]), subtotal, quitar,
    ]);
  });
  if (filas.length === 0) filas.push(crear('p', { className: 'nota', texto: 'Agrega lo que pidió la mesa.' }));
  $('lineas-pedido').replaceChildren(...filas);
  pintarTotal();
  revisarDisponibilidad();
}

function pintarTotal() {
  const total = lineas.reduce((suma, l) => suma + l.precio * (l.cantidad || 0), 0);
  $('total-pedido').textContent = `Total: ${formato.dinero(total)}`;
}

/** Pasa al pedido el producto elegido. Devuelve false si falta algo. */
function agregarProducto() {
  const producto = carta.find((p) => p.id === Number($('p-producto').value));
  const cantidad = Number($('p-cantidad').value);
  if (!producto) {
    marcarCampo('productos', 'Elige un producto');
    return false;
  }
  if (!Number.isInteger(cantidad) || cantidad < 1) {
    marcarCampo('productos', 'La cantidad debe ser un número entero');
    return false;
  }
  marcarCampo('productos', '');
  const observacion = $('p-nota-linea').value.trim() || null;
  const existente = lineas.find((l) => l.producto_id === producto.id && l.observacion === observacion);
  if (existente) existente.cantidad += cantidad; // el mismo producto otra vez: suma
  else lineas.push({ producto_id: producto.id, nombre: producto.nombre, precio: producto.precio_venta, cantidad, observacion });
  $('p-producto').value = '';
  $('p-cantidad').value = '1';
  $('p-nota-linea').value = '';
  $('p-buscar').value = '';
  pintarOpcionesCarta('');
  pintarLineas();
  return true;
}

$('agregar-producto').addEventListener('click', agregarProducto);

// RF-05.6 Mientras se arma el pedido, se revisa si el inventario alcanza (sin guardar nada)
let temporizadorDisponibilidad;
function revisarDisponibilidad() {
  clearTimeout(temporizadorDisponibilidad);
  const items = lineas.filter((l) => Number.isInteger(l.cantidad) && l.cantidad > 0)
    .map((l) => ({ producto_id: l.producto_id, cantidad: l.cantidad }));
  if (items.length === 0) {
    $('disponibilidad').hidden = true;
    return;
  }
  temporizadorDisponibilidad = setTimeout(async () => {
    try {
      const r = await api('POST', '/pedidos/disponibilidad', { items });
      $('disponibilidad').hidden = false;
      $('disponibilidad').className = `disponibilidad ${r.disponible ? 'ok' : 'falta'}`;
      $('disponibilidad').textContent = r.disponible
        ? '✓ Hay inventario para todo el pedido'
        : `No alcanza: ${r.faltantes.map((f) => `${f.insumo} (faltan ${formato.cantidad(f.falta)} ${f.unidad_medida})`).join(', ')}`;
    } catch {
      $('disponibilidad').hidden = true; // no bloquea: al guardar el servidor vuelve a revisar
    }
  }, 400);
}

function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`)?.classList.toggle('invalido', Boolean(mensaje));
}

function mostrarErrorPedido(mensaje) {
  $('error-pedido').textContent = mensaje;
  $('error-pedido').hidden = false;
}

function validarPedido() {
  const comensales = Number($('p-comensales').value);
  const errores = {
    mesa: $('p-mesa').value ? '' : 'Elige la mesa',
    comensales: Number.isInteger(comensales) && comensales > 0 ? '' : 'Escribe cuántas personas hay',
    productos: lineas.length === 0 ? 'Agrega al menos un producto'
      : lineas.every((l) => Number.isInteger(l.cantidad) && l.cantidad > 0) ? ''
        : 'Las cantidades deben ser números enteros mayores que cero',
  };
  for (const [campo, mensaje] of Object.entries(errores)) marcarCampo(campo, mensaje);
  return Object.values(errores).every((mensaje) => !mensaje);
}

$('form-pedido').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-pedido').hidden = true;
  if ($('p-producto').value && !agregarProducto()) return; // elegido sin tocar ⊕: se agrega solo
  if (!validarPedido()) return;

  const datos = {
    mesa_id: Number($('p-mesa').value),
    comensales: Number($('p-comensales').value),
    observaciones: $('p-observaciones').value.trim(),
    items: lineas.map((l) => ({ producto_id: l.producto_id, cantidad: l.cantidad, observacion: l.observacion })),
  };
  $('guardar-pedido').disabled = true;
  try {
    const pedido = pedidoEditado
      ? await api('PUT', `/pedidos/${pedidoEditado.id}`, datos) // RF-05.4
      : await api('POST', '/pedidos', datos); // RF-05.1
    dialogoPedido.close();
    mostrarAviso(pedidoEditado ? `${pedido.codigo} actualizado` : `Pedido ${pedido.codigo} registrado en la mesa ${pedido.mesa.numero}`);
    refrescar();
    abrirDetalle(pedido.id);
  } catch (error) {
    mostrarErrorPedido(error.message); // por ejemplo "No alcanza 'Pollo' para este pedido…"
  } finally {
    $('guardar-pedido').disabled = false;
  }
});

$('cancelar-pedido').addEventListener('click', () => dialogoPedido.close());

// =====================================================================
//  Detalle: RF-05.3 Agregar, RF-05.7 Confirmar, RF-05.8 Cocina, RF-05.9 Estado
// =====================================================================

const dialogoDetalle = $('dialogo-detalle');
let pedidoAbierto = null;

async function abrirDetalle(id) {
  $('error-detalle').hidden = true;
  try {
    const pedido = await api('GET', `/pedidos/${id}`);
    if (carta.length === 0 && pedido.editable && puedeGestionar) await cargarCarta();
    pintarDetalle(pedido);
    if (!dialogoDetalle.open) dialogoDetalle.showModal();
  } catch (error) {
    mostrarAviso(error.message);
  }
}

function pintarDetalle(pedido) {
  pedidoAbierto = pedido;
  $('detalle-titulo').replaceChildren(crear('span', { texto: `${pedido.codigo} · Mesa ${pedido.mesa.numero} ` }), chipEstado(pedido.estado));

  const cobro = { ABIERTA: 'Sin cobrar', CERRADA: 'Cobrado', CANCELADA: 'Cancelado' }[pedido.estado_orden];
  const datos = [
    ['Mesa', `${pedido.mesa.numero}${pedido.mesa.ubicacion ? ` · ${pedido.mesa.ubicacion}` : ''} · ${pedido.comensales} comensales`],
    ['Mesero', pedido.mesero],
    ['Registrado', `${fechaHora(pedido.fecha)} (${espera(pedido.fecha)})`],
    ['Cuenta', cobro],
    ['Observaciones', pedido.observaciones],
  ].filter(([, valor]) => valor);
  $('detalle-datos').replaceChildren(...datos.flatMap(([titulo, valor]) => [crear('dt', { texto: titulo }), crear('dd', { texto: valor })]));

  // RF-05.9 Recorrido: cada paso con su hora
  $('detalle-tiempo').replaceChildren(...pedido.linea_de_tiempo.map((paso) =>
    crear('li', { texto: `${NOMBRES_ESTADO[paso.estado]} ${hora(paso.fecha)}` })));

  $('detalle-lineas').replaceChildren(...pedido.detalles.map((d) => crear('li', {}, [
    crear('span', { texto: `${d.cantidad} × ${d.producto}${d.observacion ? ` (${d.observacion})` : ''}` }),
    crear('span', { texto: formato.dinero(d.subtotal) }),
  ])));
  $('detalle-total').textContent = `Total: ${formato.dinero(pedido.total)}`;

  // RF-05.3 Agregar productos: solo mientras no vaya para cocina
  const sePuedeAgregar = puedeGestionar && pedido.editable;
  $('bloque-agregar').hidden = !sePuedeAgregar;
  if (sePuedeAgregar) {
    $('a-producto').replaceChildren(crear('option', { value: '', texto: 'Elige un producto…' }),
      ...carta.map((p) => crear('option', { value: p.id, texto: `${p.nombre} · ${formato.dinero(p.precio_venta)}` })));
    $('a-cantidad').value = '1';
  }
  pintarAcciones(pedido);
}

function pintarAcciones(pedido) {
  const botones = [botonTexto('Cerrar', () => dialogoDetalle.close())];
  if (puedeGestionar && pedido.editable) {
    botones.push(botonTexto('Cancelar pedido', () => {
      const motivo = prompt(`¿Por qué se cancela ${pedido.codigo}? (opcional)`, '');
      if (motivo !== null) ejecutar('PATCH', `/pedidos/${pedido.id}/cancelar`, { motivo }, `${pedido.codigo} cancelado`);
    }));
    botones.push(botonTexto('Modificar', () => {
      dialogoDetalle.close();
      abrirFormulario(pedido);
    }));
  }
  if (puedeGestionar && pedido.estado === 'REGISTRADO' && pedido.estado_orden === 'ABIERTA') {
    botones.push(botonPrincipal('Confirmar pedido', 'check_circle',
      () => ejecutar('PATCH', `/pedidos/${pedido.id}/confirmar`, undefined, `${pedido.codigo} confirmado`)));
  }
  if (puedeGestionar && pedido.estado === 'CONFIRMADO' && pedido.estado_orden !== 'CANCELADA') {
    botones.push(botonPrincipal('Enviar a cocina', 'soup_kitchen', async () => {
      const ok = await ejecutar('PATCH', `/pedidos/${pedido.id}/enviar-cocina`, undefined, `${pedido.codigo} enviado a cocina`);
      if (ok) abrirComanda(pedido.id);
    }));
  }
  if (pedido.fecha_envio_cocina) {
    botones.push(botonTexto('Imprimir comanda', () => abrirComanda(pedido.id)));
  }
  if (pedido.estado_orden === 'ABIERTA' && pedido.estado !== 'REGISTRADO' && yo.permisos.includes('pagos.ver')) {
    botones.push(botonTexto('Cobrar en caja', () => { location.href = 'caja.html'; }));
  }
  $('detalle-acciones').replaceChildren(...botones);
}

function abrirComanda(id) {
  window.open(`comanda.html?pedido=${encodeURIComponent(id)}`, '_blank', 'width=420,height=640');
}

/** Llama a la API, muestra el aviso y repinta el detalle. Devuelve true si salió bien. */
async function ejecutar(metodo, ruta, datos, aviso) {
  $('error-detalle').hidden = true;
  try {
    const actualizado = await api(metodo, ruta, datos);
    mostrarAviso(aviso);
    pintarDetalle(actualizado);
    refrescar();
    return true;
  } catch (error) {
    $('error-detalle').textContent = error.message; // por ejemplo "Primero confirma el pedido con el cliente"
    $('error-detalle').hidden = false;
    return false;
  }
}

$('boton-agregar').addEventListener('click', () => {
  const productoId = Number($('a-producto').value);
  const cantidad = Number($('a-cantidad').value);
  if (!productoId || !Number.isInteger(cantidad) || cantidad < 1) {
    $('error-detalle').textContent = 'Elige un producto y una cantidad entera';
    $('error-detalle').hidden = false;
    return;
  }
  ejecutar('POST', `/pedidos/${pedidoAbierto.id}/productos`, { items: [{ producto_id: productoId, cantidad }] },
    'Producto agregado al pedido');
});

// =====================================================================
//  Administrar mesas
// =====================================================================

const dialogoMesas = $('dialogo-mesas');
let mesaEditada = null;

if (puedeGestionar) {
  $('boton-admin-mesas').hidden = false;
  $('boton-admin-mesas').addEventListener('click', abrirAdminMesas);
}

async function abrirAdminMesas() {
  editarMesa(null);
  dialogoMesas.showModal();
  await pintarAdminMesas();
}

async function pintarAdminMesas() {
  try {
    const todas = await api('GET', '/mesas?todas=true');
    $('lista-admin-mesas').replaceChildren(...todas.map((m) => {
      const li = crear('li', {}, [
        crear('span', {
          className: m.activa ? '' : 'mesa-inactiva',
          texto: `Mesa ${m.numero} · ${m.capacidad} personas${m.ubicacion ? ` · ${m.ubicacion}` : ''}${m.activa ? '' : ' (inactiva)'}`,
        }),
        botonTexto('Editar', () => editarMesa(m)),
      ]);
      return li;
    }));
  } catch (error) {
    $('error-mesas').textContent = error.message;
    $('error-mesas').hidden = false;
  }
}

function editarMesa(mesa) {
  mesaEditada = mesa;
  $('error-mesas').hidden = true;
  $('titulo-mesa').textContent = mesa ? `Editar mesa ${mesa.numero}` : 'Nueva mesa';
  $('m-numero').value = mesa?.numero ?? '';
  $('m-capacidad').value = mesa?.capacidad ?? 4;
  $('m-ubicacion').value = mesa?.ubicacion ?? '';
  $('m-activa').checked = mesa ? mesa.activa : true;
  $('nueva-mesa').hidden = !mesa;
}

$('nueva-mesa').addEventListener('click', () => editarMesa(null));
$('cerrar-mesas').addEventListener('click', () => {
  dialogoMesas.close();
  refrescar();
});

$('form-mesa').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-mesas').hidden = true;
  const datos = {
    numero: Number($('m-numero').value),
    capacidad: Number($('m-capacidad').value),
    ubicacion: $('m-ubicacion').value.trim(),
    activa: $('m-activa').checked,
  };
  try {
    const mesa = mesaEditada
      ? await api('PUT', `/mesas/${mesaEditada.id}`, datos)
      : await api('POST', '/mesas', datos);
    mostrarAviso(`Mesa ${mesa.numero} guardada`);
    editarMesa(null);
    await pintarAdminMesas();
  } catch (error) {
    $('error-mesas').textContent = error.message; // por ejemplo "Ya existe la mesa 3"
    $('error-mesas').hidden = false;
  }
});

mostrarVista('mesas');
