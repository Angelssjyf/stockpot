"""Autenticación: iniciar sesión (RF-01.4), la sesión del usuario y su seguridad (tercer corte).

Sesiones seguras: cada inicio de sesión queda guardado (tabla sesiones). Se puede bloquear la
pantalla y volver con el PIN, cerrar la sesión de verdad y crear o cambiar el PIN personal.
"""

import re
from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, request
from flask_jwt_extended import create_access_token, decode_token, verify_jwt_in_request

from ...extensions import db
from ...models import Empresa, Sesion, Usuario
from ...utils.auth import abrir_sesion, cerrar_sesion, comprobar_secreto, rechazo

# Un Blueprint agrupa las rutas de un módulo. Se registra en create_app con el prefijo /api/auth
bp = Blueprint("auth", __name__)

PIN_VALIDO = re.compile(r"^\d{4,6}$")


def _pin_debil(pin):
    """Todos los dígitos iguales (1111) o seguidos (1234, 9876) son fáciles de adivinar."""
    pasos = {int(b) - int(a) for a, b in zip(pin, pin[1:])}
    return pasos in ({0}, {1}, {-1})


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

    ahora = datetime.now()
    usuario.ultimo_acceso = ahora
    # El token dice quién es; lo que puede hacer se lee de la base de datos en cada petición
    token = create_access_token(identity=str(usuario.id),
                                additional_claims={"rol": usuario.rol.nombre, "empresa": usuario.empresa_id})
    db.session.add(Sesion(jti=decode_token(token)["jti"], usuario_id=usuario.id, creada=ahora, ultima_actividad=ahora))
    db.session.commit()

    permisos = sorted(p.codigo for p in usuario.rol.permisos)
    return jsonify(access_token=token, usuario={**usuario.to_dict(), "permisos": permisos})


def _sesion_actual(permitir_bloqueada=True):
    verify_jwt_in_request()
    return abrir_sesion(permitir_bloqueada=permitir_bloqueada)


@bp.get("/me")
def me():
    """Datos del usuario de la sesión, sus permisos actuales y cómo está su sesión."""
    error = _sesion_actual()
    if error:
        return error
    return jsonify({
        **g.usuario.to_dict(),
        "permisos": sorted(g.permisos),
        "bloqueada": g.sesion.bloqueada,
        "bloqueo_minutos": current_app.config["BLOQUEO_MINUTOS"],
    })


@bp.post("/logout")
def logout():
    """Cerrar sesión: el token deja de servir aunque no haya vencido."""
    error = _sesion_actual()
    if error:
        return error
    cerrar_sesion(g.sesion, "SALIDA")
    return jsonify(mensaje="Sesión cerrada")


@bp.post("/bloquear")
def bloquear():
    """Bloquea la sesión (botón Bloquear o inactividad en la pantalla). Para volver: PIN o contraseña."""
    error = _sesion_actual()
    if error:
        return error
    g.sesion.bloqueada = True
    db.session.commit()
    return jsonify(bloqueada=True)


@bp.post("/desbloquear")
def desbloquear():
    """Desbloquea con el PIN (o con la contraseña si todavía no tiene PIN). Body: {"pin": "4826"}"""
    error = _sesion_actual()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    if data.get("pin"):
        correcto = bool(g.usuario.pin_hash) and g.usuario.check_pin(str(data["pin"]).strip())
        error = comprobar_secreto(g.sesion, correcto, "PIN incorrecto")
    elif data.get("password"):
        error = comprobar_secreto(g.sesion, g.usuario.check_password(data["password"]), "Contraseña incorrecta")
    else:
        return rechazo("Escribe tu PIN o tu contraseña", 422)
    if error:
        return error
    g.sesion.bloqueada = False
    g.sesion.ultima_actividad = datetime.now()
    db.session.commit()
    return jsonify(bloqueada=False)


@bp.put("/pin")
def crear_pin():
    """Crea o cambia el PIN personal (4 a 6 dígitos). Pide la contraseña para confirmar que es el dueño.

    Body: {"password": "...", "pin": "4826"}
    """
    error = _sesion_actual(permitir_bloqueada=False)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    error = comprobar_secreto(g.sesion, g.usuario.check_password(data.get("password") or ""), "Contraseña incorrecta")
    if error:
        return error
    pin = str(data.get("pin") or "").strip()
    if not PIN_VALIDO.match(pin):
        return rechazo("El PIN debe tener de 4 a 6 números", 422)
    if _pin_debil(pin):
        return rechazo("Ese PIN es muy fácil de adivinar (números iguales o seguidos)", 422)
    g.usuario.set_pin(pin)
    db.session.commit()
    return jsonify(mensaje="PIN guardado", tiene_pin=True)
