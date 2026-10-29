"""Modelos de ILF04 Insumos e ILF05 Movimientos de inventario (Iteración 2)."""

from ..extensions import db

UNIDADES_MEDIDA = ("KG", "G", "L", "ML", "UNIDAD")

# RF-03.10 Categorías de insumos: agrupan el inventario y subdividen a los proveedores (RF-02.9)
CATEGORIAS_INSUMO = (
    "CARNES", "GRANOS", "LACTEOS", "FRUTAS_VERDURAS", "BEBIDAS", "ABARROTES",
    "DESECHABLES", "LIMPIEZA", "MOBILIARIO", "OTROS",
)


class Insumo(db.Model):
    __tablename__ = "insumos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    nombre = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.Enum(*CATEGORIAS_INSUMO, name="categoria_insumo"), nullable=False,
                          default="OTROS", server_default="OTROS")
    unidad_medida = db.Column(db.Enum(*UNIDADES_MEDIDA, name="unidad_medida"), nullable=False)
    stock_actual = db.Column(db.Numeric(12, 3), nullable=False, default=0, server_default="0")
    stock_minimo = db.Column(db.Numeric(12, 3), nullable=False, default=0, server_default="0")
    costo_unitario = db.Column(db.Numeric(12, 2), nullable=False, default=0, server_default="0")
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @property
    def estado_stock(self):
        """RF-03.8 AGOTADO (sin stock), BAJO (en el mínimo o por debajo) u OK."""
        if self.stock_actual <= 0:
            return "AGOTADO"
        if self.stock_actual <= self.stock_minimo:
            return "BAJO"
        return "OK"

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "unidad_medida": self.unidad_medida,
            "stock_actual": float(self.stock_actual),  # Decimal -> número para JSON
            "stock_minimo": float(self.stock_minimo),
            "costo_unitario": float(self.costo_unitario),
            "estado_stock": self.estado_stock,
            "activo": self.activo,
        }


class MovimientoInventario(db.Model):
    """ILF05 Un cambio de stock: entrada o salida, con su motivo, cantidad y responsable."""

    __tablename__ = "movimientos_inventario"

    TIPOS = ("ENTRADA", "SALIDA")
    MOTIVOS = ("COMPRA", "AJUSTE", "DEVOLUCION", "CONSUMO", "MERMA")

    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), nullable=False)
    tipo = db.Column(db.Enum(*TIPOS, name="tipo_movimiento"), nullable=False)
    motivo = db.Column(db.Enum(*MOTIVOS, name="motivo_movimiento"), nullable=False)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
    stock_resultante = db.Column(db.Numeric(12, 3), nullable=False)
    orden_compra_id = db.Column(db.Integer, db.ForeignKey("ordenes_compra.id"))
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    observacion = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    insumo = db.relationship("Insumo")
    usuario = db.relationship("Usuario")
    orden_compra = db.relationship("OrdenCompra")

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": self.created_at.isoformat() if self.created_at else None,
            "insumo_id": self.insumo_id,
            "insumo": self.insumo.nombre,
            "unidad_medida": self.insumo.unidad_medida,
            "tipo": self.tipo,
            "motivo": self.motivo,
            "cantidad": float(self.cantidad),
            "stock_resultante": float(self.stock_resultante),
            "orden_compra": self.orden_compra.codigo if self.orden_compra else None,
            "usuario": f"{self.usuario.nombre} {self.usuario.apellido}",
            "observacion": self.observacion,
        }
