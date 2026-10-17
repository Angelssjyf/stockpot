"""Módulo 1 - Gestión de usuarios y roles (RF-01)."""

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ...extensions import db
from ...models import Rol, Usuario
from ...utils.auth import permiso_requerido, usuario_actual

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


@bp.get("/usuarios/<int:usuario_id>")
@permiso_requerido("usuarios.ver")
def obtener_usuario(usuario_id):
    """RF-01.2 Consultar el detalle de un usuario."""
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        return jsonify(error="El usuario no existe"), 404
    return jsonify(usuario.to_dict())


@bp.put("/usuarios/<int:usuario_id>")
@permiso_requerido("usuarios.gestionar")
def modificar_usuario(usuario_id):
    """RF-01.3 Modificar usuarios.

    Solo se cambian los campos que vienen en la petición. La contraseña es opcional.
    El rol se cambia aparte (RF-01.5), con su propio permiso.
    """
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        return jsonify(error="El usuario no existe"), 404

    data = request.get_json(silent=True) or {}

    def rechazar(mensaje, codigo):
        """Deshace los cambios ya aplicados en memoria y responde con el error."""
        db.session.rollback()
        return jsonify(error=mensaje), codigo

    # Campos de texto obligatorios: si vienen, no pueden quedar vacíos
    for campo in ("nombre", "apellido"):
        if campo in data:
            valor = (data[campo] or "").strip()
            if not valor:
                return rechazar(f"El campo '{campo}' no puede quedar vacío", 422)
            setattr(usuario, campo, valor)

    if "telefono" in data:
        usuario.telefono = (data["telefono"] or "").strip() or None

    if "email" in data:
        email = (data["email"] or "").strip().lower()
        if "@" not in email:
            return rechazar("El correo no es válido", 422)
        otro = Usuario.query.filter_by(email=email).first()
        if otro and otro.id != usuario.id:
            return rechazar("Ya existe un usuario con ese correo", 409)
        usuario.email = email

    if data.get("password"):
        if len(data["password"]) < 8:
            return rechazar("La contraseña debe tener al menos 8 caracteres", 422)
        usuario.set_password(data["password"])

    if "activo" in data:
        if not isinstance(data["activo"], bool):
            return rechazar("'activo' debe ser true o false", 422)
        # Evita que el administrador se bloquee a sí mismo
        if data["activo"] is False and usuario.id == usuario_actual().id:
            return rechazar("No puedes desactivar tu propio usuario", 409)
        usuario.activo = data["activo"]

    db.session.commit()
    return jsonify(usuario.to_dict())
