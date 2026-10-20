// Menú principal: muestra solo los módulos que el rol del usuario puede ver.
import { cerrarSesion, exigirSesion } from './api.js';
import { crear, mostrarAviso } from './ui.js';

/**
 * Los 11 módulos de StockPot, en el orden de las iteraciones..
 * permiso: el permiso mínimo para ver el módulo (cargados en database/02_seed.sql).
 * pagina: la pantalla del módulo; null = todavía en construcción.
 */
const MODULOS = [
  { titulo: 'Usuarios', icono: 'group', permiso: 'usuarios.ver', pagina: 'usuarios.html' },
  { titulo: 'Proveedores', icono: 'local_shipping', permiso: 'proveedores.ver', pagina: 'proveedores.html' },
  { titulo: 'Inventario', icono: 'inventory_2', permiso: 'inventario.ver', pagina: 'insumos.html' },
  { titulo: 'Menú', icono: 'restaurant_menu', permiso: 'productos.ver', pagina: 'productos.html' },
  { titulo: 'Pedidos', icono: 'receipt_long', permiso: 'pedidos.ver', pagina: null },
  { titulo: 'Cocina', icono: 'soup_kitchen', permiso: 'cocina.ver', pagina: null },
  { titulo: 'Reservas', icono: 'event_seat', permiso: 'reservas.ver', pagina: null },
  { titulo: 'Domicilios', icono: 'delivery_dining', permiso: 'domicilios.ver', pagina: 'domicilios.html' },
  { titulo: 'Pagos', icono: 'payments', permiso: 'pagos.ver', pagina: 'caja.html' },
  { titulo: 'Ventas', icono: 'point_of_sale', permiso: 'ventas.ver', pagina: 'ventas.html' },
  { titulo: 'Reportes', icono: 'bar_chart', permiso: 'reportes.ver', pagina: 'reportes.html' },
];

const usuario = await exigirSesion(); // sin sesión vuelve al login

document.getElementById('usuario-actual').textContent = `${usuario.nombre} · ${usuario.rol}`;
document.getElementById('cerrar-sesion').addEventListener('click', cerrarSesion);

// El filtro por rol: solo los módulos cuyo permiso tiene el usuario
const visibles = MODULOS.filter((modulo) => usuario.permisos.includes(modulo.permiso));

const contenedor = document.getElementById('modulos');
for (const modulo of visibles) {
  const tarjeta = crear('button', { className: 'tarjeta-modulo', type: 'button' }, [
    crear('span', { className: 'icono', texto: modulo.icono, 'aria-hidden': 'true' }),
    crear('span', { texto: modulo.titulo }),
  ]);
  tarjeta.addEventListener('click', () => {
    if (modulo.pagina) {
      location.href = modulo.pagina;
    } else {
      mostrarAviso(`El módulo ${modulo.titulo} está en construcción`);
    }
  });
  contenedor.appendChild(tarjeta);
}
