"""Módulo 10 - Ventas y consumo (RF-10.1 a RF-10.6)."""

from decimal import Decimal
from uuid import uuid4

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ...extensions import db
from ...models import Consumo, DetalleOrden, Insumo, Orden, Producto, Venta
from ...services.inventario import StockInsuficiente
from ...services.ordenes import armar_detalles
from ...services.ventas import PagoRechazado, cuenta, registrar_pago
from ...utils.auth import permiso_requerido, usuario_actual
from ...utils.fechas import filtrar_por_fechas
from ..pagos.routes import leer_pago

bp = Blueprint("ventas", __name__)

ERROR_FECHAS = "Las fechas deben tener el formato AAAA-MM-DD"


@bp.post("/ventas")
@permiso_requerido("pagos.gestionar")
def venta_de_mostrador():
    """RF-10.1 Registrar ventas de mostrador (para llevar): pedido y pago en un solo paso.

    Body: {"items": [{"producto_id": 6, "cantidad": 2}], "metodo": "EFECTIVO",
           "recibido": 20000, "observaciones": "..."}
    Se cobra el total completo, así que la venta queda registrada y el inventario descontado.
    """
    data = request.get_json(silent=True) or {}
    usuario = usuario_actual()
    orden = Orden(codigo=uuid4().hex[:20], tipo="LLEVAR", usuario=usuario,
                  observaciones=str(data.get("observaciones") or "").strip() or None)
    error = armar_detalles(orden, data.get("items"))
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]
    db.session.add(orden)
    db.session.flush()
    orden.codigo = f"PED-{orden.id:06d}"

    data["monto"] = str(orden.total)  # en mostrador se paga todo de una vez
    datos, error = leer_pago(data)
    if error:
        db.session.rollback()
        return jsonify(error=error), 422
    try:
        pago = registrar_pago(orden, usuario=usuario, **datos)
    except PagoRechazado as rechazo:
        db.session.rollback()
        return jsonify(error=str(rechazo)), rechazo.codigo
    except StockInsuficiente as excepcion:
        db.session.rollback()
        return jsonify(error=str(excepcion)), 409

    db.session.commit()
    return jsonify(venta=orden.venta.to_dict(), pago=pago.to_dict(), cuenta=cuenta(orden)), 201


@bp.get("/ventas")
@permiso_requerido("ventas.ver")
def consultar_ventas():
    """RF-10.2 Consultar ventas, de la más reciente a la más antigua, con su resumen.
    Filtros: ?desde=2026-10-01&hasta=2026-10-31"""
    try:
        consulta = filtrar_por_fechas(Venta.query, Venta.created_at, request.args)
    except ValueError:
        return jsonify(error=ERROR_FECHAS), 422
    ventas = consulta.order_by(Venta.created_at.desc(), Venta.id.desc()).limit(300).all()

    total = sum((v.total for v in ventas), Decimal("0"))
    subtotal = sum((v.subtotal for v in ventas), Decimal("0"))
    costo = sum((v.costo_insumos for v in ventas), Decimal("0"))
    resumen = {
        "ventas": len(ventas),
        "total": float(total),
        "ticket_promedio": float(round(total / len(ventas), 2)) if ventas else 0.0,
        "costo_insumos": float(costo),
        "ganancia": float(subtotal - costo),
    }
    return jsonify(resumen=resumen, ventas=[v.to_dict() for v in ventas])


@bp.get("/ventas/<int:venta_id>")
@permiso_requerido("ventas.ver")
def detalle_venta(venta_id):
    """RF-10.4 Relacionar ventas con productos y RF-10.3 ver el consumo de esa venta."""
    venta = db.session.get(Venta, venta_id)
    if venta is None:
        return jsonify(error="La venta no existe"), 404
    return jsonify(venta.to_dict(completo=True))


@bp.get("/ventas/mas-vendidos")
@permiso_requerido("ventas.ver", "reportes.ver")
def productos_mas_vendidos():
    """RF-10.5 Consultar productos más vendidos (por unidades). ?desde, ?hasta y ?limite=10"""
    cantidad = func.sum(DetalleOrden.cantidad)
    consulta = (
        db.session.query(Producto.id, Producto.nombre, Producto.categoria, cantidad,
                         func.sum(DetalleOrden.subtotal))
        .join(DetalleOrden, DetalleOrden.producto_id == Producto.id)
        .join(Venta, Venta.orden_id == DetalleOrden.orden_id)
    )
    try:
        consulta = filtrar_por_fechas(consulta, Venta.created_at, request.args)
    except ValueError:
        return jsonify(error=ERROR_FECHAS), 422
    limite = min(request.args.get("limite", 10, type=int), 50)
    filas = consulta.group_by(Producto.id, Producto.nombre, Producto.categoria) \
        .order_by(cantidad.desc(), Producto.nombre).limit(limite).all()
    return jsonify([{"producto_id": f[0], "producto": f[1], "categoria": f[2],
                     "cantidad": int(f[3]), "total": float(f[4])} for f in filas])


@bp.get("/ventas/consumo")
@permiso_requerido("ventas.ver", "reportes.ver")
def consumo_de_insumos():
    """RF-10.6 Consultar historial de consumo: cuánto se gastó de cada insumo en las ventas
    del periodo y cuánto costó. ?desde y ?hasta"""
    cantidad = func.sum(Consumo.cantidad)
    costo = func.sum(Consumo.cantidad * Consumo.costo_unitario)
    consulta = (
        db.session.query(Insumo.id, Insumo.nombre, Insumo.unidad_medida, cantidad, costo)
        .join(Consumo, Consumo.insumo_id == Insumo.id)
        .join(Venta, Venta.id == Consumo.venta_id)
    )
    try:
        consulta = filtrar_por_fechas(consulta, Venta.created_at, request.args)
    except ValueError:
        return jsonify(error=ERROR_FECHAS), 422
    filas = consulta.group_by(Insumo.id, Insumo.nombre, Insumo.unidad_medida) \
        .order_by(costo.desc()).all()
    insumos = [{"insumo_id": f[0], "insumo": f[1], "unidad_medida": f[2],
                "cantidad": float(f[3]), "costo": float(round(f[4], 2))} for f in filas]
    return jsonify(insumos=insumos, costo_total=round(sum(i["costo"] for i in insumos), 2))
