"""Modelos de ILF12 Clientes, ILF09 Órdenes, ILF10 Detalle de órdenes e ILF13 Domicilios."""

from ..extensions import db


def _fecha(valor):
    return valor.isoformat() if valor else None


class Cliente(db.Model):
    """ILF12 Cliente que pide a domicilio (RF-08.2)."""

    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    barrio = db.Column(db.String(80))
    referencia = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "telefono": self.telefono,
            "email": self.email,
            "direccion": self.direccion,
            "barrio": self.barrio,
            "referencia": self.referencia,
        }


class Orden(db.Model):
    """ILF09 Encabezado de un pedido (a domicilio, en mesa o para llevar)."""

    __tablename__ = "ordenes"

    TIPOS = ("MESA", "DOMICILIO", "LLEVAR")
    ESTADOS = ("ABIERTA", "CERRADA", "CANCELADA")

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)  # PED-000001
    tipo = db.Column(db.Enum(*TIPOS, name="tipo_orden"), nullable=False)
    estado = db.Column(db.Enum(*ESTADOS, name="estado_orden"), nullable=False,
                       default="ABIERTA", server_default="ABIERTA")
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False, default=0, server_default="0")
    observaciones = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    cliente = db.relationship("Cliente")
    usuario = db.relationship("Usuario")
    detalles = db.relationship("DetalleOrden", back_populates="orden",
                               cascade="all, delete-orphan")
    domicilio = db.relationship("Domicilio", back_populates="orden", uselist=False)

    @property
    def total(self):
        """Lo que paga el cliente: productos más el envío si es a domicilio."""
        envio = self.domicilio.costo_envio if self.domicilio else 0
        return self.subtotal + envio

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "tipo": self.tipo,
            "estado": self.estado,
            "fecha": _fecha(self.created_at),
            "usuario": f"{self.usuario.nombre} {self.usuario.apellido}",
            "subtotal": float(self.subtotal),
            "total": float(self.total),
            "observaciones": self.observaciones,
            "detalles": [d.to_dict() for d in self.detalles],
        }


class DetalleOrden(db.Model):
    """ILF10 Un producto del pedido, con el precio que tenía al pedirlo."""

    __tablename__ = "detalle_ordenes"

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)
    observacion = db.Column(db.String(150))

    orden = db.relationship("Orden", back_populates="detalles")
    producto = db.relationship("Producto")

    def to_dict(self):
        return {
            "producto_id": self.producto_id,
            "producto": self.producto.nombre,
            "cantidad": self.cantidad,
            "precio_unitario": float(self.precio_unitario),
            "subtotal": float(self.subtotal),
            "observacion": self.observacion,
        }


class Domicilio(db.Model):
    """ILF13 Entrega a domicilio de una orden (RF-08.1 a RF-08.8)."""

    __tablename__ = "domicilios"

    ESTADOS = ("RECIBIDO", "EN_PREPARACION", "LISTO", "EN_CAMINO", "ENTREGADO", "CANCELADO")
    FINALES = ("ENTREGADO", "CANCELADO")

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes.id"), nullable=False, unique=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    barrio = db.Column(db.String(80))
    referencia = db.Column(db.String(200))
    telefono_contacto = db.Column(db.String(20), nullable=False)
    costo_envio = db.Column(db.Numeric(12, 2), nullable=False, default=0, server_default="0")
    estado = db.Column(db.Enum(*ESTADOS, name="estado_domicilio"), nullable=False,
                       default="RECIBIDO", server_default="RECIBIDO")
    domiciliario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    fecha_asignacion = db.Column(db.DateTime)
    fecha_salida = db.Column(db.DateTime)
    fecha_entrega = db.Column(db.DateTime)
    recibido_por = db.Column(db.String(120))
    observacion_entrega = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    orden = db.relationship("Orden", back_populates="domicilio")
    cliente = db.relationship("Cliente")
    domiciliario = db.relationship("Usuario")

    def to_dict(self, con_orden=True):
        datos = {
            "id": self.id,
            "codigo": self.orden.codigo,
            "estado": self.estado,
            "fecha": _fecha(self.created_at),
            "cliente": self.cliente.to_dict(),
            "direccion": self.direccion,
            "barrio": self.barrio,
            "referencia": self.referencia,
            "telefono_contacto": self.telefono_contacto,
            "costo_envio": float(self.costo_envio),
            "total": float(self.orden.total),
            "domiciliario_id": self.domiciliario_id,
            "domiciliario": (f"{self.domiciliario.nombre} {self.domiciliario.apellido}"
                             if self.domiciliario else None),
            "fecha_asignacion": _fecha(self.fecha_asignacion),
            "fecha_salida": _fecha(self.fecha_salida),
            "fecha_entrega": _fecha(self.fecha_entrega),
            "recibido_por": self.recibido_por,
            "observacion_entrega": self.observacion_entrega,
        }
        if con_orden:
            datos["orden"] = self.orden.to_dict()
        return datos
