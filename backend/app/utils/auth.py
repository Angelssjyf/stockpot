"""Control de acceso por permisos, compartido por todos los módulos."""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models import Usuario


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

            permisos_del_usuario = set(get_jwt().get("permisos", []))
            if not permisos_del_usuario.intersection(codigos):
                return jsonify(error="No tienes permiso para realizar esta acción"), 403

            return funcion(*args, **kwargs)

        return envoltura

    return decorador


def usuario_actual():
    """Devuelve el Usuario dueño del token de la petición actual."""
    return db.session.get(Usuario, int(get_jwt_identity()))
