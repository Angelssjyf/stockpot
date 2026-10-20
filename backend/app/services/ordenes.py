"""Servicio de órdenes: arma las líneas de un pedido revisando la carta y el inventario.

Lo usan los domicilios (RF-08.1), las ventas de mostrador (RF-10.1) y los pedidos en mesa
(RF-05.1 a RF-05.7).
"""

from collections import defaultdict
from decimal import Decimal

from ..extensions import db
from ..models import DetalleOrden, Producto
from .inventario import numero


def _texto(valor):
    return str(valor if valor is not None else "").strip()


def leer_items(items):
    """Revisa los productos pedidos. Devuelve (lineas, necesario, None) o (None, None, error).

    lineas: [(producto, cantidad, observacion)]; necesario: {insumo: cantidad total que pide
    el pedido}, sumando lo que piden varios productos que comparten insumos.
    error: (mensaje, código HTTP).
    """
    if not isinstance(items, list) or not items:
        return None, None, ("El pedido debe tener al menos un producto", 422)

    lineas = []
    necesario = defaultdict(Decimal)
    for item in items:
        producto_id = item.get("producto_id") if isinstance(item, dict) else None
        producto = db.session.get(Producto, producto_id) if isinstance(producto_id, int) else None
        if producto is None or not producto.activo:
            return None, None, (f"El producto {producto_id} no existe", 422)
        if not producto.disponible:
            return None, None, (f"'{producto.nombre}' no está disponible hoy", 409)

        cantidad = item.get("cantidad")
        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
            return None, None, (
                f"La cantidad de '{producto.nombre}' debe ser un número entero mayor que cero", 422)

        for linea in producto.receta:
            necesario[linea.insumo] += linea.cantidad * cantidad
        lineas.append((producto, cantidad, _texto(item.get("observacion")) or None))
    return lineas, necesario, None


def faltantes(necesario):
    """Insumos que no alcanzan, del que más falta al que menos (lista vacía si alcanza todo)."""
    lista = [
        {
            "insumo_id": insumo.id,
            "insumo": insumo.nombre,
            "unidad_medida": insumo.unidad_medida,
            "hay": float(insumo.stock_actual),
            "necesita": float(cantidad),
            "falta": float(cantidad - insumo.stock_actual),
        }
        for insumo, cantidad in necesario.items()
        if insumo.stock_actual < cantidad
    ]
    return sorted(lista, key=lambda f: (-f["falta"], f["insumo"]))


def armar_detalles(orden, items):
    """Agrega las líneas a la orden y calcula el subtotal. Devuelve (mensaje, código) o None.

    Revisa que cada producto esté en la carta y que el inventario alcance para preparar
    TODO el pedido (sumando lo que piden varios productos que comparten insumos).
    """
    lineas, necesario, error = leer_items(items)
    if error:
        return error

    subtotal = Decimal("0")
    for producto, cantidad, observacion in lineas:
        linea_subtotal = producto.precio_venta * cantidad
        orden.detalles.append(DetalleOrden(
            producto=producto, cantidad=cantidad, precio_unitario=producto.precio_venta,
            subtotal=linea_subtotal, observacion=observacion,
        ))
        subtotal += linea_subtotal

    for insumo, cantidad in necesario.items():
        if insumo.stock_actual < cantidad:
            return (f"No alcanza '{insumo.nombre}' para este pedido: hay "
                    f"{numero(insumo.stock_actual)} {insumo.unidad_medida} y se necesitan "
                    f"{numero(cantidad)}"), 409

    orden.subtotal = subtotal
    return None
