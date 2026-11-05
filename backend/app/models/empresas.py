"""Varios restaurantes en un mismo StockPot (tercer corte).

Cada restaurante es una Empresa y sus datos llevan empresa_id (la mezcla DeEmpresa). Para que
un restaurante nunca vea los datos de otro, el filtro se pone solo en cada consulta:

- permiso_requerido guarda en g.empresa_id la empresa del token (None para el súper administrador);
- antes de cada SELECT se agrega "empresa_id = la de la sesión" a todas las tablas DeEmpresa
  (el súper administrador solo ve las filas sin empresa: él mismo y su rol);
- antes de guardar, lo nuevo sin empresa queda en la empresa de la sesión.

Sin sesión de empresa (inicio de sesión, comandos de consola) no se filtra. Una consulta puede
saltarse el filtro a propósito con execution_options(todas_las_empresas=True).
"""

from flask import g, has_app_context
from sqlalchemy import event
from sqlalchemy.orm import Session, declared_attr, with_loader_criteria

from ..extensions import db


class Empresa(db.Model):
    """Un restaurante que usa StockPot. Lo administra el súper administrador."""

    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    nit = db.Column(db.String(20), nullable=False, unique=True)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    activa = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "nit": self.nit,
            "telefono": self.telefono,
            "email": self.email,
            "direccion": self.direccion,
            "activa": self.activa,
            "fecha": self.created_at.isoformat() if self.created_at else None,
        }


class DeEmpresa:
    """Mezcla para las tablas de un restaurante: cada fila pertenece a una empresa."""

    @declared_attr
    def empresa_id(cls):
        return db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)


def _empresa_de_la_sesion():
    """(True, id) si la petición es de una empresa (id None = súper administrador); (False, None) si no."""
    if has_app_context() and "empresa_id" in g:
        return True, g.empresa_id
    return False, None


@event.listens_for(Session, "do_orm_execute")
def _filtrar_por_empresa(estado):
    # Las cargas de una relación o de una columna parten de un objeto que ya pasó el filtro
    if (not estado.is_select or estado.is_column_load or estado.is_relationship_load
            or estado.execution_options.get("todas_las_empresas")):
        return
    hay_sesion, empresa_id = _empresa_de_la_sesion()
    if not hay_sesion:
        return
    if empresa_id is None:
        criterio = with_loader_criteria(DeEmpresa, lambda cls: cls.empresa_id.is_(None), include_aliases=True)
    else:
        criterio = with_loader_criteria(DeEmpresa, lambda cls: cls.empresa_id == empresa_id,
                                        include_aliases=True)
    estado.statement = estado.statement.options(criterio)


@event.listens_for(Session, "before_flush")
def _asignar_empresa(sesion, contexto, instancias):
    hay_sesion, empresa_id = _empresa_de_la_sesion()
    if not hay_sesion or empresa_id is None:
        return
    for objeto in sesion.new:
        if isinstance(objeto, DeEmpresa) and objeto.empresa_id is None:
            objeto.empresa_id = empresa_id
