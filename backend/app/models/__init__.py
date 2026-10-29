"""Reúne todos los modelos para importarlos desde app.models."""

from .incidencias import CodigoIncidencia, Incidencia
from .inventario import Insumo, MovimientoInventario
from .ordenes import Cliente, DetalleOrden, Domicilio, Orden
from .pedidos import Mesa, PedidoMesa
from .productos import Producto, Receta
from .proveedores import DetalleOrdenCompra, OrdenCompra, Proveedor, ProveedorInsumo
from .usuarios import Permiso, Rol, Usuario, rol_permisos
from .ventas import Consumo, Pago, Venta

__all__ = [
    "Cliente",
    "CodigoIncidencia",
    "Consumo",
    "DetalleOrden",
    "DetalleOrdenCompra",
    "Incidencia",
    "Domicilio",
    "Insumo",
    "Mesa",
    "MovimientoInventario",
    "Orden",
    "OrdenCompra",
    "Pago",
    "PedidoMesa",
    "Permiso",
    "Producto",
    "Proveedor",
    "ProveedorInsumo",
    "Receta",
    "Rol",
    "Usuario",
    "Venta",
    "rol_permisos",
]
