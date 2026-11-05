"""Autenticación: iniciar sesión (RF-01.4) y consultar el usuario de la sesión."""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required

from ...extensions import db
from ...models import Empresa, Usuario
from ...utils.auth import abrir_sesion_de_empresa

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

    # El correo es único en todo StockPot: se busca en todas las empresas
    usuario = Usuario.query.execution_options(todas_las_empresas=True).filter_by(email=email).first()

    # Mismo mensaje si no existe el correo o si la clave es incorrecta,
    # para no revelar qué correos están registrados.
    if usuario is None or not usuario.check_password(password):
        return jsonify(error="Correo o contraseña incorrectos"), 401
    if not usuario.activo:
        return jsonify(error="El usuario está desactivado"), 403
    empresa = db.session.get(Empresa, usuario.empresa_id) if usuario.empresa_id else None
    if empresa is not None and not empresa.activa:
        return jsonify(error="El restaurante está desactivado. Comunícate con StockPot"), 403

    usuario.ultimo_acceso = datetime.now()
    db.session.commit()

    permisos = sorted(p.codigo for p in usuario.rol.permisos)
    token = create_access_token(
        identity=str(usuario.id),  # quién es
        # qué puede hacer y de qué restaurante es (None: súper administrador)
        additional_claims={"rol": usuario.rol.nombre, "permisos": permisos, "empresa": usuario.empresa_id},
    )
    return jsonify(access_token=token, usuario={**usuario.to_dict(), "permisos": permisos})


@bp.get("/me")
@jwt_required()  # solo responde si la petición trae un token válido
def me():
    """Devuelve los datos del usuario dueño del token."""
    rechazo = abrir_sesion_de_empresa(get_jwt())
    if rechazo:
        return rechazo
    usuario = db.session.get(Usuario, int(get_jwt_identity()))
    if usuario is None or not usuario.activo:
        return jsonify(error="Usuario no válido o inactivo"), 401
    permisos = sorted(p.codigo for p in usuario.rol.permisos)
    return jsonify({**usuario.to_dict(), "permisos": permisos})
