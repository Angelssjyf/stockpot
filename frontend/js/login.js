// RF-01.4 Pantalla de inicio de sesión.
import { api, sesion } from './api.js';

const formulario = document.getElementById('form-login');
const email = document.getElementById('email');
const password = document.getElementById('password');
const verClave = document.getElementById('ver-clave');
const botonIngresar = document.getElementById('boton-ingresar');
const errorLogin = document.getElementById('error-login');

/** Muestra la pantalla de carga (la olla echando vapor) y luego abre el menú. */
function entrar() {
  document.getElementById('pantalla-carga').hidden = false;
  const espera = matchMedia('(prefers-reduced-motion: reduce)').matches ? 200 : 1400;
  setTimeout(() => location.replace('/menu.html'), espera);
}

// Si ya hay una sesión guardada y sigue vigente, entra directo al menú
if (sesion.token) {
  api('GET', '/auth/me')
    .then(entrar)
    .catch((error) => {
      if (error.codigo === 401) sesion.cerrar(); // token vencido: hay que iniciar sesión
    });
}

// Botón del ojo: muestra u oculta la contraseña
verClave.addEventListener('click', () => {
  const oculta = password.type === 'password';
  password.type = oculta ? 'text' : 'password';
  verClave.querySelector('.icono').textContent = oculta ? 'visibility_off' : 'visibility';
  verClave.title = oculta ? 'Ocultar contraseña' : 'Mostrar contraseña';
});

/** Marca un campo con su mensaje de error (o lo limpia si el mensaje está vacío). */
function marcarCampo(nombre, mensaje) {
  document.getElementById(`error-${nombre}`).textContent = mensaje;
  document.getElementById(`campo-${nombre}`).classList.toggle('invalido', Boolean(mensaje));
}

/** Revisa los campos antes de llamar a la API. Devuelve true si están bien. */
function validar() {
  const errorEmail = email.value.includes('@') ? '' : 'Escribe un correo válido';
  const errorClave = password.value ? '' : 'Escribe tu contraseña';
  marcarCampo('email', errorEmail);
  marcarCampo('password', errorClave);
  return !errorEmail && !errorClave;
}

formulario.addEventListener('submit', async (evento) => {
  evento.preventDefault(); // evita que el navegador recargue la página
  errorLogin.hidden = true;
  if (!validar()) return;

  botonIngresar.disabled = true;
  botonIngresar.textContent = 'Ingresando…';
  try {
    const respuesta = await api('POST', '/auth/login', {
      email: email.value.trim(),
      password: password.value,
    });
    sesion.guardar(respuesta.access_token);
    entrar();
  } catch (error) {
    errorLogin.textContent = error.message; // mensaje que envía la API, en español
    errorLogin.hidden = false;
    botonIngresar.disabled = false;
    botonIngresar.textContent = 'Ingresar';
  }
});
