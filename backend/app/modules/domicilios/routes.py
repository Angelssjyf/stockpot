"""Módulo 8 - Gestión de domicilios (RF-08.1 a RF-08.8), con sus clientes."""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt
from sqlalchemy import or_

from ...extensions import db
from ...models import Cliente, Domicilio, Orden, Rol, Usuario
from ...services.ordenes import armar_detalles
from ...utils.auth import permiso_requerido, usuario_actual

bp = Blueprint("domicilios", __name__)

# RF-08.6 Estado actual -> estados a los que puede pasar. ENTREGADO se registra aparte
# (RF-08.7) porque pide quién recibió. ENTREGADO y CANCELADO son finales.
TRANSICIONES = {
    "RECIBIDO": {"EN_PREPARACION", "CANCELADO"},
    "EN_PREPARACION": {"LISTO", "CANCELADO"},
    "LISTO": {"EN_CAMINO", "CANCELADO"},
    "EN_CAMINO": set(),  # de aquí solo sale con la entrega (RF-08.7)
    "ENTREGADO": set(),
    "CANCELADO": set(),
}


def _texto(valor):
    """Convierte un valor recibido en texto sin espacios a los lados ('' si viene vacío)."""
    return str(valor if valor is not None else "").strip()


def _puede_gestionar():
    """True si el usuario gestiona domicilios (CAJERO, ADMINISTRADOR). El DOMICILIARIO
    solo ve y mueve los domicilios que tiene asignados."""
    return "domicilios.gestionar" in get_jwt().get("permisos", [])


def _buscar_domicilio(domicilio_id):
    """Devuelve (domicilio, None) o (None, respuesta de error) respetando quién lo puede ver."""
    domicilio = db.session.get(Domicilio, domicilio_id)
    if domicilio is None or (
        not _puede_gestionar() and domicilio.domiciliario_id != usuario_actual().id
    ):
        return None, (jsonify(error="El domicilio no existe"), 404)
    return domicilio, None


# =====================================================================
#  RF-08.2 Registrar información del cliente
# =====================================================================


def _aplicar_cliente(cliente, data):
    """Valida y copia los datos del cliente. Devuelve (mensaje, código) o None."""
    if "nombre" in data:
        nombre = _texto(data["nombre"])
        if not nombre:
            return "El nombre no puede quedar vacío", 422
        cliente.nombre = nombre

    if "telefono" in data:
        telefono = _texto(data["telefono"]).replace(" ", "")
        if not telefono.isdigit() or not 7 <= len(telefono) <= 15:
            return "El teléfono debe tener entre 7 y 15 dígitos", 422
        otro = Cliente.query.filter_by(telefono=telefono).first()
        if otro and otro.id != cliente.id:
            return "Ya existe un cliente con ese teléfono", 409
        cliente.telefono = telefono

    if "email" in data:
        email = _texto(data["email"]).lower()
        if email and "@" not in email:
            return "El correo no es válido", 422
        cliente.email = email or None

    for campo in ("direccion", "barrio", "referencia"):
        if campo in data:
            setattr(cliente, campo, _texto(data[campo]) or None)
    return None


@bp.get("/clientes")
@permiso_requerido("domicilios.gestionar")
def listar_clientes():
    """RF-08.2 Buscar clientes por teléfono o nombre: ?q=300123"""
    consulta = Cliente.query
    texto = request.args.get("q", "").strip()
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.filter(or_(Cliente.telefono.ilike(patron), Cliente.nombre.ilike(patron)))
    clientes = consulta.order_by(Cliente.nombre).limit(50).all()
    return jsonify([cliente.to_dict() for cliente in clientes])


@bp.post("/clientes")
@permiso_requerido("domicilios.gestionar")
def crear_cliente():
    """RF-08.2 Registrar información del cliente (nombre y teléfono obligatorios)."""
    data = request.get_json(silent=True) or {}
    faltantes = [campo for campo in ("nombre", "telefono") if not _texto(data.get(campo))]
    if faltantes:
        return jsonify(error="Faltan campos obligatorios", faltantes=faltantes), 422

    cliente = Cliente()
    error = _aplicar_cliente(cliente, data)
    if error:
        return jsonify(error=error[0]), error[1]
    db.session.add(cliente)
    db.session.commit()
    return jsonify(cliente.to_dict()), 201


@bp.put("/clientes/<int:cliente_id>")
@permiso_requerido("domicilios.gestionar")
def modificar_cliente(cliente_id):
    """RF-08.2 Actualizar los datos de un cliente."""
    cliente = db.session.get(Cliente, cliente_id)
    if cliente is None:
        return jsonify(error="El cliente no existe"), 404
    error = _aplicar_cliente(cliente, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]
    db.session.commit()
    return jsonify(cliente.to_dict())


# =====================================================================
#  RF-08.1 Registrar pedidos a domicilio y RF-08.3 Dirección de entrega
# =====================================================================


@bp.post("/domicilios")
@permiso_requerido("domicilios.gestionar")
def registrar_domicilio():
    """RF-08.1 Registrar pedidos a domicilio, con RF-08.3 la dirección de entrega.

    Body: {"cliente_id": 1, "direccion": "Calle 45 # 27-30", "barrio": "...", "referencia": "...",
           "telefono_contacto": "...", "costo_envio": 3000, "observaciones": "...",
           "items": [{"producto_id": 1, "cantidad": 2, "observacion": "sin cebolla"}, ...]}
    Si no llegan dirección, barrio, referencia o teléfono, se usan los del cliente.
    """
    data = request.get_json(silent=True) or {}
    cliente = db.session.get(Cliente, data.get("cliente_id") or 0)
    if cliente is None:
        return jsonify(error="El cliente no existe"), 422

    direccion = _texto(data.get("direccion")) or cliente.direccion
    if not direccion:
        return jsonify(error="Falta la dirección de entrega"), 422

    try:
        costo_envio = Decimal(str(data.get("costo_envio") or 0))
    except InvalidOperation:
        return jsonify(error="El costo de envío debe ser un número"), 422
    if costo_envio < 0:
        return jsonify(error="El costo de envío no puede ser negativo"), 422

    orden = Orden(
        codigo=uuid4().hex[:20],  # código temporal; el definitivo depende del id
        tipo="DOMICILIO",
        cliente=cliente,
        usuario=usuario_actual(),
        observaciones=_texto(data.get("observaciones")) or None,
    )
    error = armar_detalles(orden, data.get("items"))
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]

    domicilio = Domicilio(
        orden=orden,
        cliente=cliente,
        direccion=direccion,
        barrio=_texto(data.get("barrio")) or cliente.barrio,
        referencia=_texto(data.get("referencia")) or cliente.referencia,
        telefono_contacto=_texto(data.get("telefono_contacto")) or cliente.telefono,
        costo_envio=costo_envio,
    )
    db.session.add_all([orden, domicilio])
    db.session.flush()  # MySQL asigna el id sin terminar la transacción
    orden.codigo = f"PED-{orden.id:06d}"
    db.session.commit()
    return jsonify(domicilio.to_dict()), 201


# =====================================================================
#  RF-08.4 Consultar pedidos a domicilio y RF-08.8 Historial
# =====================================================================


@bp.get("/domicilios")
@permiso_requerido("domicilios.ver")
def listar_domicilios():
    """RF-08.4 Consultar pedidos a domicilio en curso (los no entregados ni cancelados),
    del más antiguo al más reciente: así se atiende primero al que lleva más tiempo esperando.
    Filtro opcional: ?estado=EN_CAMINO. El DOMICILIARIO solo ve los suyos."""
    consulta = Domicilio.query.filter(Domicilio.estado.notin_(Domicilio.FINALES))
    estado = request.args.get("estado", "").upper()
    if estado in Domicilio.ESTADOS:
        consulta = consulta.filter_by(estado=estado)
    if not _puede_gestionar():
        consulta = consulta.filter_by(domiciliario_id=usuario_actual().id)
    domicilios = consulta.order_by(Domicilio.created_at, Domicilio.id).all()
    return jsonify([d.to_dict(con_orden=False) for d in domicilios])


@bp.get("/domicilios/historial")
@permiso_requerido("domicilios.ver")
def historial_domicilios():
    """RF-08.8 Consultar historial de domicilios entregados o cancelados, del más reciente al
    más antiguo. Filtros: ?desde=2026-10-01&hasta=2026-10-31&cliente_id=1&domiciliario_id=2"""
    consulta = Domicilio.query.filter(Domicilio.estado.in_(Domicilio.FINALES))
    try:
        if request.args.get("desde"):
            desde = date.fromisoformat(request.args["desde"])
            consulta = consulta.filter(Domicilio.created_at >= desde)
        if request.args.get("hasta"):
            hasta = date.fromisoformat(request.args["hasta"]) + timedelta(days=1)  # día completo
            consulta = consulta.filter(Domicilio.created_at < hasta)
    except ValueError:
        return jsonify(error="Las fechas deben tener el formato AAAA-MM-DD"), 422

    for filtro in ("cliente_id", "domiciliario_id"):
        valor = request.args.get(filtro, type=int)
        if valor:
            consulta = consulta.filter(getattr(Domicilio, filtro) == valor)
    if not _puede_gestionar():
        consulta = consulta.filter_by(domiciliario_id=usuario_actual().id)

    domicilios = consulta.order_by(Domicilio.created_at.desc(), Domicilio.id.desc()).limit(200).all()
    entregados = [d for d in domicilios if d.estado == "ENTREGADO"]
    resumen = {
        "entregados": len(entregados),
        "cancelados": len(domicilios) - len(entregados),
        "total_entregado": float(sum((d.orden.total for d in entregados), Decimal("0"))),
    }
    return jsonify(resumen=resumen, domicilios=[d.to_dict(con_orden=False) for d in domicilios])


@bp.get("/domicilios/<int:domicilio_id>")
@permiso_requerido("domicilios.ver")
def obtener_domicilio(domicilio_id):
    """RF-08.4 Detalle de un domicilio con los productos del pedido."""
    domicilio, error = _buscar_domicilio(domicilio_id)
    if error:
        return error
    return jsonify(domicilio.to_dict())


# =====================================================================
#  RF-08.5 Asignar, RF-08.6 Actualizar estado y RF-08.7 Registrar entrega
# =====================================================================


@bp.get("/domiciliarios")
@permiso_requerido("domicilios.gestionar")
def listar_domiciliarios():
    """RF-08.5 Usuarios activos con rol DOMICILIARIO, para elegir a quién asignar."""
    usuarios = (Usuario.query.join(Rol).filter(Rol.nombre == "DOMICILIARIO",
                                               Usuario.activo.is_(True))
                .order_by(Usuario.nombre).all())
    return jsonify([{"id": u.id, "nombre": f"{u.nombre} {u.apellido}", "telefono": u.telefono}
                    for u in usuarios])


@bp.patch("/domicilios/<int:domicilio_id>/asignar")
@permiso_requerido("domicilios.gestionar")
def asignar_domicilio(domicilio_id):
    """RF-08.5 Asignar pedidos para entrega a un domiciliario (o cambiarlo antes de salir).

    Body: {"domiciliario_id": 5}
    """
    domicilio = db.session.get(Domicilio, domicilio_id)
    if domicilio is None:
        return jsonify(error="El domicilio no existe"), 404
    if domicilio.estado in Domicilio.FINALES or domicilio.estado == "EN_CAMINO":
        return jsonify(error=f"No se puede asignar un domicilio {domicilio.estado}"), 409

    domiciliario = db.session.get(Usuario, (request.get_json(silent=True) or {})
                                  .get("domiciliario_id") or 0)
    if (domiciliario is None or not domiciliario.activo
            or domiciliario.rol.nombre != "DOMICILIARIO"):
        return jsonify(error="El usuario no existe o no es un domiciliario activo"), 422

    domicilio.domiciliario = domiciliario
    domicilio.fecha_asignacion = datetime.now()
    db.session.commit()
    return jsonify(domicilio.to_dict())


@bp.patch("/domicilios/<int:domicilio_id>/estado")
@permiso_requerido("domicilios.ver")
def actualizar_estado(domicilio_id):
    """RF-08.6 Actualizar estado del domicilio: RECIBIDO -> EN_PREPARACION -> LISTO ->
    EN_CAMINO (o CANCELADO). El DOMICILIARIO asignado solo puede marcar EN_CAMINO.

    Body: {"estado": "EN_CAMINO"}
    """
    domicilio, error = _buscar_domicilio(domicilio_id)
    if error:
        return error

    nuevo = _texto((request.get_json(silent=True) or {}).get("estado")).upper()
    if nuevo == "ENTREGADO":
        return jsonify(error="La entrega se registra con quién la recibió (registrar entrega)"), 422
    if nuevo not in TRANSICIONES:
        return jsonify(error=f"Estado inválido. Opciones: {', '.join(TRANSICIONES)}"), 422
    if not _puede_gestionar() and nuevo != "EN_CAMINO":
        return jsonify(error="No tienes permiso para realizar esta acción"), 403
    if nuevo not in TRANSICIONES[domicilio.estado]:
        return jsonify(error=f"Un domicilio {domicilio.estado} no puede pasar a {nuevo}"), 409
    if nuevo == "EN_CAMINO" and domicilio.domiciliario_id is None:
        return jsonify(error="Primero asigna un domiciliario"), 409

    domicilio.estado = nuevo
    if nuevo == "EN_CAMINO":
        domicilio.fecha_salida = datetime.now()
    if nuevo == "CANCELADO":
        domicilio.orden.estado = "CANCELADA"
    db.session.commit()
    return jsonify(domicilio.to_dict())


@bp.post("/domicilios/<int:domicilio_id>/entrega")
@permiso_requerido("domicilios.ver")
def registrar_entrega(domicilio_id):
    """RF-08.7 Registrar entrega del pedido: solo un domicilio EN_CAMINO.

    Body: {"recibido_por": "María Gómez", "observacion": "Pagó en efectivo"}
    """
    domicilio, error = _buscar_domicilio(domicilio_id)
    if error:
        return error
    if domicilio.estado != "EN_CAMINO":
        return jsonify(error="Solo se puede entregar un domicilio que va EN_CAMINO"), 409

    data = request.get_json(silent=True) or {}
    recibido_por = _texto(data.get("recibido_por"))
    if not recibido_por:
        return jsonify(error="Escribe quién recibió el pedido"), 422

    domicilio.estado = "ENTREGADO"
    domicilio.fecha_entrega = datetime.now()
    domicilio.recibido_por = recibido_por
    domicilio.observacion_entrega = _texto(data.get("observacion")) or None
    db.session.commit()
    return jsonify(domicilio.to_dict())
