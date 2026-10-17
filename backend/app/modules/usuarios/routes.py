"""Módulo 1 - Gestión de usuarios y roles (RF-01)."""

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ...extensions import db
from ...models import Rol, Usuario
from ...utils.auth import permiso_requerido

bp = Blueprint("usuarios", __name__)


@bp.get("/usuarios")
@permiso_requerido("usuarios.ver")
def listar_usuarios():
    """RF-01.2 Consultar usuarios. Filtro opcional ?q= por nombre, apellido o correo."""
    consulta = Usuario.query

    texto = request.args.get("q", "").strip()
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.filter(
            or_(Usuario.nombre.ilike(patron), Usuario.apellido.ilike(patron),
                Usuario.email.ilike(patron))
        )

    usuarios = consulta.order_by(Usuario.nombre, Usuario.apellido).all()
    return jsonify([u.to_dict() for u in usuarios])


@bp.post("/usuarios")
@permiso_requerido("usuarios.gestionar")
def crear_usuario():
    """RF-01.1 Registrar usuarios."""
    data = request.get_json(silent=True) or {}

    # 1. Campos obligatorios
    obligatorios = ["nombre", "apellido", "email", "password", "rol_id"]
    faltantes = [campo for campo in obligatorios if not data.get(campo)]
    if faltantes:
        return jsonify(error="Faltan campos obligatorios", faltantes=faltantes), 422

    # 2. Reglas de negocio
    email = data["email"].strip().lower()
    if "@" not in email:
        return jsonify(error="El correo no es válido"), 422
    if len(data["password"]) < 8:
        return jsonify(error="La contraseña debe tener al menos 8 caracteres"), 422

    rol = db.session.get(Rol, data["rol_id"])
    if rol is None or not rol.activo:
        return jsonify(error="El rol indicado no existe"), 422

    if Usuario.query.filter_by(email=email).first():
        return jsonify(error="Ya existe un usuario con ese correo"), 409

    # 3. Guardar
    usuario = Usuario(
        nombre=data["nombre"].strip(),
        apellido=data["apellido"].strip(),
        email=email,
        telefono=(data.get("telefono") or "").strip() or None,
        rol=rol,
    )
    usuario.set_password(data["password"])
    db.session.add(usuario)
    db.session.commit()

    return jsonify(usuario.to_dict()), 201  # 201 = creado
