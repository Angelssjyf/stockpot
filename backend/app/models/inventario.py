"""Modelo de ILF04 Insumos.

Versión básica creada en la Iteración 1 (las órdenes de compra necesitan saber qué se
compra). Se completa en la Iteración 2 con el módulo de inventario.
"""

from ..extensions import db

UNIDADES_MEDIDA = ("KG", "G", "L", "ML", "UNIDAD")


class Insumo(db.Model):
    __tablename__ = "insumos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    nombre = db.Column(db.String(120), nullable=False)
    unidad_medida = db.Column(db.Enum(*UNIDADES_MEDIDA, name="unidad_medida"), nullable=False)
    stock_actual = db.Column(db.Numeric(12, 3), nullable=False, default=0, server_default="0")
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "unidad_medida": self.unidad_medida,
            "stock_actual": float(self.stock_actual),  # Decimal -> número para JSON
            "activo": self.activo,
        }