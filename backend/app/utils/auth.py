"""Control de acceso compartido por todos los módulos: sesión, permisos y PIN.

En cada petición se revisa, contra la base de datos (no solo contra el token):
- que la sesión siga abierta y no lleve más de INACTIVIDAD_MINUTOS sin uso;
- que el usuario siga activo y su restaurante también;
- los permisos actuales de su rol (un cambio de rol aplica de inmediato);
- que la sesión no esté bloqueada (botón Bloquear o inactividad en la pantalla).
"""

from datetime import datetime, timedelta
from functools import wraps

from flask import current_app, g, jsonify, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request

from ..extensions import db
from ..models import Empresa, Sesion, Usuario

INTENTOS_PIN = 5  # al quinto PIN equivocado se cierra la sesión
REFRESCO = timedelta(seconds=30)  # no se escribe la última actividad en cada petición


def rechazo(mensaje, codigo_http, codigo=None):
    """Respuesta de error con un código para que la interfaz sepa qué hacer (pedir PIN, ir al login...)."""
    cuerpo = {"error": mensaje}
    if codigo:
        cuerpo["codigo"] = codigo
    return jsonify(cuerpo), codigo_http


def cerrar_sesion(sesion, motivo):
    sesion.cerrada = datetime.now()
    sesion.motivo_cierre = motivo
    db.session.commit()


def abrir_sesion(permitir_bloqueada=False):
    """Revisa la sesión del token y deja en g el usuario, su empresa y sus permisos.

    Devuelve None si todo está bien o la respuesta de error. Debe llamarse después de
    verify_jwt_in_request().
    """
    sesion = Sesion.query.filter_by(jti=get_jwt().get("jti")).first()
    if sesion is None or sesion.cerrada:
        return rechazo("La sesión se cerró: inicia sesión de nuevo", 401, "SESION_CERRADA")

    ahora = datetime.now()
    if ahora - sesion.ultima_actividad > timedelta(minutes=current_app.config["INACTIVIDAD_MINUTOS"]):
        cerrar_sesion(sesion, "INACTIVIDAD")
        return rechazo("La sesión se cerró por inactividad: inicia sesión de nuevo", 401, "INACTIVIDAD")

    usuario = db.session.get(Usuario, sesion.usuario_id, execution_options={"todas_las_empresas": True})
    if usuario is None or not usuario.activo:
        cerrar_sesion(sesion, "USUARIO")
        return rechazo("Tu usuario fue desactivado", 401, "SESION_CERRADA")

    g.empresa_id = usuario.empresa_id  # desde aquí cada consulta se filtra por su restaurante
    if usuario.empresa_id is not None:
        empresa = db.session.get(Empresa, usuario.empresa_id)
        if empresa is None or not empresa.activa:
            return rechazo("El restaurante está desactivado. Comunícate con StockPot", 403, "EMPRESA_INACTIVA")

    g.sesion = sesion
    g.usuario = usuario
    g.permisos = {p.codigo for p in usuario.rol.permisos} if usuario.rol.activo else set()

    if sesion.bloqueada and not permitir_bloqueada:
        return rechazo("La sesión está bloqueada: desbloquéala con tu PIN", 423, "SESION_BLOQUEADA")
    # Las consultas automáticas (avisos cada pocos segundos) no cuentan como actividad
    if not request.headers.get("X-Segundo-Plano") and ahora - sesion.ultima_actividad > REFRESCO:
        sesion.ultima_actividad = ahora
        db.session.commit()
    return None


def permiso_requerido(*codigos):
    """Decorador: exige una sesión válida y al menos uno de los permisos indicados.

    Uso:
        @bp.post("/usuarios")
        @permiso_requerido("usuarios.gestionar")
        def crear_usuario(): ...
    """

    def decorador(funcion):
        @wraps(funcion)  # conserva el nombre y la documentación de la función original
        def envoltura(*args, **kwargs):
            verify_jwt_in_request()  # sin token o token inválido -> 401 automático
            error = abrir_sesion()
            if error:
                return error
            if not g.permisos.intersection(codigos):
                return jsonify(error="No tienes permiso para realizar esta acción"), 403
            return funcion(*args, **kwargs)

        return envoltura

    return decorador


def tiene_permiso(codigo):
    """True si el usuario de la petición tiene ese permiso (leído de la base de datos)."""
    return codigo in g.get("permisos", set())


def usuario_actual():
    """El Usuario de la sesión de la petición actual."""
    return g.usuario


def verificar_pin(datos):
    """PIN para acciones con dinero o inventario (cobrar, anular pagos, registrar salidas).

    Confirma que quien está frente a la pantalla es el dueño de la sesión. Devuelve None si
    el PIN es correcto o la respuesta de error. Al quinto PIN equivocado se cierra la sesión.
    """
    if not current_app.config["EXIGIR_PIN"]:
        return None
    usuario, sesion = g.usuario, g.sesion
    if not usuario.pin_hash:
        return rechazo("Crea tu PIN para hacer esta operación", 428, "PIN_NO_CONFIGURADO")
    pin = str(datos.get("pin") or "").strip()
    if not pin:
        return rechazo("Escribe tu PIN para continuar", 428, "PIN_REQUERIDO")
    return comprobar_secreto(sesion, usuario.check_pin(pin), "PIN incorrecto")


def comprobar_secreto(sesion, correcto, mensaje):
    """Cuenta los intentos fallidos de PIN o contraseña en la sesión; al quinto la cierra."""
    if correcto:
        if sesion.intentos_pin:
            sesion.intentos_pin = 0
            db.session.commit()
        return None
    sesion.intentos_pin += 1
    if sesion.intentos_pin >= INTENTOS_PIN:
        cerrar_sesion(sesion, "PIN")
        return rechazo("Demasiados intentos fallidos: la sesión se cerró", 401, "SESION_CERRADA")
    db.session.commit()
    quedan = INTENTOS_PIN - sesion.intentos_pin
    return rechazo(f"{mensaje} (te quedan {quedan} intento{'s' if quedan > 1 else ''})", 403, "PIN_INCORRECTO")
