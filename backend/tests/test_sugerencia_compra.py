"""Casos de prueba: sugerencia de compra (alertas de stock mínimo -> órdenes de compra).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import DetalleOrdenCompra, Insumo, OrdenCompra, Proveedor, ProveedorInsumo, Usuario

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def bodega(admin_headers):
    """Pollo 3/5 KG y arroz 8/10 KG (bajos), gaseosa 10/24 UNIDAD (baja), sal 5/1 (bien) y
    limón 1/3 KG (bajo, sin proveedor). Avícola vende pollo a 13.000; Granos vende arroz a
    4.200, gaseosa a 2.000 y pollo más caro (14.000); un proveedor inactivo lo vende a 9.000."""
    insumos = {
        "pollo": Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG", stock_actual=3, stock_minimo=5, costo_unitario=13000),
        "arroz": Insumo(codigo="INS-001", nombre="Arroz", unidad_medida="KG", stock_actual=8, stock_minimo=10, costo_unitario=4200),
        "gaseosa": Insumo(codigo="INS-011", nombre="Gaseosa", unidad_medida="UNIDAD", stock_actual=10, stock_minimo=24, costo_unitario=2200),
        "sal": Insumo(codigo="INS-008", nombre="Sal", unidad_medida="KG", stock_actual=5, stock_minimo=1, costo_unitario=1500),
        "limon": Insumo(codigo="INS-012", nombre="Limón", unidad_medida="KG", stock_actual=1, stock_minimo=3, costo_unitario=4000),
    }
    avicola = Proveedor(nit="900111", razon_social="Avícola Norte")
    granos = Proveedor(nit="900222", razon_social="Granos del Valle")
    cerrado = Proveedor(nit="900333", razon_social="Proveedor Cerrado", activo=False)
    db.session.add_all([*insumos.values(), avicola, granos, cerrado])
    db.session.flush()
    db.session.add_all([
        ProveedorInsumo(proveedor=avicola, insumo=insumos["pollo"], precio_referencia=13000),
        ProveedorInsumo(proveedor=granos, insumo=insumos["pollo"], precio_referencia=14000),
        ProveedorInsumo(proveedor=granos, insumo=insumos["arroz"], precio_referencia=4200),
        ProveedorInsumo(proveedor=granos, insumo=insumos["gaseosa"], precio_referencia=2000),
        ProveedorInsumo(proveedor=cerrado, insumo=insumos["pollo"], precio_referencia=9000),
    ])
    db.session.commit()
    return {**{k: v.id for k, v in insumos.items()}, "avicola": avicola.id, "granos": granos.id}


def _sugerencia(client, headers):
    r = client.get("/api/ordenes-compra/sugerencia", headers=headers)
    assert r.status_code == 200
    return r.get_json()


def _linea(sugerencia, insumo_id):
    return next(l for g in sugerencia["grupos"] for l in g["lineas"] if l["insumo_id"] == insumo_id)


def test_cp_sug_1_cantidades_y_proveedor_mas_barato(client, admin_headers, bodega):
    """CP-SUG-1 | Compras | Se pide hasta el doble del mínimo, redondeado hacia arriba, al
    proveedor activo más barato, agrupado por proveedor."""
    s = _sugerencia(client, admin_headers)

    assert [g["proveedor"] for g in s["grupos"]] == ["Avícola Norte", "Granos del Valle"]
    pollo = _linea(s, bodega["pollo"])
    assert pollo["cantidad"] == 7 and pollo["precio_unitario"] == 13000 and pollo["subtotal"] == 91000
    assert [p["proveedor"] for p in pollo["proveedores"]] == ["Avícola Norte", "Granos del Valle"]  # sin el inactivo
    assert _linea(s, bodega["arroz"])["cantidad"] == 12
    assert _linea(s, bodega["gaseosa"])["cantidad"] == 38  # 48 − 10, unidades enteras
    granos = next(g for g in s["grupos"] if g["proveedor"] == "Granos del Valle")
    assert granos["total"] == 12 * 4200 + 38 * 2000


def test_cp_sug_2_sin_proveedor_y_stock_suficiente(client, admin_headers, bodega):
    """CP-SUG-2 | Compras | Un insumo bajo sin proveedor queda aparte; uno con stock suficiente
    no aparece."""
    s = _sugerencia(client, admin_headers)
    assert [i["insumo"] for i in s["sin_proveedor"]] == ["Limón"] and s["sin_proveedor"][0]["cantidad"] == 5
    todos = [l["insumo"] for g in s["grupos"] for l in g["lineas"]] + [i["insumo"] for i in s["sin_proveedor"]]
    assert "Sal" not in todos


def test_cp_sug_3_descuenta_lo_que_viene_en_camino(client, admin_headers, bodega):
    """CP-SUG-3 | Compras | Lo ya pedido en órdenes pendientes o enviadas se descuenta; si
    alcanza, el insumo pasa a «cubiertos». Las órdenes recibidas o canceladas no cuentan."""
    admin = Usuario.query.filter_by(email="admin@stockpot.test").one()
    for estado, insumo, cantidad in (("PENDIENTE", "arroz", 5), ("ENVIADA", "pollo", 10), ("CANCELADA", "gaseosa", 99)):
        orden = OrdenCompra(codigo=f"OC-{estado}", proveedor_id=bodega["granos"], usuario=admin, estado=estado)
        orden.detalles.append(DetalleOrdenCompra(insumo_id=bodega[insumo], cantidad=cantidad, precio_unitario=1, subtotal=cantidad))
        db.session.add(orden)
    db.session.commit()

    s = _sugerencia(client, admin_headers)
    arroz = _linea(s, bodega["arroz"])
    assert arroz["en_camino"] == 5 and arroz["cantidad"] == 7  # 20 − 8 − 5
    assert [c["insumo"] for c in s["cubiertos"]] == ["Pollo"]  # 3 + 10 en camino ≥ 10
    assert _linea(s, bodega["gaseosa"])["cantidad"] == 38  # la cancelada no cuenta


def test_cp_sug_4_crear_ordenes(client, admin_headers, bodega):
    """CP-SUG-4 | RF-02.6 | Con las líneas revisadas se crea una orden PENDIENTE por proveedor,
    con su total; después esos insumos ya figuran en camino."""
    r = client.post("/api/ordenes-compra/sugerencia", headers=admin_headers, json={
        "fecha_entrega_estimada": "2026-11-20",
        "lineas": [
            {"proveedor_id": bodega["avicola"], "insumo_id": bodega["pollo"], "cantidad": 8, "precio_unitario": 13000},
            {"proveedor_id": bodega["granos"], "insumo_id": bodega["arroz"], "cantidad": 12, "precio_unitario": 4200},
            {"proveedor_id": bodega["granos"], "insumo_id": bodega["gaseosa"], "cantidad": 38, "precio_unitario": 2000},
        ]})
    assert r.status_code == 201
    ordenes = {o["proveedor"]: o for o in r.get_json()}
    assert set(ordenes) == {"Avícola Norte", "Granos del Valle"}
    assert ordenes["Avícola Norte"]["total"] == 104000 and ordenes["Avícola Norte"]["estado"] == "PENDIENTE"
    assert len(ordenes["Granos del Valle"]["detalles"]) == 2
    assert ordenes["Granos del Valle"]["observaciones"] == "Sugerida por stock mínimo"

    s = _sugerencia(client, admin_headers)
    assert {c["insumo"] for c in s["cubiertos"]} == {"Pollo", "Arroz", "Gaseosa"}
    assert s["grupos"] == []


def test_cp_sug_5_todo_o_nada(client, admin_headers, bodega):
    """CP-SUG-5 | RF-02.6 | Si una línea no es válida no se crea ninguna orden; sin líneas → 422."""
    r = client.post("/api/ordenes-compra/sugerencia", headers=admin_headers, json={"lineas": [
        {"proveedor_id": bodega["avicola"], "insumo_id": bodega["pollo"], "cantidad": 8, "precio_unitario": 13000},
        {"proveedor_id": bodega["granos"], "insumo_id": bodega["arroz"], "cantidad": 0, "precio_unitario": 4200},
    ]})
    assert r.status_code == 422
    assert OrdenCompra.query.count() == 0
    assert client.post("/api/ordenes-compra/sugerencia", headers=admin_headers, json={"lineas": []}).status_code == 422


def test_cp_seg_43_permisos_de_sugerencia(client, bodega):
    """CP-SEG-43 | Compras | Sin sesión 401; el MESERO (sin compras) no ve ni crea la sugerencia."""
    assert client.get("/api/ordenes-compra/sugerencia").status_code == 401
    crear_usuario("MESERO", "mesero2@stockpot.test")
    mesero = iniciar_sesion(client, "mesero2@stockpot.test")
    assert client.get("/api/ordenes-compra/sugerencia", headers=mesero).status_code == 403
    assert client.post("/api/ordenes-compra/sugerencia", headers=mesero, json={"lineas": []}).status_code == 403
