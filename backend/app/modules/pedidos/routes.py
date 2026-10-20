"""Módulo 5 - Gestión de pedidos en mesa (RF-05.1 a RF-05.9), con sus mesas."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from flask import Blueprint, jsonify, request

from ...extensions import db
from ...models import Mesa, Orden, PedidoMesa
from ...services.ordenes import armar_detalles, faltantes, leer_items
from ...utils.auth import permiso_requerido, usuario_actual
from ...utils.fechas import filtrar_por_fechas

bp = Blueprint("pedidos", __name__)


def _texto(valor):
    """Convierte un valor recibido en texto sin espacios a los lados ('' si viene vacío)."""
    return str(valor if valor is not None else "").strip()


def _entero(valor, campo, minimo=1, maximo=None):
    """Devuelve (entero, None) o (None, mensaje de error)."""
    if not isinstance(valor, int) or isinstance(valor, bool) or valor < minimo:
        return None, f"{campo} debe ser un número entero mayor o igual a {minimo}"
    if maximo is not None and valor > maximo:
        return None, f"{campo} no puede ser mayor que {maximo}"
    return valor, None


def _buscar_pedido(pedido_id):
    pedido = db.session.get(PedidoMesa, pedido_id)
    if pedido is None:
        return None, (jsonify(error="El pedido no existe"), 404)
    return pedido, None


# =====================================================================
#  Mesas (base de RF-05.2): el salón del restaurante
# =====================================================================


def _aplicar_mesa(mesa, data):
    """Valida y copia los datos de la mesa. Devuelve (mensaje, código) o None."""
    if "numero" in data or mesa.numero is None:
        numero, error = _entero(data.get("numero"), "El número de la mesa", maximo=999)
        if error:
            return error, 422
        otra = Mesa.query.filter_by(numero=numero).first()
        if otra and otra.id != mesa.id:
            return f"Ya existe la mesa {numero}", 409
        mesa.numero = numero

    if "capacidad" in data or mesa.capacidad is None:
        capacidad, error = _entero(data.get("capacidad", 4), "La capacidad", maximo=30)
        if error:
            return error, 422
        mesa.capacidad = capacidad

    if "ubicacion" in data:
        mesa.ubicacion = _texto(data["ubicacion"])[:60] or None

    if "activa" in data:
        if not isinstance(data["activa"], bool):
            return "El campo activa debe ser verdadero o falso", 422
        if not data["activa"] and mesa.id and mesa.pedido_abierto:
            return f"La mesa {mesa.numero} tiene un pedido abierto; no se puede desactivar", 409
        mesa.activa = data["activa"]
    return None


@bp.get("/mesas")
@permiso_requerido("pedidos.ver")
def listar_mesas():
    """Mesas activas con su estado (libre u ocupada) y el pedido abierto que tienen.
    ?todas=true incluye las inactivas."""
    consulta = Mesa.query
    if request.args.get("todas") != "true":
        consulta = consulta.filter_by(activa=True)
    return jsonify([m.to_dict() for m in consulta.order_by(Mesa.numero).all()])


@bp.post("/mesas")
@permiso_requerido("pedidos.gestionar")
def crear_mesa():
    """Agregar una mesa. Body: {"numero": 9, "capacidad": 4, "ubicacion": "Terraza"}"""
    mesa = Mesa(numero=None, capacidad=None)
    error = _aplicar_mesa(mesa, request.get_json(silent=True) or {})
    if error:
        return jsonify(error=error[0]), error[1]
    db.session.add(mesa)
    db.session.commit()
    return jsonify(mesa.to_dict()), 201


@bp.put("/mesas/<int:mesa_id>")
@permiso_requerido("pedidos.gestionar")
def modificar_mesa(mesa_id):
    """Cambiar número, capacidad, ubicación o desactivar una mesa (si no tiene pedido abierto)."""
    mesa = db.session.get(Mesa, mesa_id)
    if mesa is None:
        return jsonify(error="La mesa no existe"), 404
    error = _aplicar_mesa(mesa, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]
    db.session.commit()
    return jsonify(mesa.to_dict())


# =====================================================================
#  RF-05.6 Validar disponibilidad de insumos
# =====================================================================


@bp.post("/pedidos/disponibilidad")
@permiso_requerido("pedidos.ver")
def validar_disponibilidad():
    """RF-05.6 Revisa si el inventario alcanza para los productos, sin guardar nada.

    Body: {"items": [{"producto_id": 1, "cantidad": 2}, ...]}
    Responde: {"disponible": true/false, "subtotal": 44000, "faltantes": [{insumo, hay, necesita,
    falta, unidad_medida}, ...]} con TODOS los insumos que no alcanzan.
    """
    lineas, necesario, error = leer_items((request.get_json(silent=True) or {}).get("items"))
    if error:
        return jsonify(error=error[0]), error[1]
    lista = faltantes(necesario)
    subtotal = sum((producto.precio_venta * cantidad for producto, cantidad, _ in lineas), Decimal("0"))
    return jsonify(disponible=not lista, subtotal=float(subtotal), faltantes=lista)


# =====================================================================
#  RF-05.1 Registrar pedidos, RF-05.2 asociarlos a una mesa y RF-05.3 sus productos
# =====================================================================


def _aplicar_mesa_y_comensales(pedido, data):
    """RF-05.2 Valida la mesa (activa y libre) y los comensales. Devuelve (mensaje, código) o None."""
    if "mesa_id" in data or pedido.mesa is None:
        mesa = db.session.get(Mesa, data.get("mesa_id")) if isinstance(data.get("mesa_id"), int) else None
        if mesa is None or not mesa.activa:
            return "La mesa no existe", 422
        abierto = mesa.pedido_abierto
        if abierto and abierto.id != pedido.id:
            return f"La mesa {mesa.numero} ya tiene el pedido {abierto.orden.codigo}", 409
        pedido.mesa = mesa

    if "comensales" in data or pedido.comensales is None:
        comensales, error = _entero(data.get("comensales", 1), "Los comensales")
        if error:
            return error, 422
        if comensales > pedido.mesa.capacidad:
            return f"La mesa {pedido.mesa.numero} es para {pedido.mesa.capacidad} personas", 422
        pedido.comensales = comensales
    elif pedido.comensales > pedido.mesa.capacidad:
        return f"La mesa {pedido.mesa.numero} es para {pedido.mesa.capacidad} personas", 422
    return None


@bp.post("/pedidos")
@permiso_requerido("pedidos.gestionar")
def registrar_pedido():
    """RF-05.1 Registrar un pedido en mesa, RF-05.2 asociado a su mesa y RF-05.3 con sus
    productos. RF-05.6 Si el inventario no alcanza para todo el pedido, no se registra.

    Body: {"mesa_id": 3, "comensales": 2, "observaciones": "...",
           "items": [{"producto_id": 1, "cantidad": 2, "observacion": "sin cebolla"}, ...]}
    """
    data = request.get_json(silent=True) or {}
    orden = Orden(
        codigo=uuid4().hex[:20],  # código temporal; el definitivo depende del id
        tipo="MESA",
        usuario=usuario_actual(),
        observaciones=_texto(data.get("observaciones"))[:255] or None,
    )
    pedido = PedidoMesa(orden=orden, comensales=None)

    error = _aplicar_mesa_y_comensales(pedido, data) or armar_detalles(orden, data.get("items"))
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]

    db.session.add_all([orden, pedido])
    db.session.flush()  # MySQL asigna el id sin terminar la transacción
    orden.codigo = f"PED-{orden.id:06d}"
    db.session.commit()
    return jsonify(pedido.to_dict()), 201


# =====================================================================
#  RF-05.5 Consultar pedidos
# =====================================================================


@bp.get("/pedidos")
@permiso_requerido("pedidos.ver")
def listar_pedidos():
    """RF-05.5 Consultar pedidos en mesa, del más antiguo al más reciente.

    Por defecto, los activos (sin cobrar). ?vista=historial muestra todos, del más reciente al
    más antiguo, con ?desde=AAAA-MM-DD&hasta=AAAA-MM-DD. Filtros: ?estado=EN_COCINA&mesa_id=3&q=PED-12
    """
    consulta = PedidoMesa.query.join(Orden)
    historial = request.args.get("vista") == "historial"
    if historial:
        try:
            consulta = filtrar_por_fechas(consulta, Orden.created_at, request.args)
        except ValueError:
            return jsonify(error="Las fechas deben tener el formato AAAA-MM-DD"), 422
    else:
        consulta = consulta.filter(Orden.estado == "ABIERTA")

    estado = _texto(request.args.get("estado")).upper()
    if estado:
        if estado not in PedidoMesa.ESTADOS:
            return jsonify(error=f"Estado inválido. Opciones: {', '.join(PedidoMesa.ESTADOS)}"), 422
        consulta = consulta.filter(PedidoMesa.estado == estado)
    mesa_id = request.args.get("mesa_id", type=int)
    if mesa_id:
        consulta = consulta.filter(PedidoMesa.mesa_id == mesa_id)
    texto = _texto(request.args.get("q"))
    if texto:
        consulta = consulta.filter(Orden.codigo.ilike(f"%{texto}%"))

    if historial:
        consulta = consulta.order_by(Orden.created_at.desc(), Orden.id.desc()).limit(200)
    else:
        consulta = consulta.order_by(Orden.created_at, Orden.id)
    return jsonify([p.to_dict() for p in consulta.all()])


@bp.get("/pedidos/<int:pedido_id>")
@permiso_requerido("pedidos.ver")
def obtener_pedido(pedido_id):
    """RF-05.5 Detalle de un pedido: mesa, mesero, productos, total y recorrido."""
    pedido, error = _buscar_pedido(pedido_id)
    if error:
        return error
    return jsonify(pedido.to_dict())


# =====================================================================
#  RF-05.4 Modificar pedidos y RF-05.3 agregar productos
# =====================================================================


def _items_actuales(orden):
    return [{"producto_id": d.producto_id, "cantidad": d.cantidad, "observacion": d.observacion}
            for d in orden.detalles]


def _rehacer_lineas(orden, items):
    """Reemplaza las líneas del pedido revisando carta e inventario. Devuelve error o None."""
    orden.detalles.clear()  # las líneas viejas se borran (delete-orphan)
    return armar_detalles(orden, items)


def _volver_a_registrado(pedido):
    """Si un pedido confirmado cambia, hay que confirmarlo otra vez (RF-05.7)."""
    if pedido.estado == "CONFIRMADO":
        pedido.estado = "REGISTRADO"
        pedido.fecha_confirmacion = None


def _no_editable(pedido):
    if pedido.orden.estado != "ABIERTA":
        return jsonify(error=f"El pedido {pedido.orden.codigo} ya está "
                             f"{'cobrado' if pedido.orden.estado == 'CERRADA' else 'cancelado'}"), 409
    return jsonify(error=f"El pedido {pedido.orden.codigo} ya está en cocina; no se puede modificar"), 409


@bp.put("/pedidos/<int:pedido_id>")
@permiso_requerido("pedidos.gestionar")
def modificar_pedido(pedido_id):
    """RF-05.4 Modificar un pedido que aún no va para cocina: mesa, comensales, observaciones
    y productos (si llegan "items", reemplazan a los actuales). Un pedido CONFIRMADO que se
    modifica vuelve a REGISTRADO para confirmarlo otra vez.

    Body (todo opcional): {"mesa_id": 4, "comensales": 3, "observaciones": "...", "items": [...]}
    """
    pedido, error = _buscar_pedido(pedido_id)
    if error:
        return error
    if not pedido.editable:
        return _no_editable(pedido)

    data = request.get_json(silent=True) or {}
    error = _aplicar_mesa_y_comensales(pedido, data)
    if not error and "items" in data:
        error = _rehacer_lineas(pedido.orden, data["items"])
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]
    if "observaciones" in data:
        pedido.orden.observaciones = _texto(data["observaciones"])[:255] or None

    _volver_a_registrado(pedido)
    db.session.commit()
    return jsonify(pedido.to_dict())


@bp.post("/pedidos/<int:pedido_id>/productos")
@permiso_requerido("pedidos.gestionar")
def agregar_productos(pedido_id):
    """RF-05.3 Agregar productos a un pedido que aún no va para cocina. Si el producto ya está
    con la misma observación, se suma la cantidad. RF-05.6 El inventario debe alcanzar para
    TODO el pedido (lo que ya tenía más lo nuevo).

    Body: {"items": [{"producto_id": 6, "cantidad": 1}, ...]}
    """
    pedido, error = _buscar_pedido(pedido_id)
    if error:
        return error
    if not pedido.editable:
        return _no_editable(pedido)

    nuevos = (request.get_json(silent=True) or {}).get("items")
    _, _, error = leer_items(nuevos)  # primero se validan solos, para dar un mensaje claro
    if error:
        return jsonify(error=error[0]), error[1]

    items = _items_actuales(pedido.orden)
    for nuevo in nuevos:
        observacion = _texto(nuevo.get("observacion")) or None
        igual = next((i for i in items if i["producto_id"] == nuevo["producto_id"]
                      and i["observacion"] == observacion), None)
        if igual:
            igual["cantidad"] += nuevo["cantidad"]
        else:
            items.append({"producto_id": nuevo["producto_id"], "cantidad": nuevo["cantidad"],
                          "observacion": observacion})

    error = _rehacer_lineas(pedido.orden, items)
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]
    _volver_a_registrado(pedido)
    db.session.commit()
    return jsonify(pedido.to_dict())


# =====================================================================
#  RF-05.7 Confirmar pedidos y RF-05.8 enviarlos a cocina
# =====================================================================


@bp.patch("/pedidos/<int:pedido_id>/confirmar")
@permiso_requerido("pedidos.gestionar")
def confirmar_pedido(pedido_id):
    """RF-05.7 Confirmar el pedido con el cliente: REGISTRADO -> CONFIRMADO. Se vuelve a
    revisar el inventario (RF-05.6), porque pudo cambiar desde que se registró."""
    pedido, error = _buscar_pedido(pedido_id)
    if error:
        return error
    if pedido.estado != "REGISTRADO" or pedido.orden.estado != "ABIERTA":
        return jsonify(error=f"Un pedido {pedido.estado} no se puede confirmar"), 409

    _, necesario, error = leer_items(_items_actuales(pedido.orden))
    if error:
        return jsonify(error=error[0]), error[1]
    lista = faltantes(necesario)
    if lista:
        f = lista[0]
        return jsonify(error=f"No alcanza '{f['insumo']}' para este pedido", faltantes=lista), 409

    pedido.estado = "CONFIRMADO"
    pedido.fecha_confirmacion = datetime.now()
    db.session.commit()
    return jsonify(pedido.to_dict())


@bp.patch("/pedidos/<int:pedido_id>/enviar-cocina")
@permiso_requerido("pedidos.gestionar")
def enviar_a_cocina(pedido_id):
    """RF-05.8 Enviar a cocina un pedido confirmado: CONFIRMADO -> EN_COCINA. Desde aquí ya no
    se modifica; la cocina (RF-06) lo prepara."""
    pedido, error = _buscar_pedido(pedido_id)
    if error:
        return error
    if pedido.estado == "REGISTRADO":
        return jsonify(error="Primero confirma el pedido con el cliente"), 409
    if pedido.estado != "CONFIRMADO" or pedido.orden.estado == "CANCELADA":
        return jsonify(error=f"Un pedido {pedido.estado} no se puede enviar a cocina"), 409

    pedido.estado = "EN_COCINA"
    pedido.fecha_envio_cocina = datetime.now()
    db.session.commit()
    return jsonify(pedido.to_dict())


@bp.get("/pedidos/<int:pedido_id>/comanda")
@permiso_requerido("pedidos.ver")
def comanda(pedido_id):
    """RF-05.8 La comanda para la cocina: mesa, hora y productos con sus observaciones (sin
    precios). Solo existe cuando el pedido ya se envió a cocina."""
    pedido, error = _buscar_pedido(pedido_id)
    if error:
        return error
    if pedido.fecha_envio_cocina is None:
        return jsonify(error="El pedido todavía no se ha enviado a cocina"), 409
    orden = pedido.orden
    return jsonify(
        codigo=orden.codigo,
        mesa=pedido.mesa.numero,
        comensales=pedido.comensales,
        mesero=f"{orden.usuario.nombre} {orden.usuario.apellido}",
        enviado=pedido.fecha_envio_cocina.isoformat(),
        observaciones=orden.observaciones,
        productos=[{"cantidad": d.cantidad, "producto": d.producto.nombre, "observacion": d.observacion}
                   for d in orden.detalles],
    )


# =====================================================================
#  RF-05.9 Consultar estado del pedido, y cancelación
# =====================================================================


@bp.get("/pedidos/<int:pedido_id>/estado")
@permiso_requerido("pedidos.ver")
def estado_pedido(pedido_id):
    """RF-05.9 Estado actual del pedido, cuánto lleva y los pasos por los que ya pasó."""
    pedido, error = _buscar_pedido(pedido_id)
    if error:
        return error
    minutos = int((datetime.now() - pedido.orden.created_at).total_seconds() // 60)
    return jsonify(
        codigo=pedido.orden.codigo,
        mesa=pedido.mesa.numero,
        estado=pedido.estado,
        cobrado=pedido.orden.estado == "CERRADA",
        minutos=max(minutos, 0),
        linea_de_tiempo=pedido.linea_de_tiempo(),
    )


@bp.patch("/pedidos/<int:pedido_id>/cancelar")
@permiso_requerido("pedidos.gestionar")
def cancelar_pedido(pedido_id):
    """Cancelar un pedido que aún no va para cocina y no tiene pagos. La mesa queda libre.
    Body opcional: {"motivo": "El cliente se fue"}"""
    pedido, error = _buscar_pedido(pedido_id)
    if error:
        return error
    if not pedido.editable:
        return _no_editable(pedido)
    if any(p.estado == "APROBADO" for p in pedido.orden.pagos):
        return jsonify(error="El pedido tiene pagos; anúlalos en la caja antes de cancelarlo"), 409

    motivo = _texto((request.get_json(silent=True) or {}).get("motivo"))
    if motivo:
        anteriores = pedido.orden.observaciones
        pedido.orden.observaciones = (f"{anteriores} · " if anteriores else "")[:120] + f"Cancelado: {motivo}"[:130]
    pedido.estado = "CANCELADO"
    pedido.orden.estado = "CANCELADA"
    db.session.commit()
    return jsonify(pedido.to_dict())
