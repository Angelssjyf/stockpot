// RF-05.8 Comanda para la cocina: mesa, hora y productos con sus observaciones (sin precios).
import { api, exigirSesion } from './api.js';
import { crear } from './ui.js';

await exigirSesion('pedidos.ver');

const contenedor = document.getElementById('comanda');

document.getElementById('imprimir').addEventListener('click', () => window.print());
document.getElementById('cerrar').addEventListener('click', () => window.close());

/** Una fila de dos columnas: texto a la izquierda y valor a la derecha. */
function fila(texto, valor, clase = '') {
  return crear('div', { className: `fila-comprobante ${clase}` }, [crear('span', { texto }), crear('span', { texto: valor })]);
}

try {
  const pedidoId = new URLSearchParams(location.search).get('pedido');
  const c = await api('GET', `/pedidos/${encodeURIComponent(pedidoId)}/comanda`);
  const enviado = new Date(c.enviado).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });
  const partes = [
    crear('h1', { texto: `MESA ${c.mesa}` }),
    crear('p', { className: 'centrado', texto: 'Comanda de cocina' }),
    fila('Pedido', c.codigo), fila('Enviado', enviado), fila('Mesero', c.mesero), fila('Comensales', String(c.comensales)),
    crear('hr'),
  ];
  for (const p of c.productos) {
    partes.push(crear('div', { className: 'producto-comanda', texto: `${p.cantidad} × ${p.producto}` }));
    if (p.observacion) partes.push(crear('div', { className: 'pequena', texto: `   → ${p.observacion}` }));
  }
  if (c.observaciones) partes.push(crear('hr'), fila('Nota', c.observaciones));
  contenedor.replaceChildren(...partes);
} catch (error) {
  contenedor.replaceChildren(crear('p', { className: 'alerta-error', texto: error.message }));
}
