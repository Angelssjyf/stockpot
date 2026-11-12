"""Turnos de caja y cierre de caja (arqueo).

El cajero abre la caja con la base de efectivo con la que empieza. Mientras el turno está
abierto, cada pago aprobado (en mesa, a domicilio o de mostrador) cuenta para ese turno. Al
cerrar, el cajero escribe lo que contó por método de pago; el sistema lo compara con lo que
esperaba y guarda la diferencia (sobrante o faltante). Si no cuadra, hay que explicar por qué.
"""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import func, select

from ...extensions import db
from ...models import Empresa, Pago, TurnoCaja, Venta
from ...models.caja import METODOS
from ...utils.auth import permiso_requerido, usuario_actual, verificar_pin
from ...utils.fechas import filtrar_por_fechas

bp = Blueprint("caja", __name__)

CENTAVO = Decimal("0.01")


def _monto(valor, campo):
    """(Decimal, None) o (None, mensaje). Vacío o negativo no se acepta."""
    try:
        numero = Decimal(str(valor)).quantize(CENTAVO)
    except (InvalidOperation, ValueError):
        return None, f"'{campo}' debe ser un número"
    if numero < 0:
        return None, f"'{campo}' no puede ser negativo"
    return numero, None


def turno_abierto():
    return TurnoCaja.query.filter_by(estado="ABIERTO").order_by(TurnoCaja.id.desc()).first()


def en_el_turno(consulta, columna, turno):
    """Filtra la consulta a lo hecho entre la apertura y el cierre del turno. Las fechas se
    comparan columna contra columna dentro de la base (no con un valor de Python), así se
    comparan en el mismo formato en MySQL y en SQLite."""
    del_turno = lambda campo: select(campo).where(TurnoCaja.id == turno.id).scalar_subquery()  # noqa: E731
    consulta = consulta.filter(columna >= del_turno(TurnoCaja.abierto_en))
    if turno.cerrado_en is not None:
        consulta = consulta.filter(columna <= del_turno(TurnoCaja.cerrado_en))
    return consulta


def pagos_del_turno(turno):
    """Pagos (aprobados y anulados) hechos entre la apertura y el cierre del turno."""
    return en_el_turno(Pago.query, Pago.created_at, turno).order_by(Pago.created_at, Pago.id).all()


def resumen(turno):
    """Lo que debería haber en caja ahora: la base más el efectivo, y lo de tarjeta y transferencia."""
    pagos = pagos_del_turno(turno)
    aprobados = [p for p in pagos if p.estado == "APROBADO"]
    por_metodo = {m: sum((p.monto for p in aprobados if p.metodo == m), Decimal("0")) for m in METODOS}
    ventas = en_el_turno(Venta.query, Venta.created_at, turno)
    return {
        "esperado": {
            "efectivo": turno.base_inicial + por_metodo["EFECTIVO"],
            "tarjeta": por_metodo["TARJETA"],
            "transferencia": por_metodo["TRANSFERENCIA"],
        },
        "ventas_efectivo": por_metodo["EFECTIVO"],
        "num_pagos": len(aprobados),
        "anulados": len(pagos) - len(aprobados),
        "propinas": sum((v.propina for v in ventas.all()), Decimal("0")),
    }


def _resumen_json(datos):
    return {
        "esperado": {k: float(v) for k, v in datos["esperado"].items()},
        "ventas_efectivo": float(datos["ventas_efectivo"]),
        "num_pagos": datos["num_pagos"],
        "anulados": datos["anulados"],
        "propinas": float(datos["propinas"]),
    }


@bp.get("/caja/turno")
@permiso_requerido("pagos.ver")
def ver_turno():
    """El turno abierto con lo que debería haber en caja ahora, y el último cierre."""
    turno = turno_abierto()
    ultimo = (TurnoCaja.query.filter_by(estado="CERRADO")
              .order_by(TurnoCaja.cerrado_en.desc(), TurnoCaja.id.desc()).first())
    return jsonify(
        turno={**turno.to_dict(), "actual": _resumen_json(resumen(turno))} if turno else None,
        ultimo=ultimo.to_dict() if ultimo else None,
    )


@bp.post("/caja/abrir")
@permiso_requerido("pagos.gestionar")
def abrir_caja():
    """Body: {"base_inicial": 200000} — el efectivo con el que empieza la caja."""
    data = request.get_json(silent=True) or {}
    base, error = _monto(data.get("base_inicial", 0), "base_inicial")
    if error:
        return jsonify(error=error), 422
    # Bloquea el restaurante para que dos cajeros no abran la caja al mismo tiempo
    db.session.execute(select(Empresa.id).where(Empresa.id == usuario_actual().empresa_id).with_for_update())
    if turno_abierto() is not None:
        return jsonify(error="La caja ya está abierta: ciérrala antes de abrir otro turno"), 409
    turno = TurnoCaja(base_inicial=base, abierto_por=usuario_actual())
    db.session.add(turno)
    db.session.commit()
    return jsonify(turno.to_dict()), 201


@bp.post("/caja/cerrar")
@permiso_requerido("pagos.gestionar")
def cerrar_caja():
    """Body: {"contado_efectivo": 350000, "contado_tarjeta": 120000, "contado_transferencia": 80000,
    "observacion": "...", "pin": "1234"}. Si lo contado no cuadra, la observación es obligatoria."""
    data = request.get_json(silent=True) or {}
    db.session.execute(select(Empresa.id).where(Empresa.id == usuario_actual().empresa_id).with_for_update())
    turno = turno_abierto()
    if turno is None:
        return jsonify(error="La caja no está abierta"), 409

    contado = {}
    for metodo in METODOS:
        campo = f"contado_{metodo.lower()}"
        if data.get(campo) in (None, ""):
            return jsonify(error=f"Escribe cuánto contaste en {metodo.lower()}", campo=campo), 422
        contado[metodo.lower()], error = _monto(data[campo], campo)
        if error:
            return jsonify(error=error, campo=campo), 422
    observacion = str(data.get("observacion") or "").strip()[:255] or None

    datos = resumen(turno)
    diferencia = sum((contado[m] - datos["esperado"][m] for m in contado), Decimal("0"))
    if diferencia != 0 and not observacion:
        return jsonify(error="La caja no cuadra: explica la diferencia en la observación",
                       diferencia=float(diferencia)), 422
    error = verificar_pin(data)  # cerrar la caja pide el PIN, como cobrar
    if error:
        return error

    for metodo in contado:
        setattr(turno, f"esperado_{metodo}", datos["esperado"][metodo])
        setattr(turno, f"contado_{metodo}", contado[metodo])
    turno.num_pagos = datos["num_pagos"]
    turno.propinas = datos["propinas"]
    turno.observacion = observacion
    turno.estado = "CERRADO"
    turno.cerrado_por = usuario_actual()
    turno.cerrado_en = func.now()  # NOW() de la base al guardar: el mismo reloj que fecha los pagos
    db.session.commit()
    return jsonify(turno.to_dict())


@bp.get("/caja/turnos")
@permiso_requerido("pagos.ver")
def historial_turnos():
    """Turnos cerrados, del más reciente al más antiguo. Filtros: ?desde=AAAA-MM-DD&hasta=AAAA-MM-DD"""
    consulta = TurnoCaja.query.filter_by(estado="CERRADO")
    try:
        consulta = filtrar_por_fechas(consulta, TurnoCaja.cerrado_en, request.args)
    except ValueError:
        return jsonify(error="Las fechas deben tener el formato AAAA-MM-DD"), 422
    turnos = consulta.order_by(TurnoCaja.cerrado_en.desc(), TurnoCaja.id.desc()).limit(100).all()
    return jsonify([t.to_dict() for t in turnos])


@bp.get("/caja/turnos/<int:turno_id>")
@permiso_requerido("pagos.ver")
def detalle_turno(turno_id):
    """Un turno con sus pagos (para revisar de dónde sale una diferencia)."""
    turno = db.session.get(TurnoCaja, turno_id)
    if turno is None:
        return jsonify(error="El turno no existe"), 404
    datos = turno.to_dict()
    if turno.estado == "ABIERTO":
        datos["actual"] = _resumen_json(resumen(turno))
    datos["pagos"] = [p.to_dict() for p in pagos_del_turno(turno)]
    return jsonify(datos)
