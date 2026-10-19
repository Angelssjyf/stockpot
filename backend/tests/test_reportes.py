"""Casos de prueba: reportes y estadísticas (RF-11.1 a RF-11.6).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import func

from app.extensions import db
from app.models import Insumo, Producto, Receta, Venta

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def hoy(app):
    """La fecha de hoy según la base de datos (la de pruebas guarda la hora en UTC)."""
    return date.fromisoformat(str(db.session.execute(db.select(func.date(func.now()))).scalar()))


@pytest.fixture()
def negocio(client, admin_headers):
    """Insumos, carta y dos ventas de hoy:
    venta 1 = 2 bandejas + 1 gaseosa ($48.500, efectivo); venta 2 = 3 gaseosas ($13.500, tarjeta).
    Además, una merma de 0,5 KG de pollo."""
    pollo = Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG",
                   stock_actual=5, stock_minimo=1, costo_unitario=12000)
    gaseosa = Insumo(codigo="INS-011", nombre="Gaseosa", unidad_medida="UNIDAD",
                     stock_actual=24, stock_minimo=30, costo_unitario=2200)
    sal = Insumo(codigo="INS-008", nombre="Sal", unidad_medida="KG", stock_actual=0)
    bandeja = Producto(codigo="PRD-001", nombre="Bandeja", categoria="PLATO_FUERTE",
                       precio_venta=22000, receta=[Receta(insumo=pollo, cantidad=0.25)])
    bebida = Producto(codigo="PRD-006", nombre="Gaseosa 400 ml", categoria="BEBIDA",
                      precio_venta=4500, receta=[Receta(insumo=gaseosa, cantidad=1)])
    postre = Producto(codigo="PRD-008", nombre="Arroz con leche", categoria="POSTRE",
                      precio_venta=7000)
    db.session.add_all([pollo, gaseosa, sal, bandeja, bebida, postre])
    db.session.commit()

    for items, metodo in (
        ([{"producto_id": bandeja.id, "cantidad": 2}, {"producto_id": bebida.id, "cantidad": 1}], "EFECTIVO"),
        ([{"producto_id": bebida.id, "cantidad": 3}], "TARJETA"),
    ):
        r = client.post("/api/ventas", headers=admin_headers, json={"items": items, "metodo": metodo})
        assert r.status_code == 201, r.get_json()
    client.post(f"/api/insumos/{pollo.id}/movimientos", headers=admin_headers,
                json={"tipo": "SALIDA", "motivo": "MERMA", "cantidad": 0.5})
    return {"pollo": pollo.id}


def _get(client, headers, url):
    respuesta = client.get(url, headers=headers)
    assert respuesta.status_code == 200, respuesta.get_json()
    return respuesta.get_json()


# ------------------------------------------------------- RF-11.1 Inventario


def test_cp_11_1_1_reporte_de_inventario(client, admin_headers, negocio, hoy):
    """CP-11.1-1 | RF-11.1 | Existencias valorizadas y movimientos del periodo por insumo."""
    HOY = hoy.isoformat()
    r = _get(client, admin_headers, f"/api/reportes/inventario?desde={HOY}&hasta={HOY}")
    filas = {f["insumo"]: f for f in r["insumos"]}
    assert filas["Pollo"]["stock_actual"] == 4.0          # 5 − 0,5 vendido − 0,5 merma
    assert (filas["Pollo"]["consumo"], filas["Pollo"]["merma"]) == (0.5, 0.5)
    assert filas["Pollo"]["valor"] == 48000.0
    assert filas["Gaseosa"]["estado_stock"] == "BAJO"     # 20 ≤ 30
    assert r["resumen"]["agotados"] == 1                  # la sal
    assert r["resumen"]["valor_total"] == 92000.0         # 48.000 + 20 × 2.200


# ------------------------------------------------------- RF-11.2 Ventas


def test_cp_11_2_1_reporte_de_ventas(client, admin_headers, negocio, hoy):
    """CP-11.2-1 | RF-11.2 | Totales, margen, ventas por día, por tipo y por método de pago."""
    HOY = hoy.isoformat()
    desde = (hoy - timedelta(days=6)).isoformat()
    r = _get(client, admin_headers, f"/api/reportes/ventas?desde={desde}&hasta={HOY}")
    assert r["resumen"] == {"ventas": 2, "total": 62000.0, "costo_insumos": 14800.0,
                            "ganancia": 47200.0, "margen": 76.1, "ticket_promedio": 31000.0}
    assert len(r["por_dia"]) == 7                         # también los días sin ventas
    assert r["por_dia"][-1] == {"fecha": HOY, "ventas": 2, "total": 62000.0, "ganancia": 47200.0}
    assert r["por_tipo"] == {"LLEVAR": {"ventas": 2, "total": 62000.0}}
    assert r["por_metodo"] == {"EFECTIVO": 48500.0, "TARJETA": 13500.0, "TRANSFERENCIA": 0.0}


@pytest.mark.parametrize("consulta", ["desde=ayer", "desde=2026-10-18&hasta=2000-01-01"])
def test_cp_11_2_2_fechas_invalidas(client, admin_headers, consulta):
    """CP-11.2-2 | RF-11.2 | Fecha mal escrita o 'desde' mayor que 'hasta' → 422."""
    assert client.get(f"/api/reportes/ventas?{consulta}", headers=admin_headers).status_code == 422


# ------------------------------------------------------- RF-11.3 Consumo


def test_cp_11_3_1_reporte_de_consumo(client, admin_headers, negocio, hoy):
    """CP-11.3-1 | RF-11.3 | Consumo por ventas y merma de cada insumo, con su costo."""
    HOY = hoy.isoformat()
    r = _get(client, admin_headers, f"/api/reportes/consumo?desde={HOY}&hasta={HOY}")
    filas = {f["insumo"]: f for f in r["insumos"]}
    assert (filas["Pollo"]["consumo"], filas["Pollo"]["costo_consumo"]) == (0.5, 6000.0)
    assert (filas["Pollo"]["merma"], filas["Pollo"]["costo_merma"]) == (0.5, 6000.0)
    assert (filas["Gaseosa"]["consumo"], filas["Gaseosa"]["costo_consumo"]) == (4.0, 8800.0)
    assert [f["insumo"] for f in r["insumos"]] == ["Pollo", "Gaseosa"]  # del más costoso al menos
    assert r["resumen"] == {"costo_consumo": 14800.0, "costo_merma": 6000.0}


# ------------------------------------------------------- RF-11.4 Productos


def test_cp_11_4_1_productos_mas_vendidos(client, admin_headers, negocio, hoy):
    """CP-11.4-1 | RF-11.4 | Ranking por unidades con ingresos y margen, y productos sin ventas."""
    HOY = hoy.isoformat()
    r = _get(client, admin_headers, f"/api/reportes/productos?desde={HOY}&hasta={HOY}")
    assert [(p["producto"], p["cantidad"], p["total"], p["margen"]) for p in r["vendidos"]] == [
        ("Gaseosa 400 ml", 4, 18000.0, 51.1),   # (18.000 − 4 × 2.200) / 18.000
        ("Bandeja", 2, 44000.0, 86.4),          # (44.000 − 2 × 3.000) / 44.000
    ]
    assert r["sin_ventas"] == ["Arroz con leche"]


# ------------------------------------------------------- RF-11.5 Histórico


def test_cp_11_5_1_informacion_historica(client, admin_headers, negocio):
    """CP-11.5-1 | RF-11.5 | Resumen mes a mes; el mes actual trae las ventas de hoy."""
    r = _get(client, admin_headers, "/api/reportes/historico?meses=3")
    assert len(r) == 3
    actual = r[-1]
    assert (actual["ventas"], actual["total"], actual["ganancia"]) == (2, 62000.0, 47200.0)
    assert r[0]["ventas"] == 0


# ------------------------------------------------------- RF-11.6 Estadísticas


def test_cp_11_6_1_estadisticas(client, admin_headers, negocio, hoy):
    """CP-11.6-1 | RF-11.6 | Indicadores, cobertura del inventario y recomendaciones."""
    HOY = hoy.isoformat()
    r = _get(client, admin_headers, f"/api/reportes/estadisticas?desde={HOY}&hasta={HOY}")
    ind = r["indicadores"]
    assert (ind["ventas"], ind["total"], ind["ticket_promedio"]) == (2, 62000.0, 31000.0)
    assert ind["producto_estrella"] == "Gaseosa 400 ml"
    assert ind["producto_menor_margen"] == "Gaseosa 400 ml"
    assert ind["variacion_total"] is None   # ayer no hubo ventas para comparar
    # Gaseosa: 20 unidades al ritmo de 4 por día → 5 días; pollo: 4 KG a 0,5 por día → 8 días
    assert [(c["insumo"], c["dias"]) for c in r["cobertura"]] == [("Gaseosa", 5.0), ("Pollo", 8.0)]
    texto = " ".join(r["recomendaciones"])
    assert "insumo(s) agotado(s)" in texto
    assert "día de más ventas" in texto


def test_cp_11_6_2_alerta_de_cobertura_y_caida(client, admin_headers, negocio, hoy):
    """CP-11.6-2 | RF-11.6 | Recomienda comprar si un insumo alcanza para menos de 3 días y
    avisa cuando las ventas caen frente al periodo anterior."""
    HOY = hoy.isoformat()
    # Las ventas de hoy se pasan a ayer: hoy no hay ventas y ayer sí → caída del 100 %
    for venta in Venta.query.all():
        venta.created_at = venta.created_at - timedelta(days=1)
    db.session.commit()
    r = _get(client, admin_headers, f"/api/reportes/estadisticas?desde={HOY}&hasta={HOY}")
    assert r["indicadores"]["variacion_total"] == -100.0
    assert any("bajaron 100.0 %" in rec for rec in r["recomendaciones"])

    ayer = (hoy - timedelta(days=1)).isoformat()
    db.session.get(Insumo, negocio["pollo"]).stock_actual = 1  # 1 KG a 0,5 por día = 2 días
    db.session.commit()
    r = _get(client, admin_headers, f"/api/reportes/estadisticas?desde={ayer}&hasta={ayer}")
    assert any("'Pollo' alcanza para 2.0 días" in rec for rec in r["recomendaciones"])


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_22_solo_administrador(client, negocio):
    """CP-SEG-22 | Seguridad | Los reportes son solo del ADMINISTRADOR: el CAJERO recibe 403."""
    crear_usuario("CAJERO", "caja@stockpot.test")
    caja = iniciar_sesion(client, "caja@stockpot.test")
    for reporte in ("inventario", "ventas", "consumo", "productos", "historico", "estadisticas"):
        assert client.get(f"/api/reportes/{reporte}", headers=caja).status_code == 403
