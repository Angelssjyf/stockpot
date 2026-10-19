"""Casos de prueba: ventas y consumo de insumos (RF-10.1 a RF-10.6).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import Insumo, Orden, Producto, Receta

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def cajero_headers(client):
    crear_usuario("CAJERO", "caja@stockpot.test")
    return iniciar_sesion(client, "caja@stockpot.test")


@pytest.fixture()
def carta():
    """Bandeja ($22.000: 0,25 KG de pollo a $12.000) y gaseosa ($4.500: 1 unidad a $2.200)."""
    pollo = Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG",
                   stock_actual=5, costo_unitario=12000)
    gaseosa = Insumo(codigo="INS-011", nombre="Gaseosa", unidad_medida="UNIDAD",
                     stock_actual=24, costo_unitario=2200)
    bandeja = Producto(codigo="PRD-001", nombre="Bandeja", categoria="PLATO_FUERTE",
                       precio_venta=22000, receta=[Receta(insumo=pollo, cantidad=0.25)])
    bebida = Producto(codigo="PRD-006", nombre="Gaseosa 400 ml", categoria="BEBIDA",
                      precio_venta=4500, receta=[Receta(insumo=gaseosa, cantidad=1)])
    db.session.add_all([pollo, gaseosa, bandeja, bebida])
    db.session.commit()
    return {"bandeja": bandeja.id, "gaseosa": bebida.id, "pollo": pollo.id,
            "insumo_gaseosa": gaseosa.id}


def _vender(client, headers, items, **pago):
    datos = {"items": items, "metodo": "EFECTIVO", **pago}
    return client.post("/api/ventas", headers=headers, json=datos)


@pytest.fixture()
def dos_ventas(client, cajero_headers, carta):
    """Venta 1: 2 bandejas + 1 gaseosa ($48.500). Venta 2: 3 gaseosas ($13.500)."""
    primera = _vender(client, cajero_headers, [{"producto_id": carta["bandeja"], "cantidad": 2},
                                               {"producto_id": carta["gaseosa"], "cantidad": 1}],
                      recibido=50000)
    segunda = _vender(client, cajero_headers, [{"producto_id": carta["gaseosa"], "cantidad": 3}],
                      metodo="TARJETA")
    assert primera.status_code == 201, primera.get_json()
    assert segunda.status_code == 201, segunda.get_json()
    return [primera.get_json()["venta"], segunda.get_json()["venta"]]


# ------------------------------------------------------- RF-10.1 Registrar ventas


def test_cp_10_1_1_venta_de_mostrador(client, cajero_headers, carta):
    """CP-10.1-1 | RF-10.1, RF-09.1 | La venta de mostrador cobra todo, calcula el cambio y cierra la orden."""
    r = _vender(client, cajero_headers, [{"producto_id": carta["gaseosa"], "cantidad": 2}],
                recibido=10000)
    assert r.status_code == 201
    body = r.get_json()
    assert body["venta"]["codigo"] == "VTA-000001"
    assert body["venta"]["tipo"] == "LLEVAR"
    assert body["venta"]["total"] == 9000.0
    assert body["pago"]["cambio"] == 1000.0
    assert db.session.get(Orden, body["venta"]["orden_id"]).estado == "CERRADA"


@pytest.mark.parametrize("items, codigo", [([], 422), ([{"producto_id": 99, "cantidad": 1}], 422)])
def test_cp_10_1_2_venta_invalida(client, cajero_headers, carta, items, codigo):
    """CP-10.1-2 | RF-10.1 | Sin productos o con un producto inexistente → 422 y no se crea nada."""
    assert _vender(client, cajero_headers, items).status_code == codigo
    assert Orden.query.count() == 0


def test_cp_10_1_3_efectivo_insuficiente(client, cajero_headers, carta):
    """CP-10.1-3 | RF-10.1, RF-09.2 | Si el efectivo recibido no alcanza → 422 y no queda la orden."""
    r = _vender(client, cajero_headers, [{"producto_id": carta["bandeja"], "cantidad": 1}],
                recibido=5000)
    assert r.status_code == 422
    assert Orden.query.count() == 0


# ------------------------------------------------------- RF-10.2 Consultar ventas


def test_cp_10_2_1_consultar_ventas(client, cajero_headers, dos_ventas):
    """CP-10.2-1 | RF-10.2 | Lista las ventas (la más reciente primero) con total, ticket y ganancia."""
    r = client.get("/api/ventas", headers=cajero_headers).get_json()
    assert [v["codigo"] for v in r["ventas"]] == ["VTA-000002", "VTA-000001"]
    assert r["resumen"] == {
        "ventas": 2, "total": 62000.0, "ticket_promedio": 31000.0,
        "costo_insumos": 14800.0,   # 0,5 × 12.000 + 4 × 2.200
        "ganancia": 47200.0,
    }
    vacio = client.get("/api/ventas?desde=2000-01-01&hasta=2000-01-31", headers=cajero_headers)
    assert vacio.get_json()["ventas"] == []
    assert client.get("/api/ventas?desde=hoy", headers=cajero_headers).status_code == 422


# ------------------------------------------------------- RF-10.3 / RF-10.4 Detalle


def test_cp_10_3_1_consumo_de_la_venta(client, cajero_headers, dos_ventas, carta):
    """CP-10.3-1 | RF-10.3, RF-10.4 | La venta muestra sus productos, el consumo de insumos y su costo,
    y el inventario baja."""
    venta = client.get(f"/api/ventas/{dos_ventas[0]['id']}", headers=cajero_headers).get_json()
    assert [(p["producto"], p["cantidad"]) for p in venta["productos"]] == \
        [("Bandeja", 2), ("Gaseosa 400 ml", 1)]
    consumos = {c["insumo"]: (c["cantidad"], c["costo"]) for c in venta["consumos"]}
    assert consumos == {"Pollo": (0.5, 6000.0), "Gaseosa": (1.0, 2200.0)}
    assert venta["costo_insumos"] == 8200.0
    assert venta["ganancia"] == 40300.0
    assert [p["metodo"] for p in venta["pagos"]] == ["EFECTIVO"]
    assert float(db.session.get(Insumo, carta["insumo_gaseosa"]).stock_actual) == 20.0
    assert client.get("/api/ventas/999", headers=cajero_headers).status_code == 404


# ------------------------------------------------------- RF-10.5 Más vendidos


def test_cp_10_5_1_productos_mas_vendidos(client, cajero_headers, dos_ventas):
    """CP-10.5-1 | RF-10.5 | Ordena los productos por unidades vendidas."""
    r = client.get("/api/ventas/mas-vendidos", headers=cajero_headers).get_json()
    assert [(p["producto"], p["cantidad"], p["total"]) for p in r] == \
        [("Gaseosa 400 ml", 4, 18000.0), ("Bandeja", 2, 44000.0)]
    assert len(client.get("/api/ventas/mas-vendidos?limite=1", headers=cajero_headers).get_json()) == 1


def test_cp_10_5_2_solo_cuentan_ventas_cerradas(client, cajero_headers, carta, dos_ventas):
    """CP-10.5-2 | RF-10.5 | Un pedido sin pagar no cuenta como vendido."""
    cliente = client.post("/api/clientes", headers=cajero_headers,
                          json={"nombre": "Ana", "telefono": "3000000001", "direccion": "Cra 1"}).get_json()
    client.post("/api/domicilios", headers=cajero_headers, json={
        "cliente_id": cliente["id"], "items": [{"producto_id": carta["bandeja"], "cantidad": 9}]})
    r = client.get("/api/ventas/mas-vendidos", headers=cajero_headers).get_json()
    assert {p["producto"]: p["cantidad"] for p in r}["Bandeja"] == 2


# ------------------------------------------------------- RF-10.6 Historial de consumo


def test_cp_10_6_1_consumo_de_insumos(client, cajero_headers, dos_ventas):
    """CP-10.6-1 | RF-10.6 | Suma lo gastado de cada insumo en el periodo, del más costoso al menos."""
    r = client.get("/api/ventas/consumo", headers=cajero_headers).get_json()
    assert [(i["insumo"], i["cantidad"], i["costo"]) for i in r["insumos"]] == \
        [("Gaseosa", 4.0, 8800.0), ("Pollo", 0.5, 6000.0)]
    assert r["costo_total"] == 14800.0


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_21_quien_ve_las_ventas(client, dos_ventas, cajero_headers):
    """CP-SEG-21 | Seguridad | El CAJERO consulta ventas; el BODEGUERO no ve ventas ni vende → 403."""
    assert client.get("/api/ventas", headers=cajero_headers).status_code == 200
    crear_usuario("BODEGUERO", "bodega@stockpot.test")
    bodega = iniciar_sesion(client, "bodega@stockpot.test")
    assert client.get("/api/ventas", headers=bodega).status_code == 403
    assert _vender(client, bodega, [{"producto_id": 1, "cantidad": 1}]).status_code == 403
