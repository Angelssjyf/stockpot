"""Modelos de ILF06 Productos y platos e ILF07 Recetas (Iteración 2)."""

from decimal import Decimal

from ..extensions import db

CATEGORIAS = ("ENTRADA", "PLATO_FUERTE", "BEBIDA", "POSTRE", "ADICIONAL")


class Producto(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(255))
    categoria = db.Column(db.Enum(*CATEGORIAS, name="categoria_producto"), nullable=False)
    precio_venta = db.Column(db.Numeric(12, 2), nullable=False)
    disponible = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # producto.receta -> lista de Receta (qué insumos lleva y cuánto)
    receta = db.relationship("Receta", back_populates="producto", cascade="all, delete-orphan")

    @property
    def costo(self):
        """Costo de una porción: suma de cantidad × costo unitario de cada insumo."""
        return sum((linea.costo for linea in self.receta), Decimal("0"))

    @property
    def porciones_posibles(self):
        """Cuántas porciones alcanzan con el stock actual (None si no tiene receta)."""
        if not self.receta:
            return None
        return min(int(linea.insumo.stock_actual // linea.cantidad) for linea in self.receta)

    def to_dict(self, con_receta=False):
        datos = {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "categoria": self.categoria,
            "precio_venta": float(self.precio_venta),
            "costo": float(self.costo),
            "margen": float(self.precio_venta - self.costo),  # ganancia por porción
            "porciones_posibles": self.porciones_posibles,
            "disponible": self.disponible,
            "activo": self.activo,
        }
        if con_receta:
            datos["receta"] = [linea.to_dict() for linea in self.receta]
        return datos


class Receta(db.Model):
    """RF-04.4 Un insumo de la receta y la cantidad que lleva una porción."""

    __tablename__ = "recetas"

    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), primary_key=True)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)

    producto = db.relationship("Producto", back_populates="receta")
    insumo = db.relationship("Insumo")

    @property
    def costo(self):
        return self.cantidad * self.insumo.costo_unitario

    def to_dict(self):
        return {
            "insumo_id": self.insumo_id,
            "insumo": self.insumo.nombre,
            "unidad_medida": self.insumo.unidad_medida,
            "cantidad": float(self.cantidad),
            "costo": float(self.costo),
        }
