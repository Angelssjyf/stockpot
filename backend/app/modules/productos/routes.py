"""Módulo 4 - Gestión de productos y menú (RF-04.1 a RF-04.6)."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ...extensions import db
from ...models import Insumo, Producto, Receta
from ...models.productos import CATEGORIAS
from ...utils.auth import permiso_requerido

bp = Blueprint("productos", __name__)

# Quienes toman o cobran pedidos también necesitan ver la carta
PERMISOS_VER = ("productos.ver", "pedidos.ver", "domicilios.ver", "ventas.ver")


def _texto(valor):
    """Convierte un valor recibido en texto sin espacios a los lados ('' si viene vacío)."""
    return str(valor if valor is not None else "").strip()


def _aplicar_datos(producto, data):
    """Valida los datos recibidos y los copia al producto.

    Devuelve (mensaje, código HTTP) si algo está mal, o None si todo está bien.
    Solo se tocan los campos que vienen en la petición.
    """
    if "codigo" in data:
        codigo = _texto(data["codigo"]).upper()
        if not codigo:
            return "El código no puede quedar vacío", 422
        otro = Producto.query.filter_by(codigo=codigo).first()
        if otro and otro.id != producto.id:
            return "Ya existe un producto con ese código", 409
        producto.codigo = codigo

    if "nombre" in data:
        nombre = _texto(data["nombre"])
        if not nombre:
            return "El nombre no puede quedar vacío", 422
        producto.nombre = nombre

    if "descripcion" in data:
        producto.descripcion = _texto(data["descripcion"]) or None

    if "categoria" in data:
        categoria = _texto(data["categoria"]).upper()
        if categoria not in CATEGORIAS:
            return f"Categoría inválida. Opciones: {', '.join(CATEGORIAS)}", 422
        producto.categoria = categoria

    # RF-04.5 Establecer precios de venta
    if "precio_venta" in data:
        try:
            precio = Decimal(str(data["precio_venta"]))
        except (InvalidOperation, ValueError):
            return "El precio de venta debe ser un número", 422
        if precio <= 0:
            return "El precio de venta debe ser mayor que cero", 422
        producto.precio_venta = precio

    # RF-04.6 Gestionar disponibilidad (y activo = sigue en la carta)
    for campo in ("disponible", "activo"):
        if campo in data:
            if not isinstance(data[campo], bool):
                return f"'{campo}' debe ser true o false", 422
            setattr(producto, campo, data[campo])

    if "receta" in data:
        return _aplicar_receta(producto, data["receta"])

    return None


def _aplicar_receta(producto, items):
    """RF-04.4 Asociar insumos a productos: reemplaza la receta completa.

    items: [{"insumo_id": 1, "cantidad": 0.25}, ...]  (cantidad por porción)
    """
    if not isinstance(items, list):
        return "'receta' debe ser una lista", 422

    actuales = {linea.insumo_id: linea for linea in producto.receta}
    nueva_receta = []
    ids_vistos = set()  # para detectar insumos repetidos
    for item in items:
        insumo_id = item.get("insumo_id") if isinstance(item, dict) else None
        insumo = db.session.get(Insumo, insumo_id) if isinstance(insumo_id, int) else None
        if insumo is None or not insumo.activo:
            return f"El insumo {insumo_id} no existe", 422
        if insumo.id in ids_vistos:
            return f"El insumo '{insumo.nombre}' está repetido en la receta", 422
        ids_vistos.add(insumo.id)

        try:
            cantidad = Decimal(str(item.get("cantidad")))
        except (InvalidOperation, ValueError):
            return f"La cantidad de '{insumo.nombre}' debe ser un número", 422
        if cantidad <= 0:
            return f"La cantidad de '{insumo.nombre}' debe ser mayor que cero", 422

        # Si el insumo ya estaba en la receta se actualiza la cantidad; si no, se agrega
        linea = actuales.get(insumo.id) or Receta(insumo=insumo)
        linea.cantidad = cantidad
        nueva_receta.append(linea)

    producto.receta = nueva_receta  # los insumos que ya no están se quitan
    return None


@bp.get("/productos")
@permiso_requerido(*PERMISOS_VER)
def listar_productos():
    """RF-04.2 Consultar productos y platos. Filtros opcionales: ?q= (código o nombre),
    ?categoria=BEBIDA y ?disponible=true (solo lo que hoy se puede pedir: la carta)."""
    consulta = Producto.query

    texto = request.args.get("q", "").strip()
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.filter(or_(Producto.codigo.ilike(patron), Producto.nombre.ilike(patron)))

    categoria = request.args.get("categoria", "").strip().upper()
    if categoria:
        consulta = consulta.filter(Producto.categoria == categoria)

    if request.args.get("disponible") == "true":
        consulta = consulta.filter(Producto.activo.is_(True), Producto.disponible.is_(True))

    productos = consulta.order_by(Producto.nombre).all()
    return jsonify([producto.to_dict() for producto in productos])


@bp.get("/productos/<int:producto_id>")
@permiso_requerido(*PERMISOS_VER)
def obtener_producto(producto_id):
    """RF-04.2 Consultar el detalle de un producto, con su receta y su costo."""
    producto = db.session.get(Producto, producto_id)
    if producto is None:
        return jsonify(error="El producto no existe"), 404
    return jsonify(producto.to_dict(con_receta=True))


@bp.post("/productos")
@permiso_requerido("productos.gestionar")
def crear_producto():
    """RF-04.1 Registrar productos y platos (con su receta si viene: RF-04.4)."""
    data = request.get_json(silent=True) or {}

    obligatorios = ("codigo", "nombre", "categoria", "precio_venta")
    faltantes = [campo for campo in obligatorios if not _texto(data.get(campo))]
    if faltantes:
        return jsonify(error="Faltan campos obligatorios", faltantes=faltantes), 422

    producto = Producto()
    error = _aplicar_datos(producto, data)
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]

    db.session.add(producto)
    db.session.commit()
    return jsonify(producto.to_dict(con_receta=True)), 201


@bp.put("/productos/<int:producto_id>")
@permiso_requerido("productos.gestionar")
def modificar_producto(producto_id):
    """RF-04.3 Modificar productos y platos: datos, precio (RF-04.5), disponibilidad
    (RF-04.6) y receta (RF-04.4)."""
    producto = db.session.get(Producto, producto_id)
    if producto is None:
        return jsonify(error="El producto no existe"), 404

    error = _aplicar_datos(producto, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()  # no deja cambios a medias
        return jsonify(error=error[0]), error[1]

    db.session.commit()
    return jsonify(producto.to_dict(con_receta=True))


@bp.patch("/productos/<int:producto_id>/disponibilidad")
@permiso_requerido("productos.gestionar", "cocina.gestionar")
def cambiar_disponibilidad(producto_id):
    """RF-04.6 Gestionar disponibilidad: marcar un plato como agotado o disponible hoy.
    También lo puede hacer la cocina cuando se le acaba algo.

    Body: {"disponible": false}
    """
    producto = db.session.get(Producto, producto_id)
    if producto is None:
        return jsonify(error="El producto no existe"), 404

    disponible = (request.get_json(silent=True) or {}).get("disponible")
    if not isinstance(disponible, bool):
        return jsonify(error="'disponible' debe ser true o false"), 422

    producto.disponible = disponible
    db.session.commit()
    return jsonify(producto.to_dict())
