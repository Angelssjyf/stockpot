// Módulo de pedidos en mesa (RF-05.1 a RF-05.9): mesas, pedidos, cocina y estado.
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, normalizar, pintarSuave } from './ui.js';

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
  pintarSuave($('resumen-mesas'),
    tarjetaResumen('event_available', 'Mesas libres', String(mesas.length - ocupadas.length)),
    tarjetaResumen('groups', 'Mesas ocupadas', String(ocupadas.length)),
    tarjetaResumen('payments', 'En mesas sin cobrar', formato.dinero(porCobrar)),
  );
  $('estado-mesas').hidden = mesas.length > 0;
  $('estado-mesas').textContent = puedeGestionar
    ? 'Todavía no hay mesas. Créalas con «Administrar mesas».' : 'Todavía no hay mesas registradas.';
  pintarSuave($('mesas'), ...mesas.map(tarjetaMesa));
}

function tarjetaMesa(mesa) {
  // Como las tarjetas del menú: arriba el número en un marquito, al centro el ícono y abajo su estado
  const partes = [
    crear('span', { className: 'marco-mesa', texto: `Mesa ${mesa.numero}` }),
    crear('span', { className: 'icono icono-mesa', texto: 'table_restaurant', 'aria-hidden': 'true' }),
  ];
  if (mesa.ocupada) {
    const p = mesa.pedido;
    partes.push(
      chipEstado(p.estado),
      crear('span', { className: 'estado-mesa', texto: `${p.codigo} · ${formato.dinero(p.total)}` }),
      crear('span', { className: 'detalle-mesa', texto: `${p.productos} producto${p.productos === 1 ? '' : 's'} · ${espera(p.fecha)}` }),
    );
  } else {
    partes.push(
      crear('span', { className: 'estado-mesa', texto: 'Libre' }),
      crear('span', { className: 'detalle-mesa' }, [
        crear('span', { className: 'icono', texto: 'group', 'aria-hidden': 'true' }),
        document.createTextNode([`${mesa.capacidad}`, mesa.ubicacion].filter(Boolean).join(' · ')),
      ]),
    );
  }
  const tarjeta = crear('button', {
    type: 'button', className: `mesa${mesa.ocupada ? ' ocupada' : ''}`,
    'aria-label': `Mesa ${mesa.numero}, ${mesa.ocupada ? 'ocupada' : 'libre'}`,
    // Clave y versión: al refrescar solo se ilumina la mesa que cambió (no por el "hace N min")
    'data-clave': mesa.id,
    'data-version': mesa.ocupada ? [mesa.pedido.codigo, mesa.pedido.estado, mesa.pedido.total, mesa.pedido.productos].join('|') : 'libre',
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
  const fila = crear('li', { className: 'fila editable', 'data-clave': pedido.id, 'data-version': `${pedido.estado}|${pedido.total}` }, [
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
  pintarSuave($('lista-activos'), ...visibles.map((p) => filaDePedido(p, true)));
}

const iso = (fecha) => fecha.toLocaleDateString('en-CA'); // AAAA-MM-DD en hora local
$('h-desde').value = iso(new Date(Date.now() - 7 * 24 * 3600 * 1000));
$('h-hasta').value = iso(new Date());

async function cargarHistorial() {
  if (empezarCarga($('lista-historial'))) {
    $('estado-historial').hidden = false;
    $('estado-historial').textContent = 'Cargando…';
  }
  try {
    const parametros = new URLSearchParams({ vista: 'historial', desde: $('h-desde').value, hasta: $('h-hasta').value });
    if ($('h-codigo').value.trim()) parametros.set('q', $('h-codigo').value.trim());
    const lista = await api('GET', `/pedidos?${parametros}`);
    $('estado-historial').hidden = lista.length > 0;
    $('estado-historial').textContent = 'No hay pedidos en esas fechas';
    pintarSuave($('lista-historial'), ...lista.map((p) => filaDePedido(p, false)));
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
let categoriaCarta = ''; // '' = toda la carta

const CATEGORIAS = {
  ENTRADA: 'Entradas', PLATO_FUERTE: 'Platos fuertes', BEBIDA: 'Bebidas', POSTRE: 'Postres', ADICIONAL: 'Adicionales',
};
const ICONOS_CATEGORIA = {
  ENTRADA: 'tapas', PLATO_FUERTE: 'dinner_dining', BEBIDA: 'local_bar', POSTRE: 'cake', ADICIONAL: 'add_circle',
};
// Lo que más piden los clientes, según el tipo de producto (se tocan para agregarlas a la observación)
const SUGERENCIAS = {
  ENTRADA: ['Sin cebolla', 'Sin picante', 'Salsa aparte', 'Para compartir'],
  PLATO_FUERTE: ['Sin cebolla', 'Término medio', 'Bien asado', 'Sin sal', 'Salsa aparte', 'Sin ensalada'],
  BEBIDA: ['Sin hielo', 'Sin azúcar', 'Bien fría', 'Al clima'],
  POSTRE: ['Sin azúcar', 'Con vela', 'Para llevar'],
  ADICIONAL: ['Aparte', 'Para llevar'],
};

if (puedeGestionar) $('boton-nuevo').addEventListener('click', () => abrirFormulario(null));

async function cargarCarta() {
  carta = await api('GET', '/productos?disponible=true');
}

/** El nombre con la parte buscada resaltada (con nodos de texto, nunca HTML). */
function nombreResaltado(nombre, texto) {
  const original = nombre.normalize('NFC'); // así cada letra con tilde ocupa lo mismo que sin tilde
  const posicion = texto ? normalizar(original).indexOf(texto) : -1;
  if (posicion < 0) return [document.createTextNode(original)];
  return [
    document.createTextNode(original.slice(0, posicion)),
    crear('mark', { texto: original.slice(posicion, posicion + texto.length) }),
    document.createTextNode(original.slice(posicion + texto.length)),
  ];
}

/** Los productos de la carta que coinciden por nombre, categoría o código; primero los que empiezan así. */
function coincidencias(texto) {
  return carta
    .filter((p) => normalizar(`${p.nombre} ${CATEGORIAS[p.categoria] ?? ''} ${p.codigo}`).includes(texto))
    .sort((a, b) => normalizar(b.nombre).startsWith(texto) - normalizar(a.nombre).startsWith(texto));
}

/**
 * Buscador de la carta: al escribir (o al tocar el campo) muestra los productos que coinciden por
 * nombre, categoría o código; al tocar uno, o con Enter, llama a alElegir(producto).
 * Con las flechas se recorre la lista y con Escape se cierra sin cerrar la ventana.
 */
function buscadorDeCarta(entrada, lista, alElegir) {
  let resultados = [];
  let marcado = -1;

  function marcar(posicion) {
    marcado = posicion;
    [...lista.children].forEach((li, i) => {
      li.classList.toggle('marcado', i === marcado);
      li.setAttribute('aria-selected', String(i === marcado));
    });
    lista.children[marcado]?.scrollIntoView({ block: 'nearest' });
  }

  function abrir() {
    const texto = normalizar(entrada.value.trim());
    resultados = coincidencias(texto);
    lista.replaceChildren(...(resultados.length ? resultados.map((producto) => {
      const quedan = producto.porciones_posibles;
      const detalle = [CATEGORIAS[producto.categoria], quedan != null && quedan <= 10 ? `quedan ${quedan}` : null].filter(Boolean).join(' · ');
      const opcion = crear('li', { role: 'option' }, [
        crear('div', {}, [
          crear('div', { className: 'nombre-producto' }, nombreResaltado(producto.nombre, texto)),
          ...(detalle ? [crear('small', { texto: detalle })] : []),
        ]),
        crear('span', { className: 'precio', texto: formato.dinero(producto.precio_venta) }),
        crear('span', { className: 'icono', texto: 'add_circle', 'aria-hidden': 'true' }),
      ]);
      opcion.addEventListener('mousedown', (evento) => evento.preventDefault()); // el campo no pierde el foco
      opcion.addEventListener('click', () => elegir(producto));
      return opcion;
    }) : [crear('li', { className: 'sin-resultados', texto: carta.length ? 'No hay productos con ese nombre' : 'No hay productos disponibles hoy' })]));
    lista.hidden = false;
    lista.scrollTop = 0;
    entrada.setAttribute('aria-expanded', 'true');
    marcar(texto && resultados.length ? 0 : -1); // con algo escrito, Enter agrega el primero
  }

  function cerrar() {
    lista.hidden = true;
    entrada.setAttribute('aria-expanded', 'false');
  }

  function elegir(producto) {
    if (alElegir(producto) === false) return;
    entrada.value = '';
    cerrar();
    const campo = entrada.closest('.campo');
    campo.classList.remove('agregado');
    void campo.offsetWidth; // reinicia la animación si se agregan dos seguidos
    campo.classList.add('agregado');
  }

  entrada.addEventListener('input', abrir);
  entrada.addEventListener('click', abrir); // al tocar el campo se ve toda la carta
  entrada.addEventListener('blur', () => setTimeout(cerrar, 150)); // deja terminar el toque sobre un producto
  entrada.addEventListener('keydown', (evento) => {
    if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
      evento.preventDefault();
      if (lista.hidden) abrir();
      const paso = evento.key === 'ArrowDown' ? 1 : -1;
      if (resultados.length) marcar((marcado + paso + resultados.length) % resultados.length);
    } else if (evento.key === 'Enter') {
      evento.preventDefault(); // no envía el formulario
      if (!lista.hidden && resultados[marcado]) elegir(resultados[marcado]);
    } else if (evento.key === 'Escape' && !lista.hidden) {
      evento.preventDefault(); // cierra la lista, no la ventana
      cerrar();
    }
  });
  return { cerrar };
}

const buscadorDetalle = buscadorDeCarta($('a-buscar'), $('a-resultados'), agregarAlPedidoAbierto);

// ---------------------------------------------------------------- La carta dentro de la ventana del pedido

function pintarCategoriasCarta() {
  const presentes = Object.entries(CATEGORIAS).filter(([valor]) => carta.some((p) => p.categoria === valor));
  $('p-categorias').replaceChildren(...[['', 'Todo'], ...presentes].map(([valor, texto]) => {
    const boton = crear('button', {
      type: 'button', className: 'chip filtro', texto, 'aria-pressed': String(valor === categoriaCarta),
    });
    boton.addEventListener('click', () => {
      categoriaCarta = valor;
      pintarCategoriasCarta();
      pintarCarta();
    });
    return boton;
  }));
}

/** Los platos que se ven: filtrados por lo escrito y la categoría; los que ya van en el pedido muestran "× 2". */
function pintarCarta() {
  const texto = normalizar($('p-buscar').value.trim());
  const visibles = coincidencias(texto).filter((p) => !categoriaCarta || p.categoria === categoriaCarta);
  pintarSuave($('p-carta'), visibles.length ? visibles.map((producto) => platoDeCarta(producto, texto))
    : [crear('li', { className: 'nota sin-resultados', 'data-clave': 'vacio',
      texto: carta.length ? 'No hay platos con ese nombre' : 'No hay productos disponibles hoy' })]);
}

function platoDeCarta(producto, texto) {
  const enPedido = lineas.filter((l) => l.producto_id === producto.id).reduce((suma, l) => suma + (l.cantidad || 0), 0);
  const quedan = producto.porciones_posibles;
  const detalle = [producto.descripcion, quedan != null && quedan <= 10 ? `quedan ${quedan}` : null].filter(Boolean).join(' · ');
  const boton = crear('button', {
    type: 'button', className: `plato${enPedido ? ' en-pedido' : ''}`,
    'aria-label': `${producto.nombre}, ${formato.dinero(producto.precio_venta)}${enPedido ? `, ${enPedido} en el pedido` : ''}`,
  }, [
    crear('span', { className: 'icono icono-categoria', texto: ICONOS_CATEGORIA[producto.categoria] ?? 'restaurant', 'aria-hidden': 'true' }),
    crear('span', { className: 'datos-plato' }, [
      crear('span', { className: 'nombre-producto' }, nombreResaltado(producto.nombre, texto)),
      crear('small', { texto: detalle || CATEGORIAS[producto.categoria] || '' }),
    ]),
    crear('span', { className: 'precio-plato' }, [
      crear('span', { className: 'precio', texto: formato.dinero(producto.precio_venta) }),
      enPedido ? crear('span', { className: 'chip contador-plato', texto: `× ${enPedido}` })
        : crear('span', { className: 'icono', texto: 'add_circle', 'aria-hidden': 'true' }),
    ]),
  ]);
  boton.addEventListener('click', () => elegirPlato(producto));
  return crear('li', { 'data-clave': producto.id, 'data-version': enPedido }, [boton]);
}

$('p-buscar').addEventListener('input', pintarCarta);
$('p-buscar').addEventListener('keydown', (evento) => {
  if (evento.key !== 'Enter') return;
  evento.preventDefault(); // no envía el formulario: con un solo plato a la vista, lo abre
  const visibles = coincidencias(normalizar($('p-buscar').value.trim())).filter((p) => !categoriaCarta || p.categoria === categoriaCarta);
  if (visibles.length === 1) elegirPlato(visibles[0]);
});

/** Al tocar un plato de la carta se abre su ventana para la cantidad y las observaciones. */
function elegirPlato(producto) {
  abrirPlato(producto, {
    alGuardar: ({ cantidad, observacion }) => {
      marcarCampo('productos', '');
      const existente = lineas.find((l) => l.producto_id === producto.id && l.observacion === observacion);
      if (existente) existente.cantidad += cantidad; // el mismo plato con la misma observación: suma
      else lineas.push({ producto_id: producto.id, nombre: producto.nombre, precio: producto.precio_venta, cantidad, observacion });
      pintarLineas();
      mostrarAviso(`${cantidad} × ${producto.nombre} agregado`, 'exito');
    },
  });
}

/** Cambiar la cantidad o las observaciones de una línea ya agregada (o quitarla). */
function editarLinea(posicion) {
  const linea = lineas[posicion];
  const producto = carta.find((p) => p.id === linea.producto_id)
    ?? { id: linea.producto_id, nombre: linea.nombre, precio_venta: linea.precio };
  abrirPlato(producto, {
    cantidad: linea.cantidad, observacion: linea.observacion, textoGuardar: 'Guardar',
    alGuardar: ({ cantidad, observacion }) => {
      const igual = lineas.find((l, i) => i !== posicion && l.producto_id === linea.producto_id && l.observacion === observacion);
      if (igual) { // quedó igual a otra línea: se juntan
        igual.cantidad += cantidad;
        lineas.splice(posicion, 1);
      } else {
        Object.assign(linea, { cantidad, observacion });
      }
      pintarLineas();
    },
    alQuitar: () => {
      lineas.splice(posicion, 1);
      pintarLineas();
    },
  });
}

/** pedido: el pedido a modificar, o null para uno nuevo. mesaId: mesa elegida al tocar una mesa libre. */
async function abrirFormulario(pedido, mesaId = null) {
  pedidoEditado = pedido;
  $('form-pedido').reset();
  for (const campo of ['mesa', 'comensales', 'productos']) marcarCampo(campo, '');
  $('error-pedido').hidden = true;
  $('disponibilidad').hidden = true;
  $('titulo-pedido').textContent = pedido ? `Modificar ${pedido.codigo}` : 'Nuevo pedido';
  categoriaCarta = '';
  lineas = pedido ? pedido.detalles.map((d) => ({
    producto_id: d.producto_id, nombre: d.producto, precio: d.precio_unitario, cantidad: d.cantidad, observacion: d.observacion,
  })) : [];
  pintarLineas();
  pintarSuave($('p-carta'), crear('li', { className: 'nota', texto: 'Cargando la carta…' }));
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
    ponerTituloPedido();
    pintarCategoriasCarta();
    pintarLineas();
  } catch (error) {
    mostrarErrorPedido(error.message);
  }
}

/** "Mesa 3 · Nuevo pedido" en cuanto se sabe la mesa. */
function ponerTituloPedido() {
  if (pedidoEditado) return;
  const opcion = $('p-mesa').selectedOptions[0];
  $('titulo-pedido').textContent = $('p-mesa').value ? `${opcion.textContent.split(' · ')[0]} · Nuevo pedido` : 'Nuevo pedido';
}

$('p-mesa').addEventListener('change', ponerTituloPedido);

function pintarLineas() {
  const filas = lineas.map((linea, posicion) => {
    const cantidad = crear('input', { type: 'number', min: '1', step: '1', 'aria-label': `Cantidad de ${linea.nombre}` });
    cantidad.value = linea.cantidad;
    cantidad.addEventListener('input', () => {
      linea.cantidad = Number(cantidad.value);
      subtotal.textContent = formato.dinero(linea.precio * (linea.cantidad || 0));
      pintarTotal();
      revisarDisponibilidad();
      pintarCarta();
    });
    const subtotal = crear('span', { className: 'texto-linea', texto: formato.dinero(linea.precio * linea.cantidad) });
    const quitar = crear('button', { type: 'button', className: 'boton-icono', title: 'Quitar' }, [
      crear('span', { className: 'icono', texto: 'delete', 'aria-hidden': 'true' }),
    ]);
    quitar.addEventListener('click', () => {
      lineas.splice(posicion, 1);
      pintarLineas();
    });
    const nombre = crear('button', { type: 'button', className: 'nombre-linea', title: 'Cambiar cantidad u observaciones' }, [
      crear('span', { className: 'texto-linea', texto: linea.nombre }),
      crear('small', { className: `observacion-linea${linea.observacion ? '' : ' vacia'}` }, [
        crear('span', { className: 'icono', texto: 'edit_note', 'aria-hidden': 'true' }),
        document.createTextNode(linea.observacion || 'Agregar observación'),
      ]),
    ]);
    nombre.addEventListener('click', () => editarLinea(posicion));
    return crear('div', {
      className: 'linea con-cantidad', 'data-clave': `${linea.producto_id}|${linea.observacion ?? ''}`, 'data-version': linea.cantidad,
    }, [nombre, crear('div', { className: 'campo' }, [cantidad]), subtotal, quitar]);
  });
  if (filas.length === 0) filas.push(crear('p', { className: 'nota', 'data-clave': 'vacio', texto: 'Toca los platos de la carta para agregarlos.' }));
  pintarSuave($('lineas-pedido'), filas);
  pintarTotal();
  revisarDisponibilidad();
  pintarCarta();
}

function pintarTotal() {
  const total = lineas.reduce((suma, l) => suma + l.precio * (l.cantidad || 0), 0);
  $('total-pedido').textContent = `Total: ${formato.dinero(total)}`;
  $('texto-guardar').textContent = `${pedidoEditado ? 'Guardar cambios' : 'Registrar pedido'}${total ? ` · ${formato.dinero(total)}` : ''}`;
}

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
    mostrarAviso(pedidoEditado ? `${pedido.codigo} actualizado` : `Pedido ${pedido.codigo} registrado en la mesa ${pedido.mesa.numero}`, 'exito');
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
    mostrarAviso(error.message, 'error');
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
  pintarSuave($('detalle-datos'), ...datos.flatMap(([titulo, valor]) => [crear('dt', { texto: titulo }), crear('dd', { texto: valor })]));

  // RF-05.9 Recorrido: cada paso con su hora
  pintarSuave($('detalle-tiempo'), ...pedido.linea_de_tiempo.map((paso) =>
    crear('li', { texto: `${NOMBRES_ESTADO[paso.estado]} ${hora(paso.fecha)}` })));

  pintarSuave($('detalle-lineas'), ...pedido.detalles.map((d) => crear('li', {}, [
    crear('span', { texto: `${d.cantidad} × ${d.producto}${d.observacion ? ` (${d.observacion})` : ''}` }),
    crear('span', { texto: formato.dinero(d.subtotal) }),
  ])));
  $('detalle-total').textContent = `Total: ${formato.dinero(pedido.total)}`;

  // RF-05.3 Agregar productos: solo mientras no vaya para cocina
  const sePuedeAgregar = puedeGestionar && pedido.editable;
  $('bloque-agregar').hidden = !sePuedeAgregar;
  $('a-buscar').value = '';
  buscadorDetalle.cerrar();
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
    mostrarAviso(aviso, 'exito');
    pintarDetalle(actualizado);
    refrescar();
    return true;
  } catch (error) {
    $('error-detalle').textContent = error.message; // por ejemplo "Primero confirma el pedido con el cliente"
    $('error-detalle').hidden = false;
    return false;
  }
}

/** RF-05.3 Al elegir un producto en el detalle se abre su ventana (cantidad y observaciones) y se agrega. */
function agregarAlPedidoAbierto(producto) {
  abrirPlato(producto, {
    textoGuardar: 'Agregar al pedido',
    alGuardar: ({ cantidad, observacion }) => {
      ejecutar('POST', `/pedidos/${pedidoAbierto.id}/productos`, { items: [{ producto_id: producto.id, cantidad, observacion }] },
        `${cantidad} × ${producto.nombre} agregado al pedido`);
    },
  });
  return true;
}

// =====================================================================
//  Ventana del plato: cantidad y observaciones del cliente
// =====================================================================

const dialogoPlato = $('dialogo-plato');
let platoAbierto = null; // { producto, alGuardar, alQuitar, textoGuardar, cantidad }

/** Abre la ventana de un plato. alGuardar recibe { cantidad, observacion }; alQuitar (opcional) muestra "Quitar". */
function abrirPlato(producto, { cantidad = 1, observacion = '', textoGuardar = 'Agregar', alGuardar, alQuitar = null }) {
  platoAbierto = { producto, alGuardar, alQuitar, textoGuardar, cantidad: 1 };
  $('plato-icono').textContent = ICONOS_CATEGORIA[producto.categoria] ?? 'restaurant';
  $('plato-nombre').textContent = producto.nombre;
  $('plato-detalle').textContent = [CATEGORIAS[producto.categoria], formato.dinero(producto.precio_venta)].filter(Boolean).join(' · ');
  $('plato-descripcion').textContent = producto.descripcion ?? '';
  $('plato-descripcion').hidden = !producto.descripcion;
  $('plato-observacion').value = observacion ?? '';
  $('plato-quitar').hidden = !alQuitar;
  ponerCantidad(cantidad);
  pintarSugerencias();
  dialogoPlato.showModal();
}

function ponerCantidad(cantidad) {
  platoAbierto.cantidad = Math.min(Math.max(cantidad, 1), 99);
  $('plato-cantidad').textContent = platoAbierto.cantidad;
  $('plato-menos').disabled = platoAbierto.cantidad === 1;
  $('plato-texto-guardar').textContent =
    `${platoAbierto.textoGuardar} · ${formato.dinero(platoAbierto.producto.precio_venta * platoAbierto.cantidad)}`;
}

/** Las observaciones escritas, separadas por comas. */
function partesObservacion() {
  return $('plato-observacion').value.split(',').map((parte) => parte.trim()).filter(Boolean);
}

/** Chips con lo que más se pide; se ven marcadas las que ya están en la observación. */
function pintarSugerencias() {
  const escritas = partesObservacion().map(normalizar);
  const sugerencias = SUGERENCIAS[platoAbierto.producto.categoria] ?? ['Para llevar'];
  $('plato-sugerencias').replaceChildren(...sugerencias.map((texto) => {
    const marcada = escritas.includes(normalizar(texto));
    const chip = crear('button', { type: 'button', className: 'chip filtro', texto, 'aria-pressed': String(marcada) });
    chip.addEventListener('click', () => {
      const partes = partesObservacion();
      const resto = partes.filter((parte) => normalizar(parte) !== normalizar(texto));
      $('plato-observacion').value = (marcada ? resto : [...partes, texto]).join(', ').slice(0, 150);
      pintarSugerencias();
    });
    return chip;
  }));
  $('plato-caracteres').textContent = `${$('plato-observacion').value.length} / 150`;
}

$('plato-observacion').addEventListener('input', pintarSugerencias);
$('plato-menos').addEventListener('click', () => ponerCantidad(platoAbierto.cantidad - 1));
$('plato-mas').addEventListener('click', () => ponerCantidad(platoAbierto.cantidad + 1));
$('plato-cancelar').addEventListener('click', () => dialogoPlato.close());
$('plato-quitar').addEventListener('click', () => {
  platoAbierto.alQuitar();
  dialogoPlato.close();
});
$('form-plato').addEventListener('submit', (evento) => {
  evento.preventDefault();
  platoAbierto.alGuardar({ cantidad: platoAbierto.cantidad, observacion: $('plato-observacion').value.trim() || null });
  dialogoPlato.close();
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
    pintarSuave($('lista-admin-mesas'), ...todas.map((m) => {
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
    mostrarAviso(`Mesa ${mesa.numero} guardada`, 'exito');
    editarMesa(null);
    await pintarAdminMesas();
  } catch (error) {
    $('error-mesas').textContent = error.message; // por ejemplo "Ya existe la mesa 3"
    $('error-mesas').hidden = false;
  }
});

mostrarVista('mesas');
