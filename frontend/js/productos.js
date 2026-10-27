// Módulo de productos y menú (RF-04.1 a RF-04.6): carta, recetas, precios y disponibilidad.
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, mostrarEstado, pintarSuave } from './ui.js';

const yo = await exigirSesion('productos.ver'); // sin el permiso vuelve al menú
const puedeGestionar = yo.permisos.includes('productos.gestionar');
// La cocina también puede marcar un plato como agotado (RF-04.6)
const puedeCambiarDisponibilidad = puedeGestionar || yo.permisos.includes('cocina.gestionar');

const $ = (id) => document.getElementById(id);

const CATEGORIAS = {
  ENTRADA: 'Entradas', PLATO_FUERTE: 'Platos fuertes', BEBIDA: 'Bebidas',
  POSTRE: 'Postres', ADICIONAL: 'Adicionales',
};

/** Quita tildes y mayúsculas: así "limonada" encuentra "Limonada". */
function normalizar(texto) {
  return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

// =====================================================================
//  RF-04.2 Consultar productos: búsqueda mientras se escribe y categorías
// =====================================================================

let productos = []; // todos, ya ordenados por nombre desde la API
let categoriaElegida = ''; // '' = todas

function pintarCategorias() {
  const opciones = [['', 'Todos'], ...Object.entries(CATEGORIAS)];
  $('categorias').replaceChildren(...opciones.map(([valor, texto]) => {
    const boton = crear('button', {
      type: 'button', className: 'chip filtro', texto,
      'aria-pressed': String(valor === categoriaElegida),
    });
    boton.addEventListener('click', () => {
      categoriaElegida = valor;
      pintarCategorias();
      pintarLista();
    });
    return boton;
  }));
}

async function cargar() {
  if (empezarCarga($('lista'))) mostrarEstado('Cargando…'); // al recargar, la lista se queda atenuada
  try {
    productos = await api('GET', '/productos');
    pintarLista();
  } catch (error) {
    mostrarEstado(error.message, { reintentar: true });
  }
}

function pintarLista() {
  const texto = normalizar($('buscar').value.trim());
  const visibles = productos.filter((p) =>
    (!categoriaElegida || p.categoria === categoriaElegida)
    && normalizar(`${p.codigo} ${p.nombre}`).includes(texto));
  if (visibles.length === 0) {
    if (productos.length) {
      mostrarEstado('No se encontraron productos', {
        icono: 'search_off', detalle: 'Prueba con otro nombre o código, o elige otra categoría.',
        accion: $('buscar').value.trim() ? { texto: 'Limpiar búsqueda', icono: 'close', alHacer: () => $('limpiar').click() } : null,
      });
    } else {
      mostrarEstado('Todavía no hay productos', {
        icono: 'restaurant_menu', detalle: 'Crea los platos de la carta con su receta para calcular el costo.',
        accion: puedeGestionar ? { texto: 'Crear el primer producto', alHacer: () => abrirFormulario(null) } : null,
      });
    }
    pintarSuave($('lista'));
  } else {
    $('estado').hidden = true;
    pintarSuave($('lista'), ...visibles.map(filaDeProducto));
  }
}

/** Una fila: nombre, categoría, precio, avisos y el interruptor de disponibilidad. */
function filaDeProducto(producto) {
  const chips = [crear('span', { className: 'chip', texto: formato.dinero(producto.precio_venta) })];
  if (!producto.activo) {
    chips.unshift(crear('span', { className: 'chip', texto: 'Inactivo' }));
  } else if (producto.porciones_posibles === 0) {
    // Algún insumo de la receta se acabó: avisa aunque siga marcado como disponible
    chips.unshift(crear('span', { className: 'chip estado-AGOTADO', texto: 'Sin insumos' }));
  }

  const fila = crear('li', { className: 'fila editable' }, [
    crear('div', { className: 'avatar' }, [
      crear('span', { className: 'icono', texto: 'restaurant', 'aria-hidden': 'true' }),
    ]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: producto.nombre }),
      crear('div', { className: 'correo', texto: `${producto.codigo} · ${CATEGORIAS[producto.categoria]}` }),
    ]),
    crear('div', { className: 'chips' }, chips),
  ]);
  if (!producto.disponible) fila.classList.add('no-disponible');

  // RF-04.6 Interruptor de disponibilidad directamente en la lista
  if (puedeCambiarDisponibilidad && producto.activo) {
    const interruptor = crear('input', {
      type: 'checkbox', className: 'interruptor-mini',
      title: 'Disponible hoy', 'aria-label': `${producto.nombre} disponible hoy`,
    });
    interruptor.checked = producto.disponible;
    interruptor.addEventListener('click', (evento) => evento.stopPropagation()); // no abre la ficha
    interruptor.addEventListener('change', () => cambiarDisponibilidad(producto, interruptor));
    fila.appendChild(interruptor);
  }

  fila.addEventListener('click', () => abrirFormulario(producto.id));
  return fila;
}

async function cambiarDisponibilidad(producto, interruptor) {
  interruptor.disabled = true;
  try {
    const actualizado = await api('PATCH', `/productos/${producto.id}/disponibilidad`,
      { disponible: interruptor.checked });
    Object.assign(producto, actualizado);
    mostrarAviso(actualizado.disponible ? `${producto.nombre} disponible` : `${producto.nombre} agotado por hoy`);
    pintarLista();
  } catch (error) {
    interruptor.checked = !interruptor.checked; // vuelve a como estaba
    mostrarAviso(error.message);
  } finally {
    interruptor.disabled = false;
  }
}

$('buscar').addEventListener('input', pintarLista); // filtra con cada letra
$('form-buscar').addEventListener('submit', (evento) => evento.preventDefault());
$('limpiar').addEventListener('click', () => {
  $('buscar').value = '';
  pintarLista();
  $('buscar').focus();
});
$('reintentar').addEventListener('click', cargar);

// =====================================================================
//  RF-04.1 Registrar y RF-04.3 Modificar, con receta, precio y disponibilidad
// =====================================================================

const dialogo = $('dialogo-producto');
let productoId = null; // null = crear uno nuevo
let receta = []; // [{insumo_id, insumo, unidad_medida, cantidad, costo_unitario}]
let insumosDisponibles = []; // insumos activos para el selector (solo quien gestiona)

$('f-categoria').replaceChildren(
  crear('option', { value: '', texto: 'Elige una categoría' }),
  ...Object.entries(CATEGORIAS).map(([valor, texto]) => crear('option', { value: valor, texto })),
);

if (puedeGestionar) {
  $('boton-nuevo').hidden = false;
  $('boton-nuevo').addEventListener('click', () => abrirFormulario(null));
}

/** Quien solo puede ver (por ejemplo el MESERO) abre la ficha sin poder editarla. */
function soloLectura(activar) {
  for (const id of ['f-codigo', 'f-categoria', 'f-nombre', 'f-descripcion', 'f-precio',
    'f-disponible', 'f-activo']) {
    $(id).disabled = activar;
  }
  $('guardar').hidden = activar;
  $('agregar-linea').hidden = activar;
}

async function abrirFormulario(id) {
  productoId = id;
  const esEdicion = id !== null;

  $('form-producto').reset();
  for (const campo of ['codigo', 'categoria', 'nombre', 'precio', 'receta']) marcarCampo(campo, '');
  $('error-formulario').hidden = true;
  soloLectura(!puedeGestionar);
  $('titulo-formulario').textContent = esEdicion ? 'Producto' : 'Nuevo producto';
  $('bloque-activo').hidden = !esEdicion;
  receta = [];
  pintarReceta();
  if (!dialogo.open) dialogo.showModal();

  try {
    const [producto, insumos] = await Promise.all([
      esEdicion ? api('GET', `/productos/${id}`) : null,
      puedeGestionar ? api('GET', '/insumos?activo=true') : [],
    ]);
    insumosDisponibles = insumos;
    if (producto) {
      $('titulo-formulario').textContent = puedeGestionar ? 'Editar producto' : producto.nombre;
      $('f-codigo').value = producto.codigo;
      $('f-categoria').value = producto.categoria;
      $('f-nombre').value = producto.nombre;
      $('f-descripcion').value = producto.descripcion ?? '';
      $('f-precio').value = producto.precio_venta;
      $('f-disponible').checked = producto.disponible;
      $('f-activo').checked = producto.activo;
      receta = producto.receta.map((linea) => ({
        ...linea,
        costo_unitario: linea.cantidad ? linea.costo / linea.cantidad : 0,
      }));
    }
    pintarReceta();
  } catch (error) {
    $('error-formulario').textContent = error.message;
    $('error-formulario').hidden = false;
  }
}

// ---------------------------------------------------- RF-04.4 Receta

function pintarReceta() {
  const filas = receta.map((linea, posicion) => {
    const unidad = `${linea.insumo} (${linea.unidad_medida})`;
    if (!puedeGestionar) {
      return crear('div', { className: 'linea' }, [
        crear('span', { className: 'texto-linea', texto: unidad }),
        crear('span', { className: 'texto-linea', texto: formato.cantidad(linea.cantidad) }),
      ]);
    }
    const cantidad = crear('input', {
      type: 'number', min: '0', step: 'any', 'aria-label': `Cantidad de ${linea.insumo}`,
    });
    cantidad.value = linea.cantidad;
    cantidad.addEventListener('input', () => {
      linea.cantidad = Number(cantidad.value);
      pintarCostos();
    });
    const quitar = crear('button', { type: 'button', className: 'boton-icono', title: 'Quitar' }, [
      crear('span', { className: 'icono', texto: 'delete', 'aria-hidden': 'true' }),
    ]);
    quitar.addEventListener('click', () => {
      receta.splice(posicion, 1);
      pintarReceta();
    });
    return crear('div', { className: 'linea' }, [
      crear('span', { className: 'texto-linea', texto: unidad }),
      crear('div', { className: 'campo' }, [cantidad]),
      quitar,
    ]);
  });
  if (filas.length === 0) filas.push(crear('p', { className: 'nota', texto: 'Todavía no tiene insumos.' }));
  pintarSuave($('lineas-receta'), ...filas);

  // En el selector solo aparecen los insumos que todavía no están en la receta
  const yaEstan = new Set(receta.map((linea) => linea.insumo_id));
  $('nuevo-insumo').replaceChildren(
    crear('option', { value: '', texto: 'Agregar un insumo…' }),
    ...insumosDisponibles
      .filter((insumo) => !yaEstan.has(insumo.id))
      .map((insumo) => crear('option', { value: insumo.id, texto: `${insumo.nombre} (${insumo.unidad_medida})` })),
  );
  pintarCostos();
}

/** Costo de la porción y ganancia, recalculados mientras se edita. */
function pintarCostos() {
  if (!puedeGestionar) {
    pintarSuave($('costos')); // el costo y la ganancia son información del administrador
    return;
  }
  const costo = receta.reduce((total, linea) => total + (linea.cantidad || 0) * linea.costo_unitario, 0);
  const precio = Number($('f-precio').value) || 0;
  const margen = precio - costo;
  const ganancia = precio > 0 ? `${Math.round((margen / precio) * 100)} % del precio` : 'Escribe el precio';
  // Tres tarjetas: precio, costo y ganancia (en rojo si el plato se vende a pérdida)
  const tarjeta = (titulo, valor, detalle, clase = '') => crear('div', { className: `costo ${clase}` }, [
    crear('small', { texto: titulo }),
    crear('strong', { texto: valor }),
    crear('small', { texto: detalle }),
  ]);
  pintarSuave($('costos'),
    tarjeta('Precio', formato.dinero(precio), 'por porción'),
    tarjeta('Costo', formato.dinero(costo), `${receta.length} ${receta.length === 1 ? 'insumo' : 'insumos'}`),
    tarjeta('Ganancia', precio > 0 ? formato.dinero(margen) : '—', ganancia, precio > 0 && margen < 0 ? 'perdida' : 'ganancia'));
}

$('f-precio').addEventListener('input', pintarCostos);

/** Pasa a la receta el insumo elegido en la lista. Devuelve false si falta algo. */
function agregarInsumo() {
  const insumo = insumosDisponibles.find((i) => i.id === Number($('nuevo-insumo').value));
  const cantidad = Number($('nueva-cantidad').value);
  if (!insumo) {
    marcarCampo('receta', 'Elige un insumo');
    return false;
  }
  if (!(cantidad > 0)) {
    marcarCampo('receta', 'Escribe la cantidad que lleva una porción');
    return false;
  }
  marcarCampo('receta', '');
  receta.push({
    insumo_id: insumo.id,
    insumo: insumo.nombre,
    unidad_medida: insumo.unidad_medida,
    cantidad,
    costo_unitario: insumo.costo_unitario,
  });
  $('nueva-cantidad').value = '';
  pintarReceta();
  return true;
}

$('agregar-insumo').addEventListener('click', agregarInsumo);

// ---------------------------------------------------- Validar y guardar

function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`)?.classList.toggle('invalido', Boolean(mensaje));
}

function validar() {
  const obligatorio = (valor) => (valor.trim() ? '' : 'Campo obligatorio');
  const errores = {
    codigo: obligatorio($('f-codigo').value),
    categoria: $('f-categoria').value ? '' : 'Elige una categoría',
    nombre: obligatorio($('f-nombre').value),
    precio: Number($('f-precio').value) > 0 ? '' : 'Escribe un precio mayor que cero',
    receta: receta.every((linea) => linea.cantidad > 0) ? '' : 'Todas las cantidades deben ser mayores que cero',
  };
  for (const [campo, mensaje] of Object.entries(errores)) marcarCampo(campo, mensaje);
  return Object.values(errores).every((mensaje) => !mensaje);
}

$('form-producto').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-formulario').hidden = true;
  // Si quedó un insumo elegido sin tocar el botón ⊕, se agrega solo
  if ($('nuevo-insumo').value && !agregarInsumo()) return;
  if (!validar()) return;

  const datos = {
    codigo: $('f-codigo').value.trim(),
    categoria: $('f-categoria').value,
    nombre: $('f-nombre').value.trim(),
    descripcion: $('f-descripcion').value.trim(),
    precio_venta: Number($('f-precio').value), // RF-04.5
    disponible: $('f-disponible').checked, // RF-04.6
    receta: receta.map((linea) => ({ insumo_id: linea.insumo_id, cantidad: linea.cantidad })), // RF-04.4
  };

  $('guardar').disabled = true;
  try {
    if (productoId) {
      datos.activo = $('f-activo').checked;
      await api('PUT', `/productos/${productoId}`, datos); // RF-04.3
    } else {
      await api('POST', '/productos', datos); // RF-04.1
    }
    dialogo.close();
    mostrarAviso(productoId ? 'Producto actualizado' : 'Producto registrado');
    cargar();
  } catch (error) {
    $('error-formulario').textContent = error.message; // por ejemplo "Ya existe un producto con ese código"
    $('error-formulario').hidden = false;
  } finally {
    $('guardar').disabled = false;
  }
});

$('cancelar').addEventListener('click', () => dialogo.close());

pintarCategorias();
cargar();
