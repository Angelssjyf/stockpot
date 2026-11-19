// Restaurantes (tercer corte): el súper administrador crea, modifica, activa y desactiva empresas.
// No ve el inventario, los pedidos ni las ventas de ningún restaurante.
import { api, cerrarSesion, exigirSesion } from './api.js';
import {
  confirmar, contarHasta, crear, empezarCarga, mostrarAviso, mostrarEstado, normalizar, pintarSuave,
} from './ui.js';

const yo = await exigirSesion('empresas.gestionar'); // sin el permiso vuelve al menú

const $ = (id) => document.getElementById(id);
$('usuario-actual').textContent = 'Súper administrador';
$('cerrar-sesion').addEventListener('click', cerrarSesion);

// Saludo según la hora, con la fecha de hoy (como en el menú de los restaurantes)
const ahora = new Date();
const saludo = ahora.getHours() < 12 ? 'Buenos días' : ahora.getHours() < 19 ? 'Buenas tardes' : 'Buenas noches';
const fechaLarga = ahora.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
$('saludo').replaceChildren(crear('div', {}, [
  crear('h2', { texto: `${saludo}, ${yo.nombre}` }),
  crear('p', { className: 'nota', texto: `${fechaLarga.charAt(0).toUpperCase() + fechaLarga.slice(1)} · los restaurantes que usan StockPot` }),
]));

function tarjetaResumen(icono, titulo, valor, clase = '') {
  const numero = crear('div', { className: 'valor', texto: '0' });
  contarHasta(numero, valor);
  return crear('div', { className: `tarjeta-resumen ${clase}`.trim() }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    numero,
    crear('div', { texto: titulo }),
  ]);
}

/** «Activo hace 5 min», «hace 3 h», «ayer», «hace 4 días» o la fecha. */
function haceCuanto(iso) {
  if (!iso) return 'Nadie ha entrado todavía';
  const minutos = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
  if (minutos < 1) return 'Activo hace un momento';
  if (minutos < 60) return `Activo hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `Activo hace ${horas} h`;
  const dias = Math.round(horas / 24);
  if (dias === 1) return 'Activo ayer';
  if (dias < 30) return `Activo hace ${dias} días`;
  return `Activo el ${new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })}`;
}

/** Iniciales del restaurante para su círculo: «Café La Esquina» → «CL», «Asadero El Fogón» → «AF». */
function inicialesDe(nombre) {
  const palabras = nombre.split(/\s+/).filter((p) => p.length > 2);
  return (palabras.length ? palabras : [nombre]).slice(0, 2).map((p) => p[0].toUpperCase()).join('');
}

let empresas = [];
let filtro = 'todos';

async function cargar() {
  if (empezarCarga($('lista'))) mostrarEstado('Cargando…', { cargando: true });
  try {
    empresas = await api('GET', '/empresas');
    const activas = empresas.filter((e) => e.activa).length;
    const desactivadas = empresas.length - activas;
    pintarSuave($('resumen'),
      tarjetaResumen('storefront', 'Restaurantes', empresas.length),
      tarjetaResumen('check_circle', 'Activos', activas),
      tarjetaResumen('block', 'Desactivados', desactivadas, desactivadas ? 'aviso-agotado' : ''),
      tarjetaResumen('group', 'Usuarios activos', empresas.reduce((n, e) => n + e.usuarios_activos, 0)),
      tarjetaResumen('wifi', 'Conectados ahora', empresas.reduce((n, e) => n + (e.conectados ?? 0), 0)),
    );
    pintarLista();
  } catch (error) {
    mostrarEstado(error.message, { reintentar: true });
  }
}

/** Aplica la búsqueda y el filtro de estado sin volver a pedir los datos. */
function pintarLista() {
  if (empresas.length === 0) {
    mostrarEstado('Todavía no hay restaurantes', {
      icono: 'storefront', detalle: 'Crea el primero con su administrador.',
      accion: { texto: 'Nuevo restaurante', icono: 'add_business', alHacer: () => abrirFormulario(null) },
    });
    pintarSuave($('lista'));
    return;
  }
  const texto = normalizar($('buscar').value.trim());
  const visibles = empresas.filter((e) => (filtro === 'todos' || (filtro === 'activos') === e.activa)
    && (!texto || normalizar([e.nombre, e.nit, ...e.administradores.flatMap((a) => [a.nombre, a.email])].join(' '))
      .includes(texto)));
  if (visibles.length === 0) {
    mostrarEstado('Ningún restaurante coincide', {
      icono: 'search_off', detalle: 'Prueba con otro nombre o NIT, o cambia el filtro.',
      accion: { texto: 'Ver todos', icono: 'close', alHacer: limpiarFiltros },
    });
    pintarSuave($('lista'));
    return;
  }
  $('estado').hidden = true;
  pintarSuave($('lista'), ...visibles.map(filaDeEmpresa));
}

function elegirFiltro(nuevo) {
  filtro = nuevo;
  for (const chip of $('filtros').querySelectorAll('.chip')) {
    chip.setAttribute('aria-pressed', String(chip.dataset.filtro === nuevo));
  }
  pintarLista();
}

function limpiarFiltros() {
  $('buscar').value = '';
  elegirFiltro('todos');
}

$('filtros').addEventListener('click', (evento) => {
  const chip = evento.target.closest('.chip');
  if (chip) elegirFiltro(chip.dataset.filtro);
});
$('buscar').addEventListener('input', pintarLista);
$('form-buscar').addEventListener('submit', (evento) => evento.preventDefault());

/** Una fila: iniciales, nombre, NIT y contacto, su administrador, actividad, estado y usuarios. */
function filaDeEmpresa(empresa) {
  const conectados = empresa.conectados ?? 0;
  const chips = [
    crear('span', { className: `chip ${empresa.activa ? 'estado-ENTREGADO' : 'estado-CANCELADO'}`,
      texto: empresa.activa ? 'Activo' : 'Desactivado' }),
    crear('span', { className: 'chip', texto: `${empresa.usuarios_activos} de ${empresa.usuarios} usuarios` }),
  ];
  const admin = empresa.administradores[0];
  const actividad = crear('div', { className: `actividad${conectados ? ' en-linea' : ''}` }, [
    crear('span', { className: 'punto', 'aria-hidden': 'true' }),
    crear('span', {
      texto: conectados ? `${conectados} ${conectados === 1 ? 'persona conectada' : 'personas conectadas'} ahora`
        : haceCuanto(empresa.ultima_actividad),
    }),
  ]);
  const fila = crear('li', { className: `fila editable fila-empresa${empresa.activa ? '' : ' inactiva'}` }, [
    crear('div', { className: 'avatar', texto: inicialesDe(empresa.nombre), 'aria-hidden': 'true' }),
    crear('div', { className: 'datos' }, [
      crear('div', { className: 'nombre', texto: empresa.nombre }),
      crear('div', { className: 'correo', texto: [`NIT ${empresa.nit}`, empresa.telefono, empresa.direccion].filter(Boolean).join(' · ') }),
      crear('div', { className: 'correo', texto: admin ? `Administra: ${admin.nombre} (${admin.email})` : 'Sin administrador' }),
      actividad,
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
        if (!$('f-activa').checked && !await confirmar(`¿Desactivar ${editada.nombre}?`, {
          texto: 'Su personal no podrá entrar hasta que lo vuelvas a activar.', aceptar: 'Desactivar', peligro: true,
          icono: 'block',
        })) {
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
