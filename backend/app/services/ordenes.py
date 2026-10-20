"""Servicio de órdenes: arma las líneas de un pedido revisando la carta y el inventario.

Lo usan los domicilios (RF-08.1) y las ventas de mostrador (RF-10.1); más adelante, los
pedidos en mesa de la Iteración 3.
"""

from collections import defaultdict
from decimal import Decimal

from ..extensions import db
from ..models import DetalleOrden, Producto
from .inventario import numero


def _texto(valor):
    return str(valor if valor is not None else "").strip()


def armar_detalles(orden, items):
    """Agrega las líneas a la orden y calcula el subtotal. Devuelve (mensaje, código) o None.

    Revisa que cada producto esté en la carta y que el inventario alcance para preparar
    TODO el pedido (sumando lo que piden varios productos que comparten insumos).
    """
    if not isinstance(items, list) or not items:
        return "El pedido debe tener al menos un producto", 422

    necesario = defaultdict(Decimal)  # insumo -> cantidad total que pide el pedido
    subtotal = Decimal("0")
    for item in items:
        producto_id = item.get("producto_id") if isinstance(item, dict) else None
        producto = db.session.get(Producto, producto_id) if isinstance(producto_id, int) else None
        if producto is None or not producto.activo:
            return f"El producto {producto_id} no existe", 422
        if not producto.disponible:
            return f"'{producto.nombre}' no está disponible hoy", 409

        cantidad = item.get("cantidad")
        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
            return f"La cantidad de '{producto.nombre}' debe ser un número entero mayor que cero", 422

        for linea in producto.receta:
            necesario[linea.insumo] += linea.cantidad * cantidad

        linea_subtotal = producto.precio_venta * cantidad
        orden.detalles.append(DetalleOrden(
            producto=producto, cantidad=cantidad, precio_unitario=producto.precio_venta,
            subtotal=linea_subtotal, observacion=_texto(item.get("observacion")) or None,
        ))
        subtotal += linea_subtotal

    for insumo, cantidad in necesario.items():
        if insumo.stock_actual < cantidad:
            return (f"No alcanza '{insumo.nombre}' para este pedido: hay "
                    f"{numero(insumo.stock_actual)} {insumo.unidad_medida} y se necesitan "
                    f"{numero(cantidad)}"), 409

    orden.subtotal = subtotal
    return None
