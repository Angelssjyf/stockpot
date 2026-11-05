"""Modelo de ILF11 Reservas (RF-07.1 a RF-07.8)."""

from datetime import timedelta

from ..extensions import db
from .empresas import DeEmpresa


def _fecha(valor):
    return valor.isoformat() if valor else None


class Reserva(DeEmpresa, db.Model):
    """Una mesa apartada para un cliente en una fecha y hora.

    PENDIENTE -> CONFIRMADA -> CUMPLIDA (el cliente llegó) o NO_ASISTIO
    Mientras no llegue se puede CANCELAR. Las que están PENDIENTE o CONFIRMADA ocupan la mesa
    desde fecha_hora durante duracion_minutos.
    """

    __tablename__ = "reservas"

    ESTADOS = ("PENDIENTE", "CONFIRMADA", "CUMPLIDA", "NO_ASISTIO", "CANCELADA")
    ACTIVAS = ("PENDIENTE", "CONFIRMADA")  # apartan la mesa y se pueden modificar

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)  # RES-000001
    mesa_id = db.Column(db.Integer, db.ForeignKey("mesas.id"), nullable=False)
    cliente = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    personas = db.Column(db.Integer, nullable=False)
    fecha_hora = db.Column(db.DateTime, nullable=False, index=True)  # RF-07.5
    duracion_minutos = db.Column(db.Integer, nullable=False, default=120, server_default="120")
    estado = db.Column(db.Enum(*ESTADOS, name="estado_reserva"), nullable=False,
                       default="PENDIENTE", server_default="PENDIENTE")
    observaciones = db.Column(db.String(255))
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    mesa = db.relationship("Mesa")
    usuario = db.relationship("Usuario")

    @property
    def fin(self):
        return self.fecha_hora + timedelta(minutes=self.duracion_minutos)

    @property
    def activa(self):
        return self.estado in self.ACTIVAS

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "mesa_id": self.mesa_id,
            "mesa": self.mesa.numero,
            "ubicacion": self.mesa.ubicacion,
            "capacidad": self.mesa.capacidad,
            "cliente": self.cliente,
            "telefono": self.telefono,
            "personas": self.personas,
            "fecha_hora": _fecha(self.fecha_hora),
            "fin": _fecha(self.fin),
            "duracion_minutos": self.duracion_minutos,
            "estado": self.estado,
            "activa": self.activa,
            "observaciones": self.observaciones,
            "registrada_por": f"{self.usuario.nombre} {self.usuario.apellido}",
            "fecha_registro": _fecha(self.created_at),
        }
