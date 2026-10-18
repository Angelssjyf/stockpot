"""Módulo 2 - Órdenes de compra (RF-02.6 a RF-02.8)."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, jsonify, request

from ...extensions import db
from ...models import DetalleOrdenCompra, Insumo, OrdenCompra, Proveedor
from ...utils.auth import permiso_requerido, usuario_actual

bp = Blueprint("compras", __name__)

# RF-02.7 Estado actual -> estados a los que puede pasar. RECIBIDA y CANCELADA son finales.
TRANSICIONES = {
    "PENDIENTE": {"ENVIADA", "CANCELADA"},
    "ENVIADA": {"RECIBIDA", "CANCELADA"},
    "RECIBIDA": set(),
    "CANCELADA": set(),
}


def _numero(valor, campo, permitir_cero=False):
    """Convierte un valor en Decimal positivo. Devuelve (numero, None) o (None, mensaje)."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None, f"'{campo}' debe ser un número"
    if numero < 0 or (numero == 0 and not permitir_cero):
        return None, f"'{campo}' debe ser mayor que cero"
    return numero, None


@bp.get("/ordenes-compra")
@permiso_requerido("compras.ver")
def listar_ordenes():
    """Consultar órdenes de compra, de la más reciente a la más antigua.
    Filtros opcionales: ?estado=PENDIENTE y ?proveedor_id=1"""
    consulta = OrdenCompra.query

    estado = request.args.get("estado", "").upper()
    if estado in OrdenCompra.ESTADOS:
        consulta = consulta.filter_by(estado=estado)

    proveedor_id = request.args.get("proveedor_id", type=int)
    if proveedor_id:
        consulta = consulta.filter_by(proveedor_id=proveedor_id)

    ordenes = consulta.order_by(OrdenCompra.fecha_orden.desc(), OrdenCompra.id.desc()).all()
    return jsonify([orden.to_dict(con_detalles=False) for orden in ordenes])


@bp.get("/ordenes-compra/<int:orden_id>")
@permiso_requerido("compras.ver")
def obtener_orden(orden_id):
    """Consultar una orden de compra con todas sus líneas."""
    orden = db.session.get(OrdenCompra, orden_id)
    if orden is None:
        return jsonify(error="La orden de compra no existe"), 404
    return jsonify(orden.to_dict())


@bp.post("/ordenes-compra")
@permiso_requerido("compras.gestionar")
def crear_orden():
    """RF-02.6 Registrar órdenes de compra.

    Body: {"proveedor_id": 1, "fecha_entrega_estimada": "2026-10-20", "observaciones": "...",
           "detalles": [{"insumo_id": 1, "cantidad": 20, "precio_unitario": 4200}, ...]}
    El sistema calcula los subtotales, el total y el código consecutivo (OC-000001).
    """
    data = request.get_json(silent=True) or {}

    proveedor = db.session.get(Proveedor, data.get("proveedor_id") or 0)
    if proveedor is None or not proveedor.activo:
        return jsonify(error="El proveedor no existe o está inactivo"), 422

    detalles = data.get("detalles")
    if not isinstance(detalles, list) or not detalles:
        return jsonify(error="La orden debe tener al menos un insumo"), 422

    fecha_entrega = None
    if data.get("fecha_entrega_estimada"):
        try:
            fecha_entrega = date.fromisoformat(data["fecha_entrega_estimada"])
        except (TypeError, ValueError):
            return jsonify(error="La fecha de entrega debe tener el formato AAAA-MM-DD"), 422

    orden = OrdenCompra(
        codigo=uuid4().hex[:20],  # código temporal; el definitivo depende del id (ver abajo)
        proveedor=proveedor,
        usuario=usuario_actual(),
        fecha_entrega_estimada=fecha_entrega,
        observaciones=(str(data.get("observaciones") or "").strip() or None),
    )

    total = Decimal("0")
    ids_vistos = set()
    for linea in detalles:
        insumo_id = linea.get("insumo_id") if isinstance(linea, dict) else None
        insumo = db.session.get(Insumo, insumo_id) if isinstance(insumo_id, int) else None
        if insumo is None or not insumo.activo:
            return jsonify(error=f"El insumo {insumo_id} no existe"), 422
        if insumo.id in ids_vistos:
            return jsonify(error=f"El insumo '{insumo.nombre}' está repetido en la orden"), 422
        ids_vistos.add(insumo.id)

        cantidad, error = _numero(linea.get("cantidad"), "cantidad")
        if error:
            return jsonify(error=error), 422
        precio, error = _numero(linea.get("precio_unitario"), "precio_unitario",
                                permitir_cero=True)
        if error:
            return jsonify(error=error), 422

        subtotal = (cantidad * precio).quantize(Decimal("0.01"))  # redondeo a centavos
        orden.detalles.append(DetalleOrdenCompra(
            insumo=insumo, cantidad=cantidad, precio_unitario=precio, subtotal=subtotal,
        ))
        total += subtotal

    orden.total = total
    db.session.add(orden)
    db.session.flush()  # MySQL asigna el id sin terminar la transacción
    orden.codigo = f"OC-{orden.id:06d}"
    db.session.commit()
    return jsonify(orden.to_dict()), 201


@bp.patch("/ordenes-compra/<int:orden_id>/estado")
@permiso_requerido("compras.gestionar")
def actualizar_estado(orden_id):
    """RF-02.7 Actualizar el estado de la orden: PENDIENTE -> ENVIADA -> RECIBIDA (o CANCELADA).

    RF-02.8 Relacionar compras con inventario: al pasar a RECIBIDA, el stock de cada insumo
    aumenta con la cantidad comprada.
    """
    orden = db.session.get(OrdenCompra, orden_id)
    if orden is None:
        return jsonify(error="La orden de compra no existe"), 404

    nuevo = str((request.get_json(silent=True) or {}).get("estado") or "").upper()
    if nuevo not in TRANSICIONES.get(orden.estado, set()):
        return jsonify(error=f"No se puede pasar de {orden.estado} a {nuevo or '(vacío)'}"), 409

    if nuevo == "RECIBIDA":
        for detalle in orden.detalles:
            detalle.insumo.stock_actual += detalle.cantidad  # RF-02.8
        orden.fecha_recepcion = datetime.now()

    orden.estado = nuevo
    db.session.commit()
    return jsonify(orden.to_dict()
                   )
