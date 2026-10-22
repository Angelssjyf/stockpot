// Módulo de inventario (RF-03.1 a RF-03.8): insumos, existencias, movimientos y alertas.
import { api, exigirSesion } from './api.js';
import { contarHasta, crear, formato, mostrarAviso, normalizar, pintarSuave } from './ui.js';

const yo = await exigirSesion('inventario.ver'); // sin el permiso vuelve al menú
const puedeGestionar = yo.permisos.includes('inventario.gestionar');

const $ = (id) => document.getElementById(id);

function textoStock(insumo) {
  return `${formato.cantidad(insumo.stock_actual)} ${insumo.unidad_medida}`;
}

/** Fecha y hora cortas para el historial: "18 oct, 7:40 p. m." */
function fechaHora(iso) {
  return new Date(iso).toLocaleString('es-CO', {
    day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  });
}

// =====================================================================
//  RF-03.6 Existencias (resumen) y RF-03.8 Alertas de stock
// =====================================================================

const TARJETAS = [ // [dato del resumen, ícono, título, formato, clase cuando el dato no es cero]
  ['total_insumos', 'inventory_2', 'Insumos activos', String, ''],
  ['bajos', 'trending_down', 'En el mínimo', String, 'aviso-bajo'],
  ['agotados', 'block', 'Agotados', String, 'aviso-agotado'],
  ['valor_total', 'payments', 'Valor del inventario', formato.dinero, ''],
];

/** Las tarjetas se crean una vez; al recargar solo cambian sus números (con un conteo corto). */
function pintarResumen(resumen) {
  if ($('resumen').children.length !== TARJETAS.length) {
    $('resumen').replaceChildren(...TARJETAS.map(([, icono, titulo]) => crear('div', { className: 'tarjeta-resumen' }, [
      crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
      crear('div', { className: 'valor' }),
      crear('div', { texto: titulo }),
    ])));
  }
  TARJETAS.forEach(([dato, , , formatear, clase], posicion) => {
    const tarjeta = $('resumen').children[posicion];
    if (clase) tarjeta.classList.toggle(clase, Boolean(resumen[dato]));
    contarHasta(tarjeta.querySelector('.valor'), Number(resumen[dato]), formatear);
  });
}

async function cargarResumen() {
  try {
    const [existencias, alertas] = await Promise.all([
      api('GET', '/inventario/existencias'),
      api('GET', '/inventario/alertas'),
    ]);
    pintarResumen(existencias.resumen);

    $('alertas').hidden = alertas.length === 0;
    pintarSuave($('lista-alertas'), alertas.map(filaDeAlerta));
  } catch (error) {
    $('resumen').replaceChildren(crear('p', { className: 'nota', texto: error.message }));
  }
}

/** Una alerta: al tocarla abre la ficha del insumo para reponerlo ahí mismo. */
function filaDeAlerta(alerta) {
  const fila = crear('li', { className: 'alerta-item', tabindex: '0', role: 'button' }, [
    crear('span', { texto: `${alerta.nombre} · ${textoStock(alerta)} (mínimo ${formato.cantidad(alerta.stock_minimo)})` }),
    crear('span', { className: `chip estado-${alerta.estado_stock}`,
                    texto: alerta.estado_stock === 'AGOTADO' ? 'Agotado' : `Faltan ${formato.cantidad(alerta.faltante)}` }),
  ]);
  fila.dataset.clave = alerta.id;
  fila.dataset.version = alerta.stock_actual;
  fila.addEventListener('click', () => abrirFormulario(alerta));
  fila.addEventListener('keydown', (evento) => {
    if (evento.key === 'Enter') abrirFormulario(alerta); // también con teclado
  });
  return fila;
}

// =====================================================================
//  RF-03.2 Consultar insumos: lista con búsqueda mientras se escribe
// =====================================================================

let insumos = []; // todos los insumos, ya ordenados por nombre desde la API

async function cargar() {
  // Solo la primera vez se ve "Cargando…"; al recargar, la lista actual se queda hasta que llegan los datos
  if (insumos.length === 0) mostrarEstado('Cargando…');
  try {
    insumos = await api('GET', '/insumos');
    pintarLista();
  } catch (error) {
    mostrarEstado(error.message, true);
  }
}

/** Muestra solo los insumos cuyo código o nombre contiene lo escrito en el buscador. */
function pintarLista() {
  const texto = normalizar($('buscar').value.trim());
  const visibles = insumos.filter((i) => normalizar(`${i.codigo} ${i.nombre}`).includes(texto));
  if (visibles.length === 0) mostrarEstado(insumos.length ? 'No se encontraron insumos' : 'Todavía no hay insumos');
  else $('estado').hidden = true;
  pintarSuave($('lista'), visibles.map(filaDeInsumo)); // las filas que siguen visibles no se mueven
}

/** Recarga todo: resumen, alertas y lista (después de cualquier cambio). */
function recargar() {
  cargarResumen();
  cargar();
}

function mostrarEstado(texto, conReintentar = false) {
  $('estado').hidden = false;
  $('estado-texto').textContent = texto;
  $('reintentar').hidden = !conReintentar;
}

/** Una fila: código, nombre y el stock con color según su estado (OK, BAJO, AGOTADO). */
function filaDeInsumo(insumo) {
  const chips = [crear('span', { className: `chip estado-${insumo.estado_stock}`, texto: textoStock(insumo) })];
  if (!insumo.activo) chips.unshift(crear('span', { className: 'chip', texto: 'Inactivo' }));

  const fila = crear('li', { className: 'fila editable' }, [
    crear('div', { className: 'avatar' }, [
      crear('span', { className: 'icono', texto: 'inventory_2', 'aria-hidden': 'true' }),
    ]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: insumo.nombre }),
      crear('div', { className: 'correo', texto: insumo.codigo }),
    ]),
    crear('div', { className: 'chips' }, chips),
  ]);
  fila.dataset.clave = insumo.id;
  fila.dataset.version = [insumo.nombre, insumo.codigo, insumo.stock_actual, insumo.activo].join('|');
  fila.addEventListener('click', () => abrirFormulario(insumo));
  return fila;
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
//  RF-03.1 Registrar, RF-03.3 Modificar y RF-03.7 Niveles mínimos
// =====================================================================

const dialogo = $('dialogo-insumo');
let insumoEditado = null; // null = crear uno nuevo

if (puedeGestionar) {
  $('boton-nuevo').hidden = false;
  $('boton-nuevo').addEventListener('click', () => abrirFormulario(null));
}

/** Quien solo puede ver (por ejemplo el COCINERO) abre la ficha sin poder editarla. */
function soloLectura(activar) {
  for (const id of ['f-codigo', 'f-nombre', 'f-unidad', 'f-minimo', 'f-costo', 'f-activo']) {
    $(id).disabled = activar;
  }
  $('guardar').hidden = activar;
  $('botones-movimiento').hidden = activar;
}

function abrirFormulario(insumo) {
  insumoEditado = insumo;
  const esEdicion = insumo !== null;

  $('form-insumo').reset();
  for (const campo of ['codigo', 'nombre', 'unidad', 'minimo', 'costo']) marcarCampo(campo, '');
  $('error-formulario').hidden = true;
  soloLectura(!puedeGestionar);

  $('titulo-formulario').textContent = !esEdicion ? 'Nuevo insumo'
    : puedeGestionar ? 'Editar insumo' : insumo.nombre;
  $('bloque-edicion').hidden = !esEdicion;

  if (esEdicion) {
    $('f-codigo').value = insumo.codigo;
    $('f-nombre').value = insumo.nombre;
    $('f-unidad').value = insumo.unidad_medida;
    $('f-minimo').value = insumo.stock_minimo;
    $('f-costo').value = insumo.costo_unitario;
    $('f-activo').checked = insumo.activo;
    $('stock-actual').textContent = textoStock(insumo);
    $('boton-entrada').disabled = !insumo.activo;
    $('boton-salida').disabled = !insumo.activo;
    cargarHistorial(insumo);
  }

  if (!dialogo.open) dialogo.showModal();
}

function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`).classList.toggle('invalido', Boolean(mensaje));
}

function validar() {
  const obligatorio = (valor) => (valor.trim() ? '' : 'Campo obligatorio');
  const noNegativo = (valor) => (valor === '' || Number(valor) >= 0 ? '' : 'No puede ser negativo');
  const errores = {
    codigo: obligatorio($('f-codigo').value),
    nombre: obligatorio($('f-nombre').value),
    unidad: $('f-unidad').value ? '' : 'Elige una unidad',
    minimo: noNegativo($('f-minimo').value),
    costo: noNegativo($('f-costo').value),
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
    stock_minimo: Number($('f-minimo').value || 0), // RF-03.7
    costo_unitario: Number($('f-costo').value || 0),
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
    recargar();
  } catch (error) {
    $('error-formulario').textContent = error.message; // por ejemplo "Ya existe un insumo con ese código"
    $('error-formulario').hidden = false;
  } finally {
    $('guardar').disabled = false;
  }
});

$('cancelar').addEventListener('click', () => dialogo.close());

// =====================================================================
//  RF-03.4 Entradas y RF-03.5 Salidas: historial y registro
// =====================================================================

const NOMBRES_MOTIVO = {
  COMPRA: 'Compra', AJUSTE: 'Ajuste', DEVOLUCION: 'Devolución', CONSUMO: 'Consumo', MERMA: 'Merma',
};
// Los mismos motivos que acepta la API para un movimiento manual
const MOTIVOS = { ENTRADA: ['COMPRA', 'AJUSTE', 'DEVOLUCION'], SALIDA: ['CONSUMO', 'MERMA', 'AJUSTE'] };

async function cargarHistorial(insumo) {
  const lista = $('historial');
  // Si ya se ve el historial de este insumo (por ejemplo después de un movimiento), se deja mientras carga
  if (lista.dataset.insumo !== String(insumo.id)) {
    lista.dataset.insumo = insumo.id;
    lista.replaceChildren(crear('li', { className: 'nota', texto: 'Cargando movimientos…' }));
  }
  try {
    const movimientos = await api('GET', `/insumos/${insumo.id}/movimientos`);
    if (movimientos.length === 0) {
      lista.replaceChildren(crear('li', { className: 'nota', texto: 'Todavía no hay movimientos' }));
      return;
    }
    pintarSuave(lista, movimientos.map((m) => {
      const signo = m.tipo === 'ENTRADA' ? '+' : '−';
      const detalle = [NOMBRES_MOTIVO[m.motivo], m.orden_compra, m.observacion].filter(Boolean).join(' · ');
      return crear('li', { 'data-clave': m.id }, [
        crear('div', {}, [
          crear('div', { texto: detalle }),
          crear('small', { className: 'nota', texto: `${fechaHora(m.fecha)} · ${m.usuario}` }),
        ]),
        crear('div', { className: 'cantidad-movimiento' }, [
          crear('div', { className: `movimiento-${m.tipo}`, texto: `${signo}${formato.cantidad(m.cantidad)}` }),
          crear('small', { className: 'nota', texto: `Queda ${formato.cantidad(m.stock_resultante)}` }),
        ]),
      ]);
    }));
  } catch (error) {
    lista.replaceChildren(crear('li', { className: 'nota', texto: error.message }));
  }
}

const dialogoMovimiento = $('dialogo-movimiento');
let tipoMovimiento = 'ENTRADA';

function abrirMovimiento(tipo) {
  tipoMovimiento = tipo;
  $('form-movimiento').reset();
  marcarCampo('cantidad', '');
  $('error-movimiento').hidden = true;

  $('titulo-movimiento').textContent = tipo === 'ENTRADA' ? 'Registrar entrada' : 'Registrar salida';
  $('insumo-movimiento').textContent = `${insumoEditado.nombre} · hay ${textoStock(insumoEditado)}`;
  $('m-unidad').textContent = insumoEditado.unidad_medida;
  $('m-motivo').replaceChildren(...MOTIVOS[tipo].map(
    (motivo) => crear('option', { value: motivo, texto: NOMBRES_MOTIVO[motivo] }),
  ));
  dialogoMovimiento.showModal();
}

$('boton-entrada').addEventListener('click', () => abrirMovimiento('ENTRADA'));
$('boton-salida').addEventListener('click', () => abrirMovimiento('SALIDA'));
$('cancelar-movimiento').addEventListener('click', () => dialogoMovimiento.close());

$('form-movimiento').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-movimiento').hidden = true;
  const cantidad = Number($('m-cantidad').value);
  if (!(cantidad > 0)) {
    marcarCampo('cantidad', 'Escribe una cantidad mayor que cero');
    return;
  }
  marcarCampo('cantidad', '');

  $('guardar-movimiento').disabled = true;
  try {
    const respuesta = await api('POST', `/insumos/${insumoEditado.id}/movimientos`, {
      tipo: tipoMovimiento,
      motivo: $('m-motivo').value,
      cantidad,
      observacion: $('m-observacion').value.trim(),
    });
    dialogoMovimiento.close();
    mostrarAviso(tipoMovimiento === 'ENTRADA' ? 'Entrada registrada' : 'Salida registrada');
    abrirFormulario(respuesta.insumo); // la ficha muestra el nuevo stock y el historial
    recargar();
  } catch (error) {
    $('error-movimiento').textContent = error.message; // por ejemplo "Stock insuficiente…"
    $('error-movimiento').hidden = false;
  } finally {
    $('guardar-movimiento').disabled = false;
  }
});

recargar();
