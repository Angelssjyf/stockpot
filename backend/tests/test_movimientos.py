"""Casos de prueba: inventario completo (RF-03.4 a RF-03.8) y su relación con compras.

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import Insumo, MovimientoInventario, Proveedor

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def arroz(client, admin_headers):
    """Insumo con 10 KG de stock (entrada inicial por ajuste) y mínimo de 4."""
    r = client.post("/api/insumos", headers=admin_headers, json={
        "codigo": "INS-001", "nombre": "Arroz", "unidad_medida": "KG",
        "stock_minimo": 4, "costo_unitario": 4200,
    })
    insumo = r.get_json()
    client.post(f"/api/insumos/{insumo['id']}/movimientos", headers=admin_headers,
                json={"tipo": "ENTRADA", "motivo": "AJUSTE", "cantidad": 10})
    return insumo


def _mover(client, headers, insumo_id, tipo, motivo, cantidad, **extra):
    return client.post(f"/api/insumos/{insumo_id}/movimientos", headers=headers,
                       json={"tipo": tipo, "motivo": motivo, "cantidad": cantidad, **extra})


# ------------------------------------------------------- RF-03.4 Entradas


def test_cp_03_4_1_registrar_entrada(client, admin_headers, arroz):
    """CP-03.4-1 | RF-03.4 | Una entrada suma stock y deja el movimiento con quién lo hizo."""
    r = _mover(client, admin_headers, arroz["id"], "ENTRADA", "COMPRA", 5.5,
               observacion="Compra en plaza")
    assert r.status_code == 201
    body = r.get_json()
    assert body["insumo"]["stock_actual"] == 15.5
    assert body["movimiento"]["stock_resultante"] == 15.5
    assert body["movimiento"]["usuario"] == "Prueba Administrador"
    assert body["movimiento"]["observacion"] == "Compra en plaza"


def test_cp_03_4_2_motivo_invalido(client, admin_headers, arroz):
    """CP-03.4-2 | RF-03.4 | Una entrada con motivo de salida (MERMA) → 422."""
    assert _mover(client, admin_headers, arroz["id"], "ENTRADA", "MERMA", 1).status_code == 422


@pytest.mark.parametrize("cantidad", [0, -2, "mucho"])
def test_cp_03_4_3_cantidad_invalida(client, admin_headers, arroz, cantidad):
    """CP-03.4-3 | RF-03.4 | Cantidad en cero, negativa o no numérica → 422."""
    assert _mover(client, admin_headers, arroz["id"], "ENTRADA", "AJUSTE", cantidad).status_code \
        == 422


# ------------------------------------------------------- RF-03.5 Salidas


def test_cp_03_5_1_registrar_salida(client, admin_headers, arroz):
    """CP-03.5-1 | RF-03.5 | Una salida por merma resta stock."""
    r = _mover(client, admin_headers, arroz["id"], "SALIDA", "MERMA", 2.25)
    assert r.status_code == 201
    assert r.get_json()["insumo"]["stock_actual"] == 7.75


def test_cp_03_5_2_stock_insuficiente(client, admin_headers, arroz):
    """CP-03.5-2 | RF-03.5 | Sacar más de lo que hay → 409 y el stock no cambia."""
    r = _mover(client, admin_headers, arroz["id"], "SALIDA", "CONSUMO", 11)
    assert r.status_code == 409
    assert "Stock insuficiente" in r.get_json()["error"]
    assert float(db.session.get(Insumo, arroz["id"]).stock_actual) == 10.0
    assert MovimientoInventario.query.filter_by(tipo="SALIDA").count() == 0


def test_cp_03_5_3_insumo_inactivo(client, admin_headers, arroz):
    """CP-03.5-3 | RF-03.5 | No se mueve el stock de un insumo inactivo → 409."""
    client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers, json={"activo": False})
    assert _mover(client, admin_headers, arroz["id"], "SALIDA", "MERMA", 1).status_code == 409


def test_cp_03_5_4_historial_de_movimientos(client, admin_headers, arroz):
    """CP-03.5-4 | RF-03.4, RF-03.5 | El historial muestra los movimientos, el más reciente primero."""
    _mover(client, admin_headers, arroz["id"], "SALIDA", "MERMA", 1)
    r = client.get(f"/api/insumos/{arroz['id']}/movimientos", headers=admin_headers)
    movimientos = r.get_json()
    assert [(m["tipo"], m["motivo"]) for m in movimientos] == [("SALIDA", "MERMA"),
                                                               ("ENTRADA", "AJUSTE")]
    assert [m["stock_resultante"] for m in movimientos] == [9.0, 10.0]


# ------------------------------------------------------- RF-03.6 Existencias


def test_cp_03_6_1_consultar_existencias(client, admin_headers, arroz):
    """CP-03.6-1 | RF-03.6 | Existencias con estado, valor del inventario y resumen."""
    client.post("/api/insumos", headers=admin_headers,
                json={"codigo": "INS-002", "nombre": "Sal", "unidad_medida": "KG"})
    r = client.get("/api/inventario/existencias", headers=admin_headers)
    assert r.status_code == 200
    body = r.get_json()
    filas = {f["nombre"]: f for f in body["insumos"]}
    assert filas["Arroz"]["estado_stock"] == "OK"
    assert filas["Arroz"]["valor"] == 42000.0          # 10 KG × $4.200
    assert filas["Sal"]["estado_stock"] == "AGOTADO"   # stock 0
    assert body["resumen"] == {"total_insumos": 2, "bajos": 0, "agotados": 1,
                               "valor_total": 42000.0}


# ------------------------------------------------------- RF-03.7 Niveles mínimos


def test_cp_03_7_1_establecer_minimo(client, admin_headers, arroz):
    """CP-03.7-1 | RF-03.7 | Cambiar el stock mínimo y el costo de un insumo."""
    r = client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers,
                   json={"stock_minimo": 12, "costo_unitario": 4500})
    assert r.get_json()["stock_minimo"] == 12.0
    assert r.get_json()["costo_unitario"] == 4500.0
    assert r.get_json()["estado_stock"] == "BAJO"  # 10 <= 12


def test_cp_03_7_2_minimo_negativo(client, admin_headers, arroz):
    """CP-03.7-2 | RF-03.7 | Un mínimo negativo → 422."""
    r = client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers, json={"stock_minimo": -1})
    assert r.status_code == 422


# ------------------------------------------------------- RF-03.8 Alertas


def test_cp_03_8_1_alertas_de_stock(client, admin_headers, arroz):
    """CP-03.8-1 | RF-03.8 | La alerta aparece al llegar al mínimo y desaparece al reponer."""
    alertas = lambda: client.get("/api/inventario/alertas", headers=admin_headers).get_json()  # noqa: E731
    assert alertas() == []

    _mover(client, admin_headers, arroz["id"], "SALIDA", "CONSUMO", 7)  # queda 3, mínimo 4
    lista = alertas()
    assert [(a["nombre"], a["estado_stock"], a["faltante"]) for a in lista] == [("Arroz", "BAJO", 1.0)]

    _mover(client, admin_headers, arroz["id"], "ENTRADA", "COMPRA", 10)  # queda 13
    assert alertas() == []


def test_cp_03_8_2_agotados_primero(client, admin_headers, arroz):
    """CP-03.8-2 | RF-03.8 | Los insumos agotados aparecen primero en las alertas."""
    _mover(client, admin_headers, arroz["id"], "SALIDA", "CONSUMO", 8)  # queda 2 (BAJO)
    client.post("/api/insumos", headers=admin_headers,
                json={"codigo": "INS-002", "nombre": "Sal", "unidad_medida": "KG"})  # stock 0
    lista = client.get("/api/inventario/alertas", headers=admin_headers).get_json()
    assert [(a["nombre"], a["estado_stock"]) for a in lista] == [("Sal", "AGOTADO"),
                                                                ("Arroz", "BAJO")]


# ------------------------------------------------------- Integración con compras


def test_cp_03_9_1_compra_recibida_deja_movimiento(client, admin_headers, arroz):
    """CP-03.9-1 | RF-02.8, RF-03.4 | Recibir una compra crea una ENTRADA por COMPRA y actualiza el costo."""
    proveedor = Proveedor(nit="900", razon_social="La Cosecha")
    db.session.add(proveedor)
    db.session.commit()
    orden = client.post("/api/ordenes-compra", headers=admin_headers, json={
        "proveedor_id": proveedor.id,
        "detalles": [{"insumo_id": arroz["id"], "cantidad": 20, "precio_unitario": 4600}],
    }).get_json()
    for estado in ("ENVIADA", "RECIBIDA"):
        client.patch(f"/api/ordenes-compra/{orden['id']}/estado", headers=admin_headers,
                     json={"estado": estado})

    movimiento = client.get(f"/api/insumos/{arroz['id']}/movimientos",
                            headers=admin_headers).get_json()[0]
    assert (movimiento["tipo"], movimiento["motivo"]) == ("ENTRADA", "COMPRA")
    assert movimiento["orden_compra"] == orden["codigo"]
    assert movimiento["stock_resultante"] == 30.0
    insumo = client.get(f"/api/insumos/{arroz['id']}", headers=admin_headers).get_json()
    assert insumo["costo_unitario"] == 4600.0


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_17_cocinero_no_mueve_stock(client, arroz):
    """CP-SEG-17 | Seguridad | Un COCINERO (solo inventario.ver) ve alertas pero no mueve stock → 403."""
    crear_usuario("COCINERO", "cocina@stockpot.test")
    headers = iniciar_sesion(client, "cocina@stockpot.test")
    assert client.get("/api/inventario/alertas", headers=headers).status_code == 200
    assert _mover(client, headers, arroz["id"], "SALIDA", "MERMA", 1).status_code == 403
