// Módulo de domicilios (RF-08.1 a RF-08.8): pedidos, clientes, asignación, estados y entregas.
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, mostrarEstado, pintarSuave } from './ui.js';

const yo = await exigirSesion('domicilios.ver'); // sin el permiso vuelve al menú
// CAJERO y ADMINISTRADOR gestionan; el DOMICILIARIO solo ve y entrega lo suyo
const puedeGestionar = yo.permisos.includes('domicilios.gestionar');

const $ = (id) => document.getElementById(id);

const NOMBRES_ESTADO = {
  RECIBIDO: 'Recibido', EN_PREPARACION: 'En preparación', LISTO: 'Listo',
  EN_CAMINO: 'En camino', ENTREGADO: 'Entregado', CANCELADO: 'Cancelado',
};

/** "hace 12 min", "hace 1 h 5 min": cuánto lleva esperando el cliente. */
function espera(iso) {
  const minutos = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
  if (minutos < 60) return `hace ${minutos} min`;
  return `hace ${Math.floor(minutos / 60)} h ${minutos % 60} min`;
}

function fechaHora(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-CO', {
    day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  });
}

function chipEstado(estado) {
  return crear('span', { className: `chip estado-${estado}`, texto: NOMBRES_ESTADO[estado] });
}

/** Fila de la lista: código, cliente, dirección, estado y total. */
function filaDeDomicilio(domicilio, conEspera) {
  const detalle = [domicilio.direccion, domicilio.domiciliario && `🛵 ${domicilio.domiciliario}`]
    .filter(Boolean).join(' · ');
  const fila = crear('li', { className: 'fila editable', 'data-clave': domicilio.id, 'data-version': `${domicilio.estado}|${domicilio.total}|${domicilio.domiciliario ?? ''}` }, [
    crear('div', { className: 'avatar' }, [
      crear('span', { className: 'icono', texto: 'delivery_dining', 'aria-hidden': 'true' }),
    ]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: `${domicilio.codigo} · ${domicilio.cliente.nombre}` }),
      crear('div', { className: 'correo', texto: detalle }),
      crear('div', { className: 'correo', texto: conEspera ? espera(domicilio.fecha) : fechaHora(domicilio.fecha) }),
    ]),
    crear('div', { className: 'chips' }, [
      chipEstado(domicilio.estado),
      crear('span', { className: 'chip', texto: formato.dinero(domicilio.total) }),
    ]),
  ]);
  fila.addEventListener('click', () => abrirDetalle(domicilio.id));
  return fila;
}

// =====================================================================
//  Pestañas: En curso / Historial
// =====================================================================

function mostrarPestana(historial) {
  $('tab-curso').setAttribute('aria-selected', String(!historial));
  $('tab-historial').setAttribute('aria-selected', String(historial));
  $('vista-curso').hidden = historial;
  $('vista-historial').hidden = !historial;
  $('boton-nuevo').hidden = historial || !puedeGestionar;
  if (historial) cargarHistorial(); else cargar();
}

$('tab-curso').addEventListener('click', () => mostrarPestana(false));
$('tab-historial').addEventListener('click', () => mostrarPestana(true));

// =====================================================================
//  RF-08.4 Consultar pedidos a domicilio en curso
// =====================================================================

let domicilios = [];
let estadoElegido = ''; // '' = todos

function pintarFiltros() {
  const opciones = [['', 'Todos'], ['RECIBIDO'], ['EN_PREPARACION'], ['LISTO'], ['EN_CAMINO']];
  $('filtro-estados').replaceChildren(...opciones.map(([valor, texto]) => {
    const cuantos = valor ? domicilios.filter((d) => d.estado === valor).length : domicilios.length;
    const boton = crear('button', {
      type: 'button', className: 'chip filtro',
      texto: `${texto ?? NOMBRES_ESTADO[valor]} (${cuantos})`,
      'aria-pressed': String(valor === estadoElegido),
    });
    boton.addEventListener('click', () => {
      estadoElegido = valor;
      pintarLista();
    });
    return boton;
  }));
}

async function cargar() {
  try {
    domicilios = await api('GET', '/domicilios');
    pintarLista();
  } catch (error) {
    mostrarEstado(error.message, { reintentar: true });
  }
}

function pintarLista() {
  pintarFiltros();
  const visibles = domicilios.filter((d) => !estadoElegido || d.estado === estadoElegido);
  if (visibles.length === 0) {
    if (estadoElegido) {
      mostrarEstado('No hay domicilios en ese estado', { icono: 'filter_alt_off', detalle: 'Elige otro estado arriba.' });
    } else if (puedeGestionar) {
      mostrarEstado('No hay domicilios en curso', {
        icono: 'delivery_dining', detalle: 'Los pedidos a domicilio aparecen aquí hasta que se entregan.',
        accion: { texto: 'Registrar un domicilio', alHacer: abrirNuevo },
      });
    } else {
      mostrarEstado('No tienes domicilios asignados', {
        icono: 'delivery_dining', detalle: 'Cuando te asignen una entrega, aparecerá aquí.',
      });
    }
    pintarSuave($('lista'));
  } else {
    $('estado').hidden = true;
    pintarSuave($('lista'), ...visibles.map((d) => filaDeDomicilio(d, true)));
  }
}

$('reintentar').addEventListener('click', cargar);

// La lista se actualiza sola cada 30 segundos (si no hay una ventana abierta)
setInterval(() => {
  const ocupado = document.querySelector('dialog[open]');
  if (!ocupado && !$('vista-curso').hidden) cargar();
}, 30000);

// =====================================================================
//  RF-08.8 Historial de domicilios
// =====================================================================

const hoy = new Date();
const haceUnaSemana = new Date(hoy.getTime() - 7 * 24 * 3600 * 1000);
const iso = (fecha) => fecha.toLocaleDateString('en-CA'); // AAAA-MM-DD en hora local
$('h-desde').value = iso(haceUnaSemana);
$('h-hasta').value = iso(hoy);

async function cargarHistorial() {
  if (empezarCarga($('lista-historial'))) {
    $('estado-historial').hidden = false;
    $('estado-historial').textContent = 'Cargando…';
  }
  try {
    const parametros = new URLSearchParams({ desde: $('h-desde').value, hasta: $('h-hasta').value });
    const { resumen, domicilios: lista } = await api('GET', `/domicilios/historial?${parametros}`);
    pintarSuave($('resumen-historial'),
      tarjetaResumen('task_alt', 'Entregados', String(resumen.entregados)),
      tarjetaResumen('cancel', 'Cancelados', String(resumen.cancelados)),
      tarjetaResumen('payments', 'Total entregado', formato.dinero(resumen.total_entregado)),
    );
    $('estado-historial').hidden = lista.length > 0;
    $('estado-historial').textContent = 'No hay domicilios en esas fechas';
    pintarSuave($('lista-historial'), ...lista.map((d) => filaDeDomicilio(d, false)));
  } catch (error) {
    $('estado-historial').textContent = error.message;
  }
}

function tarjetaResumen(icono, titulo, valor) {
  return crear('div', { className: 'tarjeta-resumen' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
  ]);
}

$('form-historial').addEventListener('submit', (evento) => {
  evento.preventDefault();
  cargarHistorial();
});

// =====================================================================
//  RF-08.1 Registrar pedido, con RF-08.2 cliente y RF-08.3 dirección
// =====================================================================

const dialogoNuevo = $('dialogo-nuevo');
let clienteElegido = null; // cliente existente, o null
let clienteNuevo = false; // true = se registra al guardar
let carta = []; // productos disponibles hoy
let lineas = []; // [{producto_id, nombre, precio, cantidad}]

if (puedeGestionar) {
  $('boton-nuevo').hidden = false;
  $('boton-nuevo').addEventListener('click', abrirNuevo);
}

async function abrirNuevo() {
  $('form-nuevo').reset();
  for (const campo of ['cliente', 'c-nombre', 'c-telefono', 'direccion', 'productos']) marcarCampo(campo, '');
  $('error-nuevo').hidden = true;
  elegirCliente(null);
  lineas = [];
  pintarLineas();
  dialogoNuevo.showModal();
  $('c-buscar').focus();
  try {
    carta = await api('GET', '/productos?disponible=true');
    $('p-producto').replaceChildren(
      crear('option', { value: '', texto: 'Elige un producto…' }),
      ...carta.map((p) => crear('option', { value: p.id, texto: `${p.nombre} · ${formato.dinero(p.precio_venta)}` })),
    );
  } catch (error) {
    mostrarErrorNuevo(error.message);
  }
}

// ---------------------------------------------------- RF-08.2 Buscar o registrar cliente

let temporizadorBusqueda;
$('c-buscar').addEventListener('input', () => {
  clearTimeout(temporizadorBusqueda);
  temporizadorBusqueda = setTimeout(buscarClientes, 300); // espera a que deje de escribir
});

async function buscarClientes() {
  const texto = $('c-buscar').value.trim();
  if (texto.length < 3) {
    $('sugerencias').replaceChildren();
    return;
  }
  try {
    const clientes = await api('GET', `/clientes?q=${encodeURIComponent(texto)}`);
    const opciones = clientes.map((c) => {
      const li = crear('li', { className: 'alerta-item', tabindex: '0', role: 'button' }, [
        crear('span', { texto: `${c.nombre} · ${c.telefono}` }),
        crear('span', { className: 'nota', texto: c.direccion ?? '' }),
      ]);
      li.addEventListener('click', () => elegirCliente(c));
      return li;
    });
    const nuevo = crear('li', { className: 'alerta-item', tabindex: '0', role: 'button' }, [
      crear('span', { texto: '➕ Registrar cliente nuevo' }),
    ]);
    nuevo.addEventListener('click', () => elegirCliente('nuevo'));
    $('sugerencias').replaceChildren(...opciones, nuevo);
  } catch (error) {
    mostrarErrorNuevo(error.message);
  }
}

/** cliente: un cliente existente, 'nuevo' para registrarlo, o null para volver a buscar. */
function elegirCliente(cliente) {
  clienteNuevo = cliente === 'nuevo';
  clienteElegido = clienteNuevo ? null : cliente;
  $('sugerencias').replaceChildren();
  $('campo-cliente').hidden = Boolean(cliente);
  $('bloque-cliente-nuevo').hidden = !clienteNuevo;
  $('cliente-elegido').hidden = !clienteElegido;
  marcarCampo('cliente', '');

  if (clienteNuevo) {
    const escrito = $('c-buscar').value.trim();
    $(/^\d+$/.test(escrito.replace(/\s/g, '')) ? 'c-telefono' : 'c-nombre').value = escrito;
    const cambiar = crear('button', { type: 'button', className: 'boton-texto', texto: 'Buscar otro cliente' });
    cambiar.addEventListener('click', () => elegirCliente(null));
    $('bloque-cliente-nuevo').querySelector('.nota').replaceChildren(
      crear('span', { texto: 'Cliente nuevo: completa sus datos. ' }), cambiar,
    );
  }
  if (clienteElegido) {
    const cambiar = crear('button', { type: 'button', className: 'boton-texto', texto: 'Cambiar' });
    cambiar.addEventListener('click', () => elegirCliente(null));
    $('cliente-elegido').replaceChildren(
      crear('span', { className: 'icono', texto: 'person', 'aria-hidden': 'true' }),
      crear('span', { texto: `${clienteElegido.nombre} · ${clienteElegido.telefono}` }),
      cambiar,
    );
    // RF-08.3 Se propone la dirección habitual del cliente (se puede cambiar)
    $('d-direccion').value = clienteElegido.direccion ?? '';
    $('d-barrio').value = clienteElegido.barrio ?? '';
    $('d-referencia').value = clienteElegido.referencia ?? '';
  }
}

// ---------------------------------------------------- Productos del pedido

function pintarLineas() {
  const filas = lineas.map((linea, posicion) => {
    const cantidad = crear('input', {
      type: 'number', min: '1', step: '1', 'aria-label': `Cantidad de ${linea.nombre}`,
    });
    cantidad.value = linea.cantidad;
    cantidad.addEventListener('input', () => {
      linea.cantidad = Number(cantidad.value);
      subtotal.textContent = formato.dinero(linea.precio * (linea.cantidad || 0));
      pintarTotal();
    });
    const subtotal = crear('span', { className: 'texto-linea', texto: formato.dinero(linea.precio * linea.cantidad) });
    const quitar = crear('button', { type: 'button', className: 'boton-icono', title: 'Quitar' }, [
      crear('span', { className: 'icono', texto: 'delete', 'aria-hidden': 'true' }),
    ]);
    quitar.addEventListener('click', () => {
      lineas.splice(posicion, 1);
      pintarLineas();
    });
    return crear('div', { className: 'linea con-cantidad' }, [
      crear('span', { className: 'texto-linea', texto: linea.nombre }),
      crear('div', { className: 'campo' }, [cantidad]),
      subtotal,
      quitar,
    ]);
  });
  if (filas.length === 0) filas.push(crear('p', { className: 'nota', texto: 'Agrega los productos que pidió el cliente.' }));
  pintarSuave($('lineas-pedido'), ...filas);
  pintarTotal();
}

function pintarTotal() {
  const productos = lineas.reduce((total, l) => total + l.precio * (l.cantidad || 0), 0);
  const envio = Number($('d-envio').value) || 0;
  $('total-nuevo').textContent = `Total: ${formato.dinero(productos + envio)}`;
}

$('d-envio').addEventListener('input', pintarTotal);

/** Pasa al pedido el producto elegido en la lista. Devuelve false si falta algo. */
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
  const existente = lineas.find((l) => l.producto_id === producto.id);
  if (existente) {
    existente.cantidad += cantidad; // el mismo producto otra vez: suma
  } else {
    lineas.push({ producto_id: producto.id, nombre: producto.nombre, precio: producto.precio_venta, cantidad });
  }
  $('p-producto').value = '';
  $('p-cantidad').value = '1';
  pintarLineas();
  return true;
}

$('agregar-producto').addEventListener('click', agregarProducto);

// ---------------------------------------------------- Validar y guardar

function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`)?.classList.toggle('invalido', Boolean(mensaje));
}

function mostrarErrorNuevo(mensaje) {
  $('error-nuevo').textContent = mensaje;
  $('error-nuevo').hidden = false;
}

function validarNuevo() {
  const errores = {
    cliente: clienteElegido || clienteNuevo ? '' : 'Busca al cliente por su teléfono o regístralo',
    'c-nombre': clienteNuevo && !$('c-nombre').value.trim() ? 'Campo obligatorio' : '',
    'c-telefono': clienteNuevo && !$('c-telefono').value.trim() ? 'Campo obligatorio' : '',
    direccion: $('d-direccion').value.trim() ? '' : 'Escribe la dirección de entrega',
    productos: lineas.length === 0 ? 'Agrega al menos un producto'
      : lineas.every((l) => Number.isInteger(l.cantidad) && l.cantidad > 0) ? ''
        : 'Las cantidades deben ser números enteros mayores que cero',
  };
  for (const [campo, mensaje] of Object.entries(errores)) marcarCampo(campo, mensaje);
  return Object.values(errores).every((mensaje) => !mensaje);
}

$('form-nuevo').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-nuevo').hidden = true;
  // Si quedó un producto elegido sin tocar el botón ⊕, se agrega solo
  if ($('p-producto').value && !agregarProducto()) return;
  if (!validarNuevo()) return;

  const direccion = {
    direccion: $('d-direccion').value.trim(),
    barrio: $('d-barrio').value.trim(),
    referencia: $('d-referencia').value.trim(),
  };

  $('guardar-nuevo').disabled = true;
  try {
    if (clienteNuevo) {
      // RF-08.2 Se registra el cliente con esta dirección como la habitual
      const cliente = await api('POST', '/clientes', {
        nombre: $('c-nombre').value.trim(), telefono: $('c-telefono').value.trim(), ...direccion,
      });
      elegirCliente(cliente); // si el pedido falla, el cliente ya queda registrado
    }
    const domicilio = await api('POST', '/domicilios', { // RF-08.1
      cliente_id: clienteElegido.id,
      ...direccion,
      costo_envio: Number($('d-envio').value) || 0,
      observaciones: $('d-observaciones').value.trim(),
      items: lineas.map((l) => ({ producto_id: l.producto_id, cantidad: l.cantidad })),
    });
    dialogoNuevo.close();
    mostrarAviso(`Domicilio ${domicilio.codigo} registrado`, 'exito');
    cargar();
  } catch (error) {
    mostrarErrorNuevo(error.message); // por ejemplo "No alcanza 'Pollo' para este pedido…"
  } finally {
    $('guardar-nuevo').disabled = false;
  }
});

$('cancelar-nuevo').addEventListener('click', () => dialogoNuevo.close());

// =====================================================================
//  Detalle: RF-08.5 Asignar, RF-08.6 Estado y RF-08.7 Entrega
// =====================================================================

const dialogoDetalle = $('dialogo-detalle');
let domicilioAbierto = null;
let domiciliarios = null; // se cargan la primera vez que se necesitan

// Siguiente paso de cada estado: [estado nuevo, texto del botón]
const SIGUIENTE = {
  RECIBIDO: ['EN_PREPARACION', 'Pasar a preparación'],
  EN_PREPARACION: ['LISTO', 'Marcar listo'],
  LISTO: ['EN_CAMINO', 'Salió a entregar'],
};

async function abrirDetalle(id) {
  $('error-detalle').hidden = true;
  try {
    const domicilio = await api('GET', `/domicilios/${id}`);
    if (puedeGestionar && domiciliarios === null) {
      domiciliarios = await api('GET', '/domiciliarios');
    }
    pintarDetalle(domicilio);
    if (!dialogoDetalle.open) dialogoDetalle.showModal();
  } catch (error) {
    mostrarAviso(error.message, 'error');
  }
}

function pintarDetalle(domicilio) {
  domicilioAbierto = domicilio;
  const { cliente, orden } = domicilio;
  $('detalle-titulo').replaceChildren(
    crear('span', { texto: `${domicilio.codigo} ` }), chipEstado(domicilio.estado),
  );

  const datos = [
    ['Cliente', `${cliente.nombre} · ${domicilio.telefono_contacto}`],
    ['Dirección', [domicilio.direccion, domicilio.barrio].filter(Boolean).join(', ')],
    ['Referencia', domicilio.referencia],
    ['Pedido', `${fechaHora(domicilio.fecha)} por ${orden.usuario}`],
    ['Domiciliario', domicilio.domiciliario],
    ['Salió', domicilio.fecha_salida && fechaHora(domicilio.fecha_salida)],
    ['Entregado', domicilio.fecha_entrega && `${fechaHora(domicilio.fecha_entrega)} · recibió ${domicilio.recibido_por}`],
    ['Observaciones', [orden.observaciones, domicilio.observacion_entrega].filter(Boolean).join(' · ')],
  ].filter(([, valor]) => valor);
  pintarSuave($('detalle-datos'), ...datos.flatMap(([titulo, valor]) => [
    crear('dt', { texto: titulo }), crear('dd', { texto: valor }),
  ]));

  pintarSuave($('detalle-lineas'),
    ...orden.detalles.map((d) => crear('li', {}, [
      crear('span', { texto: `${d.cantidad} × ${d.producto}${d.observacion ? ` (${d.observacion})` : ''}` }),
      crear('span', { texto: formato.dinero(d.subtotal) }),
    ])),
    crear('li', {}, [crear('span', { texto: 'Envío' }), crear('span', { texto: formato.dinero(domicilio.costo_envio) })]),
  );
  $('detalle-total').textContent = `Total: ${formato.dinero(domicilio.total)}`;

  // RF-08.5 Asignar: solo quien gestiona y antes de que salga
  const sePuedeAsignar = puedeGestionar && ['RECIBIDO', 'EN_PREPARACION', 'LISTO'].includes(domicilio.estado);
  $('bloque-asignar').hidden = !sePuedeAsignar;
  if (sePuedeAsignar) {
    $('a-domiciliario').replaceChildren(
      crear('option', { value: '', texto: domiciliarios.length ? 'Elige un domiciliario…' : 'No hay domiciliarios activos' }),
      ...domiciliarios.map((d) => crear('option', { value: d.id, texto: d.nombre })),
    );
    $('a-domiciliario').value = domicilio.domiciliario_id ?? '';
  }

  // RF-08.7 Registrar entrega
  $('bloque-entrega').hidden = domicilio.estado !== 'EN_CAMINO';
  $('e-recibido').value = domicilio.estado === 'EN_CAMINO' ? cliente.nombre : '';
  $('e-observacion').value = '';
  marcarCampo('recibido', '');

  pintarAcciones(domicilio);
}

function pintarAcciones(domicilio) {
  const botones = [];
  const cerrar = crear('button', { type: 'button', className: 'boton-texto', texto: 'Cerrar' });
  cerrar.addEventListener('click', () => dialogoDetalle.close());
  botones.push(cerrar);

  if (puedeGestionar && SIGUIENTE[domicilio.estado]) {
    const cancelar = crear('button', { type: 'button', className: 'boton-texto', texto: 'Cancelar pedido' });
    cancelar.addEventListener('click', () => {
      if (confirm(`¿Cancelar el domicilio ${domicilio.codigo}? No se puede deshacer.`)) {
        cambiarEstado('CANCELADO');
      }
    });
    botones.push(cancelar);
  }

  const siguiente = SIGUIENTE[domicilio.estado];
  // El domiciliario solo puede marcar la salida de un pedido listo
  if (siguiente && (puedeGestionar || domicilio.estado === 'LISTO')) {
    botones.push(botonPrincipal(siguiente[1], 'arrow_forward', () => cambiarEstado(siguiente[0])));
  }
  if (domicilio.estado === 'EN_CAMINO') {
    botones.push(botonPrincipal('Registrar entrega', 'task_alt', registrarEntrega));
  }
  $('detalle-acciones').replaceChildren(...botones);
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

async function ejecutar(metodo, ruta, datos, aviso) {
  $('error-detalle').hidden = true;
  try {
    const actualizado = await api(metodo, ruta, datos);
    mostrarAviso(aviso, 'exito');
    pintarDetalle(actualizado);
    cargar();
  } catch (error) {
    $('error-detalle').textContent = error.message; // por ejemplo "Primero asigna un domiciliario"
    $('error-detalle').hidden = false;
  }
}

function cambiarEstado(estado) {
  return ejecutar('PATCH', `/domicilios/${domicilioAbierto.id}/estado`, { estado },
    `${domicilioAbierto.codigo}: ${NOMBRES_ESTADO[estado]}`);
}

$('boton-asignar').addEventListener('click', () => {
  const domiciliarioId = Number($('a-domiciliario').value);
  if (!domiciliarioId) {
    $('error-detalle').textContent = 'Elige un domiciliario';
    $('error-detalle').hidden = false;
    return;
  }
  ejecutar('PATCH', `/domicilios/${domicilioAbierto.id}/asignar`, { domiciliario_id: domiciliarioId },
    'Domiciliario asignado');
});

function registrarEntrega() {
  const recibidoPor = $('e-recibido').value.trim();
  if (!recibidoPor) {
    marcarCampo('recibido', 'Escribe quién recibió el pedido');
    return Promise.resolve();
  }
  return ejecutar('POST', `/domicilios/${domicilioAbierto.id}/entrega`,
    { recibido_por: recibidoPor, observacion: $('e-observacion').value.trim() },
    `${domicilioAbierto.codigo} entregado`);
}

mostrarPestana(false);
