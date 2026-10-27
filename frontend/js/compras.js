// Órdenes de compra: RF-02.6 Registrar, RF-02.7 Actualizar estado y RF-02.8 Relación con inventario.
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, mostrarEstado, pintarSuave } from './ui.js';

const yo = await exigirSesion('compras.ver'); // sin el permiso vuelve al menú
const puedeGestionar = yo.permisos.includes('compras.gestionar');

const $ = (id) => document.getElementById(id);

// Botones que se muestran según el estado actual (las mismas reglas de la API)
const ACCIONES = {
  PENDIENTE: [
    { estado: 'ENVIADA', texto: 'Marcar como enviada', icono: 'send' },
    { estado: 'CANCELADA', texto: 'Cancelar orden', icono: 'cancel' },
  ],
  ENVIADA: [
    { estado: 'RECIBIDA', texto: 'Recibir mercancía', icono: 'inventory' },
    { estado: 'CANCELADA', texto: 'Cancelar orden', icono: 'cancel' },
  ],
  RECIBIDA: [],
  CANCELADA: [],
};

// =====================================================================
//  Lista de órdenes con filtro por estado
// =====================================================================

async function cargar() {
  if (empezarCarga($('lista'))) mostrarEstado('Cargando…', { cargando: true }); // al recargar, la lista se queda atenuada
  try {
    const estado = $('filtro-estado').value;
    const ordenes = await api('GET', `/ordenes-compra${estado ? `?estado=${estado}` : ''}`);
    if (ordenes.length === 0) {
      mostrarEstado(estado ? 'No hay órdenes con ese estado' : 'Todavía no hay órdenes de compra', {
        icono: 'shopping_cart',
        detalle: estado ? 'Elige otro estado en el filtro.' : 'Pide insumos a un proveedor y registra aquí cuando lleguen.',
        accion: !estado && puedeGestionar ? { texto: 'Crear la primera orden', alHacer: abrirNueva } : null,
      });
      pintarSuave($('lista'));
    } else {
      $('estado').hidden = true;
      pintarSuave($('lista'), ...ordenes.map(filaDeOrden));
    }
  } catch (error) {
    mostrarEstado(error.message, { reintentar: true });
  }
}

function filaDeOrden(orden) {
  const fila = crear('li', { className: 'fila editable' }, [
    crear('div', { className: 'avatar' }, [
      crear('span', { className: 'icono', texto: 'receipt_long', 'aria-hidden': 'true' }),
    ]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: `${orden.codigo} · ${orden.proveedor}` }),
      crear('div', { className: 'correo', texto: `${formato.fecha(orden.fecha_orden)} · ${formato.dinero(orden.total)}` }),
    ]),
    crear('div', { className: 'chips' }, [
      crear('span', { className: `chip estado-${orden.estado}`, texto: orden.estado }),
    ]),
  ]);
  fila.addEventListener('click', () => abrirDetalle(orden.id));
  return fila;
}

$('filtro-estado').addEventListener('change', cargar);
$('reintentar').addEventListener('click', cargar);

// =====================================================================
//  Detalle de una orden y cambio de estado (RF-02.7 y RF-02.8)
// =====================================================================

const dialogoDetalle = $('dialogo-detalle');

async function abrirDetalle(id) {
  $('error-detalle').hidden = true;
  try {
    const orden = await api('GET', `/ordenes-compra/${id}`);
    pintarDetalle(orden);
    if (!dialogoDetalle.open) dialogoDetalle.showModal();
  } catch (error) {
    mostrarAviso(error.message, 'error');
  }
}

function pintarDetalle(orden) {
  $('detalle-titulo').textContent = `Orden ${orden.codigo}`;

  const datos = [
    ['Proveedor', orden.proveedor],
    ['Estado', null],
    ['Registrada', `${formato.fecha(orden.fecha_orden)} por ${orden.usuario}`],
    ['Entrega estimada', formato.fecha(orden.fecha_entrega_estimada)],
    ['Recibida', formato.fecha(orden.fecha_recepcion)],
    ['Observaciones', orden.observaciones || '—'],
  ];
  pintarSuave($('detalle-datos'), ...datos.flatMap(([etiqueta, valor]) => [
    crear('dt', { texto: etiqueta }),
    valor === null
      ? crear('dd', {}, [crear('span', { className: `chip estado-${orden.estado}`, texto: orden.estado })])
      : crear('dd', { texto: valor }),
  ]));

  pintarSuave($('detalle-lineas'), ...orden.detalles.map((linea) => crear('li', {}, [
    crear('span', {
      texto: `${linea.insumo} · ${formato.cantidad(linea.cantidad)} ${linea.unidad_medida} × ${formato.dinero(linea.precio_unitario)}`,
    }),
    crear('strong', { texto: formato.dinero(linea.subtotal) }),
  ])));
  $('detalle-total').textContent = `Total: ${formato.dinero(orden.total)}`;

  // Botones de cambio de estado: solo con el permiso compras.gestionar
  const botones = puedeGestionar ? ACCIONES[orden.estado].map((accion) => {
    const boton = crear('button', {
      type: 'button',
      className: accion.estado === 'CANCELADA' ? 'boton-texto' : 'boton-principal',
    }, [
      crear('span', { className: 'icono', texto: accion.icono, 'aria-hidden': 'true' }),
      crear('span', { texto: ` ${accion.texto}` }),
    ]);
    boton.addEventListener('click', () => cambiarEstado(orden, accion.estado));
    return boton;
  }) : [];
  const cerrar = crear('button', { type: 'button', className: 'boton-texto', texto: 'Cerrar' });
  cerrar.addEventListener('click', () => dialogoDetalle.close());
  $('detalle-acciones').replaceChildren(cerrar, ...botones);
}

async function cambiarEstado(orden, estado) {
  const preguntas = {
    RECIBIDA: '¿Confirmas que llegó la mercancía? El stock de cada insumo aumentará con lo comprado.',
    CANCELADA: '¿Seguro que quieres cancelar esta orden? No se puede deshacer.',
  };
  if (preguntas[estado] && !window.confirm(preguntas[estado])) return;

  try {
    const actualizada = await api('PATCH', `/ordenes-compra/${orden.id}/estado`, { estado });
    pintarDetalle(actualizada);
    mostrarAviso(estado === 'RECIBIDA'
      ? 'Orden recibida: el inventario se actualizó'
      : `Orden ${actualizada.estado.toLowerCase()}`, 'exito');
    cargar();
  } catch (error) {
    $('error-detalle').textContent = error.message;
    $('error-detalle').hidden = false;
  }
}

// =====================================================================
//  RF-02.6 Registrar una orden de compra
// =====================================================================

const dialogoNueva = $('dialogo-nueva');
let insumos = []; // insumos activos
let preciosProveedor = new Map(); // insumo_id -> precio de referencia del proveedor elegido

if (puedeGestionar) {
  $('boton-nueva').hidden = false;
  $('boton-nueva').addEventListener('click', abrirNueva);
}

async function abrirNueva() {
  $('form-orden').reset();
  $('error-nueva').hidden = true;
  marcar('proveedor', '');
  $('error-lineas').textContent = '';
  $('lineas').replaceChildren();
  preciosProveedor = new Map();
  dialogoNueva.showModal();

  try {
    const [proveedores, listaInsumos] = await Promise.all([
      api('GET', '/proveedores?activo=true'),
      api('GET', '/insumos?activo=true'),
    ]);
    insumos = listaInsumos;
    $('f-proveedor').replaceChildren(
      crear('option', { value: '', texto: 'Elige un proveedor' }),
      ...proveedores.map((p) => crear('option', { value: p.id, texto: p.razon_social })),
    );
    agregarLinea();
  } catch (error) {
    $('error-nueva').textContent = error.message;
    $('error-nueva').hidden = false;
  }
}

// Al elegir proveedor se traen sus precios de referencia
$('f-proveedor').addEventListener('change', async () => {
  preciosProveedor = new Map();
  const id = $('f-proveedor').value;
  if (!id) return;
  const proveedor = await api('GET', `/proveedores/${id}`);
  for (const item of proveedor.insumos) {
    if (item.precio_referencia !== null) preciosProveedor.set(item.insumo_id, item.precio_referencia);
  }
  for (const linea of $('lineas').children) linea.rellenarPrecio?.();
});

/** Agrega una línea: insumo, cantidad, precio unitario y botón para quitarla. */
function agregarLinea() {
  const selector = crear('select', { 'aria-label': 'Insumo' }, [
    crear('option', { value: '', texto: 'Insumo…' }),
    ...insumos.map((i) => crear('option', { value: i.id, texto: `${i.nombre} (${i.unidad_medida})` })),
  ]);
  const cantidad = crear('input', { type: 'number', min: '0', step: 'any', placeholder: 'Cant.', 'aria-label': 'Cantidad' });
  const precio = crear('input', { type: 'number', min: '0', step: 'any', placeholder: 'Precio', 'aria-label': 'Precio unitario' });
  const quitar = crear('button', { type: 'button', className: 'boton-icono', title: 'Quitar' }, [
    crear('span', { className: 'icono', texto: 'delete', 'aria-hidden': 'true' }),
  ]);

  const linea = crear('div', { className: 'linea con-cantidad' }, [
    crear('div', { className: 'campo' }, [selector]),
    crear('div', { className: 'campo' }, [cantidad]),
    crear('div', { className: 'campo' }, [precio]),
    quitar,
  ]);
  linea.datos = () => ({ insumo_id: Number(selector.value), cantidad: cantidad.value, precio: precio.value });
  linea.rellenarPrecio = () => {
    const sugerido = preciosProveedor.get(Number(selector.value));
    if (sugerido !== undefined && precio.value === '') precio.value = sugerido;
    calcularTotal();
  };

  selector.addEventListener('change', linea.rellenarPrecio);
  cantidad.addEventListener('input', calcularTotal);
  precio.addEventListener('input', calcularTotal);
  quitar.addEventListener('click', () => {
    linea.remove();
    calcularTotal();
  });
  $('lineas').appendChild(linea);
}

$('agregar-linea').addEventListener('click', agregarLinea);

function calcularTotal() {
  let total = 0;
  for (const linea of $('lineas').children) {
    const { cantidad, precio } = linea.datos();
    total += (Number(cantidad) || 0) * (Number(precio) || 0);
  }
  $('total').textContent = `Total: ${formato.dinero(total)}`;
}

function marcar(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`).classList.toggle('invalido', Boolean(mensaje));
}

$('form-orden').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-nueva').hidden = true;

  const lineas = [...$('lineas').children].map((linea) => linea.datos());
  const errorProveedor = $('f-proveedor').value ? '' : 'Elige un proveedor';
  let errorLineas = '';
  if (lineas.length === 0) errorLineas = 'Agrega al menos un insumo';
  else if (lineas.some((l) => !l.insumo_id)) errorLineas = 'Elige el insumo de cada línea';
  else if (lineas.some((l) => !(Number(l.cantidad) > 0))) errorLineas = 'Cada cantidad debe ser mayor que cero';
  else if (lineas.some((l) => l.precio === '' || Number(l.precio) < 0)) errorLineas = 'Escribe el precio de cada insumo';
  marcar('proveedor', errorProveedor);
  $('error-lineas').textContent = errorLineas;
  if (errorProveedor || errorLineas) return;

  $('guardar-orden').disabled = true;
  try {
    const orden = await api('POST', '/ordenes-compra', {
      proveedor_id: Number($('f-proveedor').value),
      fecha_entrega_estimada: $('f-entrega').value || null,
      observaciones: $('f-observaciones').value.trim(),
      detalles: lineas.map((l) => ({
        insumo_id: l.insumo_id, cantidad: Number(l.cantidad), precio_unitario: Number(l.precio),
      })),
    });
    dialogoNueva.close();
    mostrarAviso(`Orden ${orden.codigo} registrada`, 'exito');
    cargar();
  } catch (error) {
    $('error-nueva').textContent = error.message; // por ejemplo "El insumo 'Arroz' está repetido"
    $('error-nueva').hidden = false;
  } finally {
    $('guardar-orden').disabled = false;
  }
});

$('cancelar-nueva').addEventListener('click', () => dialogoNueva.close());

cargar();
