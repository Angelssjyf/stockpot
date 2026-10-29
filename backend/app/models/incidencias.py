"""Modelos de ILF10 Códigos de incidencia e ILF11 Incidencias (RF-12, sugerencia de la sustentación)."""

from ..extensions import db

MODULOS_INCIDENCIA = ("INVENTARIO", "VENTAS", "COMPRAS", "OTRO")


class CodigoIncidencia(db.Model):
    """RF-12.1 Un tipo de error del catálogo (INV-01, VEN-02...). OTRO sirve para cualquier registro."""

    __tablename__ = "codigos_incidencia"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), nullable=False, unique=True)
    modulo = db.Column(db.Enum(*MODULOS_INCIDENCIA, name="modulo_incidencia"), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    # Si es true, al reportar se indica la cantidad real y el sistema hace el ajuste de inventario
    corrige_stock = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "modulo": self.modulo,
            "nombre": self.nombre,
            "corrige_stock": self.corrige_stock,
            "activo": self.activo,
        }


class Incidencia(db.Model):
    """RF-12.2 Un error reportado sobre un registro: quién lo cometió, quién lo reportó y qué pasó."""

    __tablename__ = "incidencias"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)  # INC-000001
    codigo_incidencia_id = db.Column(db.Integer, db.ForeignKey("codigos_incidencia.id"), nullable=False)
    # El registro con el error: solo uno de los tres
    movimiento_id = db.Column(db.Integer, db.ForeignKey("movimientos_inventario.id"))
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"))
    orden_compra_id = db.Column(db.Integer, db.ForeignKey("ordenes_compra.id"))
    responsable_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)  # quien hizo el registro
    reportado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    observacion = db.Column(db.String(500), nullable=False)
    # RF-12.3 Corrección de inventario: lo que se registró, lo real y el ajuste que lo arregló
    cantidad_registrada = db.Column(db.Numeric(12, 3))
    cantidad_real = db.Column(db.Numeric(12, 3))
    ajuste_id = db.Column(db.Integer, db.ForeignKey("movimientos_inventario.id"))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    tipo = db.relationship("CodigoIncidencia")
    movimiento = db.relationship("MovimientoInventario", foreign_keys=[movimiento_id])
    ajuste = db.relationship("MovimientoInventario", foreign_keys=[ajuste_id])
    venta = db.relationship("Venta")
    orden_compra = db.relationship("OrdenCompra")
    responsable = db.relationship("Usuario", foreign_keys=[responsable_id])
    reportado_por = db.relationship("Usuario", foreign_keys=[reportado_por_id])

    @property
    def registro(self):
        """Texto corto del registro con el error, para la bitácora."""
        if self.movimiento:
            m = self.movimiento
            return f"{m.tipo.capitalize()} de {float(m.cantidad):g} {m.insumo.unidad_medida} de {m.insumo.nombre}"
        if self.venta:
            return f"Venta {self.venta.codigo}"
        if self.orden_compra:
            return f"Orden {self.orden_compra.codigo}"
        return "—"

    def to_dict(self):
        nombre = lambda u: f"{u.nombre} {u.apellido}"  # noqa: E731
        return {
            "id": self.id,
            "codigo": self.codigo,
            "fecha": self.created_at.isoformat() if self.created_at else None,
            "tipo": self.tipo.to_dict(),
            "registro": self.registro,
            "movimiento_id": self.movimiento_id,
            "venta_id": self.venta_id,
            "orden_compra_id": self.orden_compra_id,
            "responsable_id": self.responsable_id,
            "responsable": nombre(self.responsable),
            "reportado_por": nombre(self.reportado_por),
            "observacion": self.observacion,
            "cantidad_registrada": float(self.cantidad_registrada) if self.cantidad_registrada is not None else None,
            "cantidad_real": float(self.cantidad_real) if self.cantidad_real is not None else None,
            "ajuste": (
                {"id": self.ajuste.id, "tipo": self.ajuste.tipo, "cantidad": float(self.ajuste.cantidad)}
                if self.ajuste else None
            ),
        }
