"""Módulo 11 - Reportes y estadísticas (RF-11.1 a RF-11.6).

Los reportes leen lo que registran los demás módulos (inventario, compras, ventas, pagos y
domicilios); no guardan nada. Los totales se calculan en Python para que funcionen igual en
MySQL y en la base de pruebas.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import wraps

from flask import Blueprint, jsonify, request

from ...models import Domicilio, Insumo, MovimientoInventario, OrdenCompra, Pago, Producto, Venta
from ...utils.auth import permiso_requerido
from ...utils.fechas import filtrar_por_fechas

bp = Blueprint("reportes", __name__)

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _rango():
    """Lee ?desde y ?hasta (por defecto, los últimos 30 días). Lanza ValueError si son inválidas."""
    hasta = date.fromisoformat(request.args["hasta"]) if request.args.get("hasta") else date.today()
    desde = (date.fromisoformat(request.args["desde"]) if request.args.get("desde")
             else hasta - timedelta(days=29))
    if desde > hasta:
        raise ValueError
    return desde, hasta


def _args(desde, hasta):
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat()}


def _ventas(desde, hasta):
    consulta = filtrar_por_fechas(Venta.query, Venta.created_at, _args(desde, hasta))
    return consulta.order_by(Venta.created_at).all()


def _dinero(valor):
    return float(round(Decimal(valor), 2))


def _con_rango(funcion):
    """Responde 422 si las fechas del reporte no son válidas."""
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        try:
            desde, hasta = _rango()
        except ValueError:
            return jsonify(error="Fechas inválidas: usa AAAA-MM-DD y que 'desde' no sea mayor que 'hasta'"), 422
        return funcion(desde, hasta, *args, **kwargs)
    return envoltura


# =====================================================================
#  RF-11.1 Reporte de inventario
# =====================================================================


@bp.get("/reportes/inventario")
@permiso_requerido("reportes.ver")
@_con_rango
def reporte_inventario(desde, hasta):
    """RF-11.1 Generar reportes de inventario: existencias valorizadas de cada insumo activo y
    sus movimientos en el periodo (entradas, consumo por ventas, mermas y ajustes)."""
    movimientos = filtrar_por_fechas(MovimientoInventario.query, MovimientoInventario.created_at,
                                     _args(desde, hasta)).all()
    por_insumo = defaultdict(lambda: defaultdict(Decimal))
    for m in movimientos:
        clave = "entradas" if m.tipo == "ENTRADA" else m.motivo.lower()  # consumo, merma, ajuste
        por_insumo[m.insumo_id][clave] += m.cantidad

    filas = []
    for insumo in Insumo.query.filter(Insumo.activo.is_(True)).order_by(Insumo.nombre):
        mov = por_insumo[insumo.id]
        filas.append({
            "codigo": insumo.codigo,
            "insumo": insumo.nombre,
            "unidad_medida": insumo.unidad_medida,
            "stock_actual": float(insumo.stock_actual),
            "stock_minimo": float(insumo.stock_minimo),
            "estado_stock": insumo.estado_stock,
            "costo_unitario": float(insumo.costo_unitario),
            "valor": _dinero(insumo.stock_actual * insumo.costo_unitario),
            "entradas": float(mov["entradas"]),
            "consumo": float(mov["consumo"]),
            "merma": float(mov["merma"]),
            "ajuste_salida": float(mov["ajuste"]),
        })
    resumen = {
        "insumos": len(filas),
        "valor_total": _dinero(sum(f["valor"] for f in filas)),
        "bajos": sum(1 for f in filas if f["estado_stock"] == "BAJO"),
        "agotados": sum(1 for f in filas if f["estado_stock"] == "AGOTADO"),
        "movimientos": len(movimientos),
    }
    return jsonify(desde=desde.isoformat(), hasta=hasta.isoformat(), resumen=resumen, insumos=filas)


# =====================================================================
#  RF-11.2 Reporte de ventas
# =====================================================================


@bp.get("/reportes/ventas")
@permiso_requerido("reportes.ver")
@_con_rango
def reporte_ventas(desde, hasta):
    """RF-11.2 Generar reportes de ventas: totales del periodo, ventas por día (para la gráfica),
    por tipo de pedido y por método de pago."""
    ventas = _ventas(desde, hasta)

    por_dia = {}
    dia = desde
    while dia <= hasta:  # todos los días, también los que no tuvieron ventas
        por_dia[dia] = {"fecha": dia.isoformat(), "ventas": 0, "total": Decimal("0"),
                        "ganancia": Decimal("0")}
        dia += timedelta(days=1)
    por_tipo = defaultdict(lambda: {"ventas": 0, "total": Decimal("0")})
    for v in ventas:
        fila = por_dia[v.created_at.date()]
        fila["ventas"] += 1
        fila["total"] += v.total
        fila["ganancia"] += v.subtotal - v.costo_insumos
        por_tipo[v.orden.tipo]["ventas"] += 1
        por_tipo[v.orden.tipo]["total"] += v.total

    pagos = filtrar_por_fechas(Pago.query.filter_by(estado="APROBADO"), Pago.created_at,
                               _args(desde, hasta)).all()
    por_metodo = {m: Decimal("0") for m in Pago.METODOS}
    for pago in pagos:
        por_metodo[pago.metodo] += pago.monto

    total = sum((v.total for v in ventas), Decimal("0"))
    costo = sum((v.costo_insumos for v in ventas), Decimal("0"))
    subtotal = sum((v.subtotal for v in ventas), Decimal("0"))
    resumen = {
        "ventas": len(ventas),
        "total": _dinero(total),
        "costo_insumos": _dinero(costo),
        "ganancia": _dinero(subtotal - costo),
        "margen": round(float((subtotal - costo) / subtotal * 100), 1) if subtotal else 0.0,
        "ticket_promedio": _dinero(total / len(ventas)) if ventas else 0.0,
    }
    return jsonify(
        desde=desde.isoformat(), hasta=hasta.isoformat(), resumen=resumen,
        por_dia=[{**f, "total": _dinero(f["total"]), "ganancia": _dinero(f["ganancia"])}
                 for f in por_dia.values()],
        por_tipo={t: {"ventas": d["ventas"], "total": _dinero(d["total"])} for t, d in por_tipo.items()},
        por_metodo={m: _dinero(v) for m, v in por_metodo.items()},
    )


# =====================================================================
#  RF-11.3 Reporte de consumo y RF-11.4 Productos más vendidos
# =====================================================================


@bp.get("/reportes/consumo")
@permiso_requerido("reportes.ver")
@_con_rango
def reporte_consumo(desde, hasta):
    """RF-11.3 Generar reportes de consumo: lo que se gastó de cada insumo en ventas y lo que
    se perdió por merma, con su costo, del más costoso al menos."""
    filas = defaultdict(lambda: {"consumo": Decimal("0"), "costo_consumo": Decimal("0"),
                                 "merma": Decimal("0"), "costo_merma": Decimal("0")})
    insumos = {}
    for venta in _ventas(desde, hasta):
        for c in venta.consumos:
            insumos[c.insumo_id] = c.insumo
            filas[c.insumo_id]["consumo"] += c.cantidad
            filas[c.insumo_id]["costo_consumo"] += c.cantidad * c.costo_unitario
    mermas = filtrar_por_fechas(MovimientoInventario.query.filter_by(tipo="SALIDA", motivo="MERMA"),
                                MovimientoInventario.created_at, _args(desde, hasta)).all()
    for m in mermas:
        insumos[m.insumo_id] = m.insumo
        filas[m.insumo_id]["merma"] += m.cantidad
        filas[m.insumo_id]["costo_merma"] += m.cantidad * m.insumo.costo_unitario

    resultado = sorted((
        {"insumo": insumos[i].nombre, "unidad_medida": insumos[i].unidad_medida,
         "consumo": float(f["consumo"]), "costo_consumo": _dinero(f["costo_consumo"]),
         "merma": float(f["merma"]), "costo_merma": _dinero(f["costo_merma"])}
        for i, f in filas.items()
    ), key=lambda f: -(f["costo_consumo"] + f["costo_merma"]))
    resumen = {
        "costo_consumo": _dinero(sum(f["costo_consumo"] for f in resultado)),
        "costo_merma": _dinero(sum(f["costo_merma"] for f in resultado)),
    }
    return jsonify(desde=desde.isoformat(), hasta=hasta.isoformat(), resumen=resumen, insumos=resultado)


def _productos_vendidos(desde, hasta):
    """Unidades, ingresos y ganancia de cada producto vendido en el periodo."""
    datos = defaultdict(lambda: {"cantidad": 0, "total": Decimal("0"), "costo": Decimal("0")})
    for venta in _ventas(desde, hasta):
        for d in venta.orden.detalles:
            fila = datos[d.producto_id]
            fila["cantidad"] += d.cantidad
            fila["total"] += d.subtotal
            fila["costo"] += d.producto.costo * d.cantidad
    return datos


@bp.get("/reportes/productos")
@permiso_requerido("reportes.ver")
@_con_rango
def reporte_productos(desde, hasta):
    """RF-11.4 Consultar productos más vendidos, con ingresos y margen de cada uno, y los
    productos de la carta que no se vendieron en el periodo."""
    datos = _productos_vendidos(desde, hasta)
    productos = {p.id: p for p in Producto.query.filter(Producto.activo.is_(True))}
    vendidos = sorted((
        {"producto": productos[i].nombre if i in productos else f"Producto {i}",
         "categoria": productos[i].categoria if i in productos else None,
         "cantidad": f["cantidad"], "total": _dinero(f["total"]),
         "margen": round(float((f["total"] - f["costo"]) / f["total"] * 100), 1) if f["total"] else 0.0}
        for i, f in datos.items()
    ), key=lambda f: (-f["cantidad"], f["producto"]))
    sin_ventas = sorted(p.nombre for i, p in productos.items() if i not in datos)
    return jsonify(desde=desde.isoformat(), hasta=hasta.isoformat(), vendidos=vendidos,
                   sin_ventas=sin_ventas)


# =====================================================================
#  RF-11.5 Información histórica
# =====================================================================


@bp.get("/reportes/historico")
@permiso_requerido("reportes.ver")
def reporte_historico():
    """RF-11.5 Consultar información histórica mes a mes (?meses=6, máximo 24): ventas,
    ganancia, compras recibidas y domicilios entregados."""
    meses = max(1, min(request.args.get("meses", 6, type=int), 24))
    hoy = date.today()
    inicio = date(hoy.year, hoy.month, 1)
    for _ in range(meses - 1):  # retrocede al primer día del mes más antiguo
        inicio = date(inicio.year - (inicio.month == 1), (inicio.month - 2) % 12 + 1, 1)

    filas = {}
    mes = inicio
    while mes <= hoy:
        filas[(mes.year, mes.month)] = {
            "mes": f"{MESES[mes.month - 1]} {mes.year}", "ventas": 0, "total": Decimal("0"),
            "ganancia": Decimal("0"), "compras": Decimal("0"), "domicilios": 0}
        mes = date(mes.year + (mes.month == 12), mes.month % 12 + 1, 1)

    def fila(fecha):
        return filas.get((fecha.year, fecha.month))

    for v in Venta.query.filter(Venta.created_at >= inicio):
        f = fila(v.created_at)
        if f:
            f["ventas"] += 1
            f["total"] += v.total
            f["ganancia"] += v.subtotal - v.costo_insumos
    for oc in OrdenCompra.query.filter(OrdenCompra.estado == "RECIBIDA",
                                       OrdenCompra.fecha_recepcion >= inicio):
        f = fila(oc.fecha_recepcion)
        if f:
            f["compras"] += oc.total
    for d in Domicilio.query.filter(Domicilio.estado == "ENTREGADO", Domicilio.fecha_entrega >= inicio):
        f = fila(d.fecha_entrega)
        if f:
            f["domicilios"] += 1

    return jsonify([{**f, "total": _dinero(f["total"]), "ganancia": _dinero(f["ganancia"]),
                     "compras": _dinero(f["compras"])} for f in filas.values()])


# =====================================================================
#  RF-11.6 Estadísticas para apoyar la toma de decisiones
# =====================================================================


def _variacion(actual, anterior):
    """Porcentaje de cambio frente al periodo anterior (None si antes no hubo nada)."""
    if not anterior:
        return None
    return round(float((Decimal(actual) - Decimal(anterior)) / Decimal(anterior) * 100), 1)


@bp.get("/reportes/estadisticas")
@permiso_requerido("reportes.ver")
@_con_rango
def estadisticas(desde, hasta):
    """RF-11.6 Generar estadísticas para apoyar la toma de decisiones: comparación con el periodo
    anterior, día y hora de más ventas, producto estrella, cobertura del inventario y
    recomendaciones automáticas."""
    dias = (hasta - desde).days + 1
    ventas = _ventas(desde, hasta)
    anteriores = _ventas(desde - timedelta(days=dias), desde - timedelta(days=1))
    total = sum((v.total for v in ventas), Decimal("0"))
    total_anterior = sum((v.total for v in anteriores), Decimal("0"))

    por_dia_semana = Counter()
    por_hora = Counter()
    for v in ventas:
        por_dia_semana[v.created_at.weekday()] += v.total
        por_hora[v.created_at.hour] += 1
    dia_top = max(por_dia_semana, key=por_dia_semana.get) if por_dia_semana else None
    hora_top = max(por_hora, key=por_hora.get) if por_hora else None

    vendidos = _productos_vendidos(desde, hasta)
    productos = {p.id: p for p in Producto.query.all()}
    estrella = max(vendidos, key=lambda i: vendidos[i]["cantidad"]) if vendidos else None
    con_margen = {i: (f["total"] - f["costo"]) / f["total"] for i, f in vendidos.items() if f["total"]}
    menor_margen = min(con_margen, key=con_margen.get) if con_margen else None

    # Cobertura: cuántos días alcanza el stock al ritmo de consumo del periodo
    consumo_diario = defaultdict(Decimal)
    for v in ventas:
        for c in v.consumos:
            consumo_diario[c.insumo_id] += c.cantidad / dias
    cobertura = []
    for insumo in Insumo.query.filter(Insumo.activo.is_(True)):
        ritmo = consumo_diario.get(insumo.id)
        if ritmo:
            cobertura.append({"insumo": insumo.nombre, "unidad_medida": insumo.unidad_medida,
                              "stock_actual": float(insumo.stock_actual),
                              "consumo_diario": round(float(ritmo), 3),
                              "dias": round(float(insumo.stock_actual / ritmo), 1)})
    cobertura.sort(key=lambda c: c["dias"])

    recomendaciones = []
    variacion = _variacion(total, total_anterior)
    if variacion is not None and variacion <= -10:
        recomendaciones.append(f"Las ventas bajaron {abs(variacion)} % frente al periodo anterior: "
                               "revisa precios, promociones o la disponibilidad de la carta.")
    elif variacion is not None and variacion >= 10:
        recomendaciones.append(f"Las ventas subieron {variacion} %: asegura el inventario de los "
                               "productos más pedidos.")
    for c in cobertura:
        if c["dias"] < 3:
            recomendaciones.append(f"'{c['insumo']}' alcanza para {c['dias']} días al ritmo actual: "
                                   "programa una orden de compra.")
    if menor_margen is not None and con_margen[menor_margen] < Decimal("0.5"):
        recomendaciones.append(f"'{productos[menor_margen].nombre}' deja solo "
                               f"{round(float(con_margen[menor_margen]) * 100)} % de margen: "
                               "revisa su precio o su receta.")
    if dia_top is not None:
        recomendaciones.append(f"El día de más ventas es el {DIAS[dia_top]}: refuerza personal e "
                               "inventario ese día.")
    agotados = Insumo.query.filter(Insumo.activo.is_(True), Insumo.stock_actual <= 0).count()
    if agotados:
        recomendaciones.append(f"Hay {agotados} insumo(s) agotado(s): revisa Inventario.")
    if not ventas:
        recomendaciones.append("No hay ventas en el periodo: registra ventas para obtener estadísticas.")

    return jsonify(
        desde=desde.isoformat(), hasta=hasta.isoformat(),
        indicadores={
            "ventas": len(ventas),
            "total": _dinero(total),
            "variacion_total": variacion,
            "ventas_por_dia": round(len(ventas) / dias, 1),
            "ticket_promedio": _dinero(total / len(ventas)) if ventas else 0.0,
            "dia_mas_ventas": DIAS[dia_top] if dia_top is not None else None,
            "hora_pico": f"{hora_top}:00 - {hora_top + 1}:00" if hora_top is not None else None,
            "producto_estrella": productos[estrella].nombre if estrella else None,
            "producto_menor_margen": productos[menor_margen].nombre if menor_margen else None,
        },
        cobertura=cobertura,
        recomendaciones=recomendaciones,
        generado=datetime.now().isoformat(timespec="minutes"),
    )
