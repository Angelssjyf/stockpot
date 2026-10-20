"""Módulo 9 - Gestión de pagos (RF-09.1 a RF-09.7)."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from ...extensions import db
from ...models import Orden, Pago
from ...services.inventario import StockInsuficiente
from ...services.ventas import PagoRechazado, cuenta, pagado, registrar_pago
from ...utils.auth import permiso_requerido, usuario_actual
from ...utils.fechas import filtrar_por_fechas

bp = Blueprint("pagos", __name__)

NOMBRE_RESTAURANTE = "StockPot Restaurante"


def _texto(valor):
    return str(valor if valor is not None else "").strip()


def _decimal(valor, campo):
    """Devuelve (Decimal, None) o (None, mensaje)."""
    try:
        return Decimal(str(valor)), None
    except (InvalidOperation, ValueError):
        return None, f"'{campo}' debe ser un número"


def leer_pago(data):
    """Lee método, monto, recibido y referencia del body. Devuelve (datos, None) o (None, error)."""
    monto, error = _decimal(data.get("monto"), "monto")
    if error:
        return None, error
    recibido = None
    if data.get("recibido") not in (None, ""):
        recibido, error = _decimal(data["recibido"], "recibido")
        if error:
            return None, error
    return {
        "metodo": _texto(data.get("metodo")).upper(),
        "monto": monto,
        "recibido": recibido,
        "referencia": _texto(data.get("referencia")) or None,
    }, None


@bp.get("/ordenes/por-cobrar")
@permiso_requerido("pagos.ver")
def ordenes_por_cobrar():
    """RF-09.4 Órdenes abiertas con su saldo pendiente, de la más antigua a la más reciente.
    Los pedidos en mesa aparecen cuando ya están confirmados (RF-05.7)."""
    ordenes = Orden.query.filter_by(estado="ABIERTA").order_by(Orden.created_at, Orden.id).all()
    ordenes = [o for o in ordenes if not (o.pedido_mesa and o.pedido_mesa.estado == "REGISTRADO")]
    return jsonify([{
        "orden_id": o.id,
        "codigo": o.codigo,
        "tipo": o.tipo,
        "fecha": o.created_at.isoformat() if o.created_at else None,
        "cliente": o.cliente.nombre if o.cliente else None,
        "estado_domicilio": o.domicilio.estado if o.domicilio else None,
        "mesa": o.pedido_mesa.mesa.numero if o.pedido_mesa else None,
        "estado_pedido": o.pedido_mesa.estado if o.pedido_mesa else None,
        "total": float(o.total),
        "pagado": float(pagado(o)),
        "saldo": float(o.total - pagado(o)),
    } for o in ordenes])


@bp.get("/ordenes/<int:orden_id>/cuenta")
@permiso_requerido("pagos.ver")
def ver_cuenta(orden_id):
    """RF-09.3 Calcular el valor total del pedido y RF-09.4 Consultar estado del pago."""
    orden = db.session.get(Orden, orden_id)
    if orden is None:
        return jsonify(error="La orden no existe"), 404
    return jsonify(cuenta(orden))


@bp.post("/ordenes/<int:orden_id>/pagos")
@permiso_requerido("pagos.gestionar")
def pagar_orden(orden_id):
    """RF-09.1 Registrar pagos, RF-09.2 método y RF-09.5 asociado al pedido.

    Body: {"metodo": "EFECTIVO", "monto": 30000, "recibido": 50000}
          {"metodo": "TRANSFERENCIA", "monto": 23000, "referencia": "M123456"}
    Se puede pagar en partes. Cuando lo pagado completa el total se registra la venta
    (RF-10.1) y se descuenta el inventario (RF-10.3).
    """
    orden = db.session.get(Orden, orden_id)
    if orden is None:
        return jsonify(error="La orden no existe"), 404

    datos, error = leer_pago(request.get_json(silent=True) or {})
    if error:
        return jsonify(error=error), 422
    try:
        pago = registrar_pago(orden, usuario=usuario_actual(), **datos)
    except PagoRechazado as rechazo:
        db.session.rollback()
        return jsonify(error=str(rechazo)), rechazo.codigo
    except StockInsuficiente as excepcion:
        db.session.rollback()  # ni el pago ni la venta quedan registrados
        return jsonify(error=f"{excepcion}. Registra la entrada en Inventario y vuelve a cobrar"), 409

    db.session.commit()
    return jsonify(pago=pago.to_dict(), cuenta=cuenta(orden)), 201


@bp.patch("/pagos/<int:pago_id>/anular")
@permiso_requerido("pagos.gestionar")
def anular_pago(pago_id):
    """RF-09.4 Anular un pago mal registrado (solo mientras la orden siga abierta)."""
    pago = db.session.get(Pago, pago_id)
    if pago is None:
        return jsonify(error="El pago no existe"), 404
    if pago.estado == "ANULADO":
        return jsonify(error="El pago ya está anulado"), 409
    if pago.orden.estado != "ABIERTA":
        return jsonify(error="La venta ya se cerró: no se pueden anular sus pagos"), 409
    pago.estado = "ANULADO"
    db.session.commit()
    return jsonify(pago=pago.to_dict(), cuenta=cuenta(pago.orden))


@bp.get("/ordenes/<int:orden_id>/comprobante")
@permiso_requerido("pagos.ver")
def comprobante(orden_id):
    """RF-09.6 Generar comprobante de pago: los datos para imprimir el recibo."""
    orden = db.session.get(Orden, orden_id)
    if orden is None:
        return jsonify(error="La orden no existe"), 404
    datos = cuenta(orden)
    if datos["estado_pago"] == "PENDIENTE":
        return jsonify(error="La orden todavía no tiene pagos"), 409
    datos["restaurante"] = NOMBRE_RESTAURANTE
    datos["numero"] = datos["venta"] or f"Abono {orden.codigo}"
    datos["atendido_por"] = f"{orden.usuario.nombre} {orden.usuario.apellido}"
    datos["pagos"] = [p for p in datos["pagos"] if p["estado"] == "APROBADO"]
    if orden.domicilio:
        datos["direccion"] = orden.domicilio.direccion
    return jsonify(datos)


@bp.get("/pagos")
@permiso_requerido("pagos.ver")
def historial_pagos():
    """RF-09.7 Consultar historial de pagos, del más reciente al más antiguo, con el total
    por método. Filtros: ?desde=2026-10-01&hasta=2026-10-31&metodo=EFECTIVO"""
    consulta = Pago.query
    try:
        consulta = filtrar_por_fechas(consulta, Pago.created_at, request.args)
    except ValueError:
        return jsonify(error="Las fechas deben tener el formato AAAA-MM-DD"), 422
    metodo = request.args.get("metodo", "").upper()
    if metodo in Pago.METODOS:
        consulta = consulta.filter_by(metodo=metodo)

    pagos = consulta.order_by(Pago.created_at.desc(), Pago.id.desc()).limit(300).all()
    por_metodo = defaultdict(Decimal)
    for pago in pagos:
        if pago.estado == "APROBADO":
            por_metodo[pago.metodo] += pago.monto
    resumen = {
        "total": float(sum(por_metodo.values(), Decimal("0"))),
        "por_metodo": {m: float(por_metodo[m]) for m in Pago.METODOS},
        "anulados": sum(1 for p in pagos if p.estado == "ANULADO"),
    }
    return jsonify(resumen=resumen, pagos=[p.to_dict() for p in pagos])
