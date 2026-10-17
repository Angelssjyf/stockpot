// Cliente de la API: única pieza de la interfaz que habla con Flask.
// Agrega el token a cada petición y convierte los errores en ApiError.

const CLAVE_TOKEN = 'stockpot_token';

/** Error que devuelve la API, por ejemplo {"error": "Correo o contraseña incorrectos"}. */
export class ApiError extends Error {
  constructor(codigo, mensaje) {
    super(mensaje);
    this.codigo = codigo; // código HTTP: 401, 403, 422... (0 = sin conexión)
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

/**
 * Llama a la API. Ejemplo: await api('POST', '/auth/login', {email, password})
 * La interfaz y la API están en la misma dirección, así que las rutas empiezan en /api.
 */
export async function api(metodo, ruta, datos) {
  const encabezados = {
    'Content-Type': 'application/json',
    // Evita que el plan gratis de ngrok responda con su página de advertencia
    'ngrok-skip-browser-warning': 'true',
  };
  if (sesion.token) encabezados.Authorization = `Bearer ${sesion.token}`;

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
  if (!respuesta.ok) {
    throw new ApiError(respuesta.status, cuerpo?.error ?? `Error ${respuesta.status}`);
  }
  return cuerpo;
}

/**
 * Protege una página: exige una sesión válida y, si se indica, un permiso.
 * Devuelve los datos del usuario (nombre, rol, permisos...).
 * Sin sesión vuelve al login; sin el permiso vuelve al menú.
 */
export async function exigirSesion(permiso) {
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
    return usuario;
  } catch (error) {
    if (error.codigo === 401) sesion.cerrar(); // token vencido o inválido
    location.replace('/');
    return detener();
  }
}

/** Cierra la sesión y vuelve a la pantalla de login. */
export function cerrarSesion() {
  sesion.cerrar();
  location.replace('/');
}
