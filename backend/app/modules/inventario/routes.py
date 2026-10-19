"""Módulo 3 - Gestión de inventario (RF-03.1 a RF-03.8)."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ...extensions import db
from ...models import Insumo, MovimientoInventario
from ...models.inventario import UNIDADES_MEDIDA
from ...services.inventario import StockInsuficiente, registrar_movimiento
from ...utils.auth import permiso_requerido, usuario_actual

bp = Blueprint("inventario", __name__)

# RF-03.4 / RF-03.5 Motivos permitidos al registrar un movimiento a mano.
# (El consumo por ventas lo registra el sistema solo: RF-03.9 y RF-10.3.)
MOTIVOS_MANUALES = {
    "ENTRADA": ("COMPRA", "AJUSTE", "DEVOLUCION"),
    "SALIDA": ("CONSUMO", "MERMA", "AJUSTE"),
}


def _texto(valor):
    """Convierte un valor recibido en texto sin espacios a los lados ('' si viene vacío)."""
    return str(valor if valor is not None else "").strip()


def _decimal_no_negativo(valor, campo):
    """Convierte un valor en Decimal >= 0. Devuelve (numero, None) o (None, mensaje)."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None, f"'{campo}' debe ser un número"
    if numero < 0:
        return None, f"'{campo}' no puede ser negativo"
    return numero, None


def _aplicar_datos(insumo, data):
    """Valida los datos recibidos y los copia al insumo.

    Devuelve (mensaje, código HTTP) si algo está mal, o None si todo está bien.
    El stock NO se cambia aquí: solo cambia con compras recibidas (RF-02.8) y con las
    entradas y salidas de inventario (RF-03.4 y RF-03.5).
    """
    if "stock_actual" in data:
        return "El stock no se modifica aquí: cambia con las compras, entradas y salidas", 422

    if "codigo" in data:
        codigo = _texto(data["codigo"]).upper()
        if not codigo:
            return "El código no puede quedar vacío", 422
        otro = Insumo.query.filter_by(codigo=codigo).first()
        if otro and otro.id != insumo.id:
            return "Ya existe un insumo con ese código", 409
        insumo.codigo = codigo

    if "nombre" in data:
        nombre = _texto(data["nombre"])
        if not nombre:
            return "El nombre no puede quedar vacío", 422
        insumo.nombre = nombre

    if "unidad_medida" in data:
        unidad = _texto(data["unidad_medida"]).upper()
        if unidad not in UNIDADES_MEDIDA:
            return f"Unidad de medida inválida. Opciones: {', '.join(UNIDADES_MEDIDA)}", 422
        insumo.unidad_medida = unidad

    # RF-03.7 Establecer niveles mínimos de stock (y el costo unitario de referencia)
    for campo in ("stock_minimo", "costo_unitario"):
        if campo in data:
            numero, error = _decimal_no_negativo(data[campo], campo)
            if error:
                return error, 422
            setattr(insumo, campo, numero)

    if "activo" in data:
        if not isinstance(data["activo"], bool):
            return "'activo' debe ser true o false", 422
        insumo.activo = data["activo"]

    return None


@bp.get("/insumos")
@permiso_requerido("inventario.ver", "proveedores.ver", "compras.ver")
def listar_insumos():
    """RF-03.2 Consultar insumos. Filtros opcionales: ?q= (código o nombre) y
    ?activo=true|false. También lo usan proveedores y compras para elegir insumos."""
    consulta = Insumo.query

    texto = request.args.get("q", "").strip()
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.filter(or_(Insumo.codigo.ilike(patron), Insumo.nombre.ilike(patron)))

    activo = request.args.get("activo")
    if activo in ("true", "false"):
        consulta = consulta.filter(Insumo.activo.is_(activo == "true"))

    insumos = consulta.order_by(Insumo.nombre).all()
    return jsonify([insumo.to_dict() for insumo in insumos])


@bp.get("/insumos/<int:insumo_id>")
@permiso_requerido("inventario.ver", "proveedores.ver", "compras.ver")
def obtener_insumo(insumo_id):
    """RF-03.2 Consultar el detalle de un insumo."""
    insumo = db.session.get(Insumo, insumo_id)
    if insumo is None:
        return jsonify(error="El insumo no existe"), 404
    return jsonify(insumo.to_dict())


@bp.post("/insumos")
@permiso_requerido("inventario.gestionar")
def crear_insumo():
    """RF-03.1 Registrar insumos y materias primas. Empiezan con stock 0."""
    data = request.get_json(silent=True) or {}

    obligatorios = ("codigo", "nombre", "unidad_medida")
    faltantes = [campo for campo in obligatorios if not _texto(data.get(campo))]
    if faltantes:
        return jsonify(error="Faltan campos obligatorios", faltantes=faltantes), 422

    insumo = Insumo()
    error = _aplicar_datos(insumo, data)
    if error:
        db.session.rollback()
        return jsonify(error=error[0]), error[1]

    db.session.add(insumo)
    db.session.commit()
    return jsonify(insumo.to_dict()), 201


@bp.put("/insumos/<int:insumo_id>")
@permiso_requerido("inventario.gestionar")
def modificar_insumo(insumo_id):
    """RF-03.3 Modificar información de insumos (también activar o desactivar)."""
    insumo = db.session.get(Insumo, insumo_id)
    if insumo is None:
        return jsonify(error="El insumo no existe"), 404

    error = _aplicar_datos(insumo, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()  # no deja cambios a medias
        return jsonify(error=error[0]), error[1]

    db.session.commit()
    return jsonify(insumo.to_dict())


@bp.post("/insumos/<int:insumo_id>/movimientos")
@permiso_requerido("inventario.gestionar")
def registrar_movimiento_manual(insumo_id):
    """RF-03.4 Registrar entradas y RF-03.5 Registrar salidas de inventario.

    Body: {"tipo": "ENTRADA" | "SALIDA", "motivo": "MERMA", "cantidad": 2.5, "observacion": "..."}
    """
    insumo = db.session.get(Insumo, insumo_id)
    if insumo is None:
        return jsonify(error="El insumo no existe"), 404
    if not insumo.activo:
        return jsonify(error="El insumo está inactivo"), 409

    data = request.get_json(silent=True) or {}
    tipo = _texto(data.get("tipo")).upper()
    if tipo not in MOTIVOS_MANUALES:
        return jsonify(error="El tipo debe ser ENTRADA o SALIDA"), 422
    motivo = _texto(data.get("motivo")).upper()
    if motivo not in MOTIVOS_MANUALES[tipo]:
        opciones = ", ".join(MOTIVOS_MANUALES[tipo])
        return jsonify(error=f"Motivo inválido para una {tipo.lower()}. Opciones: {opciones}"), 422

    cantidad, error = _decimal_no_negativo(data.get("cantidad"), "cantidad")
    if error or cantidad == 0:
        return jsonify(error=error or "La cantidad debe ser mayor que cero"), 422

    try:
        movimiento = registrar_movimiento(
            insumo, tipo, motivo, cantidad, usuario_actual().id,
            observacion=_texto(data.get("observacion")) or None,
        )
    except StockInsuficiente as excepcion:
        db.session.rollback()
        return jsonify(error=str(excepcion)), 409

    db.session.commit()
    return jsonify(movimiento=movimiento.to_dict(), insumo=insumo.to_dict()), 201


@bp.get("/insumos/<int:insumo_id>/movimientos")
@permiso_requerido("inventario.ver")
def historial_movimientos(insumo_id):
    """RF-03.4 / RF-03.5 Historial de movimientos de un insumo (los 100 más recientes)."""
    insumo = db.session.get(Insumo, insumo_id)
    if insumo is None:
        return jsonify(error="El insumo no existe"), 404
    movimientos = (
        MovimientoInventario.query.filter_by(insumo_id=insumo.id)
        .order_by(MovimientoInventario.created_at.desc(), MovimientoInventario.id.desc())
        .limit(100)
        .all()
    )
    return jsonify([m.to_dict() for m in movimientos])


@bp.get("/inventario/existencias")
@permiso_requerido("inventario.ver")
def consultar_existencias():
    """RF-03.6 Consultar existencias: stock de cada insumo activo, su estado y su valor."""
    insumos = Insumo.query.filter(Insumo.activo.is_(True)).order_by(Insumo.nombre).all()
    filas = []
    for insumo in insumos:
        datos = insumo.to_dict()
        datos["valor"] = float(insumo.stock_actual * insumo.costo_unitario)
        filas.append(datos)
    resumen = {
        "total_insumos": len(filas),
        "bajos": sum(1 for f in filas if f["estado_stock"] == "BAJO"),
        "agotados": sum(1 for f in filas if f["estado_stock"] == "AGOTADO"),
        "valor_total": round(sum(f["valor"] for f in filas), 2),
    }
    return jsonify(resumen=resumen, insumos=filas)


@bp.get("/inventario/alertas")
@permiso_requerido("inventario.ver")
def alertas_de_stock():
    """RF-03.8 Generar alertas de stock: insumos activos agotados o en su nivel mínimo,
    del que más falta al que menos."""
    insumos = Insumo.query.filter(Insumo.activo.is_(True)).all()
    alertas = []
    for insumo in insumos:
        if insumo.estado_stock == "OK":
            continue
        datos = insumo.to_dict()
        datos["faltante"] = float(max(insumo.stock_minimo - insumo.stock_actual, 0))
        alertas.append(datos)
    alertas.sort(key=lambda a: (a["estado_stock"] != "AGOTADO", -a["faltante"], a["nombre"]))
    return jsonify(alertas)
