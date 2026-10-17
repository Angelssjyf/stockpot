"""Autenticación: iniciar sesión (RF-01.4) y consultar el usuario de la sesión."""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from ...extensions import db
from ...models import Usuario

# Un Blueprint agrupa las rutas de un módulo. Se registra en create_app con el prefijo /api/auth
bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    """RF-01.4 Iniciar sesión con correo y contraseña."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify(error="El correo y la contraseña son obligatorios"), 400

    usuario = Usuario.query.filter_by(email=email).first()

    # Mismo mensaje si no existe el correo o si la clave es incorrecta,
    # para no revelar qué correos están registrados.
    if usuario is None or not usuario.check_password(password):
        return jsonify(error="Correo o contraseña incorrectos"), 401
    if not usuario.activo:
        return jsonify(error="El usuario está desactivado"), 403

    usuario.ultimo_acceso = datetime.now()
    db.session.commit()

    permisos = sorted(p.codigo for p in usuario.rol.permisos)
    token = create_access_token(
        identity=str(usuario.id),  # quién es
        additional_claims={"rol": usuario.rol.nombre, "permisos": permisos},  # qué puede hacer
    )
    return jsonify(access_token=token, usuario={**usuario.to_dict(), "permisos": permisos})


@bp.get("/me")
@jwt_required()  # solo responde si la petición trae un token válido
def me():
    """Devuelve los datos del usuario dueño del token."""
    usuario = db.session.get(Usuario, int(get_jwt_identity()))
    if usuario is None or not usuario.activo:
        return jsonify(error="Usuario no válido o inactivo"), 401
    permisos = sorted(p.codigo for p in usuario.rol.permisos)
    return jsonify({**usuario.to_dict(), "permisos": permisos})
