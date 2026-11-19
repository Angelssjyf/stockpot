"""Turnos de caja: apertura con base de efectivo y cierre con arqueo (cuadre de caja)."""

from decimal import Decimal

from ..extensions import db
from .empresas import DeEmpresa

METODOS = ("EFECTIVO", "TARJETA", "TRANSFERENCIA")


def _fecha(valor):
    return valor.isoformat() if valor else None


def _dinero(valor):
    return float(valor) if valor is not None else None


class TurnoCaja(DeEmpresa, db.Model):
    """Un turno de caja. Mientras está ABIERTO, los pagos aprobados se le suman; al CERRARLO
    se guarda lo que esperaba el sistema y lo que contó el cajero, por método de pago."""

    __tablename__ = "turnos_caja"

    ESTADOS = ("ABIERTO", "CERRADO")

    id = db.Column(db.Integer, primary_key=True)
    estado = db.Column(db.Enum(*ESTADOS, name="estado_turno_caja"), nullable=False,
                       default="ABIERTO", server_default="ABIERTO")
    base_inicial = db.Column(db.Numeric(14, 2), nullable=False, default=0, server_default="0")
    abierto_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    abierto_en = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    cerrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    cerrado_en = db.Column(db.DateTime)
    # Lo que el sistema esperaba al cerrar (efectivo incluye la base) y lo que se contó
    esperado_efectivo = db.Column(db.Numeric(14, 2))
    esperado_tarjeta = db.Column(db.Numeric(14, 2))
    esperado_transferencia = db.Column(db.Numeric(14, 2))
    contado_efectivo = db.Column(db.Numeric(14, 2))
    contado_tarjeta = db.Column(db.Numeric(14, 2))
    contado_transferencia = db.Column(db.Numeric(14, 2))
    num_pagos = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    propinas = db.Column(db.Numeric(12, 2), nullable=False, default=0, server_default="0")
    observacion = db.Column(db.String(255))

    abierto_por = db.relationship("Usuario", foreign_keys=[abierto_por_id])
    cerrado_por = db.relationship("Usuario", foreign_keys=[cerrado_por_id])

    def diferencias(self):
        """Contado − esperado por método (positivo: sobra; negativo: falta). Solo si está cerrado."""
        if self.estado != "CERRADO":
            return None
        por_metodo = {
            metodo.lower(): getattr(self, f"contado_{metodo.lower()}") - getattr(self, f"esperado_{metodo.lower()}")
            for metodo in METODOS
        }
        return {**{k: float(v) for k, v in por_metodo.items()}, "total": float(sum(por_metodo.values(), Decimal("0")))}

    def to_dict(self):
        nombre = lambda u: f"{u.nombre} {u.apellido}" if u else None  # noqa: E731
        return {
            "id": self.id,
            "estado": self.estado,
            "base_inicial": _dinero(self.base_inicial),
            "abierto_por": nombre(self.abierto_por),
            "abierto_en": _fecha(self.abierto_en),
            "cerrado_por": nombre(self.cerrado_por),
            "cerrado_en": _fecha(self.cerrado_en),
            "esperado": {m.lower(): _dinero(getattr(self, f"esperado_{m.lower()}")) for m in METODOS},
            "contado": {m.lower(): _dinero(getattr(self, f"contado_{m.lower()}")) for m in METODOS},
            "diferencia": self.diferencias(),
            "num_pagos": self.num_pagos,
            "propinas": _dinero(self.propinas),
            "observacion": self.observacion,
        }
