"""Sugerencia de compra: une las alertas de stock mínimo (RF-03.8) con las órdenes de compra (RF-02.6).

Para cada insumo activo que está en su mínimo o por debajo:
- objetivo = 2 × stock mínimo (volver a un nivel cómodo, no quedar justo en la alerta);
- en camino = lo que ya está pedido en órdenes PENDIENTES o ENVIADAS que no han llegado;
- a pedir = objetivo − stock actual − en camino, redondeado hacia arriba (unidades enteras;
  peso y volumen con un decimal).
Se propone el proveedor activo que lo vende más barato (precio de referencia) y se agrupa por
proveedor: cada grupo será una orden de compra. Si ningún proveedor vende el insumo, queda en
«sin proveedor» para que el administrador se lo asigne en Proveedores.
"""

from collections import defaultdict
from decimal import ROUND_CEILING, Decimal

from ..extensions import db
from ..models import DetalleOrdenCompra, Insumo, OrdenCompra, Proveedor, ProveedorInsumo

FACTOR_OBJETIVO = Decimal("2")
EN_CAMINO = ("PENDIENTE", "ENVIADA")


def redondear(cantidad, unidad):
    """Hacia arriba: 2.3 UNIDAD -> 3; 1.24 KG -> 1.3."""
    paso = Decimal("1") if unidad == "UNIDAD" else Decimal("0.1")
    return (cantidad / paso).to_integral_value(rounding=ROUND_CEILING) * paso


def en_camino():
    """Insumo id -> cantidad ya pedida en órdenes que no han llegado."""
    filas = (db.session.query(DetalleOrdenCompra.insumo_id, db.func.sum(DetalleOrdenCompra.cantidad))
             .join(OrdenCompra).filter(OrdenCompra.estado.in_(EN_CAMINO))
             .group_by(DetalleOrdenCompra.insumo_id).all())
    return {insumo_id: Decimal(total) for insumo_id, total in filas}


def proveedores_de(insumo):
    """Proveedores activos que venden el insumo, del más barato al más caro (sin precio al final)."""
    ofertas = (ProveedorInsumo.query.join(Proveedor)
               .filter(ProveedorInsumo.insumo_id == insumo.id, Proveedor.activo.is_(True)).all())
    precio = lambda o: o.precio_referencia if o.precio_referencia is not None else insumo.costo_unitario  # noqa: E731
    ofertas.sort(key=lambda o: (o.precio_referencia is None, precio(o), o.proveedor.razon_social))
    return [{"proveedor_id": o.proveedor_id, "proveedor": o.proveedor.razon_social, "precio": float(precio(o))}
            for o in ofertas]


def sugerir():
    pedidos = en_camino()
    grupos = {}
    sin_proveedor, cubiertos = [], []
    bajos = (Insumo.query.filter(Insumo.activo.is_(True), Insumo.stock_minimo > 0,
                                 Insumo.stock_actual <= Insumo.stock_minimo)
             .order_by(Insumo.nombre).all())
    for insumo in bajos:
        ya_pedido = pedidos.get(insumo.id, Decimal("0"))
        falta = insumo.stock_minimo * FACTOR_OBJETIVO - insumo.stock_actual - ya_pedido
        base = {
            "insumo_id": insumo.id,
            "insumo": insumo.nombre,
            "categoria": insumo.categoria,
            "unidad_medida": insumo.unidad_medida,
            "stock_actual": float(insumo.stock_actual),
            "stock_minimo": float(insumo.stock_minimo),
            "en_camino": float(ya_pedido),
        }
        if falta <= 0:
            cubiertos.append(base)  # lo que ya viene en camino alcanza
            continue
        cantidad = redondear(falta, insumo.unidad_medida)
        ofertas = proveedores_de(insumo)
        if not ofertas:
            sin_proveedor.append({**base, "cantidad": float(cantidad)})
            continue
        elegido = ofertas[0]
        grupo = grupos.setdefault(elegido["proveedor_id"], {
            "proveedor_id": elegido["proveedor_id"], "proveedor": elegido["proveedor"], "lineas": [], "total": 0.0})
        subtotal = float((cantidad * Decimal(str(elegido["precio"]))).quantize(Decimal("0.01")))
        grupo["lineas"].append({**base, "cantidad": float(cantidad), "precio_unitario": elegido["precio"],
                                "subtotal": subtotal, "proveedores": ofertas})
        grupo["total"] = round(grupo["total"] + subtotal, 2)
    return {
        "grupos": sorted(grupos.values(), key=lambda g: g["proveedor"]),
        "sin_proveedor": sin_proveedor,
        "cubiertos": cubiertos,
    }


def agrupar_por_proveedor(lineas):
    """[{proveedor_id, insumo_id, cantidad, precio_unitario}] -> {proveedor_id: [detalles]}"""
    grupos = defaultdict(list)
    for linea in lineas:
        grupos[linea.get("proveedor_id")].append(
            {k: linea.get(k) for k in ("insumo_id", "cantidad", "precio_unitario")})
    return grupos
