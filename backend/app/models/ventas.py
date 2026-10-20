"""Modelos de ILF14 Pagos, ILF15 Ventas e ILF16 Consumo (Iteración 4)."""

from ..extensions import db


def _fecha(valor):
    return valor.isoformat() if valor else None


class Pago(db.Model):
    """ILF14 Un pago (o abono) a la cuenta de una orden."""

    __tablename__ = "pagos"

    METODOS = ("EFECTIVO", "TARJETA", "TRANSFERENCIA")
    ESTADOS = ("APROBADO", "ANULADO")

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes.id"), nullable=False)
    metodo = db.Column(db.Enum(*METODOS, name="metodo_pago"), nullable=False)
    monto = db.Column(db.Numeric(14, 2), nullable=False)
    recibido = db.Column(db.Numeric(14, 2))
    cambio = db.Column(db.Numeric(14, 2), nullable=False, default=0, server_default="0")
    referencia = db.Column(db.String(60))
    estado = db.Column(db.Enum(*ESTADOS, name="estado_pago"), nullable=False,
                       default="APROBADO", server_default="APROBADO")
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    orden = db.relationship("Orden", backref=db.backref("pagos", order_by="Pago.id"))
    usuario = db.relationship("Usuario")

    def to_dict(self):
        return {
            "id": self.id,
            "orden_id": self.orden_id,
            "orden": self.orden.codigo,
            "metodo": self.metodo,
            "monto": float(self.monto),
            "recibido": float(self.recibido) if self.recibido is not None else None,
            "cambio": float(self.cambio),
            "referencia": self.referencia,
            "estado": self.estado,
            "usuario": f"{self.usuario.nombre} {self.usuario.apellido}",
            "fecha": _fecha(self.created_at),
        }


class Venta(db.Model):
    """ILF15 Venta: una orden pagada por completo."""

    __tablename__ = "ventas"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)  # VTA-000001
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes.id"), nullable=False, unique=True)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)
    costo_envio = db.Column(db.Numeric(12, 2), nullable=False, default=0, server_default="0")
    total = db.Column(db.Numeric(14, 2), nullable=False)
    costo_insumos = db.Column(db.Numeric(14, 2), nullable=False, default=0, server_default="0")
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    orden = db.relationship("Orden", backref=db.backref("venta", uselist=False))
    usuario = db.relationship("Usuario")
    consumos = db.relationship("Consumo", back_populates="venta", cascade="all, delete-orphan")

    def to_dict(self, completo=False):
        datos = {
            "id": self.id,
            "codigo": self.codigo,
            "fecha": _fecha(self.created_at),
            "orden_id": self.orden_id,
            "orden": self.orden.codigo,
            "tipo": self.orden.tipo,
            "cliente": self.orden.cliente.nombre if self.orden.cliente else None,
            "subtotal": float(self.subtotal),
            "costo_envio": float(self.costo_envio),
            "total": float(self.total),
            "costo_insumos": float(self.costo_insumos),
            "ganancia": float(self.subtotal - self.costo_insumos),  # el envío no es ganancia
            "usuario": f"{self.usuario.nombre} {self.usuario.apellido}",
        }
        if completo:
            datos["productos"] = [d.to_dict() for d in self.orden.detalles]  # RF-10.4
            datos["consumos"] = [c.to_dict() for c in self.consumos]          # RF-10.3
            datos["pagos"] = [p.to_dict() for p in self.orden.pagos if p.estado == "APROBADO"]
        return datos


class Consumo(db.Model):
    """ILF16 Insumo gastado en una venta (RF-10.3), con su costo de ese momento."""

    __tablename__ = "consumos"

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), nullable=False)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
    costo_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    movimiento_id = db.Column(db.Integer, db.ForeignKey("movimientos_inventario.id"),
                              nullable=False)

    venta = db.relationship("Venta", back_populates="consumos")
    insumo = db.relationship("Insumo")
    movimiento = db.relationship("MovimientoInventario")

    def to_dict(self):
        return {
            "insumo_id": self.insumo_id,
            "insumo": self.insumo.nombre,
            "unidad_medida": self.insumo.unidad_medida,
            "cantidad": float(self.cantidad),
            "costo": float(self.cantidad * self.costo_unitario),
        }
