"""Módulo 7 - Gestión de reservas (RF-07.1 a RF-07.8)."""

from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ...extensions import db
from ...models import Mesa, Reserva
from ...utils.auth import permiso_requerido, usuario_actual

bp = Blueprint("reservas", __name__)

DURACION = 120  # minutos que se aparta la mesa si no se dice otra cosa
# RF-07.8 Estado actual -> estados a los que puede pasar (CANCELADA va por su propia ruta, RF-07.4)
TRANSICIONES = {
    "PENDIENTE": {"CONFIRMADA", "CUMPLIDA", "NO_ASISTIO"},
    "CONFIRMADA": {"CUMPLIDA", "NO_ASISTIO"},
}


def _texto(valor):
    return str(valor if valor is not None else "").strip()


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _leer_fecha_hora(valor):
    """RF-07.5 Acepta '2026-11-20T19:30' (o con segundos). Devuelve datetime o None."""
    try:
        return datetime.fromisoformat(_texto(valor)).replace(second=0, microsecond=0, tzinfo=None)
    except ValueError:
        return None


def cruces(mesa_id, inicio, fin, salvo_id=None):
    """Reservas activas de la mesa que se cruzan con [inicio, fin)."""
    consulta = Reserva.query.filter(Reserva.mesa_id == mesa_id, Reserva.estado.in_(Reserva.ACTIVAS),
                                    Reserva.fecha_hora < fin)
    if salvo_id:
        consulta = consulta.filter(Reserva.id != salvo_id)
    return [r for r in consulta.all() if r.fin > inicio]


def mesas_disponibles(inicio, duracion, personas, salvo_id=None):
    """RF-07.7 Mesas activas con cupo para las personas y sin otra reserva en ese horario."""
    fin = inicio + timedelta(minutes=duracion)
    mesas = Mesa.query.filter(Mesa.activa.is_(True), Mesa.capacidad >= personas).order_by(Mesa.capacidad, Mesa.numero)
    return [m for m in mesas if not cruces(m.id, inicio, fin, salvo_id)]


def _aplicar(reserva, data):
    """Valida y copia los datos (solo los que vienen al modificar). Devuelve None o (mensaje, código)."""
    nueva = reserva.id is None
    for campo, nombre in (("cliente", "nombre del cliente"), ("telefono", "teléfono")):
        if nueva or campo in data:
            valor = _texto(data.get(campo))
            if not valor:
                return f"El {nombre} es obligatorio", 422
            setattr(reserva, campo, valor[:120] if campo == "cliente" else valor[:20])
    if nueva or "personas" in data:
        personas = _entero(data.get("personas"))
        if personas is None or personas < 1:
            return "Las personas deben ser un número mayor que cero", 422
        reserva.personas = personas
    if nueva or "fecha_hora" in data:
        fecha_hora = _leer_fecha_hora(data.get("fecha_hora"))
        if fecha_hora is None:
            return "La fecha y hora deben tener el formato AAAA-MM-DDTHH:MM", 422
        if fecha_hora <= datetime.now():
            return "La reserva debe ser para una fecha y hora futuras", 422
        reserva.fecha_hora = fecha_hora
    if "duracion_minutos" in data or nueva:
        duracion = _entero(data.get("duracion_minutos", DURACION))
        if duracion is None or not 30 <= duracion <= 360:
            return "La duración debe estar entre 30 y 360 minutos", 422
        reserva.duracion_minutos = duracion
    if "observaciones" in data:
        reserva.observaciones = _texto(data["observaciones"])[:255] or None
    if nueva or "mesa_id" in data:
        mesa = db.session.get(Mesa, _entero(data.get("mesa_id")) or 0)
        if mesa is None or not mesa.activa:
            return "La mesa no existe o está inactiva", 422
        reserva.mesa = mesa

    # RF-07.6 y RF-07.7 La mesa debe tener cupo y estar libre en ese horario
    if reserva.personas > reserva.mesa.capacidad:
        return f"La mesa {reserva.mesa.numero} es para {reserva.mesa.capacidad} personas", 422
    otra = cruces(reserva.mesa.id, reserva.fecha_hora, reserva.fin, reserva.id)
    if otra:
        hora = otra[0].fecha_hora.strftime("%I:%M %p").lstrip("0").lower()
        return f"La mesa {reserva.mesa.numero} ya está reservada a esa hora ({otra[0].codigo}, {hora})", 409
    return None


def _buscar(reserva_id):
    reserva = db.session.get(Reserva, reserva_id)
    if reserva is None:
        return None, (jsonify(error="La reserva no existe"), 404)
    return reserva, None


@bp.post("/reservas")
@permiso_requerido("reservas.gestionar")
def registrar_reserva():
    """RF-07.1 Registrar reservas con RF-07.5 su fecha y hora y RF-07.6 su mesa.

    Body: {"cliente": "Ana Ruiz", "telefono": "3001234567", "personas": 4,
           "fecha_hora": "2026-11-20T19:30", "mesa_id": 3, "duracion_minutos": 120, "observaciones": "..."}
    """
    data = request.get_json(silent=True) or {}
    reserva = Reserva(usuario=usuario_actual(), codigo="TMP")
    error = _aplicar(reserva, data)
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]
    db.session.add(reserva)
    db.session.flush()
    reserva.codigo = f"RES-{reserva.id:06d}"
    db.session.commit()
    return jsonify(reserva.to_dict()), 201


@bp.get("/reservas")
@permiso_requerido("reservas.ver")
def consultar_reservas():
    """RF-07.2 Consultar reservas de un día (por defecto hoy), de la más temprana a la más tarde.
    Filtros: ?fecha=2026-11-20&estado=CONFIRMADA&q=ana (nombre, teléfono o código)"""
    try:
        dia = date.fromisoformat(request.args.get("fecha") or date.today().isoformat())
    except ValueError:
        return jsonify(error="La fecha debe tener el formato AAAA-MM-DD"), 422
    inicio = datetime.combine(dia, datetime.min.time())
    consulta = Reserva.query.filter(Reserva.fecha_hora >= inicio, Reserva.fecha_hora < inicio + timedelta(days=1))
    estado = request.args.get("estado", "").upper()
    if estado in Reserva.ESTADOS:
        consulta = consulta.filter(Reserva.estado == estado)
    texto = _texto(request.args.get("q"))
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.filter(or_(Reserva.cliente.ilike(patron), Reserva.telefono.ilike(patron),
                                       Reserva.codigo.ilike(patron)))
    reservas = consulta.order_by(Reserva.fecha_hora, Reserva.id).all()
    activas = [r for r in reservas if r.activa]
    resumen = {"reservas": len(reservas), "activas": len(activas),
               "personas": sum(r.personas for r in activas),
               "confirmadas": sum(1 for r in reservas if r.estado == "CONFIRMADA")}
    return jsonify(fecha=dia.isoformat(), resumen=resumen, reservas=[r.to_dict() for r in reservas])


@bp.get("/reservas/disponibilidad")
@permiso_requerido("reservas.ver")
def disponibilidad():
    """RF-07.7 Verificar disponibilidad de mesas: ?fecha_hora=2026-11-20T19:30&personas=4&duracion_minutos=120
    (&reserva_id=5 al modificar, para no contarse a sí misma)."""
    inicio = _leer_fecha_hora(request.args.get("fecha_hora"))
    personas = _entero(request.args.get("personas"))
    duracion = _entero(request.args.get("duracion_minutos", DURACION))
    if inicio is None or not personas or personas < 1 or duracion is None or not 30 <= duracion <= 360:
        return jsonify(error="Indica fecha_hora (AAAA-MM-DDTHH:MM), personas y una duración entre 30 y 360 minutos"), 422
    mesas = mesas_disponibles(inicio, duracion, personas, _entero(request.args.get("reserva_id")))
    return jsonify(fecha_hora=inicio.isoformat(), personas=personas,
                   mesas=[m.to_dict(con_pedido=False) for m in mesas])


@bp.get("/reservas/<int:reserva_id>")
@permiso_requerido("reservas.ver")
def obtener_reserva(reserva_id):
    reserva, error = _buscar(reserva_id)
    return error or jsonify(reserva.to_dict())


@bp.put("/reservas/<int:reserva_id>")
@permiso_requerido("reservas.gestionar")
def modificar_reserva(reserva_id):
    """RF-07.3 Modificar reservas que todavía están activas (pendiente o confirmada)."""
    reserva, error = _buscar(reserva_id)
    if error:
        return error
    if not reserva.activa:
        return jsonify(error=f"Una reserva {reserva.estado} ya no se puede modificar"), 409
    with db.session.no_autoflush:
        error = _aplicar(reserva, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]
    db.session.commit()
    return jsonify(reserva.to_dict())


@bp.patch("/reservas/<int:reserva_id>/cancelar")
@permiso_requerido("reservas.gestionar")
def cancelar_reserva(reserva_id):
    """RF-07.4 Cancelar reservas activas; la mesa queda libre en ese horario. Body opcional: {"motivo": "..."}"""
    reserva, error = _buscar(reserva_id)
    if error:
        return error
    if not reserva.activa:
        return jsonify(error=f"Una reserva {reserva.estado} no se puede cancelar"), 409
    motivo = _texto((request.get_json(silent=True) or {}).get("motivo"))
    if motivo:
        reserva.observaciones = (f"{reserva.observaciones} · " if reserva.observaciones else "")[:120] \
            + f"Cancelada: {motivo}"[:130]
    reserva.estado = "CANCELADA"
    db.session.commit()
    return jsonify(reserva.to_dict())


@bp.patch("/reservas/<int:reserva_id>/estado")
@permiso_requerido("reservas.gestionar")
def actualizar_estado(reserva_id):
    """RF-07.8 Actualizar el estado: CONFIRMADA (se llamó al cliente), CUMPLIDA (llegó) o NO_ASISTIO.

    Body: {"estado": "CONFIRMADA"}
    """
    reserva, error = _buscar(reserva_id)
    if error:
        return error
    nuevo = _texto((request.get_json(silent=True) or {}).get("estado")).upper()
    if nuevo == "CANCELADA":
        return jsonify(error="Para cancelar usa la opción Cancelar reserva"), 422
    if nuevo not in Reserva.ESTADOS:
        return jsonify(error="Estado inválido. Opciones: CONFIRMADA, CUMPLIDA, NO_ASISTIO"), 422
    if nuevo not in TRANSICIONES.get(reserva.estado, set()):
        return jsonify(error=f"Una reserva {reserva.estado} no puede pasar a {nuevo}"), 409
    if nuevo in ("CUMPLIDA", "NO_ASISTIO") and reserva.fecha_hora - timedelta(minutes=60) > datetime.now():
        return jsonify(error="Todavía falta más de una hora para la reserva"), 409
    reserva.estado = nuevo
    db.session.commit()
    return jsonify(reserva.to_dict())
