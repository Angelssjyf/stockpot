"""Reúne todos los modelos para importarlos desde app.models."""

from .usuarios import Permiso, Rol, Usuario, rol_permisos

__all__ = ["Permiso", "Rol", "Usuario", "rol_permisos"]
