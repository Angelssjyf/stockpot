"""Reúne todos los modelos para importarlos desde app.models."""

from .inventario import Insumo, MovimientoInventario
from .ordenes import Cliente, DetalleOrden, Domicilio, Orden
from .productos import Producto, Receta
from .proveedores import DetalleOrdenCompra, OrdenCompra, Proveedor, ProveedorInsumo
from .usuarios import Permiso, Rol, Usuario, rol_permisos
from .ventas import Consumo, Pago, Venta

__all__ = [
    "Cliente",
    "Consumo",
    "DetalleOrden",
    "DetalleOrdenCompra",
    "Domicilio",
    "Insumo",
    "MovimientoInventario",
    "Orden",
    "OrdenCompra",
    "Pago",
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
