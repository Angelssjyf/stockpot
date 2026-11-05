// Restaurantes (tercer corte): el súper administrador crea, modifica, activa y desactiva empresas.
// No ve el inventario, los pedidos ni las ventas de ningún restaurante.
import { api, cerrarSesion, exigirSesion } from './api.js';
import { crear, empezarCarga, mostrarAviso, mostrarEstado, pintarSuave } from './ui.js';

const yo = await exigirSesion('empresas.gestionar'); // sin el permiso vuelve al menú

const $ = (id) => document.getElementById(id);
$('usuario-actual').textContent = `${yo.nombre} · Súper administrador`;
$('cerrar-sesion').addEventListener('click', cerrarSesion);

function tarjetaResumen(icono, titulo, valor) {
  return crear('div', { className: 'tarjeta-resumen' }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
  ]);
}

async function cargar() {
  if (empezarCarga($('lista'))) mostrarEstado('Cargando…', { cargando: true });
  try {
    const empresas = await api('GET', '/empresas');
    const activas = empresas.filter((e) => e.activa).length;
    pintarSuave($('resumen'),
      tarjetaResumen('storefront', 'Restaurantes', String(empresas.length)),
      tarjetaResumen('check_circle', 'Activos', String(activas)),
      tarjetaResumen('block', 'Desactivados', String(empresas.length - activas)),
      tarjetaResumen('group', 'Usuarios activos', String(empresas.reduce((n, e) => n + e.usuarios_activos, 0))),
    );
    if (empresas.length === 0) {
      mostrarEstado('Todavía no hay restaurantes', {
        icono: 'storefront', detalle: 'Crea el primero con su administrador.',
        accion: { texto: 'Nuevo restaurante', icono: 'add_business', alHacer: () => abrirFormulario(null) },
      });
      pintarSuave($('lista'));
    } else {
      $('estado').hidden = true;
      pintarSuave($('lista'), ...empresas.map(filaDeEmpresa));
    }
  } catch (error) {
    mostrarEstado(error.message, { reintentar: true });
  }
}

/** Una fila: nombre, NIT y contacto, su administrador y cuántos usuarios tiene. */
function filaDeEmpresa(empresa) {
  const chips = [crear('span', { className: 'chip', texto: `${empresa.usuarios_activos} de ${empresa.usuarios} usuarios` })];
  if (!empresa.activa) chips.unshift(crear('span', { className: 'chip estado-CANCELADO', texto: 'Desactivado' }));
  const admin = empresa.administradores[0];
  const fila = crear('li', { className: `fila editable${empresa.activa ? '' : ' inactiva'}` }, [
    crear('div', { className: 'avatar' }, [crear('span', { className: 'icono', texto: 'storefront', 'aria-hidden': 'true' })]),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: empresa.nombre }),
      crear('div', { className: 'correo', texto: [`NIT ${empresa.nit}`, empresa.telefono, empresa.direccion].filter(Boolean).join(' · ') }),
      crear('div', { className: 'correo', texto: admin ? `Administra: ${admin.nombre} (${admin.email})` : 'Sin administrador' }),
    ]),
    crear('div', { className: 'chips' }, chips),
  ]);
  fila.addEventListener('click', () => abrirFormulario(empresa));
  return fila;
}

$('reintentar').addEventListener('click', cargar);

// =====================================================================
//  Crear y modificar: un solo formulario
// =====================================================================

const dialogo = $('dialogo-empresa');
const CAMPOS = ['nombre', 'nit', 'a-nombre', 'a-apellido', 'a-email', 'a-password'];
let editada = null; // null = restaurante nuevo

$('boton-nuevo').addEventListener('click', () => abrirFormulario(null));

function abrirFormulario(empresa) {
  editada = empresa;
  $('form-empresa').reset();
  for (const campo of CAMPOS) marcarCampo(campo, '');
  $('error-formulario').hidden = true;
  $('titulo-formulario').textContent = empresa ? empresa.nombre : 'Nuevo restaurante';
  $('bloque-admin').hidden = Boolean(empresa);
  $('bloque-estado').hidden = !empresa;
  if (empresa) {
    for (const campo of ['nombre', 'nit', 'telefono', 'email', 'direccion']) $(`f-${campo}`).value = empresa[campo] ?? '';
    $('f-activa').checked = empresa.activa;
    $('administradores').textContent = empresa.administradores.length
      ? `Administradores: ${empresa.administradores.map((a) => `${a.nombre} (${a.email})`).join(', ')}`
      : 'Este restaurante no tiene administrador activo.';
  }
  dialogo.showModal();
}

function marcarCampo(nombre, mensaje) {
  $(`error-${nombre}`).textContent = mensaje;
  $(`campo-${nombre}`).classList.toggle('invalido', Boolean(mensaje));
}

function validar() {
  const obligatorio = (id) => ($(id).value.trim() ? '' : 'Campo obligatorio');
  const errores = { nombre: obligatorio('f-nombre'), nit: obligatorio('f-nit') };
  if (!editada) {
    errores['a-nombre'] = obligatorio('a-nombre');
    errores['a-apellido'] = obligatorio('a-apellido');
    errores['a-email'] = $('a-email').value.includes('@') ? '' : 'Escribe un correo válido';
    errores['a-password'] = $('a-password').value.length >= 8 ? '' : 'Mínimo 8 caracteres';
  }
  for (const [campo, mensaje] of Object.entries(errores)) marcarCampo(campo, mensaje);
  return Object.values(errores).every((mensaje) => !mensaje);
}

$('form-empresa').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  $('error-formulario').hidden = true;
  if (!validar()) return;

  const datos = Object.fromEntries(['nombre', 'nit', 'telefono', 'email', 'direccion']
    .map((campo) => [campo, $(`f-${campo}`).value.trim()]));
  $('guardar').disabled = true;
  try {
    if (editada) {
      await api('PUT', `/empresas/${editada.id}`, datos);
      if ($('f-activa').checked !== editada.activa) {
        if (!$('f-activa').checked && !confirm(`¿Desactivar ${editada.nombre}? Su personal no podrá entrar.`)) {
          $('guardar').disabled = false;
          return;
        }
        await api('PATCH', `/empresas/${editada.id}/estado`, { activa: $('f-activa').checked });
      }
      mostrarAviso('Restaurante actualizado', 'exito');
    } else {
      datos.admin = {
        nombre: $('a-nombre').value.trim(),
        apellido: $('a-apellido').value.trim(),
        email: $('a-email').value.trim(),
        password: $('a-password').value,
      };
      await api('POST', '/empresas', datos);
      mostrarAviso(`Restaurante creado. Su administrador ya puede entrar con ${datos.admin.email}`, 'exito');
    }
    dialogo.close();
  } catch (error) {
    $('error-formulario').textContent = error.message; // por ejemplo "Ya existe un restaurante con ese NIT"
    $('error-formulario').hidden = false;
  } finally {
    $('guardar').disabled = false;
  }
});

$('cancelar').addEventListener('click', () => dialogo.close());
dialogo.addEventListener('close', cargar);

cargar();
