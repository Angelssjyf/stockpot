// Módulo de reservas (RF-07.1 a RF-07.8): reservas del día, mesas libres y estados.
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, mostrarAviso, mostrarEstado, pintarSuave } from './ui.js';

const yo = await exigirSesion('reservas.ver'); // sin el permiso vuelve al menú
const puedeGestionar = yo.permisos.includes('reservas.gestionar');

const $ = (id) => document.getElementById(id);
const ESTADOS = {
  PENDIENTE: 'Pendiente', CONFIRMADA: 'Confirmada', CUMPLIDA: 'Llegó', NO_ASISTIO: 'No asistió', CANCELADA: 'Cancelada',
};
const CHIP = { PENDIENTE: 'REGISTRADO', CONFIRMADA: 'CONFIRMADO', CUMPLIDA: 'ENTREGADO', NO_ASISTIO: 'CANCELADO', CANCELADA: 'CANCELADO' };

const iso = (fecha) => fecha.toLocaleDateString('en-CA'); // AAAA-MM-DD en hora local
const hora = (texto) => new Date(texto).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
const fechaLarga = (texto) => new Date(texto).toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });

function chip(estado) {
  return crear('span', { className: `chip estado-${CHIP[estado]}`, texto: ESTADOS[estado] });
}

function tarjetaResumen(icono, titulo, valor) {
  return crear('div', { className: 'tarjeta-resumen' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
  ]);
}

// =====================================================================
//  RF-07.2 Consultar reservas: un día a la vez, con atajos y buscador
// =====================================================================

const ATAJOS = {
  Hoy: () => new Date(),
  Mañana: () => new Date(Date.now() + 864e5),
  'Pasado mañana': () => new Date(Date.now() + 2 * 864e5),
};
$('dia').value = iso(new Date());
$('atajos').replaceChildren(...Object.entries(ATAJOS).map(([texto, dia]) => {
  const boton = crear('button', { type: 'button', className: 'chip filtro', texto, 'aria-pressed': 'false' });
  boton.addEventListener('click', () => {
    $('dia').value = iso(dia());
    cargar();
  });
  return boton;
}));
function marcarAtajo() {
  for (const boton of $('atajos').children) {
    boton.setAttribute('aria-pressed', String(iso(ATAJOS[boton.textContent]()) === $('dia').value));
  }
}

async function cargar() {
  marcarAtajo();
  if (empezarCarga($('lista'))) mostrarEstado('Cargando…', { cargando: true });
  try {
    const q = encodeURIComponent($('buscar').value.trim());
    const { resumen, reservas } = await api('GET', `/reservas?fecha=${$('dia').value}&q=${q}`);
    pintarSuave($('resumen'),
      tarjetaResumen('event_seat', 'Reservas activas', String(resumen.activas)),
      tarjetaResumen('verified', 'Confirmadas', String(resumen.confirmadas)),
      tarjetaResumen('groups', 'Personas esperadas', String(resumen.personas)),
    );
    if (reservas.length === 0) {
      mostrarEstado(q ? 'No se encontraron reservas' : 'No hay reservas para este día', {
        icono: 'event_busy', detalle: q ? 'Prueba con otro nombre o teléfono.' : 'Las reservas del día aparecen aquí en orden de hora.',
        accion: puedeGestionar && !q ? { texto: 'Nueva reserva', icono: 'event_available', alHacer: () => abrirFormulario(null) } : null,
      });
      pintarSuave($('lista'));
    } else {
      $('estado').hidden = true;
      pintarSuave($('lista'), ...reservas.map(fila));
    }
  } catch (error) {
    mostrarEstado(error.message, { reintentar: true });
  }
}

/** Una fila: la hora grande, el cliente, cuántos y en qué mesa, y su estado. */
function fila(reserva) {
  const elemento = crear('li', { className: `fila editable${reserva.activa ? '' : ' inactiva'}` }, [
    crear('div', { className: 'avatar hora-reserva', texto: hora(reserva.fecha_hora) }),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: reserva.cliente }),
      crear('div', { className: 'correo', texto: `${reserva.personas} personas · Mesa ${reserva.mesa}${reserva.ubicacion ? ` (${reserva.ubicacion})` : ''} · ${reserva.telefono}` }),
      ...(reserva.observaciones ? [crear('div', { className: 'correo', texto: reserva.observaciones })] : []),
    ]),
    crear('div', { className: 'chips' }, [chip(reserva.estado)]),
  ]);
  elemento.dataset.clave = reserva.id;
  elemento.dataset.version = `${reserva.estado}|${reserva.fecha_hora}|${reserva.mesa}`;
  elemento.addEventListener('click', () => abrirDetalle(reserva));
  return elemento;
}

$('dia').addEventListener('change', cargar);
$('form-dia').addEventListener('submit', (evento) => { evento.preventDefault(); cargar(); });
let temporizadorBusqueda;
$('buscar').addEventListener('input', () => {
  clearTimeout(temporizadorBusqueda);
  temporizadorBusqueda = setTimeout(cargar, 300);
});
$('reintentar').addEventListener('click', cargar);

// =====================================================================
//  Detalle: RF-07.8 estados y RF-07.4 cancelar
// =====================================================================

const dialogoDetalle = $('dialogo-detalle');

function abrirDetalle(reserva) {
  $('error-detalle').hidden = true;
  $('detalle-titulo').replaceChildren(crear('span', { texto: `${reserva.cliente} ` }), chip(reserva.estado));
  const datos = [
    ['Cuándo', `${fechaLarga(reserva.fecha_hora)}, ${hora(reserva.fecha_hora)} a ${hora(reserva.fin)}`],
    ['Mesa', `Mesa ${reserva.mesa} · para ${reserva.capacidad}${reserva.ubicacion ? ` · ${reserva.ubicacion}` : ''}`],
    ['Personas', String(reserva.personas)],
    ['Teléfono', reserva.telefono],
    ['Observaciones', reserva.observaciones],
    ['Código', reserva.codigo],
    ['Registró', reserva.registrada_por],
  ].filter(([, valor]) => valor);
  $('detalle-datos').replaceChildren(...datos.flatMap(([t, v]) => [crear('dt', { texto: t }), crear('dd', { texto: v })]));

  const boton = (texto, icono, clase, alHacer) => {
    const b = crear('button', { type: 'button', className: clase }, [
      ...(icono ? [crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' })] : []),
      document.createTextNode(icono ? ` ${texto}` : texto),
    ]);
    b.addEventListener('click', alHacer);
    return b;
  };
  const botones = [boton('Cerrar', null, 'boton-texto', () => dialogoDetalle.close())];
  if (puedeGestionar && reserva.activa) {
    botones.push(boton('Cancelar reserva', null, 'boton-texto', () => {
      const motivo = prompt(`¿Por qué se cancela la reserva de ${reserva.cliente}? (opcional)`, '');
      if (motivo !== null) cambiar(`/reservas/${reserva.id}/cancelar`, { motivo }, 'Reserva cancelada: la mesa quedó libre');
    }));
    botones.push(boton('Modificar', null, 'boton-texto', () => { dialogoDetalle.close(); abrirFormulario(reserva); }));
    botones.push(boton('No asistió', null, 'boton-texto', () => cambiar(`/reservas/${reserva.id}/estado`, { estado: 'NO_ASISTIO' }, 'Marcada como no asistió')));
    if (reserva.estado === 'PENDIENTE') {
      botones.push(boton('Confirmar', 'verified', 'boton-principal', () => cambiar(`/reservas/${reserva.id}/estado`, { estado: 'CONFIRMADA' }, 'Reserva confirmada')));
    }
    botones.push(boton('Llegó', 'how_to_reg', 'boton-principal', () => cambiar(`/reservas/${reserva.id}/estado`, { estado: 'CUMPLIDA' }, `${reserva.cliente} llegó: ya puedes tomar el pedido en la mesa ${reserva.mesa}`)));
  }
  $('detalle-acciones').replaceChildren(...botones);
  if (!dialogoDetalle.open) dialogoDetalle.showModal();
}

async function cambiar(ruta, datos, aviso) {
  $('error-detalle').hidden = true;
  try {
    const reserva = await api('PATCH', ruta, datos);
    mostrarAviso(aviso, 'exito');
    abrirDetalle(reserva);
    cargar();
  } catch (error) {
    $('error-detalle').textContent = error.message; // por ejemplo "Todavía falta más de una hora para la reserva"
    $('error-detalle').hidden = false;
  }
}

// =====================================================================
//  RF-07.1 Registrar y RF-07.3 Modificar, con RF-07.7 las mesas libres
// =====================================================================

const dialogo = $('dialogo-reserva');
let editada = null;
let mesaElegida = null;

if (puedeGestionar) {
  $('boton-nuevo').hidden = false;
  $('boton-nuevo').addEventListener('click', () => abrirFormulario(null));
}

function abrirFormulario(reserva) {
  editada = reserva;
  $('form-reserva').reset();
  for (const campo of ['cliente', 'telefono', 'fecha', 'hora', 'personas', 'mesa']) marcarCampo(campo, '');
  $('error-formulario').hidden = true;
  $('titulo-formulario').textContent = reserva ? `Modificar reserva de ${reserva.cliente}` : 'Nueva reserva';
  if (reserva) {
    $('f-cliente').value = reserva.cliente;
    $('f-telefono').value = reserva.telefono;
    $('f-fecha').value = reserva.fecha_hora.slice(0, 10);
    $('f-hora').value = reserva.fecha_hora.slice(11, 16);
    $('f-personas').value = reserva.personas;
    $('f-duracion').value = String(reserva.duracion_minutos);
    $('f-observaciones').value = reserva.observaciones ?? '';
    mesaElegida = reserva.mesa_id;
  } else {
    $('f-fecha').value = $('dia').value < iso(new Date()) ? iso(new Date()) : $('dia').value;
    $('f-hora').value = '19:00';
    mesaElegida = null;
  }
  dialogo.showModal();
  buscarMesas();
}

let consultaMesas = 0;
async function buscarMesas() {
  const fecha = $('f-fecha').value;
  const horaElegida = $('f-hora').value;
  const personas = Number($('f-personas').value);
  if (!fecha || !horaElegida || !personas) {
    $('opciones-mesa').replaceChildren();
    $('ayuda-mesas').textContent = 'Elige fecha, hora y personas para ver las mesas libres.';
    return;
  }
  const numero = ++consultaMesas;
  const parametros = new URLSearchParams({ fecha_hora: `${fecha}T${horaElegida}`, personas, duracion_minutos: $('f-duracion').value });
  if (editada) parametros.set('reserva_id', editada.id);
  try {
    const { mesas } = await api('GET', `/reservas/disponibilidad?${parametros}`);
    if (numero !== consultaMesas) return; // ya hay una consulta más nueva
    if (!mesas.some((m) => m.id === mesaElegida)) mesaElegida = mesas[0]?.id ?? null; // la más pequeña que sirve
    $('ayuda-mesas').textContent = mesas.length
      ? `${mesas.length} mesa${mesas.length === 1 ? '' : 's'} libre${mesas.length === 1 ? '' : 's'} para ${personas} a esa hora.`
      : 'No hay mesas libres con ese cupo a esa hora. Prueba otra hora o divide el grupo.';
    $('opciones-mesa').replaceChildren(...mesas.map((mesa) => {
      const opcion = crear('button', {
        type: 'button', className: 'opcion-mesa', role: 'radio', 'aria-checked': String(mesa.id === mesaElegida),
      }, [
        crear('b', { texto: `Mesa ${mesa.numero}` }),
        crear('span', { className: 'nota', texto: [`${mesa.capacidad} puestos`, mesa.ubicacion].filter(Boolean).join(' · ') }),
      ]);
      opcion.addEventListener('click', () => {
        mesaElegida = mesa.id;
        for (const otra of $('opciones-mesa').children) otra.setAttribute('aria-checked', String(otra === opcion));
        marcarCampo('mesa', '');
      });
      return opcion;
    }));
  } catch (error) {
    $('ayuda-mesas').textContent = error.message;
  }
}
for (const id of ['f-fecha', 'f-hora', 'f-personas', 'f-duracion']) $(id).addEventListener('change', buscarMesas);

function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`)?.classList.toggle('invalido', Boolean(mensaje));
}

function validar() {
  const obligatorio = (id) => ($(id).value.trim() ? '' : 'Campo obligatorio');
  const errores = {
    cliente: obligatorio('f-cliente'),
    telefono: obligatorio('f-telefono'),
    fecha: obligatorio('f-fecha'),
    hora: obligatorio('f-hora'),
    personas: Number($('f-personas').value) >= 1 ? '' : 'Mínimo 1',
    mesa: mesaElegida ? '' : 'Elige una mesa libre',
  };
  if (!errores.fecha && !errores.hora && new Date(`${$('f-fecha').value}T${$('f-hora').value}`) <= new Date()) {
    errores.hora = 'Debe ser una hora futura';
  }
  for (const [campo, mensaje] of Object.entries(errores)) marcarCampo(campo, mensaje);
  return Object.values(errores).every((mensaje) => !mensaje);
}

$('form-reserva').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-formulario').hidden = true;
  if (!validar()) return;
  const datos = {
    cliente: $('f-cliente').value.trim(),
    telefono: $('f-telefono').value.trim(),
    personas: Number($('f-personas').value),
    fecha_hora: `${$('f-fecha').value}T${$('f-hora').value}`,
    duracion_minutos: Number($('f-duracion').value),
    mesa_id: mesaElegida,
    observaciones: $('f-observaciones').value.trim(),
  };
  $('guardar').disabled = true;
  try {
    const reserva = editada ? await api('PUT', `/reservas/${editada.id}`, datos) : await api('POST', '/reservas', datos);
    mostrarAviso(editada ? 'Reserva modificada' : `Reserva ${reserva.codigo}: mesa ${reserva.mesa}, ${hora(reserva.fecha_hora)}`, 'exito');
    $('dia').value = reserva.fecha_hora.slice(0, 10);
    dialogo.close();
  } catch (error) {
    $('error-formulario').textContent = error.message; // por ejemplo "La mesa 3 ya está reservada a esa hora"
    $('error-formulario').hidden = false;
    buscarMesas();
  } finally {
    $('guardar').disabled = false;
  }
});

$('cancelar').addEventListener('click', () => dialogo.close());
dialogo.addEventListener('close', cargar);

cargar();
