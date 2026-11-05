"""Sesiones de trabajo (tercer corte, sesiones seguras).

Cada inicio de sesión queda guardado con el identificador de su token (jti). Así el servidor
puede bloquearla, cerrarla por inactividad o al salir, aunque el token todavía no haya vencido.
"""

from ..extensions import db


class Sesion(db.Model):
    __tablename__ = "sesiones"

    MOTIVOS = ("SALIDA", "INACTIVIDAD", "PIN", "USUARIO")  # por qué se cerró

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)  # identificador del token
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    creada = db.Column(db.DateTime, nullable=False)
    ultima_actividad = db.Column(db.DateTime, nullable=False)
    bloqueada = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    intentos_pin = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    cerrada = db.Column(db.DateTime)  # None = abierta
    motivo_cierre = db.Column(db.Enum(*MOTIVOS, name="motivo_cierre_sesion"))

    usuario = db.relationship("Usuario")
