"""Reúne todos los modelos para importarlos desde app.models."""

from .inventario import Insumo, MovimientoInventario
from .ordenes import Cliente, DetalleOrden, Domicilio, Orden
from .productos import Producto, Receta
from .proveedores import DetalleOrdenCompra, OrdenCompra, Proveedor, ProveedorInsumo
from .usuarios import Permiso, Rol, Usuario, rol_permisos

__all__ = [
    "Cliente",
    "DetalleOrden",
    "DetalleOrdenCompra",
    "Domicilio",
    "Insumo",
    "MovimientoInventario",
    "Orden",
    "OrdenCompra",
    "Permiso",
    "Producto",
    "Proveedor",
    "ProveedorInsumo",
    "Receta",
    "Rol",
    "Usuario",
    "rol_permisos",
]
