// Módulo de cocina (RF-06.1 a RF-06.7): tablero con los pedidos de mesa y los domicilios por preparar.
import { api, exigirSesion } from './api.js';
import { $, crear, mostrarAviso, mostrarEstado, pintarSuave, tarjetaResumen } from './ui.js';

// El tablero queda prendido en la cocina: no se bloquea solo (sí con el botón)
const yo = await exigirSesion('cocina.ver', { bloqueoAutomatico: false });
const puedeGestionar = yo.permisos.includes('cocina.gestionar');

const COLUMNAS = ['POR_PREPARAR', 'PREPARANDO', 'LISTO'];
const BOTON = {
  EN_PREPARACION: { texto: 'Empezar', icono: 'skillet' },
  LISTO: { texto: 'Listo', icono: 'check_circle' },
  ENTREGADO: { texto: 'Entregado', icono: 'room_service' },
};
const AVISO_MINUTOS = 15; // desde aquí la tarjeta se pone amarilla; al doble, roja

function espera(minutos) {
  if (minutos < 1) return 'recién llegado';
  return minutos < 60 ? `${minutos} min` : `${Math.floor(minutos / 60)} h ${minutos % 60} min`;
}

/** Una comanda: de dónde viene, cuánto lleva, los productos con sus notas y el botón del siguiente paso. */
function tarjeta(orden) {
  const urgencia = orden.columna === 'LISTO' ? ''
    : orden.minutos >= AVISO_MINUTOS * 2 ? ' urgente' : orden.minutos >= AVISO_MINUTOS ? ' demorada' : '';
  const partes = [
    crear('div', { className: 'cabeza-comanda' }, [
      crear('span', { className: 'icono', texto: orden.tipo === 'MESA' ? 'table_restaurant' : 'two_wheeler', 'aria-hidden': 'true' }),
      crear('div', {}, [
        crear('div', { className: 'origen', texto: orden.origen }),
        crear('div', { className: 'nota', texto: [orden.codigo, orden.detalle].filter(Boolean).join(' · ') }),
      ]),
      crear('span', { className: 'espera', texto: orden.columna === 'LISTO' ? 'Listo' : espera(orden.minutos) }),
    ]),
    crear('ul', { className: 'productos-comanda' }, orden.productos.map((p) => crear('li', {}, [
      crear('b', { texto: `${p.cantidad} ×` }),
      crear('span', { texto: ` ${p.producto}` }),
      ...(p.observacion ? [crear('div', { className: 'nota-producto', texto: p.observacion })] : []),
    ]))),
  ];
  if (orden.observaciones) partes.push(crear('p', { className: 'nota-producto', texto: orden.observaciones }));
  if (puedeGestionar && orden.siguiente) {
    const { texto, icono } = BOTON[orden.siguiente];
    const boton = crear('button', { type: 'button', className: orden.siguiente === 'LISTO' ? 'boton-principal' : 'boton-texto' }, [
      crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }), document.createTextNode(` ${texto}`),
    ]);
    boton.addEventListener('click', () => avanzar(orden, boton));
    partes.push(crear('div', { className: 'acciones' }, [boton]));
  } else if (orden.tipo === 'DOMICILIO' && orden.columna === 'LISTO') {
    partes.push(crear('p', { className: 'nota', texto: 'Esperando al domiciliario' }));
  }
  const elemento = crear('article', { className: `comanda${urgencia}` }, partes);
  elemento.dataset.clave = `${orden.tipo}-${orden.id}`;
  elemento.dataset.version = orden.estado;
  return elemento;
}

let cargando = false;
let desde = null; // hora del servidor de la última consulta (para RF-06.7)
async function cargar() {
  if (cargando) return;
  cargando = true;
  try {
    const { resumen, ordenes, hora } = await api('GET', '/cocina/ordenes');
    $('estado').hidden = true;
    desde ??= hora;
    pintarSuave($('resumen'),
      tarjetaResumen('inbox', 'Por preparar', String(resumen.POR_PREPARAR)),
      tarjetaResumen('skillet', 'Preparando', String(resumen.PREPARANDO)),
      tarjetaResumen('room_service', 'Listos', String(resumen.LISTO)),
      tarjetaResumen('timer', 'Espera más larga', espera(resumen.espera_maxima)),
    );
    for (const columna of COLUMNAS) {
      const deLaColumna = ordenes.filter((o) => o.columna === columna);
      $(`n-${columna}`).textContent = deLaColumna.length;
      if (deLaColumna.length) pintarSuave($(`col-${columna}`), ...deLaColumna.map(tarjeta));
      else $(`col-${columna}`).replaceChildren(crear('p', { className: 'nota vacia-cocina', texto: columna === 'POR_PREPARAR' ? 'Sin pedidos nuevos' : 'Nada por aquí' }));
    }
    $('actualizado').textContent = `Actualizado ${new Date(hora).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' })}`;
  } catch (error) {
    mostrarEstado(error.message, { reintentar: true });
  } finally {
    cargando = false;
  }
}

async function avanzar(orden, boton) {
  boton.disabled = true;
  try {
    await api('PATCH', `/cocina/ordenes/${orden.tipo}/${orden.id}/estado`, { estado: orden.siguiente }); // RF-06.4 a RF-06.6
    if (orden.siguiente === 'LISTO') mostrarAviso(`${orden.origen} listo para entregar`, 'exito');
    await cargar();
  } catch (error) {
    mostrarAviso(error.message, 'error'); // por ejemplo, otra persona ya lo cambió
    boton.disabled = false;
    cargar();
  }
}

// =====================================================================
//  RF-06.7 Notificar: pregunta cada 10 s qué llegó y suena un timbre corto
// =====================================================================

async function revisarNovedades() {
  if (document.hidden || !desde) return;
  try {
    const { hora, nuevos } = await api('GET', `/cocina/novedades?desde=${encodeURIComponent(desde)}`);
    desde = hora;
    if (nuevos.length) {
      mostrarAviso(nuevos.length === 1 ? `Nuevo pedido: ${nuevos[0].origen}` : `${nuevos.length} pedidos nuevos`, '',
        { sonido: 'pedido' });
      cargar();
    }
  } catch { /* si falla una consulta, la siguiente lo intenta otra vez */ }
}

$('reintentar').addEventListener('click', cargar);
setInterval(revisarNovedades, 10000);
setInterval(cargar, 60000); // también refresca los minutos de espera
document.addEventListener('visibilitychange', () => { if (!document.hidden) cargar(); });
cargar();
