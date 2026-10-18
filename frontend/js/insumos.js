// Módulo de inventario: RF-03.1 Registrar, RF-03.2 Consultar y RF-03.3 Modificar insumos.
import { api, exigirSesion } from './api.js';
import { crear, mostrarAviso } from './ui.js';

const yo = await exigirSesion('inventario.ver'); // sin el permiso vuelve al menú
const puedeGestionar = yo.permisos.includes('inventario.gestionar');

const $ = (id) => document.getElementById(id);

/** Formato colombiano para cantidades: 12,5 · 1.250 */
const formatoCantidad = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 3 });

function textoStock(insumo) {
  return `${formatoCantidad.format(insumo.stock_actual)} ${insumo.unidad_medida}`;
}

// =====================================================================
//  RF-03.2 Consultar insumos: lista con buscador
// =====================================================================

async function cargar() {
  mostrarEstado('Cargando…');
  $('lista').replaceChildren();
  try {
    const texto = encodeURIComponent($('buscar').value.trim());
    const insumos = await api('GET', `/insumos?q=${texto}`);
    if (insumos.length === 0) {
      mostrarEstado('No se encontraron insumos');
    } else {
      $('estado').hidden = true;
      $('lista').replaceChildren(...insumos.map(filaDeInsumo));
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

/** Una fila: código, nombre, stock actual e "Inactivo" si aplica. */
function filaDeInsumo(insumo) {
  const chips = [crear('span', { className: 'chip', texto: textoStock(insumo) })];
  if (!insumo.activo) chips.unshift(crear('span', { className: 'chip', texto: 'Inactivo' }));

  const fila = crear('li', { className: puedeGestionar ? 'fila editable' : 'fila' }, [
    crear('div', { className: 'avatar' }, [
      crear('span', { className: 'icono', texto: 'inventory_2', 'aria-hidden': 'true' }),
    ]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: insumo.nombre }),
      crear('div', { className: 'correo', texto: insumo.codigo }),
    ]),
    crear('div', { className: 'chips' }, chips),
  ]);
  if (puedeGestionar) fila.addEventListener('click', () => abrirFormulario(insumo));
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
//  RF-03.1 Registrar y RF-03.3 Modificar: un solo formulario
// =====================================================================

const dialogo = $('dialogo-insumo');
let insumoEditado = null; // null = crear uno nuevo

if (puedeGestionar) {
  $('boton-nuevo').hidden = false;
  $('boton-nuevo').addEventListener('click', () => abrirFormulario(null));
}

function abrirFormulario(insumo) {
  insumoEditado = insumo;
  const esEdicion = insumo !== null;

  $('form-insumo').reset();
  for (const campo of ['codigo', 'nombre', 'unidad']) marcarCampo(campo, '');
  $('error-formulario').hidden = true;

  $('titulo-formulario').textContent = esEdicion ? 'Editar insumo' : 'Nuevo insumo';
  $('bloque-edicion').hidden = !esEdicion;

  if (esEdicion) {
    $('f-codigo').value = insumo.codigo;
    $('f-nombre').value = insumo.nombre;
    $('f-unidad').value = insumo.unidad_medida;
    $('f-activo').checked = insumo.activo;
    $('stock-actual').textContent = textoStock(insumo);
  }

  dialogo.showModal();
}

function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`).classList.toggle('invalido', Boolean(mensaje));
}

function validar() {
  const obligatorio = (valor) => (valor.trim() ? '' : 'Campo obligatorio');
  const errores = {
    codigo: obligatorio($('f-codigo').value),
    nombre: obligatorio($('f-nombre').value),
    unidad: $('f-unidad').value ? '' : 'Elige una unidad',
  };
  for (const [campo, mensaje] of Object.entries(errores)) marcarCampo(campo, mensaje);
  return Object.values(errores).every((mensaje) => !mensaje);
}

$('form-insumo').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-formulario').hidden = true;
  if (!validar()) return;

  const datos = {
    codigo: $('f-codigo').value.trim(),
    nombre: $('f-nombre').value.trim(),
    unidad_medida: $('f-unidad').value,
  };

  $('guardar').disabled = true;
  try {
    if (insumoEditado) {
      datos.activo = $('f-activo').checked;
      await api('PUT', `/insumos/${insumoEditado.id}`, datos); // RF-03.3
    } else {
      await api('POST', '/insumos', datos); // RF-03.1
    }
    dialogo.close();
    mostrarAviso(insumoEditado ? 'Insumo actualizado' : 'Insumo registrado');
    cargar();
  } catch (error) {
    $('error-formulario').textContent = error.message; // por ejemplo "Ya existe un insumo con ese código"
    $('error-formulario').hidden = false;
  } finally {
    $('guardar').disabled = false;
  }
});

$('cancelar').addEventListener('click', () => dialogo.close());

cargar();
