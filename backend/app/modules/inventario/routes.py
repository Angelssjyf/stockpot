"""Módulo 3 - Gestión de inventario: insumos (RF-03.1 a RF-03.3)."""

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ...extensions import db
from ...models import Insumo
from ...models.inventario import UNIDADES_MEDIDA
from ...utils.auth import permiso_requerido

bp = Blueprint("inventario", __name__)


def _texto(valor):
    """Convierte un valor recibido en texto sin espacios a los lados ('' si viene vacío)."""
    return str(valor if valor is not None else "").strip()


def _aplicar_datos(insumo, data):
    """Valida los datos recibidos y los copia al insumo.

    Devuelve (mensaje, código HTTP) si algo está mal, o None si todo está bien.
    El stock NO se cambia aquí: solo cambia con compras recibidas (RF-02.8) y con las
    entradas y salidas de inventario (RF-03.4 y RF-03.5).
    """
    if "stock_actual" in data:
        return "El stock no se modifica aquí: cambia con las compras, entradas y salidas", 422

    if "codigo" in data:
        codigo = _texto(data["codigo"]).upper()
        if not codigo:
            return "El código no puede quedar vacío", 422
        otro = Insumo.query.filter_by(codigo=codigo).first()
        if otro and otro.id != insumo.id:
            return "Ya existe un insumo con ese código", 409
        insumo.codigo = codigo

    if "nombre" in data:
        nombre = _texto(data["nombre"])
        if not nombre:
            return "El nombre no puede quedar vacío", 422
        insumo.nombre = nombre

    if "unidad_medida" in data:
        unidad = _texto(data["unidad_medida"]).upper()
        if unidad not in UNIDADES_MEDIDA:
            return f"Unidad de medida inválida. Opciones: {', '.join(UNIDADES_MEDIDA)}", 422
        insumo.unidad_medida = unidad

    if "activo" in data:
        if not isinstance(data["activo"], bool):
            return "'activo' debe ser true o false", 422
        insumo.activo = data["activo"]

    return None


@bp.get("/insumos")
@permiso_requerido("inventario.ver", "proveedores.ver", "compras.ver")
def listar_insumos():
    """RF-03.2 Consultar insumos. Filtros opcionales: ?q= (código o nombre) y
    ?activo=true|false. También lo usan proveedores y compras para elegir insumos."""
    consulta = Insumo.query

    texto = request.args.get("q", "").strip()
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.filter(or_(Insumo.codigo.ilike(patron), Insumo.nombre.ilike(patron)))

    activo = request.args.get("activo")
    if activo in ("true", "false"):
        consulta = consulta.filter(Insumo.activo.is_(activo == "true"))

    insumos = consulta.order_by(Insumo.nombre).all()
    return jsonify([insumo.to_dict() for insumo in insumos])


@bp.get("/insumos/<int:insumo_id>")
@permiso_requerido("inventario.ver", "proveedores.ver", "compras.ver")
def obtener_insumo(insumo_id):
    """RF-03.2 Consultar el detalle de un insumo."""
    insumo = db.session.get(Insumo, insumo_id)
    if insumo is None:
        return jsonify(error="El insumo no existe"), 404
    return jsonify(insumo.to_dict())


@bp.post("/insumos")
@permiso_requerido("inventario.gestionar")
def crear_insumo():
    """RF-03.1 Registrar insumos y materias primas. Empiezan con stock 0."""
    data = request.get_json(silent=True) or {}

    obligatorios = ("codigo", "nombre", "unidad_medida")
    faltantes = [campo for campo in obligatorios if not _texto(data.get(campo))]
    if faltantes:
        return jsonify(error="Faltan campos obligatorios", faltantes=faltantes), 422

    insumo = Insumo()
    error = _aplicar_datos(insumo, data)
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]

    db.session.add(insumo)
    db.session.commit()
    return jsonify(insumo.to_dict()), 201


@bp.put("/insumos/<int:insumo_id>")
@permiso_requerido("inventario.gestionar")
def modificar_insumo(insumo_id):
    """RF-03.3 Modificar información de insumos (también activar o desactivar)."""
    insumo = db.session.get(Insumo, insumo_id)
    if insumo is None:
        return jsonify(error="El insumo no existe"), 404

    error = _aplicar_datos(insumo, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()  # no deja cambios a medias
        return jsonify(error=error[0]), error[1]

    db.session.commit()
    return jsonify(insumo.to_dict())
