"""Servicio de inventario: TODO cambio de stock pasa por aquí.

Así cada entrada o salida deja un movimiento (ILF05) que explica el cambio, y la regla
"el stock nunca queda negativo" está en un solo lugar. Lo usan las entradas y salidas
manuales (RF-03.4 y RF-03.5), las compras recibidas (RF-02.8) y, más adelante, el
consumo automático por ventas (RF-03.9 y RF-10.3).
"""

from decimal import Decimal

from ..extensions import db
from ..models import MovimientoInventario


class StockInsuficiente(Exception):
    """Una salida dejaría el stock en negativo."""


def numero(valor):
    """Decimal('25.000') -> '25' y Decimal('40.500') -> '40.5' para mostrar en mensajes."""
    return format(Decimal(valor).normalize(), "f")


def registrar_movimiento(insumo, tipo, motivo, cantidad, usuario_id, orden_compra_id=None,
                         observacion=None):
    """Suma (ENTRADA) o resta (SALIDA) stock al insumo y guarda el movimiento.

    No hace commit: quien lo llama decide cuándo confirmar toda la operación.
    Lanza StockInsuficiente si una salida dejaría el stock en negativo.
    """
    cantidad = Decimal(str(cantidad))
    if tipo == "ENTRADA":
        nuevo_stock = insumo.stock_actual + cantidad
    else:
        nuevo_stock = insumo.stock_actual - cantidad
        if nuevo_stock < 0:
            raise StockInsuficiente(
                f"Stock insuficiente de '{insumo.nombre}': hay {numero(insumo.stock_actual)} "
                f"{insumo.unidad_medida} y se necesitan {numero(cantidad)}"
            )

    insumo.stock_actual = nuevo_stock
    movimiento = MovimientoInventario(
        insumo=insumo,
        tipo=tipo,
        motivo=motivo,
        cantidad=cantidad,
        stock_resultante=nuevo_stock,
        orden_compra_id=orden_compra_id,
        usuario_id=usuario_id,
        observacion=observacion,
    )
    db.session.add(movimiento)
    return movimiento
