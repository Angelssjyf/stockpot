"""Servicio de pagos y ventas: cobra una orden y, cuando queda pagada, registra la venta.

Al cerrar la venta se descuenta del inventario lo que gastaron las recetas (RF-10.3),
dejando una SALIDA por CONSUMO por cada insumo. Todo ocurre en una sola transacción: si
algo falla (por ejemplo, no alcanza un insumo), no queda ni el pago ni la venta a medias.
"""

from collections import defaultdict
from decimal import Decimal

from ..extensions import db
from ..models import Consumo, Pago, Venta
from .inventario import registrar_movimiento

IMPOCONSUMO = Decimal("0.08")  # impuesto al consumo de restaurantes, incluido en los precios


class PagoRechazado(Exception):
    """El pago no se puede registrar. Lleva el mensaje y el código HTTP de la respuesta."""

    def __init__(self, mensaje, codigo=422):
        super().__init__(mensaje)
        self.codigo = codigo


def pagado(orden):
    return sum((p.monto for p in orden.pagos if p.estado == "APROBADO"), Decimal("0"))


def estado_pago(orden):
    """RF-09.4 PENDIENTE (nada pagado), PARCIAL (falta saldo) o PAGADO."""
    abonado = pagado(orden)
    if abonado <= 0:
        return "PENDIENTE"
    return "PAGADO" if abonado >= orden.total else "PARCIAL"


def cuenta(orden):
    """RF-09.3 Calcular el valor total del pedido y RF-09.4 su estado de pago."""
    impoconsumo = orden.subtotal - orden.subtotal / (1 + IMPOCONSUMO)
    abonado = pagado(orden)
    return {
        "orden_id": orden.id,
        "codigo": orden.codigo,
        "tipo": orden.tipo,
        "estado_orden": orden.estado,
        "fecha": orden.created_at.isoformat() if orden.created_at else None,
        "cliente": orden.cliente.to_dict() if orden.cliente else None,
        "estado_domicilio": orden.domicilio.estado if orden.domicilio else None,
        "productos": [d.to_dict() for d in orden.detalles],
        "subtotal": float(orden.subtotal),
        "impoconsumo_incluido": float(round(impoconsumo, 2)),
        "costo_envio": float(orden.domicilio.costo_envio) if orden.domicilio else 0.0,
        "total": float(orden.total),
        "pagado": float(abonado),
        "saldo": float(max(orden.total - abonado, Decimal("0"))),
        "estado_pago": estado_pago(orden),
        "pagos": [p.to_dict() for p in orden.pagos],
        "venta": orden.venta.codigo if orden.venta else None,
    }


def registrar_pago(orden, metodo, monto, usuario, recibido=None, referencia=None):
    """RF-09.1 Registrar un pago con RF-09.2 su método. Si completa el total, cierra la venta.

    No hace commit. Lanza PagoRechazado si algo no cuadra, y StockInsuficiente (del
    servicio de inventario) si al cerrar la venta no alcanza un insumo.
    """
    if orden.estado != "ABIERTA":
        raise PagoRechazado(f"La orden {orden.codigo} está {orden.estado}", 409)
    if metodo not in Pago.METODOS:
        raise PagoRechazado(f"Método de pago inválido. Opciones: {', '.join(Pago.METODOS)}")

    saldo = orden.total - pagado(orden)
    if monto <= 0:
        raise PagoRechazado("El monto debe ser mayor que cero")
    if monto > saldo:
        raise PagoRechazado(f"El monto supera el saldo pendiente (${saldo:,.0f})".replace(",", "."))

    cambio = Decimal("0")
    if metodo == "EFECTIVO":
        recibido = monto if recibido is None else recibido
        if recibido < monto:
            raise PagoRechazado("El efectivo recibido no alcanza para el monto")
        cambio = recibido - monto
    else:
        recibido = None  # con tarjeta o transferencia se paga exacto

    pago = Pago(orden=orden, metodo=metodo, monto=monto, recibido=recibido, cambio=cambio,
                referencia=referencia, usuario=usuario)
    db.session.add(pago)

    if monto == saldo:
        cerrar_venta(orden, usuario)
    return pago


def cerrar_venta(orden, usuario):
    """RF-10.1 Registrar la venta y RF-10.3 el consumo de insumos según las recetas."""
    venta = Venta(
        codigo=f"TMP-{orden.id}",  # temporal; el definitivo depende del id
        orden=orden,
        subtotal=orden.subtotal,
        costo_envio=orden.domicilio.costo_envio if orden.domicilio else 0,
        total=orden.total,
        usuario=usuario,
    )
    db.session.add(venta)
    db.session.flush()
    venta.codigo = f"VTA-{venta.id:06d}"

    # Lo que gastó cada insumo sumando todas las líneas (dos productos pueden compartirlo)
    gastado = defaultdict(Decimal)
    for detalle in orden.detalles:
        for linea in detalle.producto.receta:
            gastado[linea.insumo] += linea.cantidad * detalle.cantidad

    costo_total = Decimal("0")
    for insumo, cantidad in gastado.items():
        movimiento = registrar_movimiento(
            insumo, "SALIDA", "CONSUMO", cantidad, usuario.id,
            observacion=f"Venta {venta.codigo} (pedido {orden.codigo})",
        )
        venta.consumos.append(Consumo(insumo=insumo, cantidad=cantidad,
                                      costo_unitario=insumo.costo_unitario, movimiento=movimiento))
        costo_total += cantidad * insumo.costo_unitario

    venta.costo_insumos = costo_total.quantize(Decimal("0.01"))
    orden.estado = "CERRADA"
    return venta
