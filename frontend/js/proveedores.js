// Módulo de proveedores: RF-02.1 Registrar, RF-02.2 Consultar, RF-02.3 Modificar,
// RF-02.4 Productos suministrados y RF-02.5 Historial de compras.
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, formato, mostrarAviso, pintarSuave } from './ui.js';

const yo = await exigirSesion('proveedores.ver'); // sin el permiso vuelve al menú
const puedeGestionar = yo.permisos.includes('proveedores.gestionar');

// Las órdenes de compra son parte de este módulo: se llega a ellas desde aquí
document.getElementById('ir-compras').hidden = !yo.permisos.includes('compras.ver');

const $ = (id) => document.getElementById(id);

// =====================================================================
//  RF-02.2 Consultar proveedores: lista con buscador
// =====================================================================

async function cargar() {
  if (empezarCarga($('lista'))) mostrarEstado('Cargando…'); // al recargar, la lista se queda atenuada
  try {
    const texto = encodeURIComponent($('buscar').value.trim());
    const proveedores = await api('GET', `/proveedores?q=${texto}`);
    if (proveedores.length === 0) {
      mostrarEstado('No se encontraron proveedores');
      pintarSuave($('lista'));
    } else {
      $('estado').hidden = true;
      pintarSuave($('lista'), ...proveedores.map(filaDeProveedor));
    }
  } catch (error) {
    mostrarEstado(error.message, true);
  }
}

function mostrarEstado(texto, conReintentar = false) {
  $('estado').hidden = false;
  $('estado-texto').textContent = texto;
  $('reintentar').hidden = !conReintentar;
}

function filaDeProveedor(proveedor) {
  const chips = [];
  if (!proveedor.activo) chips.push(crear('span', { className: 'chip', texto: 'Inactivo' }));
  if (proveedor.telefono) chips.push(crear('span', { className: 'chip', texto: proveedor.telefono }));

  const fila = crear('li', { className: puedeGestionar ? 'fila editable' : 'fila' }, [
    crear('div', { className: 'avatar' }, [
      crear('span', { className: 'icono', texto: 'local_shipping', 'aria-hidden': 'true' }),
    ]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: proveedor.razon_social }),
      crear('div', { className: 'correo', texto: `NIT ${proveedor.nit}` + (proveedor.contacto ? ` · ${proveedor.contacto}` : '') }),
    ]),
    crear('div', { className: 'chips' }, chips),
  ]);
  if (puedeGestionar) fila.addEventListener('click', () => abrirFormulario(proveedor.id));
  return fila;
}

$('form-buscar').addEventListener('submit', (evento) => {
  evento.preventDefault();
  cargar();
});
$('limpiar').addEventListener('click', () => {
  $('buscar').value = '';
  cargar();
});
$('reintentar').addEventListener('click', cargar);

// =====================================================================
//  RF-02.1 Registrar y RF-02.3 Modificar (con RF-02.4 y RF-02.5 al editar)
// =====================================================================

const dialogo = $('dialogo-proveedor');
let proveedorId = null; // null = crear uno nuevo
let insumosDelProveedor = []; // [{insumo_id, insumo, unidad_medida, precio_referencia}]
let todosLosInsumos = []; // insumos activos para el selector

if (puedeGestionar) {
  $('boton-nuevo').hidden = false;
  $('boton-nuevo').addEventListener('click', () => abrirFormulario(null));
}

async function abrirFormulario(id) {
  proveedorId = id;
  const esEdicion = id !== null;

  $('form-proveedor').reset();
  for (const campo of ['nit', 'razon', 'email']) marcarCampo(campo, '');
  ocultarError();
  $('titulo-formulario').textContent = esEdicion ? 'Editar proveedor' : 'Nuevo proveedor';
  $('bloque-edicion').hidden = !esEdicion;
  if (!dialogo.open) dialogo.showModal(); // tras crear, ya está abierto

  if (!esEdicion) return;
  try {
    const [proveedor, compras, insumos] = await Promise.all([
      api('GET', `/proveedores/${id}`),
      api('GET', `/proveedores/${id}/compras`),
      api('GET', '/insumos?activo=true'),
    ]);
    $('f-nit').value = proveedor.nit;
    $('f-razon').value = proveedor.razon_social;
    $('f-contacto').value = proveedor.contacto ?? '';
    $('f-telefono').value = proveedor.telefono ?? '';
    $('f-email').value = proveedor.email ?? '';
    $('f-direccion').value = proveedor.direccion ?? '';
    $('f-activo').checked = proveedor.activo;

    insumosDelProveedor = proveedor.insumos;
    todosLosInsumos = insumos;
    pintarInsumos();
    pintarHistorial(compras);
  } catch (error) {
    mostrarError(error.message);
  }
}

// ---------------------------------------------------- RF-02.4 Insumos que vende

function pintarInsumos() {
  const filas = insumosDelProveedor.map((item, posicion) => {
    const precio = crear('input', {
      type: 'number', min: '0', step: 'any', placeholder: 'Precio',
      'aria-label': `Precio de ${item.insumo}`,
    });
    precio.value = item.precio_referencia ?? '';
    precio.addEventListener('input', () => {
      item.precio_referencia = precio.value === '' ? null : Number(precio.value);
    });
    const quitar = crear('button', { type: 'button', className: 'boton-icono', title: 'Quitar' }, [
      crear('span', { className: 'icono', texto: 'delete', 'aria-hidden': 'true' }),
    ]);
    quitar.addEventListener('click', () => {
      insumosDelProveedor.splice(posicion, 1);
      pintarInsumos();
    });
    return crear('div', { className: 'linea' }, [
      crear('span', { className: 'texto-linea', texto: `${item.insumo} (${item.unidad_medida})` }),
      crear('div', { className: 'campo' }, [precio]),
      quitar,
    ]);
  });
  if (filas.length === 0) filas.push(crear('p', { className: 'nota', texto: 'Todavía no tiene insumos.' }));
  pintarSuave($('lineas-insumos'), ...filas);

  // En el selector solo aparecen los insumos que todavía no vende
  const yaVende = new Set(insumosDelProveedor.map((item) => item.insumo_id));
  $('nuevo-insumo').replaceChildren(
    crear('option', { value: '', texto: 'Agregar un insumo…' }),
    ...todosLosInsumos
      .filter((insumo) => !yaVende.has(insumo.id))
      .map((insumo) => crear('option', { value: insumo.id, texto: `${insumo.nombre} (${insumo.unidad_medida})` })),
  );
}

$('agregar-insumo').addEventListener('click', () => {
  const insumo = todosLosInsumos.find((i) => i.id === Number($('nuevo-insumo').value));
  if (!insumo) return;
  const precio = $('nuevo-precio').value;
  insumosDelProveedor.push({
    insumo_id: insumo.id,
    insumo: insumo.nombre,
    unidad_medida: insumo.unidad_medida,
    precio_referencia: precio === '' ? null : Number(precio),
  });
  $('nuevo-precio').value = '';
  pintarInsumos();
});

// ---------------------------------------------------- RF-02.5 Historial de compras

function pintarHistorial(compras) {
  if (compras.length === 0) {
    pintarSuave($('historial'), crear('li', { texto: 'Sin compras registradas.' }));
    return;
  }
  pintarSuave($('historial'), ...compras.map((orden) => crear('li', {}, [
    crear('span', { texto: `${orden.codigo} · ${formato.fecha(orden.fecha_orden)}` }),
    crear('span', { className: `chip estado-${orden.estado}`, texto: orden.estado }),
    crear('strong', { texto: formato.dinero(orden.total) }),
  ])));
}

// ---------------------------------------------------- Validar y guardar

function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`).classList.toggle('invalido', Boolean(mensaje));
}

function mostrarError(mensaje) {
  $('error-formulario').textContent = mensaje;
  $('error-formulario').hidden = false;
}

function ocultarError() {
  $('error-formulario').hidden = true;
}

function validar() {
  const email = $('f-email').value.trim();
  const errores = {
    nit: $('f-nit').value.trim() ? '' : 'Campo obligatorio',
    razon: $('f-razon').value.trim() ? '' : 'Campo obligatorio',
    email: email && !email.includes('@') ? 'Escribe un correo válido' : '',
  };
  for (const [campo, mensaje] of Object.entries(errores)) marcarCampo(campo, mensaje);
  return Object.values(errores).every((mensaje) => !mensaje);
}

$('form-proveedor').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  ocultarError();
  if (!validar()) return;

  const datos = {
    nit: $('f-nit').value.trim(),
    razon_social: $('f-razon').value.trim(),
    contacto: $('f-contacto').value.trim(),
    telefono: $('f-telefono').value.trim(),
    email: $('f-email').value.trim(),
    direccion: $('f-direccion').value.trim(),
  };

  $('guardar').disabled = true;
  try {
    if (proveedorId) {
      datos.activo = $('f-activo').checked;
      await api('PUT', `/proveedores/${proveedorId}`, datos); // RF-02.3
      await api('PUT', `/proveedores/${proveedorId}/insumos`, { // RF-02.4
        insumos: insumosDelProveedor.map((item) => ({
          insumo_id: item.insumo_id,
          precio_referencia: item.precio_referencia,
        })),
      });
      dialogo.close();
      mostrarAviso('Proveedor actualizado');
    } else {
      const nuevo = await api('POST', '/proveedores', datos); // RF-02.1
      mostrarAviso('Proveedor registrado. Ahora puedes agregar los insumos que vende.');
      await abrirFormulario(nuevo.id); // se abre en modo edición para agregar insumos
    }
    cargar();
  } catch (error) {
    mostrarError(error.message); // por ejemplo "Ya existe un proveedor con ese NIT"
  } finally {
    $('guardar').disabled = false;
  }
});

$('cancelar').addEventListener('click', () => dialogo.close());

cargar();
