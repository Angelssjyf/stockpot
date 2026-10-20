"""Modelos de ILF08 Mesas y de los pedidos en mesa, que completan ILF09 Pedidos (Iteración 3, RF-05.1 a RF-05.9)."""

from sqlalchemy.orm import backref

from ..extensions import db


def _fecha(valor):
    return valor.isoformat() if valor else None


class Mesa(db.Model):
    """ILF08 Mesa del restaurante (RF-05.2). Que esté ocupada no se guarda: se calcula a
    partir de sus pedidos abiertos, así nunca queda desactualizado."""

    __tablename__ = "mesas"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False, unique=True)
    capacidad = db.Column(db.Integer, nullable=False, default=4, server_default="4")
    ubicacion = db.Column(db.String(60))  # Salón, Terraza, Barra...
    activa = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @property
    def pedido_abierto(self):
        """El pedido que la mesa tiene sin cobrar ni cancelar, o None si está libre."""
        from .ordenes import Orden

        return (PedidoMesa.query.join(Orden)
                .filter(PedidoMesa.mesa_id == self.id, Orden.estado == "ABIERTA")
                .order_by(PedidoMesa.id.desc()).first())

    def to_dict(self, con_pedido=True):
        datos = {
            "id": self.id,
            "numero": self.numero,
            "capacidad": self.capacidad,
            "ubicacion": self.ubicacion,
            "activa": self.activa,
        }
        if con_pedido:
            pedido = self.pedido_abierto
            datos["ocupada"] = pedido is not None
            datos["pedido"] = pedido.resumen() if pedido else None
        return datos


class PedidoMesa(db.Model):
    """ILF09 (complemento) Pedido tomado en una mesa. Las líneas y el total viven en su orden (tipo MESA);
    aquí queda la mesa, los comensales y el recorrido del pedido.

    REGISTRADO -> CONFIRMADO -> EN_COCINA -> (cocina) EN_PREPARACION -> LISTO -> ENTREGADO
    En cualquier momento antes de ir a cocina puede pasar a CANCELADO.
    """

    __tablename__ = "pedidos_mesa"

    ESTADOS = ("REGISTRADO", "CONFIRMADO", "EN_COCINA", "EN_PREPARACION", "LISTO", "ENTREGADO",
               "CANCELADO")
    EDITABLES = ("REGISTRADO", "CONFIRMADO")  # después de ir a cocina ya no se modifica

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes.id"), nullable=False, unique=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey("mesas.id"), nullable=False)
    comensales = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    estado = db.Column(db.Enum(*ESTADOS, name="estado_pedido_mesa"), nullable=False,
                       default="REGISTRADO", server_default="REGISTRADO")
    fecha_confirmacion = db.Column(db.DateTime)  # RF-05.7
    fecha_envio_cocina = db.Column(db.DateTime)  # RF-05.8
    fecha_listo = db.Column(db.DateTime)         # RF-06 (Cocina)
    fecha_entrega = db.Column(db.DateTime)       # RF-06 (Cocina)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    orden = db.relationship("Orden", backref=backref("pedido_mesa", uselist=False))
    mesa = db.relationship("Mesa")

    @property
    def editable(self):
        return self.estado in self.EDITABLES and self.orden.estado == "ABIERTA"

    def linea_de_tiempo(self):
        """RF-05.9 Los pasos por los que ya pasó el pedido, con su hora."""
        pasos = [("REGISTRADO", self.orden.created_at), ("CONFIRMADO", self.fecha_confirmacion),
                 ("EN_COCINA", self.fecha_envio_cocina), ("LISTO", self.fecha_listo),
                 ("ENTREGADO", self.fecha_entrega)]
        return [{"estado": estado, "fecha": _fecha(fecha)} for estado, fecha in pasos if fecha]

    def resumen(self):
        """Lo que se muestra en la tarjeta de la mesa."""
        return {
            "id": self.id,
            "codigo": self.orden.codigo,
            "estado": self.estado,
            "total": float(self.orden.total),
            "productos": sum(d.cantidad for d in self.orden.detalles),
            "fecha": _fecha(self.orden.created_at),
        }

    def to_dict(self):
        orden = self.orden
        return {
            "id": self.id,
            "orden_id": orden.id,
            "codigo": orden.codigo,
            "estado": self.estado,
            "estado_orden": orden.estado,  # ABIERTA (sin cobrar), CERRADA (cobrada), CANCELADA
            "editable": self.editable,
            "mesa": self.mesa.to_dict(con_pedido=False),
            "comensales": self.comensales,
            "mesero": f"{orden.usuario.nombre} {orden.usuario.apellido}",
            "fecha": _fecha(orden.created_at),
            "fecha_confirmacion": _fecha(self.fecha_confirmacion),
            "fecha_envio_cocina": _fecha(self.fecha_envio_cocina),
            "observaciones": orden.observaciones,
            "subtotal": float(orden.subtotal),
            "total": float(orden.total),
            "detalles": [d.to_dict() for d in orden.detalles],
            "linea_de_tiempo": self.linea_de_tiempo(),
        }
