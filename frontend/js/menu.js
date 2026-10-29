// Menú principal: muestra solo los módulos que el rol del usuario puede ver.
import { api, cerrarSesion, exigirSesion } from './api.js';
import { contarHasta, crear, formato, mostrarAviso } from './ui.js';

/**
 * Los 11 módulos de StockPot, en el orden de las iteraciones.
 * permiso: el permiso mínimo para ver el módulo (cargados en database/02_seed.sql).
 * pagina: la pantalla del módulo; null = todavía en construcción.
 */
const MODULOS = [
  { titulo: 'Usuarios', icono: 'group', permiso: 'usuarios.ver', pagina: 'usuarios.html' },
  { titulo: 'Proveedores', icono: 'local_shipping', permiso: 'proveedores.ver', pagina: 'proveedores.html' },
  { titulo: 'Inventario', icono: 'inventory_2', permiso: 'inventario.ver', pagina: 'insumos.html' },
  { titulo: 'Menú', icono: 'restaurant_menu', permiso: 'productos.ver', pagina: 'productos.html' },
  { titulo: 'Pedidos', icono: 'receipt_long', permiso: 'pedidos.ver', pagina: 'pedidos.html' },
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

// =====================================================================
//  Resumen de hoy: saludo, tarjetas con los números del día y paneles.
//  Cada parte se pide por separado y solo si el rol tiene el permiso;
//  si una falla, simplemente no aparece (el menú sigue funcionando).
// =====================================================================

const puede = (permiso) => usuario.permisos.includes(permiso);

/** Fecha local en AAAA-MM-DD (toISOString usaría la hora UTC y cambiaría el día por la noche). */
function iso(fecha) {
  const dos = (n) => String(n).padStart(2, '0');
  return `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}`;
}

const ahora = new Date();
const hoy = iso(ahora);
const haceSeis = iso(new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate() - 6));
const compacto = (valor) => new Intl.NumberFormat('es-CO', { notation: 'compact', maximumFractionDigits: 1 }).format(valor);

// Saludo según la hora, con la fecha de hoy
const saludo = ahora.getHours() < 12 ? 'Buenos días' : ahora.getHours() < 19 ? 'Buenas tardes' : 'Buenas noches';
const fechaLarga = ahora.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
document.getElementById('saludo').replaceChildren(crear('div', {}, [
  crear('h2', { texto: `${saludo}, ${usuario.nombre}` }),
  crear('p', { className: 'nota', texto: fechaLarga.charAt(0).toUpperCase() + fechaLarga.slice(1) }),
]));

/** Una tarjeta del día: ícono, número grande (con conteo) y detalle; al tocarla abre su módulo. */
function tarjetaHoy({ icono, titulo, valor, formatear = String, texto, detalle, pagina, alerta = false }) {
  const numero = crear('div', { className: 'valor' });
  if (texto !== undefined) numero.textContent = texto;
  else contarHasta(numero, valor, formatear);
  const tarjeta = crear('button', { type: 'button', className: `tarjeta-hoy${alerta ? ' alerta' : ''}` }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', {}, [crear('small', { texto: titulo }), numero, crear('small', { texto: detalle })]),
  ]);
  tarjeta.addEventListener('click', () => { location.href = pagina; });
  return tarjeta;
}

function panel(icono, titulo, contenido) {
  return crear('section', { className: 'panel' }, [
    crear('h3', {}, [crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }), document.createTextNode(titulo)]),
    contenido,
  ]);
}

/** Lista con puesto, nombre, valor y una barrita proporcional. */
function ranking(filas, peligro = false) {
  return crear('ol', { className: 'ranking' }, filas.map(({ nombre, valor, proporcion }, i) => crear('li', {}, [
    crear('span', { className: 'puesto', texto: String(i + 1) }),
    crear('span', { className: 'nombre-ranking', texto: nombre }),
    crear('strong', { texto: valor }),
    crear('span', { className: `medidor${peligro ? ' peligro' : ''}`, 'aria-hidden': 'true' }, [
      crear('span', { style: `--ancho: ${Math.max(4, Math.round(proporcion * 100))}%` }),
    ]),
  ])));
}

/** Barras de lo vendido cada día de la última semana (hoy resaltado). */
function barrasSemana(ventas) {
  const dias = Array.from({ length: 7 }, (_, i) => new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate() - 6 + i));
  const totales = new Map(dias.map((d) => [iso(d), 0]));
  for (const venta of ventas) {
    const dia = iso(new Date(venta.fecha));
    if (totales.has(dia)) totales.set(dia, totales.get(dia) + venta.total);
  }
  const maximo = Math.max(...totales.values(), 1);
  return crear('div', { className: 'barras-semana', role: 'img', 'aria-label': 'Ventas de los últimos 7 días' }, dias.map((d, i) => {
    const total = totales.get(iso(d));
    const nombreDia = d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric' });
    return crear('div', { className: `barra-dia${i === 6 ? ' hoy-dia' : ''}`, title: `${nombreDia}: ${formato.dinero(total)}` }, [
      crear('small', { className: 'monto', texto: total ? `$${compacto(total)}` : '' }),
      crear('span', { className: 'relleno', style: `--alto: ${(total / maximo) * 100}%; --i: ${i}` }),
      crear('small', { texto: i === 6 ? 'Hoy' : d.toLocaleDateString('es-CO', { weekday: 'short' }).replace('.', '') }),
    ]);
  }));
}

/** Pide algo a la API sin romper el menú si falla. */
const intentar = (promesa) => promesa.catch(() => null);

async function pintarResumenHoy() {
  const [ventasHoy, ventasSemana, masVendidos, mesas, porCobrar, domicilios, alertas, activos] = await Promise.all([
    puede('ventas.ver') ? intentar(api('GET', `/ventas?desde=${hoy}&hasta=${hoy}`)) : null,
    puede('ventas.ver') ? intentar(api('GET', `/ventas?desde=${haceSeis}&hasta=${hoy}`)) : null,
    puede('ventas.ver') ? intentar(api('GET', `/ventas/mas-vendidos?desde=${haceSeis}&hasta=${hoy}`)) : null,
    puede('pedidos.ver') ? intentar(api('GET', '/mesas')) : null,
    puede('pagos.ver') ? intentar(api('GET', '/ordenes/por-cobrar')) : null,
    puede('domicilios.ver') ? intentar(api('GET', '/domicilios')) : null,
    puede('inventario.ver') ? intentar(api('GET', '/inventario/alertas')) : null,
    puede('pedidos.ver') && !puede('ventas.ver') ? intentar(api('GET', '/pedidos')) : null, // el mesero ve sus pedidos
  ]);

  const tarjetas = [];
  if (ventasHoy) {
    const r = ventasHoy.resumen;
    tarjetas.push(tarjetaHoy({
      icono: 'point_of_sale', titulo: 'Vendido hoy', valor: r.total, formatear: formato.dinero, pagina: 'ventas.html',
      detalle: `${r.ventas} venta${r.ventas === 1 ? '' : 's'}${r.ventas ? ` · ticket ${formato.dinero(r.ticket_promedio)}` : ''}`,
    }));
  }
  if (mesas) {
    const activas = mesas.filter((m) => m.activa);
    const ocupadas = activas.filter((m) => m.ocupada).length;
    tarjetas.push(tarjetaHoy({
      icono: 'table_restaurant', titulo: 'Mesas ocupadas', texto: `${ocupadas} de ${activas.length}`, pagina: 'pedidos.html',
      detalle: ocupadas ? `${activas.length - ocupadas} libres` : 'Todas libres',
    }));
  }
  if (porCobrar) {
    const saldo = porCobrar.reduce((suma, o) => suma + o.saldo, 0);
    const n = porCobrar.length;
    tarjetas.push(tarjetaHoy({
      icono: 'payments', titulo: 'Por cobrar', valor: saldo, formatear: formato.dinero, pagina: 'caja.html',
      detalle: `${n} ${n === 1 ? 'orden' : 'órdenes'} abierta${n === 1 ? '' : 's'}`,
    }));
  }
  if (domicilios) {
    tarjetas.push(tarjetaHoy({
      icono: 'delivery_dining', titulo: 'Domicilios en curso', valor: domicilios.length, pagina: 'domicilios.html',
      detalle: domicilios.length ? 'por entregar' : 'Ninguno pendiente',
    }));
  }
  if (alertas) {
    const agotados = alertas.filter((a) => a.estado_stock === 'AGOTADO').length;
    tarjetas.push(tarjetaHoy({
      icono: 'warning', titulo: 'Insumos por reponer', valor: alertas.length, alerta: alertas.length > 0, pagina: 'insumos.html',
      detalle: alertas.length ? `${agotados} agotado${agotados === 1 ? '' : 's'}` : 'Todo en orden',
    }));
  }

  const paneles = [];
  if (ventasSemana) {
    const contenido = crear('div', {}, [barrasSemana(ventasSemana.ventas)]);
    if (!ventasSemana.ventas.length) {
      contenido.appendChild(crear('p', { className: 'nota barras-vacias', texto: 'Todavía no hay ventas esta semana.' }));
    }
    paneles.push(panel('bar_chart', 'Ventas de la semana', contenido));
  }
  if (masVendidos) {
    const top = masVendidos.slice(0, 5);
    paneles.push(panel('local_fire_department', 'Más vendidos de la semana', top.length
      ? ranking(top.map((p) => ({ nombre: p.producto, valor: `${p.cantidad}`, proporcion: p.cantidad / top[0].cantidad })))
      : crear('p', { className: 'nota', texto: 'Todavía no hay ventas esta semana.' })));
  }
  if (activos) {
    paneles.push(panel('receipt_long', 'Pedidos activos', activos.length
      ? ranking(activos.slice(0, 5).map((p) => ({ nombre: `${p.codigo} · Mesa ${p.mesa.numero}`, valor: formato.dinero(p.total), proporcion: 1 })))
      : crear('p', { className: 'nota', texto: 'No hay pedidos activos.' })));
  }
  if (alertas) {
    paneles.push(panel('inventory_2', 'Por reponer', alertas.length
      ? ranking(alertas.slice(0, 5).map((a) => ({
        nombre: a.nombre,
        valor: `${formato.cantidad(a.stock_actual)} ${a.unidad_medida}`,
        proporcion: a.stock_minimo ? Math.min(a.stock_actual / a.stock_minimo, 1) : 0,
      })), true)
      : crear('p', { className: 'nota', texto: 'Todos los insumos están sobre su mínimo.' })));
  }

  if (!tarjetas.length && !paneles.length) return; // el rol no tiene nada que resumir
  document.getElementById('hoy').replaceChildren(...tarjetas);
  document.getElementById('paneles').replaceChildren(...paneles);
  document.getElementById('resumen-hoy').hidden = false;
}

pintarResumenHoy();
