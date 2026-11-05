"""Control de acceso por permisos, compartido por todos los módulos."""

from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models import Empresa, Usuario


def abrir_sesion_de_empresa(claims):
    """Deja en g la empresa del token para que cada consulta se filtre sola (models/empresas.py).

    Devuelve None si todo está bien, o la respuesta de error: token de antes de que hubiera
    empresas (401) o restaurante desactivado por el súper administrador (403).
    """
    if "empresa" not in claims:
        return jsonify(error="Tu sesión es de una versión anterior: inicia sesión de nuevo"), 401
    g.empresa_id = claims["empresa"]
    if g.empresa_id is not None:
        empresa = db.session.get(Empresa, g.empresa_id)
        if empresa is None or not empresa.activa:
            return jsonify(error="El restaurante está desactivado. Comunícate con StockPot"), 403
    return None


def permiso_requerido(*codigos):
    """Decorador: exige sesión iniciada y al menos uno de los permisos indicados.

    Uso:
        @bp.post("/usuarios")
        @permiso_requerido("usuarios.gestionar")
        def crear_usuario(): ...
    """

    def decorador(funcion):
        @wraps(funcion)  # conserva el nombre y la documentación de la función original
        def envoltura(*args, **kwargs):
            verify_jwt_in_request()  # sin token o token inválido -> 401 automático
            rechazo = abrir_sesion_de_empresa(get_jwt())
            if rechazo:
                return rechazo

            permisos_del_usuario = set(get_jwt().get("permisos", []))
            if not permisos_del_usuario.intersection(codigos):
                return jsonify(error="No tienes permiso para realizar esta acción"), 403

            return funcion(*args, **kwargs)

        return envoltura

    return decorador


def usuario_actual():
    """Devuelve el Usuario dueño del token de la petición actual."""
    return db.session.get(Usuario, int(get_jwt_identity()))
