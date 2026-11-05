// Cliente de la API: única pieza de la interfaz que habla con Flask.
// Agrega el token a cada petición y convierte los errores en ApiError.
// Sesiones seguras: si el servidor pide el PIN lo pregunta y repite la petición; si la sesión
// está bloqueada muestra la pantalla de bloqueo; si se cerró vuelve al login con el motivo.

const CLAVE_TOKEN = 'stockpot_token';

/** Error que devuelve la API, por ejemplo {"error": "Correo o contraseña incorrectos"}. */
export class ApiError extends Error {
  constructor(codigo, mensaje, clave = null) {
    super(mensaje);
    this.codigo = codigo; // código HTTP: 401, 403, 422... (0 = sin conexión)
    this.clave = clave; // motivo para la interfaz: PIN_REQUERIDO, SESION_BLOQUEADA, INACTIVIDAD...
  }
}

/** Sesión guardada en el navegador (el token de inicio de sesión). */
export const sesion = {
  get token() {
    return localStorage.getItem(CLAVE_TOKEN);
  },
  guardar(token) {
    localStorage.setItem(CLAVE_TOKEN, token);
  },
  cerrar() {
    localStorage.removeItem(CLAVE_TOKEN);
  },
};

const PIDE_PIN = new Set(['PIN_REQUERIDO', 'PIN_NO_CONFIGURADO', 'PIN_INCORRECTO']);

/** Vuelve al login mostrando por qué se cerró la sesión. */
function irAlLogin(mensaje) {
  sesion.cerrar();
  if (mensaje) sessionStorage.setItem('stockpot_aviso', mensaje);
  location.replace('/');
}

/**
 * Llama a la API. Ejemplo: await api('POST', '/auth/login', {email, password})
 * La interfaz y la API están en la misma dirección, así que las rutas empiezan en /api.
 * opciones.segundoPlano: consultas automáticas (avisos) que no cuentan como uso de la sesión.
 */
export async function api(metodo, ruta, datos, opciones = {}) {
  const encabezados = {
    'Content-Type': 'application/json',
    // Evita que el plan gratis de ngrok responda con su página de advertencia
    'ngrok-skip-browser-warning': 'true',
  };
  if (sesion.token) encabezados.Authorization = `Bearer ${sesion.token}`;
  if (opciones.segundoPlano) encabezados['X-Segundo-Plano'] = '1';

  let respuesta;
  try {
    respuesta = await fetch(`/api${ruta}`, {
      method: metodo,
      headers: encabezados,
      body: datos === undefined ? undefined : JSON.stringify(datos),
    });
  } catch {
    throw new ApiError(0, 'No se pudo conectar con el servidor');
  }

  const cuerpo = await respuesta.json().catch(() => null);
  if (respuesta.ok) return cuerpo;

  const error = new ApiError(respuesta.status, cuerpo?.error ?? `Error ${respuesta.status}`, cuerpo?.codigo);
  const seguridad = () => import('./seguridad.js');
  // La operación pide el PIN (cobrar, anular, sacar inventario): se pregunta y se repite
  if (PIDE_PIN.has(error.clave) && !opciones.sinPin) {
    const pin = await (await seguridad()).pedirPin(error);
    if (pin === null) throw new ApiError(0, 'Operación cancelada: no se escribió el PIN');
    return api(metodo, ruta, { ...(datos ?? {}), pin }, opciones);
  }
  if (error.clave === 'SESION_BLOQUEADA') {
    (await seguridad()).mostrarBloqueo();
  } else if (respuesta.status === 401 && sesion.token && !ruta.startsWith('/auth/login')) {
    irAlLogin(error.message); // por ejemplo "La sesión se cerró por inactividad"
    await new Promise(() => {}); // la página se está yendo
  }
  throw error;
}

/**
 * Protege una página: exige una sesión válida y, si se indica, un permiso.
 * Devuelve los datos del usuario (nombre, rol, permisos...).
 * Sin sesión vuelve al login; sin el permiso vuelve al menú.
 * opciones.bloqueoAutomatico: false en pantallas que quedan prendidas (el tablero de cocina).
 */
export async function exigirSesion(permiso, opciones = {}) {
  const detener = () => new Promise(() => {}); // la página se está redirigiendo

  if (!sesion.token) {
    location.replace('/');
    return detener();
  }
  try {
    const usuario = await api('GET', '/auth/me');
    if (permiso && !usuario.permisos.includes(permiso)) {
      location.replace('/menu.html');
      return detener();
    }
    (await import('./seguridad.js')).instalarSeguridad(usuario, opciones);
    return usuario;
  } catch (error) {
    irAlLogin(error.codigo === 403 ? error.message : ''); // por ejemplo, restaurante desactivado
    return detener();
  }
}

/** Cierra la sesión (también en el servidor) y vuelve a la pantalla de login. */
export async function cerrarSesion() {
  try {
    await api('POST', '/auth/logout');
  } catch { /* si ya estaba cerrada, igual se sale */ }
  sesion.cerrar();
  location.replace('/');
}
