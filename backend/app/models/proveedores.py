"""Modelos de ILF03 Proveedores e ILF17 Órdenes de compra (Iteración 1).

Cada clase corresponde a una tabla creada en database/01_schema.sql.
"""

from ..extensions import db


class Proveedor(db.Model):
    __tablename__ = "proveedores"

    id = db.Column(db.Integer, primary_key=True)
    nit = db.Column(db.String(20), nullable=False, unique=True)
    razon_social = db.Column(db.String(150), nullable=False)
    contacto = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # proveedor.insumos -> lista de ProveedorInsumo (qué insumos vende y a qué precio)
    insumos = db.relationship(
        "ProveedorInsumo", back_populates="proveedor", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nit": self.nit,
            "razon_social": self.razon_social,
            "contacto": self.contacto,
            "telefono": self.telefono,
            "email": self.email,
            "direccion": self.direccion,
            "activo": self.activo,
        }


class ProveedorInsumo(db.Model):
    """RF-02.4 Productos suministrados: un insumo que vende un proveedor y su precio."""

    __tablename__ = "proveedor_insumos"

    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), primary_key=True)
    precio_referencia = db.Column(db.Numeric(12, 2))

    proveedor = db.relationship("Proveedor", back_populates="insumos")
    insumo = db.relationship("Insumo")

    def to_dict(self):
        return {
            "insumo_id": self.insumo_id,
            "insumo": self.insumo.nombre,
            "unidad_medida": self.insumo.unidad_medida,
            "precio_referencia": (
                float(self.precio_referencia) if self.precio_referencia is not None else None
            ),
        }


class OrdenCompra(db.Model):
    """ILF17 Encabezado de una orden de compra."""

    __tablename__ = "ordenes_compra"

    ESTADOS = ("PENDIENTE", "ENVIADA", "RECIBIDA", "CANCELADA")

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)  # OC-000001
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    fecha_orden = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    fecha_entrega_estimada = db.Column(db.Date)
    fecha_recepcion = db.Column(db.DateTime)
    estado = db.Column(
        db.Enum(*ESTADOS, name="estado_orden_compra"),
        nullable=False,
        default="PENDIENTE",
        server_default="PENDIENTE",
    )
    total = db.Column(db.Numeric(14, 2), nullable=False, default=0, server_default="0")
    observaciones = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    proveedor = db.relationship("Proveedor")
    usuario = db.relationship("Usuario")
    # orden.detalles -> líneas de la orden; se borran junto con la orden
    detalles = db.relationship(
        "DetalleOrdenCompra", back_populates="orden", cascade="all, delete-orphan"
    )

    def to_dict(self, con_detalles=True):
        datos = {
            "id": self.id,
            "codigo": self.codigo,
            "proveedor_id": self.proveedor_id,
            "proveedor": self.proveedor.razon_social,
            "usuario": f"{self.usuario.nombre} {self.usuario.apellido}",
            "fecha_orden": self.fecha_orden.isoformat() if self.fecha_orden else None,
            "fecha_entrega_estimada": (
                self.fecha_entrega_estimada.isoformat() if self.fecha_entrega_estimada else None
            ),
            "fecha_recepcion": self.fecha_recepcion.isoformat() if self.fecha_recepcion else None,
            "estado": self.estado,
            "total": float(self.total),
            "observaciones": self.observaciones,
        }
        if con_detalles:
            datos["detalles"] = [d.to_dict() for d in self.detalles]
        return datos


class DetalleOrdenCompra(db.Model):
    """ILF17 Una línea de la orden: qué insumo, cuánto y a qué precio."""

    __tablename__ = "detalle_orden_compra"

    id = db.Column(db.Integer, primary_key=True)
    orden_compra_id = db.Column(db.Integer, db.ForeignKey("ordenes_compra.id"), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), nullable=False)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)  # cantidad x precio_unitario

    orden = db.relationship("OrdenCompra", back_populates="detalles")
    insumo = db.relationship("Insumo")

    def to_dict(self):
        return {
            "insumo_id": self.insumo_id,
            "insumo": self.insumo.nombre,
            "unidad_medida": self.insumo.unidad_medida,
            "cantidad": float(self.cantidad),
            "precio_unitario": float(self.precio_unitario),
            "subtotal": float(self.subtotal),
        }