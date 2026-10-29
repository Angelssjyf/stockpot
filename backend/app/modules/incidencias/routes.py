"""Módulo 12 - Incidencias: errores en inventario, ventas y compras (RF-12.1 a RF-12.4).

Sugerencia de la docente en la sustentación del 2.º corte: registrar los errores con un
código y una observación, saber quién los cometió y darle al administrador una bitácora.
"""

import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, jsonify, request

from ...extensions import db
from ...models import CodigoIncidencia, Incidencia, MovimientoInventario, OrdenCompra, Venta
from ...models.incidencias import MODULOS_INCIDENCIA
from ...services.inventario import StockInsuficiente, registrar_movimiento
from ...utils.auth import permiso_requerido, usuario_actual
from ...utils.fechas import filtrar_por_fechas

bp = Blueprint("incidencias", __name__)

# Registro con el error -> (modelo, módulo al que pertenece)
REGISTROS = {
    "movimiento_id": (MovimientoInventario, "INVENTARIO"),
    "venta_id": (Venta, "VENTAS"),
    "orden_compra_id": (OrdenCompra, "COMPRAS"),
}


def _texto(valor):
    return str(valor if valor is not None else "").strip()


# =====================================================================
#  RF-12.1 Catálogo de códigos de incidencia
# =====================================================================

@bp.get("/codigos-incidencia")
@permiso_requerido("incidencias.reportar", "incidencias.ver")
def listar_codigos():
    """RF-12.1 Códigos activos. ?modulo= trae los de ese módulo más los de OTRO;
    ?todos=true (para administrar el catálogo) incluye los inactivos."""
    consulta = CodigoIncidencia.query
    if request.args.get("todos") != "true":
        consulta = consulta.filter_by(activo=True)
    modulo = request.args.get("modulo", "").strip().upper()
    if modulo:
        consulta = consulta.filter(CodigoIncidencia.modulo.in_((modulo, "OTRO")))
    return jsonify([c.to_dict() for c in consulta.order_by(CodigoIncidencia.codigo).all()])


@bp.post("/codigos-incidencia")
@permiso_requerido("incidencias.gestionar")
def crear_codigo():
    """RF-12.1 El administrador agrega un código al catálogo (por ejemplo DOM-01)."""
    data = request.get_json(silent=True) or {}
    codigo = _texto(data.get("codigo")).upper()
    nombre = _texto(data.get("nombre"))
    modulo = _texto(data.get("modulo")).upper()
    if not re.fullmatch(r"[A-Z]{3}-\d{2}", codigo):
        return jsonify(error="El código debe tener tres letras, guion y dos números (ej. INV-05)"), 422
    if not nombre:
        return jsonify(error="Escribe el nombre del error"), 422
    if modulo not in MODULOS_INCIDENCIA:
        return jsonify(error=f"Módulo inválido. Opciones: {', '.join(MODULOS_INCIDENCIA)}"), 422
    if CodigoIncidencia.query.filter_by(codigo=codigo).first():
        return jsonify(error=f"Ya existe el código {codigo}"), 409
    nuevo = CodigoIncidencia(codigo=codigo, nombre=nombre, modulo=modulo)
    db.session.add(nuevo)
    db.session.commit()
    return jsonify(nuevo.to_dict()), 201


@bp.put("/codigos-incidencia/<int:codigo_id>")
@permiso_requerido("incidencias.gestionar")
def modificar_codigo(codigo_id):
    """RF-12.1 Cambiar el nombre de un código o activarlo/desactivarlo (no se borran: hay incidencias que lo usan)."""
    codigo = db.session.get(CodigoIncidencia, codigo_id)
    if codigo is None:
        return jsonify(error="El código no existe"), 404
    data = request.get_json(silent=True) or {}
    if "nombre" in data:
        nombre = _texto(data["nombre"])
        if not nombre:
            return jsonify(error="El nombre no puede quedar vacío"), 422
        codigo.nombre = nombre
    if "activo" in data:
        if not isinstance(data["activo"], bool):
            return jsonify(error="'activo' debe ser true o false"), 422
        codigo.activo = data["activo"]
    db.session.commit()
    return jsonify(codigo.to_dict())


# =====================================================================
#  RF-12.2 Reportar una incidencia y RF-12.3 corregir el inventario
# =====================================================================

def _cantidad_real(valor):
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None
    return numero if numero.is_finite() and numero >= 0 else None


@bp.post("/incidencias")
@permiso_requerido("incidencias.reportar")
def reportar_incidencia():
    """RF-12.2 Reportar un error sobre un movimiento, una venta o una orden de compra.

    El responsable sale solo del registro (quien lo hizo); quien reporta queda aparte.
    RF-12.3 Si el código corrige stock (INV-01 de más, INV-02 de menos) se indica la
    cantidad real y se crea el movimiento de ajuste; el registro original no se toca.
    """
    data = request.get_json(silent=True) or {}
    usuario = usuario_actual()

    tipo = db.session.get(CodigoIncidencia, data.get("codigo_id") or 0)
    if tipo is None or not tipo.activo:
        return jsonify(error="Elige un código de incidencia válido"), 422
    observacion = _texto(data.get("observacion"))
    if len(observacion) < 5:
        return jsonify(error="Describe el error en la observación (mínimo 5 caracteres)"), 422

    referencias = [campo for campo in REGISTROS if data.get(campo) is not None]
    if len(referencias) != 1:
        return jsonify(error="Indica el registro con el error: un movimiento, una venta o una orden de compra"), 422
    campo = referencias[0]
    modelo, modulo = REGISTROS[campo]
    if tipo.modulo not in (modulo, "OTRO"):
        return jsonify(error=f"El código {tipo.codigo} es de {tipo.modulo.lower()}, no de {modulo.lower()}"), 422
    registro = db.session.get(modelo, data[campo] or 0)
    if registro is None:
        return jsonify(error="El registro con el error no existe"), 404

    incidencia = Incidencia(
        codigo=f"TMP-{uuid4().hex[:12]}",  # temporal; el definitivo depende del id
        tipo=tipo, responsable_id=registro.usuario_id, reportado_por_id=usuario.id,
        observacion=observacion[:500], **{campo: registro.id},
    )

    if tipo.corrige_stock:
        if registro.motivo == "CONSUMO":
            return jsonify(error="Ese consumo salió de una venta: reporta la incidencia sobre la venta"), 422
        corregida = Incidencia.query.filter(
            Incidencia.movimiento_id == registro.id, Incidencia.ajuste_id.isnot(None)).first()
        if corregida:
            return jsonify(error=f"Ese movimiento ya se corrigió con la incidencia {corregida.codigo}"), 409
        real = _cantidad_real(data.get("cantidad_real"))
        if real is None:
            return jsonify(error="Escribe la cantidad real (0 o más)"), 422
        diferencia = real - registro.cantidad
        if diferencia == 0:
            return jsonify(error="La cantidad real es igual a la registrada: no hay nada que corregir"), 422
        if tipo.codigo == "INV-01" and diferencia > 0:
            return jsonify(error="INV-01 es para cantidades de más: la real debe ser menor que la registrada"), 422
        if tipo.codigo == "INV-02" and diferencia < 0:
            return jsonify(error="INV-02 es para cantidades de menos: la real debe ser mayor que la registrada"), 422
        incidencia.cantidad_registrada = registro.cantidad
        incidencia.cantidad_real = real

    db.session.add(incidencia)
    db.session.flush()
    incidencia.codigo = f"INC-{incidencia.id:06d}"

    if tipo.corrige_stock:
        # Si faltó, se repite el tipo del original; si sobró, se hace el contrario
        opuesto = "SALIDA" if registro.tipo == "ENTRADA" else "ENTRADA"
        tipo_ajuste = registro.tipo if diferencia > 0 else opuesto
        try:
            incidencia.ajuste = registrar_movimiento(
                registro.insumo, tipo_ajuste, "AJUSTE", abs(diferencia), usuario.id,
                observacion=f"Corrige {incidencia.codigo}: se registró {float(registro.cantidad):g} y eran {float(real):g}",
            )
        except StockInsuficiente as excepcion:
            db.session.rollback()  # ni la incidencia ni el ajuste quedan a medias
            return jsonify(error=str(excepcion)), 409

    db.session.commit()
    return jsonify(incidencia.to_dict()), 201


# =====================================================================
#  RF-12.4 Bitácora del administrador
# =====================================================================

@bp.get("/incidencias")
@permiso_requerido("incidencias.ver")
def bitacora():
    """RF-12.4 Todas las incidencias con un resumen: quién comete más errores, qué tipos son
    más comunes y en qué módulo. Filtros: ?desde= ?hasta= ?responsable_id= ?codigo_id= ?modulo="""
    consulta = Incidencia.query.join(CodigoIncidencia)
    try:
        consulta = filtrar_por_fechas(consulta, Incidencia.created_at, request.args)
    except ValueError:
        return jsonify(error="Fechas inválidas: usa AAAA-MM-DD"), 422
    if request.args.get("responsable_id", "").isdigit():
        consulta = consulta.filter(Incidencia.responsable_id == int(request.args["responsable_id"]))
    if request.args.get("codigo_id", "").isdigit():
        consulta = consulta.filter(Incidencia.codigo_incidencia_id == int(request.args["codigo_id"]))
    modulo = request.args.get("modulo", "").strip().upper()
    if modulo:
        consulta = consulta.filter(CodigoIncidencia.modulo == modulo)

    incidencias = consulta.order_by(Incidencia.created_at.desc(), Incidencia.id.desc()).all()
    por_usuario = Counter((i.responsable_id, f"{i.responsable.nombre} {i.responsable.apellido}") for i in incidencias)
    por_tipo = Counter((i.tipo.codigo, i.tipo.nombre) for i in incidencias)
    por_modulo = Counter(i.tipo.modulo for i in incidencias)
    return jsonify({
        "incidencias": [i.to_dict() for i in incidencias],
        "resumen": {
            "total": len(incidencias),
            "corregidas": sum(1 for i in incidencias if i.ajuste_id),
            "por_usuario": [{"usuario_id": uid, "nombre": nombre, "total": total}
                            for (uid, nombre), total in por_usuario.most_common()],
            "por_tipo": [{"codigo": codigo, "nombre": nombre, "total": total}
                         for (codigo, nombre), total in por_tipo.most_common()],
            "por_modulo": dict(por_modulo),
        },
    })
