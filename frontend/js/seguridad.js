// Sesiones seguras (tercer corte): botón Bloquear, bloqueo por inactividad, pantalla de bloqueo,
// pedir el PIN para cobrar, anular y sacar inventario, y crear el PIN personal.
import { api, cerrarSesion } from './api.js';
import { crear, mostrarAviso } from './ui.js';

const CLAVE_ACTIVIDAD = 'stockpot_actividad'; // compartida entre pestañas
let usuario = null;
let bloqueada = false;
let recargarAlDesbloquear = false; // la pantalla abrió bloqueada: sus datos no se alcanzaron a cargar

const ahora = () => Date.now();
function marcarActividad() {
  if (bloqueada) return;
  try { localStorage.setItem(CLAVE_ACTIVIDAD, String(ahora())); } catch { /* sin almacenamiento: solo esta pestaña */ }
  ultimaActividad = ahora();
}
let ultimaActividad = ahora();
function ultimaDeTodas() {
  try { return Math.max(ultimaActividad, Number(localStorage.getItem(CLAVE_ACTIVIDAD)) || 0); } catch { return ultimaActividad; }
}

/** Se llama desde exigirSesion en cada pantalla: botón, temporizador y, si ya estaba bloqueada, el bloqueo. */
export function instalarSeguridad(datos, { bloqueoAutomatico = true } = {}) {
  usuario = datos;
  const barra = document.querySelector('header.barra');
  if (barra && !document.getElementById('boton-bloquear')) {
    const boton = crear('button', { type: 'button', className: 'boton-icono', id: 'boton-bloquear', title: 'Bloquear pantalla' }, [
      crear('span', { className: 'icono', texto: 'lock', 'aria-hidden': 'true' }),
    ]);
    boton.addEventListener('click', bloquear);
    const salir = document.getElementById('cerrar-sesion');
    if (salir) salir.before(boton);
    else barra.append(boton);
  }
  if (datos.bloqueada) {
    recargarAlDesbloquear = true;
    mostrarBloqueo();
  }

  marcarActividad();
  for (const evento of ['pointerdown', 'keydown', 'wheel', 'touchstart']) {
    addEventListener(evento, marcarActividad, { passive: true });
  }
  if (bloqueoAutomatico) {
    const limite = (datos.bloqueo_minutos ?? 10) * 60000;
    setInterval(() => {
      if (!bloqueada && ahora() - ultimaDeTodas() >= limite) bloquear();
    }, 15000);
  }
}

/** Botón Bloquear o inactividad: el servidor deja de responder hasta desbloquear. */
export async function bloquear() {
  mostrarBloqueo();
  try {
    await api('POST', '/auth/bloquear');
  } catch { /* si falla, la pantalla igual queda tapada y el servidor la pedirá al usar algo */ }
}

// =====================================================================
//  Pantalla de bloqueo
// =====================================================================

export function mostrarBloqueo() {
  if (bloqueada) return;
  bloqueada = true;
  document.querySelectorAll('dialog[open]').forEach((d) => d.close());
  const conPin = Boolean(usuario?.tiene_pin);

  const campo = crear('input', {
    id: 'clave-bloqueo', type: 'password', autocomplete: conPin ? 'off' : 'current-password',
    inputmode: conPin ? 'numeric' : 'text', maxlength: conPin ? '6' : '128',
    'aria-label': conPin ? 'PIN' : 'Contraseña', placeholder: conPin ? 'PIN' : 'Contraseña',
  });
  let usandoPin = conPin;
  const error = crear('div', { className: 'alerta-error', role: 'alert', hidden: '' });
  const alternar = crear('button', { type: 'button', className: 'boton-texto', texto: 'Usar mi contraseña' });
  alternar.hidden = !conPin;
  alternar.addEventListener('click', () => {
    usandoPin = !usandoPin;
    campo.value = '';
    campo.placeholder = usandoPin ? 'PIN' : 'Contraseña';
    campo.inputMode = usandoPin ? 'numeric' : 'text';
    campo.maxLength = usandoPin ? 6 : 128;
    alternar.textContent = usandoPin ? 'Usar mi contraseña' : 'Usar mi PIN';
    campo.focus();
  });

  const salir = crear('button', { type: 'button', className: 'boton-texto', texto: 'Cerrar sesión' });
  salir.addEventListener('click', cerrarSesion);
  const formulario = crear('form', { className: 'tarjeta-bloqueo' }, [
    crear('span', { className: 'icono icono-bloqueo', texto: 'lock', 'aria-hidden': 'true' }),
    crear('h2', { texto: 'Pantalla bloqueada' }),
    crear('p', { className: 'nota', texto: usuario ? `${usuario.nombre} ${usuario.apellido} · ${usuario.rol}` : '' }),
    crear('div', { className: 'campo' }, [campo]),
    error,
    crear('button', { type: 'submit', className: 'boton-principal', texto: 'Desbloquear' }),
    crear('div', { className: 'acciones-bloqueo' }, [alternar, salir]),
    ...(conPin ? [] : [crear('p', { className: 'nota', texto: 'Crea tu PIN en el menú («Mi PIN») para desbloquear más rápido.' })]),
  ]);
  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    if (!campo.value) return;
    error.hidden = true;
    try {
      await api('POST', '/auth/desbloquear', usandoPin ? { pin: campo.value } : { password: campo.value }, { sinPin: true });
      if (recargarAlDesbloquear) {
        location.reload();
        return;
      }
      bloqueada = false;
      capa.remove();
      marcarActividad();
      mostrarAviso('Sesión desbloqueada', 'exito');
    } catch (e) {
      error.textContent = e.message; // por ejemplo "PIN incorrecto (te quedan 3 intentos)"
      error.hidden = false;
      campo.value = '';
      campo.focus();
    }
  });

  const capa = crear('div', { className: 'capa-bloqueo', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Pantalla bloqueada' }, [formulario]);
  document.body.append(capa);
  campo.focus();
}

// =====================================================================
//  PIN para cobrar, anular y sacar inventario
// =====================================================================

/** Ventana para escribir 4 a 6 números. Devuelve el texto o null si se cancela. */
function ventanaPin({ titulo, detalle, error = '', conClave = false }) {
  return new Promise((resolver) => {
    const pin = crear('input', { type: 'password', inputmode: 'numeric', maxlength: '6', autocomplete: 'off', 'aria-label': 'PIN', placeholder: '••••' });
    const clave = crear('input', { type: 'password', autocomplete: 'current-password', 'aria-label': 'Contraseña', placeholder: 'Tu contraseña' });
    const repetir = crear('input', { type: 'password', inputmode: 'numeric', maxlength: '6', autocomplete: 'off', 'aria-label': 'Repite el PIN', placeholder: 'Repite el PIN' });
    const aviso = crear('div', { className: 'alerta-error', role: 'alert', texto: error });
    aviso.hidden = !error;
    const cancelar = crear('button', { type: 'button', className: 'boton-texto', texto: 'Cancelar' });
    const dialogo = crear('dialog', { className: 'dialogo-pin' }, [
      crear('form', { method: 'dialog' }, [
        crear('h2', { texto: titulo }),
        crear('p', { className: 'nota', texto: detalle }),
        ...(conClave ? [crear('label', { className: 'etiqueta', texto: 'Contraseña' }), crear('div', { className: 'campo' }, [clave])] : []),
        ...(conClave ? [crear('label', { className: 'etiqueta', texto: 'Nuevo PIN (4 a 6 números)' })] : []),
        crear('div', { className: 'campo campo-pin' }, [pin]),
        ...(conClave ? [crear('div', { className: 'campo campo-pin' }, [repetir])] : []),
        aviso,
        crear('div', { className: 'acciones' }, [cancelar, crear('button', { type: 'submit', className: 'boton-principal', texto: conClave ? 'Guardar PIN' : 'Continuar' })]),
      ]),
    ]);
    let resultado = null;
    cancelar.addEventListener('click', () => dialogo.close());
    dialogo.querySelector('form').addEventListener('submit', (evento) => {
      if (!/^\d{4,6}$/.test(pin.value)) {
        evento.preventDefault();
        aviso.textContent = 'El PIN tiene de 4 a 6 números';
        aviso.hidden = false;
        return;
      }
      if (conClave && (pin.value !== repetir.value || !clave.value)) {
        evento.preventDefault();
        aviso.textContent = clave.value ? 'Los dos PIN no coinciden' : 'Escribe tu contraseña';
        aviso.hidden = false;
        return;
      }
      resultado = conClave ? { pin: pin.value, password: clave.value } : pin.value;
    });
    dialogo.addEventListener('close', () => { dialogo.remove(); resolver(resultado); });
    document.body.append(dialogo);
    dialogo.showModal();
    (conClave ? clave : pin).focus();
  });
}

/** Crea o cambia el PIN personal (pide la contraseña). Devuelve true si se guardó. */
export async function crearPin(detalle = 'Lo usarás para cobrar, anular pagos, sacar inventario y desbloquear la pantalla.') {
  let error = '';
  for (;;) {
    const datos = await ventanaPin({ titulo: usuario?.tiene_pin ? 'Cambiar mi PIN' : 'Crea tu PIN', detalle, error, conClave: true });
    if (!datos) return false;
    try {
      await api('PUT', '/auth/pin', datos, { sinPin: true });
      if (usuario) usuario.tiene_pin = true;
      mostrarAviso('PIN guardado', 'exito');
      return true;
    } catch (e) {
      error = e.message; // por ejemplo "Ese PIN es muy fácil de adivinar"
    }
  }
}

/** Lo llama api() cuando el servidor pide el PIN. Devuelve el PIN o null si se cancela. */
export async function pedirPin(error) {
  if (error.clave === 'PIN_NO_CONFIGURADO') {
    const creado = await crearPin('Esta operación pide tu PIN y todavía no tienes uno. Créalo ahora (lo pedirá cada vez que cobres, anules o saques inventario).');
    if (!creado) return null;
  }
  return ventanaPin({
    titulo: 'Escribe tu PIN',
    detalle: 'Confirma que eres tú antes de continuar.',
    error: error.clave === 'PIN_INCORRECTO' ? error.message : '',
  });
}
