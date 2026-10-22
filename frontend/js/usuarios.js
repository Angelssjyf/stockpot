// Módulo de usuarios: RF-01.1 Registrar, RF-01.2 Consultar, RF-01.3 Modificar, RF-01.5 Asignar roles.
import { api, exigirSesion } from './api.js';
import { crear, empezarCarga, iniciales, mostrarAviso, pintarSuave } from './ui.js';

const yo = await exigirSesion('usuarios.ver'); // sin el permiso vuelve al menú
const puedeGestionar = yo.permisos.includes('usuarios.gestionar');
const puedeCambiarRol = yo.permisos.includes('roles.gestionar');

const $ = (id) => document.getElementById(id);

// =====================================================================
//  RF-01.2 Consultar usuarios: lista con buscador
// =====================================================================

async function cargar() {
  if (empezarCarga($('lista'))) mostrarEstado('Cargando…'); // al recargar, la lista se queda atenuada
  try {
    const texto = encodeURIComponent($('buscar').value.trim());
    const usuarios = await api('GET', `/usuarios?q=${texto}`);
    if (usuarios.length === 0) {
      mostrarEstado('No se encontraron usuarios');
      pintarSuave($('lista'));
    } else {
      $('estado').hidden = true;
      pintarSuave($('lista'), ...usuarios.map(filaDeUsuario));
    }
  } catch (error) {
    mostrarEstado(error.message, true); // por ejemplo, el servidor no responde
  }
}

/** Muestra un mensaje en lugar de la lista (cargando, vacío o error con "Reintentar"). */
function mostrarEstado(texto, conReintentar = false) {
  $('estado').hidden = false;
  $('estado-texto').textContent = texto;
  $('reintentar').hidden = !conReintentar;
}

/** Una fila: círculo con iniciales, nombre, correo, rol y "Inactivo" si aplica. */
function filaDeUsuario(usuario) {
  const chips = [crear('span', { className: 'chip', texto: usuario.rol })];
  if (!usuario.activo) chips.unshift(crear('span', { className: 'chip', texto: 'Inactivo' }));

  const fila = crear('li', { className: puedeGestionar ? 'fila editable' : 'fila' }, [
    crear('div', { className: 'avatar', texto: iniciales(usuario.nombre, usuario.apellido) }),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: `${usuario.nombre} ${usuario.apellido}` }),
      crear('div', { className: 'correo', texto: usuario.email }),
    ]),
    crear('div', { className: 'chips' }, chips),
  ]);
  if (puedeGestionar) fila.addEventListener('click', () => abrirFormulario(usuario));
  return fila;
}

$('form-buscar').addEventListener('submit', (evento) => {
  evento.preventDefault();
  cargar(); // buscar al presionar Enter
});
$('limpiar').addEventListener('click', () => {
  $('buscar').value = '';
  cargar();
});
$('reintentar').addEventListener('click', cargar);

// =====================================================================
//  RF-01.1 Registrar y RF-01.3 Modificar: un solo formulario
// =====================================================================

const dialogo = $('dialogo-usuario');
let usuarioEditado = null; // null = crear uno nuevo

if (puedeGestionar) {
  $('boton-nuevo').hidden = false;
  $('boton-nuevo').addEventListener('click', () => abrirFormulario(null));
}

async function abrirFormulario(usuario) {
  usuarioEditado = usuario;
  const esEdicion = usuario !== null;

  $('form-usuario').reset();
  for (const campo of ['nombre', 'apellido', 'email', 'password', 'rol']) marcarCampo(campo, '');
  $('error-formulario').hidden = true;

  $('titulo-formulario').textContent = esEdicion ? 'Editar usuario' : 'Nuevo usuario';
  $('etiqueta-password').textContent = esEdicion ? 'Nueva contraseña (opcional)' : 'Contraseña *';
  $('ayuda-password').textContent = esEdicion ? 'Déjala vacía para no cambiarla' : 'Mínimo 8 caracteres';
  $('bloque-rol-nuevo').hidden = esEdicion;
  $('bloque-edicion').hidden = !esEdicion;

  if (esEdicion) {
    // Al editar, los campos empiezan con los datos actuales del usuario
    $('f-nombre').value = usuario.nombre;
    $('f-apellido').value = usuario.apellido;
    $('f-email').value = usuario.email;
    $('f-telefono').value = usuario.telefono ?? '';
    $('f-activo').checked = usuario.activo;
    $('rol-actual').textContent = usuario.rol;
    $('cambiar-rol').hidden = !puedeCambiarRol;
  }

  dialogo.showModal();

  if (!esEdicion) await cargarRoles(); // al crear hay que elegir un rol
}

async function cargarRoles() {
  try {
    const roles = await api('GET', '/roles');
    $('f-rol').replaceChildren(
      crear('option', { value: '', texto: 'Elige un rol' }),
      ...roles.map((rol) => crear('option', { value: rol.id, texto: rol.nombre })),
    );
  } catch (error) {
    mostrarErrorFormulario(error.message);
  }
}

/** Marca un campo con su mensaje de error (o lo limpia si el mensaje está vacío). */
function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`).classList.toggle('invalido', Boolean(mensaje));
}

function mostrarErrorFormulario(mensaje) {
  $('error-formulario').textContent = mensaje;
  $('error-formulario').hidden = false;
}

/** Revisa los campos antes de llamar a la API. Devuelve true si están bien. */
function validar() {
  const esEdicion = usuarioEditado !== null;
  const obligatorio = (valor) => (valor.trim() ? '' : 'Campo obligatorio');
  const clave = $('f-password').value;

  const errores = {
    nombre: obligatorio($('f-nombre').value),
    apellido: obligatorio($('f-apellido').value),
    email: $('f-email').value.includes('@') ? '' : 'Escribe un correo válido',
    password:
      !esEdicion && !clave ? 'Campo obligatorio'
        : clave && clave.length < 8 ? 'Mínimo 8 caracteres'
          : '',
    rol: !esEdicion && !$('f-rol').value ? 'Elige un rol' : '',
  };
  for (const [campo, mensaje] of Object.entries(errores)) marcarCampo(campo, mensaje);
  return Object.values(errores).every((mensaje) => !mensaje);
}

$('form-usuario').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-formulario').hidden = true;
  if (!validar()) return;

  const datos = {
    nombre: $('f-nombre').value.trim(),
    apellido: $('f-apellido').value.trim(),
    email: $('f-email').value.trim(),
    telefono: $('f-telefono').value.trim(),
  };
  // La contraseña solo se envía si se escribió algo (al editar es opcional)
  if ($('f-password').value) datos.password = $('f-password').value;

  $('guardar').disabled = true;
  try {
    if (usuarioEditado) {
      datos.activo = $('f-activo').checked;
      await api('PUT', `/usuarios/${usuarioEditado.id}`, datos); // RF-01.3
    } else {
      datos.rol_id = Number($('f-rol').value);
      await api('POST', '/usuarios', datos); // RF-01.1
    }
    dialogo.close();
    mostrarAviso(usuarioEditado ? 'Usuario actualizado' : 'Usuario creado');
  } catch (error) {
    mostrarErrorFormulario(error.message); // por ejemplo "Ya existe un usuario con ese correo"
  } finally {
    $('guardar').disabled = false;
  }
});

$('cancelar').addEventListener('click', () => dialogo.close());

// Al cerrar el formulario se recarga la lista (el rol pudo cambiar aunque no se haya guardado)
dialogo.addEventListener('close', cargar);

// =====================================================================
//  RF-01.5 Asignar roles: elige un rol nuevo y lo guarda de inmediato
// =====================================================================

const dialogoRol = $('dialogo-rol');

$('cambiar-rol').addEventListener('click', async () => {
  try {
    const roles = await api('GET', '/roles');
    $('opciones-rol').replaceChildren(
      ...roles.map((rol) => {
        const opcion = crear('button', { type: 'button', texto: rol.nombre });
        opcion.addEventListener('click', () => elegirRol(rol));
        return opcion;
      }),
    );
    dialogoRol.showModal();
  } catch (error) {
    mostrarErrorFormulario(error.message);
  }
});

$('cancelar-rol').addEventListener('click', () => dialogoRol.close());

async function elegirRol(rol) {
  dialogoRol.close();
  if (rol.nombre === $('rol-actual').textContent) return; // eligió el mismo

  try {
    await api('PATCH', `/usuarios/${usuarioEditado.id}/rol`, { rol_id: rol.id });
    $('rol-actual').textContent = rol.nombre;
    $('error-formulario').hidden = true;
    mostrarAviso(`Rol cambiado a ${rol.nombre}. Aplica cuando el usuario vuelva a iniciar sesión.`);
  } catch (error) {
    // Por ejemplo: "No puedes quitarle el rol al último administrador activo"
    mostrarErrorFormulario(error.message);
  }
}

cargar();
