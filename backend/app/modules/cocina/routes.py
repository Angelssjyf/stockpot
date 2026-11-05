"""Módulo 6 - Cocina (RF-06.1 a RF-06.7).

La cocina recibe los pedidos de las mesas (cuando el mesero los envía, RF-05.8) y los domicilios
(desde que se registran), los ve en orden de llegada y les cambia el estado mientras los prepara:

    Mesa:      EN_COCINA -> EN_PREPARACION -> LISTO -> ENTREGADO (lo marca el mesero o la cocina)
    Domicilio: RECIBIDO  -> EN_PREPARACION -> LISTO (de ahí sigue el módulo de domicilios)
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from ...extensions import db
from ...models import Domicilio, Orden, PedidoMesa
from ...utils.auth import permiso_requerido, tiene_permiso

bp = Blueprint("cocina", __name__)

# Estado actual -> siguiente estado en cocina
SIGUIENTE = {
    "MESA": {"EN_COCINA": "EN_PREPARACION", "EN_PREPARACION": "LISTO", "LISTO": "ENTREGADO"},
    "DOMICILIO": {"RECIBIDO": "EN_PREPARACION", "EN_PREPARACION": "LISTO"},
}
PENDIENTES = {"MESA": ("EN_COCINA", "EN_PREPARACION", "LISTO"),
              "DOMICILIO": ("RECIBIDO", "EN_PREPARACION", "LISTO")}
COLUMNA = {"EN_COCINA": "POR_PREPARAR", "RECIBIDO": "POR_PREPARAR", "EN_PREPARACION": "PREPARANDO", "LISTO": "LISTO"}


def _minutos(desde):
    return max(int((datetime.now() - desde).total_seconds() // 60), 0) if desde else 0


def _productos(orden):
    return [{"cantidad": d.cantidad, "producto": d.producto.nombre, "observacion": d.observacion}
            for d in orden.detalles]


def _de_mesa(pedido):
    llegada = pedido.fecha_envio_cocina or pedido.orden.created_at
    return {
        "tipo": "MESA", "id": pedido.id, "codigo": pedido.orden.codigo,
        "origen": f"Mesa {pedido.mesa.numero}", "detalle": f"{pedido.comensales} comensales",
        "estado": pedido.estado, "columna": COLUMNA.get(pedido.estado), "siguiente": SIGUIENTE["MESA"].get(pedido.estado),
        "llegada": llegada.isoformat(), "minutos": _minutos(llegada),
        "listo": pedido.fecha_listo.isoformat() if pedido.fecha_listo else None,
        "observaciones": pedido.orden.observaciones, "productos": _productos(pedido.orden),
    }


def _de_domicilio(domicilio):
    llegada = domicilio.orden.created_at
    return {
        "tipo": "DOMICILIO", "id": domicilio.id, "codigo": domicilio.orden.codigo,
        "origen": "Domicilio", "detalle": domicilio.barrio or domicilio.direccion,
        "estado": domicilio.estado, "columna": COLUMNA.get(domicilio.estado),
        "siguiente": SIGUIENTE["DOMICILIO"].get(domicilio.estado),
        "llegada": llegada.isoformat(), "minutos": _minutos(llegada), "listo": None,
        "observaciones": domicilio.orden.observaciones, "productos": _productos(domicilio.orden),
    }


@bp.get("/cocina/ordenes")
@permiso_requerido("cocina.ver")
def ordenes_pendientes():
    """RF-06.1 Recibir órdenes, RF-06.2 visualizar las pendientes y RF-06.3 organizarlas por llegada
    (la que lleva más tiempo esperando va primero). Los domicilios entran igual que las mesas."""
    pedidos = (PedidoMesa.query.join(Orden).filter(PedidoMesa.estado.in_(PENDIENTES["MESA"]),
                                                   Orden.estado != "CANCELADA").all())
    domicilios = (Domicilio.query.join(Orden).filter(Domicilio.estado.in_(PENDIENTES["DOMICILIO"]),
                                                     Orden.estado != "CANCELADA").all())
    ordenes = sorted([_de_mesa(p) for p in pedidos] + [_de_domicilio(d) for d in domicilios],
                     key=lambda o: (o["llegada"], o["codigo"]))
    resumen = {columna: sum(1 for o in ordenes if o["columna"] == columna)
               for columna in ("POR_PREPARAR", "PREPARANDO", "LISTO")}
    espera = [o["minutos"] for o in ordenes if o["columna"] != "LISTO"]
    resumen["espera_maxima"] = max(espera, default=0)
    return jsonify(resumen=resumen, ordenes=ordenes, hora=datetime.now().isoformat())


@bp.patch("/cocina/ordenes/<tipo>/<int:orden_id>/estado")
@permiso_requerido("cocina.gestionar", "pedidos.gestionar")
def cambiar_estado(tipo, orden_id):
    """RF-06.4 Actualizar el estado de preparación, RF-06.5 marcar como preparado (LISTO) y
    RF-06.6 marcar como entregado (solo mesas; el mesero también puede hacerlo).

    Body: {"estado": "EN_PREPARACION"} — solo se avanza un paso a la vez.
    """
    tipo = tipo.upper()
    if tipo not in SIGUIENTE:
        return jsonify(error="El tipo debe ser MESA o DOMICILIO"), 404
    objeto = db.session.get(PedidoMesa if tipo == "MESA" else Domicilio, orden_id)
    if objeto is None or objeto.orden.estado == "CANCELADA":
        return jsonify(error="La orden no existe"), 404

    nuevo = str((request.get_json(silent=True) or {}).get("estado") or "").strip().upper()
    esperado = SIGUIENTE[tipo].get(objeto.estado)
    if esperado is None:
        return jsonify(error=f"Una orden {objeto.estado} no está en cocina"), 409
    if nuevo != esperado:
        return jsonify(error=f"Una orden {objeto.estado} solo puede pasar a {esperado}"), 409
    # El mesero (sin permisos de cocina) solo puede marcar la entrega en la mesa
    if not tiene_permiso("cocina.gestionar") and nuevo != "ENTREGADO":
        return jsonify(error="No tienes permiso para realizar esta acción"), 403

    objeto.estado = nuevo
    if tipo == "MESA" and nuevo == "LISTO":
        objeto.fecha_listo = datetime.now()
    if tipo == "MESA" and nuevo == "ENTREGADO":
        objeto.fecha_entrega = datetime.now()
    db.session.commit()
    return jsonify(_de_mesa(objeto) if tipo == "MESA" else _de_domicilio(objeto))


@bp.get("/cocina/novedades")
@permiso_requerido("cocina.ver", "pedidos.ver")
def novedades():
    """RF-06.7 Notificar cambio de estado. Las pantallas preguntan cada pocos segundos con
    ?desde=<hora de la respuesta anterior> y reciben lo que cambió:
    - nuevos: pedidos que llegaron a cocina (para la cocina);
    - listos: pedidos de mesa ya preparados, para que el mesero los lleve.
    """
    if not request.args.get("desde"):  # primera consulta: solo la hora del servidor para la siguiente
        return jsonify(hora=datetime.now().isoformat(), nuevos=[], listos=[])
    try:
        desde = datetime.fromisoformat(request.args["desde"])
    except ValueError:
        return jsonify(error="'desde' debe ser una fecha y hora ISO, por ejemplo 2026-11-05T12:30:00"), 422
    nuevos = PedidoMesa.query.filter(PedidoMesa.fecha_envio_cocina > desde).all()
    domicilios = (Domicilio.query.join(Orden)
                  .filter(Orden.created_at > desde, Domicilio.estado == "RECIBIDO").all())
    listos = PedidoMesa.query.filter(PedidoMesa.fecha_listo > desde, PedidoMesa.estado == "LISTO").all()
    return jsonify(
        hora=datetime.now().isoformat(),
        nuevos=[{"codigo": p.orden.codigo, "origen": f"Mesa {p.mesa.numero}"} for p in nuevos]
        + [{"codigo": d.orden.codigo, "origen": "Domicilio"} for d in domicilios],
        listos=[{"id": p.id, "codigo": p.orden.codigo, "mesa": p.mesa.numero} for p in listos],
    )
