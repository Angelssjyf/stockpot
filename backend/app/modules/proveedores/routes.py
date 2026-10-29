"""Módulo 2 - Gestión de proveedores (RF-02.1 a RF-02.5)."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ...extensions import db
from ...models import Insumo, OrdenCompra, Proveedor, ProveedorInsumo
from ...utils.auth import permiso_requerido

bp = Blueprint("proveedores", __name__)


def _texto(valor):
    """Convierte un valor recibido en texto sin espacios a los lados ('' si viene vacío)."""
    return str(valor if valor is not None else "").strip()


def _aplicar_datos(proveedor, data):
    """Valida los datos recibidos y los copia al proveedor.

    Devuelve (mensaje, código HTTP) si algo está mal, o None si todo está bien.
    Solo se tocan los campos que vienen en la petición.
    """
    if "nit" in data:
        nit = _texto(data["nit"])
        if not nit:
            return "El NIT no puede quedar vacío", 422
        otro = Proveedor.query.filter_by(nit=nit).first()
        if otro and otro.id != proveedor.id:
            return "Ya existe un proveedor con ese NIT", 409
        proveedor.nit = nit

    if "razon_social" in data:
        razon_social = _texto(data["razon_social"])
        if not razon_social:
            return "La razón social no puede quedar vacía", 422
        proveedor.razon_social = razon_social

    if "email" in data:
        email = _texto(data["email"]).lower()
        if email and "@" not in email:
            return "El correo no es válido", 422
        proveedor.email = email or None

    for campo in ("contacto", "telefono", "direccion"):
        if campo in data:
            setattr(proveedor, campo, _texto(data[campo]) or None)

    if "activo" in data:
        if not isinstance(data["activo"], bool):
            return "'activo' debe ser true o false", 422
        proveedor.activo = data["activo"]

    return None


def _con_insumos(proveedor):
    """Datos del proveedor más la lista de insumos que vende."""
    datos = proveedor.to_dict()
    datos["insumos"] = [pi.to_dict() for pi in proveedor.insumos]
    return datos


@bp.get("/proveedores")
@permiso_requerido("proveedores.ver")
def listar_proveedores():
    """RF-02.2 Consultar proveedores. Filtros opcionales: ?q= (razón social, NIT, contacto o
    RF-02.9 un insumo que vende), ?categoria= (RF-02.9, categoría de lo que vende) y
    ?activo=true|false. Cada proveedor trae sus categorías y, si la búsqueda dio con un
    insumo, cuáles de los que vende coinciden."""
    consulta = Proveedor.query

    texto = request.args.get("q", "").strip()
    patron = f"%{texto}%"
    if texto:
        consulta = consulta.filter(
            or_(
                Proveedor.razon_social.ilike(patron),
                Proveedor.nit.ilike(patron),
                Proveedor.contacto.ilike(patron),
                Proveedor.insumos.any(ProveedorInsumo.insumo.has(Insumo.nombre.ilike(patron))),
            )
        )

    categoria = request.args.get("categoria", "").strip().upper()
    if categoria:
        consulta = consulta.filter(
            Proveedor.insumos.any(ProveedorInsumo.insumo.has(Insumo.categoria == categoria))
        )

    activo = request.args.get("activo")
    if activo in ("true", "false"):
        consulta = consulta.filter(Proveedor.activo.is_(activo == "true"))

    proveedores = consulta.order_by(Proveedor.razon_social).all()
    buscado = texto.casefold()
    respuesta = []
    for proveedor in proveedores:
        datos = proveedor.to_dict()
        datos["categorias"] = sorted({pi.insumo.categoria for pi in proveedor.insumos})
        datos["coincidencias"] = sorted(
            pi.insumo.nombre for pi in proveedor.insumos
            if buscado and buscado in pi.insumo.nombre.casefold()
        )
        respuesta.append(datos)
    return jsonify(respuesta)


@bp.get("/proveedores/<int:proveedor_id>")
@permiso_requerido("proveedores.ver")
def obtener_proveedor(proveedor_id):
    """RF-02.2 Consultar el detalle de un proveedor, con los insumos que vende."""
    proveedor = db.session.get(Proveedor, proveedor_id)
    if proveedor is None:
        return jsonify(error="El proveedor no existe"), 404
    return jsonify(_con_insumos(proveedor))


@bp.post("/proveedores")
@permiso_requerido("proveedores.gestionar")
def crear_proveedor():
    """RF-02.1 Registrar proveedores."""
    data = request.get_json(silent=True) or {}

    faltantes = [campo for campo in ("nit", "razon_social") if not _texto(data.get(campo))]
    if faltantes:
        return jsonify(error="Faltan campos obligatorios", faltantes=faltantes), 422

    proveedor = Proveedor()
    error = _aplicar_datos(proveedor, data)
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]

    db.session.add(proveedor)
    db.session.commit()
    return jsonify(proveedor.to_dict()), 201


@bp.put("/proveedores/<int:proveedor_id>")
@permiso_requerido("proveedores.gestionar")
def modificar_proveedor(proveedor_id):
    """RF-02.3 Modificar información de proveedores (también activar o desactivar)."""
    proveedor = db.session.get(Proveedor, proveedor_id)
    if proveedor is None:
        return jsonify(error="El proveedor no existe"), 404

    error = _aplicar_datos(proveedor, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()  # no deja cambios a medias
        return jsonify(error=error[0]), error[1]

    db.session.commit()
    return jsonify(proveedor.to_dict())


@bp.put("/proveedores/<int:proveedor_id>/insumos")
@permiso_requerido("proveedores.gestionar")
def asignar_insumos(proveedor_id):
    """RF-02.4 Registrar productos suministrados: reemplaza la lista de insumos del proveedor.

    Body: {"insumos": [{"insumo_id": 1, "precio_referencia": 4200}, ...]}
    """
    proveedor = db.session.get(Proveedor, proveedor_id)
    if proveedor is None:
        return jsonify(error="El proveedor no existe"), 404

    items = (request.get_json(silent=True) or {}).get("insumos")
    if not isinstance(items, list):
        return jsonify(error="'insumos' debe ser una lista"), 422

    def rechazar(mensaje):
        """Deshace los cambios ya aplicados en memoria y responde con el error."""
        db.session.rollback()
        return jsonify(error=mensaje), 422

    actuales = {pi.insumo_id: pi for pi in proveedor.insumos}
    nueva_lista = []
    ids_vistos = set()  # para detectar insumos repetidos en la lista
    for item in items:
        insumo_id = item.get("insumo_id") if isinstance(item, dict) else None
        insumo = db.session.get(Insumo, insumo_id) if isinstance(insumo_id, int) else None
        if insumo is None or not insumo.activo:
            return rechazar(f"El insumo {insumo_id} no existe")
        if insumo.id in ids_vistos:
            return rechazar(f"El insumo '{insumo.nombre}' está repetido")
        ids_vistos.add(insumo.id)

        precio = item.get("precio_referencia")
        if precio is not None:
            try:
                precio = Decimal(str(precio))
            except InvalidOperation:
                return rechazar("El precio de referencia debe ser un número")
            if precio < 0:
                return rechazar("El precio de referencia no puede ser negativo")

        # Si el proveedor ya vendía ese insumo, se actualiza el precio; si no, se agrega
        relacion = actuales.get(insumo.id) or ProveedorInsumo(insumo=insumo)
        relacion.precio_referencia = precio
        nueva_lista.append(relacion)

    proveedor.insumos = nueva_lista  # los que ya no están en la lista se eliminan
    db.session.commit()
    return jsonify(_con_insumos(proveedor))


@bp.get("/proveedores/<int:proveedor_id>/compras")
@permiso_requerido("proveedores.ver", "compras.ver")
def historial_compras(proveedor_id):
    """RF-02.5 Consultar historial de compras: órdenes del proveedor, de la más reciente a
    la más antigua."""
    proveedor = db.session.get(Proveedor, proveedor_id)
    if proveedor is None:
        return jsonify(error="El proveedor no existe"), 404

    ordenes = (
        OrdenCompra.query.filter_by(proveedor_id=proveedor.id)
        .order_by(OrdenCompra.fecha_orden.desc(), OrdenCompra.id.desc())
        .all()
    )
    return jsonify([orden.to_dict(con_detalles=False) for orden in ordenes])