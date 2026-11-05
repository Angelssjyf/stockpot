"""Módulo de empresas (tercer corte): el súper administrador crea y activa restaurantes.

Solo maneja los datos generales de cada restaurante; no ve su inventario, ventas ni pedidos.
"""

from flask import Blueprint, jsonify, request

from ...extensions import db
from ...models import Empresa, Usuario
from ...services.empresas import crear_empresa, resumen
from ...utils.auth import permiso_requerido

bp = Blueprint("empresas", __name__)

CAMPOS = ("nombre", "nit", "telefono", "email", "direccion")


def _texto(valor):
    return str(valor if valor is not None else "").strip()


def _leer_datos(data, empresa=None):
    """Valida los datos generales. Devuelve (datos, None) o (None, (mensaje, código))."""
    datos = {campo: _texto(data[campo]) or None for campo in CAMPOS if campo in data}
    if empresa is None or "nombre" in datos:
        if not datos.get("nombre"):
            return None, ("El nombre del restaurante es obligatorio", 422)
    if empresa is None or "nit" in datos:
        if not datos.get("nit"):
            return None, ("El NIT es obligatorio", 422)
        otra = Empresa.query.filter_by(nit=datos["nit"]).first()
        if otra and otra is not empresa:
            return None, ("Ya existe un restaurante con ese NIT", 409)
    if datos.get("email") and "@" not in datos["email"]:
        return None, ("El correo del restaurante no es válido", 422)
    return datos, None


@bp.get("/empresas")
@permiso_requerido("empresas.gestionar")
def listar_empresas():
    """Restaurantes con sus datos generales y cuántos usuarios tienen."""
    return jsonify([resumen(e) for e in Empresa.query.order_by(Empresa.nombre).all()])


@bp.post("/empresas")
@permiso_requerido("empresas.gestionar")
def registrar_empresa():
    """Crea un restaurante con sus roles y su administrador.

    Body: {"nombre": "...", "nit": "...", "telefono": "...", "email": "...", "direccion": "...",
           "admin": {"nombre": "...", "apellido": "...", "email": "...", "password": "..."}}
    """
    data = request.get_json(silent=True) or {}
    datos, error = _leer_datos(data)
    if error:
        return jsonify(error=error[0]), error[1]

    admin = data.get("admin") if isinstance(data.get("admin"), dict) else {}
    admin = {campo: _texto(admin.get(campo)) for campo in ("nombre", "apellido", "email", "password")}
    faltantes = [campo for campo, valor in admin.items() if not valor]
    if faltantes:
        return jsonify(error="Faltan datos del administrador", faltantes=faltantes), 422
    admin["email"] = admin["email"].lower()
    if "@" not in admin["email"]:
        return jsonify(error="El correo del administrador no es válido"), 422
    if len(admin["password"]) < 8:
        return jsonify(error="La contraseña del administrador debe tener al menos 8 caracteres"), 422
    if Usuario.query.execution_options(todas_las_empresas=True).filter_by(email=admin["email"]).first():
        return jsonify(error="Ya existe un usuario con ese correo"), 409

    empresa, _ = crear_empresa(datos, admin)
    db.session.commit()
    return jsonify(resumen(empresa)), 201


@bp.put("/empresas/<int:empresa_id>")
@permiso_requerido("empresas.gestionar")
def modificar_empresa(empresa_id):
    """Modifica los datos generales del restaurante (solo los campos que vienen)."""
    empresa = db.session.get(Empresa, empresa_id)
    if empresa is None:
        return jsonify(error="El restaurante no existe"), 404
    datos, error = _leer_datos(request.get_json(silent=True) or {}, empresa)
    if error:
        return jsonify(error=error[0]), error[1]
    for campo, valor in datos.items():
        setattr(empresa, campo, valor)
    db.session.commit()
    return jsonify(resumen(empresa))


@bp.patch("/empresas/<int:empresa_id>/estado")
@permiso_requerido("empresas.gestionar")
def cambiar_estado(empresa_id):
    """Activa o desactiva un restaurante. Desactivado, sus usuarios no pueden entrar ni seguir trabajando.

    Body: {"activa": false}
    """
    empresa = db.session.get(Empresa, empresa_id)
    if empresa is None:
        return jsonify(error="El restaurante no existe"), 404
    activa = (request.get_json(silent=True) or {}).get("activa")
    if not isinstance(activa, bool):
        return jsonify(error="'activa' debe ser true o false"), 422
    empresa.activa = activa
    db.session.commit()
    return jsonify(resumen(empresa))
