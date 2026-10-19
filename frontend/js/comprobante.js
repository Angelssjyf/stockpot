// RF-09.6 Comprobante de pago listo para imprimir (o guardar como PDF desde el navegador).
import { api, exigirSesion } from './api.js';
import { crear, formato } from './ui.js';

await exigirSesion('pagos.ver');

const METODOS = { EFECTIVO: 'Efectivo', TARJETA: 'Tarjeta', TRANSFERENCIA: 'Transferencia' };
const contenedor = document.getElementById('comprobante');

document.getElementById('imprimir').addEventListener('click', () => window.print());
document.getElementById('cerrar').addEventListener('click', () => window.close());

/** Una fila de dos columnas: texto a la izquierda y valor a la derecha. */
function fila(texto, valor, clase = '') {
  return crear('div', { className: `fila-comprobante ${clase}` }, [
    crear('span', { texto }), crear('span', { texto: valor }),
  ]);
}

try {
  const ordenId = new URLSearchParams(location.search).get('orden');
  const c = await api('GET', `/ordenes/${encodeURIComponent(ordenId)}/comprobante`);
  const fecha = new Date(c.fecha).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });

  const partes = [
    crear('h1', { texto: c.restaurante }),
    crear('p', { className: 'centrado', texto: c.venta ? 'Comprobante de venta' : 'Comprobante de abono' }),
    fila('N.º', c.numero), fila('Pedido', c.codigo), fila('Fecha', fecha), fila('Atendió', c.atendido_por),
  ];
  if (c.cliente) partes.push(fila('Cliente', `${c.cliente.nombre} · ${c.cliente.telefono}`));
  if (c.direccion) partes.push(fila('Entrega en', c.direccion));

  partes.push(crear('hr'));
  for (const d of c.productos) {
    partes.push(fila(`${d.cantidad} × ${d.producto}`, formato.dinero(d.subtotal)));
  }
  partes.push(crear('hr'), fila('Subtotal', formato.dinero(c.subtotal)));
  if (c.costo_envio) partes.push(fila('Envío', formato.dinero(c.costo_envio)));
  partes.push(
    fila('TOTAL', formato.dinero(c.total), 'grande'),
    fila('Incluye impoconsumo (8 %)', formato.dinero(c.impoconsumo_incluido), 'pequena'),
    crear('hr'),
  );
  for (const p of c.pagos) {
    partes.push(fila(METODOS[p.metodo] + (p.referencia ? ` (ref. ${p.referencia})` : ''), formato.dinero(p.monto)));
    if (p.recibido) partes.push(fila('  Recibido', formato.dinero(p.recibido), 'pequena'));
    if (p.cambio) partes.push(fila('  Cambio', formato.dinero(p.cambio), 'pequena'));
  }
  if (c.saldo > 0) partes.push(fila('Saldo pendiente', formato.dinero(c.saldo), 'grande'));
  partes.push(crear('p', { className: 'centrado', texto: '¡Gracias por su compra!' }));
  contenedor.replaceChildren(...partes);
} catch (error) {
  contenedor.replaceChildren(crear('p', { className: 'alerta-error', texto: error.message }));
}
