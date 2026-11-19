"""Casos de prueba: turnos y cierre de caja (arqueo).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import Insumo, Producto, Receta

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def cajero_headers(client):
    crear_usuario("CAJERO", "caja@stockpot.test")
    return iniciar_sesion(client, "caja@stockpot.test")


@pytest.fixture()
def gaseosa():
    """Gaseosa de $4.500 (1 unidad de inventario por venta)."""
    insumo = Insumo(codigo="INS-011", nombre="Gaseosa", unidad_medida="UNIDAD", stock_actual=50, costo_unitario=2200)
    producto = Producto(codigo="PRD-006", nombre="Gaseosa 400 ml", categoria="BEBIDA", precio_venta=4500,
                        receta=[Receta(insumo=insumo, cantidad=1)])
    db.session.add_all([insumo, producto])
    db.session.commit()
    return producto.id


def _vender(client, headers, producto, cantidad, metodo, **extra):
    """Venta de mostrador pagada de una vez (crea un pago aprobado)."""
    r = client.post("/api/ventas", headers=headers, json={
        "items": [{"producto_id": producto, "cantidad": cantidad}], "metodo": metodo, **extra})
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _abrir(client, headers, base=100000):
    return client.post("/api/caja/abrir", headers=headers, json={"base_inicial": base})


def _cerrar(client, headers, efectivo, tarjeta=0, transferencia=0, **extra):
    return client.post("/api/caja/cerrar", headers=headers, json={
        "contado_efectivo": efectivo, "contado_tarjeta": tarjeta, "contado_transferencia": transferencia, **extra})


def test_cp_caj_1_abrir_caja(client, cajero_headers):
    """CP-CAJ-1 | Caja | El cajero abre la caja con su base; el turno queda ABIERTO con quién y cuándo."""
    r = _abrir(client, cajero_headers, 150000)
    assert r.status_code == 201
    turno = r.get_json()
    assert turno["estado"] == "ABIERTO" and turno["base_inicial"] == 150000
    assert turno["abierto_por"] == "Prueba Cajero" and turno["abierto_en"]

    actual = client.get("/api/caja/turno", headers=cajero_headers).get_json()["turno"]["actual"]
    assert actual["esperado"] == {"efectivo": 150000, "tarjeta": 0, "transferencia": 0}


def test_cp_caj_2_validaciones_de_apertura(client, cajero_headers):
    """CP-CAJ-2 | Caja | Base negativa o no numérica → 422; abrir dos veces → 409."""
    assert _abrir(client, cajero_headers, -1).status_code == 422
    assert _abrir(client, cajero_headers, "mucho").status_code == 422
    assert _abrir(client, cajero_headers).status_code == 201
    r = _abrir(client, cajero_headers)
    assert r.status_code == 409 and "ya está abierta" in r.get_json()["error"]


def test_cp_caj_3_esperado_por_metodo(client, cajero_headers, gaseosa):
    """CP-CAJ-3 | Caja | Lo esperado suma la base al efectivo y separa tarjeta y transferencia;
    los pagos anulados no cuentan."""
    _abrir(client, cajero_headers, 100000)
    _vender(client, cajero_headers, gaseosa, 2, "EFECTIVO", recibido=10000)  # 9.000 en efectivo
    _vender(client, cajero_headers, gaseosa, 1, "TARJETA", referencia="A1")   # 4.500
    _vender(client, cajero_headers, gaseosa, 3, "TRANSFERENCIA", referencia="T9")  # 13.500

    actual = client.get("/api/caja/turno", headers=cajero_headers).get_json()["turno"]["actual"]
    assert actual["esperado"] == {"efectivo": 109000, "tarjeta": 4500, "transferencia": 13500}
    assert actual["ventas_efectivo"] == 9000 and actual["num_pagos"] == 3


def test_cp_caj_4_cierre_cuadrado(client, cajero_headers, gaseosa):
    """CP-CAJ-4 | Caja | Si lo contado es igual a lo esperado, la caja cuadra (diferencia 0) y
    se cierra sin observación."""
    _abrir(client, cajero_headers, 50000)
    _vender(client, cajero_headers, gaseosa, 2, "EFECTIVO")
    _vender(client, cajero_headers, gaseosa, 1, "TARJETA", referencia="A1")

    r = _cerrar(client, cajero_headers, efectivo=59000, tarjeta=4500)
    assert r.status_code == 200
    turno = r.get_json()
    assert turno["estado"] == "CERRADO" and turno["cerrado_por"] == "Prueba Cajero"
    assert turno["diferencia"] == {"efectivo": 0, "tarjeta": 0, "transferencia": 0, "total": 0}
    assert turno["num_pagos"] == 2
    assert client.get("/api/caja/turno", headers=cajero_headers).get_json()["turno"] is None


def test_cp_caj_5_faltante_exige_explicacion(client, cajero_headers, gaseosa):
    """CP-CAJ-5 | Caja | Si falta o sobra dinero hay que explicarlo; la diferencia queda guardada
    por método (negativo = faltante)."""
    _abrir(client, cajero_headers, 50000)
    _vender(client, cajero_headers, gaseosa, 2, "EFECTIVO")  # se espera 59.000

    r = _cerrar(client, cajero_headers, efectivo=57000)
    assert r.status_code == 422 and r.get_json()["diferencia"] == -2000
    assert client.get("/api/caja/turno", headers=cajero_headers).get_json()["turno"] is not None  # sigue abierta

    r = _cerrar(client, cajero_headers, efectivo=57000, observacion="Se dio mal un cambio")
    assert r.status_code == 200
    turno = r.get_json()
    assert turno["diferencia"]["efectivo"] == -2000 and turno["diferencia"]["total"] == -2000
    assert turno["observacion"] == "Se dio mal un cambio"


def test_cp_caj_6_validaciones_de_cierre(client, cajero_headers):
    """CP-CAJ-6 | Caja | Cerrar sin caja abierta → 409; sin un conteo o con uno negativo → 422."""
    assert _cerrar(client, cajero_headers, efectivo=0).status_code == 409
    _abrir(client, cajero_headers, 0)
    r = client.post("/api/caja/cerrar", headers=cajero_headers, json={"contado_efectivo": 0, "contado_tarjeta": 0})
    assert r.status_code == 422 and r.get_json()["campo"] == "contado_transferencia"
    assert _cerrar(client, cajero_headers, efectivo=-5).status_code == 422


def test_cp_caj_7_historial_y_detalle(client, cajero_headers, gaseosa):
    """CP-CAJ-7 | Caja | El historial lista los cierres y el detalle trae los pagos del turno;
    lo que se cobra después del cierre no cambia ese turno."""
    _abrir(client, cajero_headers, 0)
    _vender(client, cajero_headers, gaseosa, 1, "EFECTIVO")
    cerrado = _cerrar(client, cajero_headers, efectivo=4500).get_json()
    _abrir(client, cajero_headers, 0)
    _vender(client, cajero_headers, gaseosa, 1, "EFECTIVO")  # segundo turno

    historial = client.get("/api/caja/turnos", headers=cajero_headers).get_json()
    assert [t["id"] for t in historial] == [cerrado["id"]]
    detalle = client.get(f"/api/caja/turnos/{cerrado['id']}", headers=cajero_headers).get_json()
    assert detalle["esperado"]["efectivo"] == 4500 and detalle["contado"]["efectivo"] == 4500
    assert len(detalle["pagos"]) >= 1
    assert client.get("/api/caja/turnos/999", headers=cajero_headers).status_code == 404
    assert client.get("/api/caja/turnos?desde=ayer", headers=cajero_headers).status_code == 422


def test_cp_seg_42_permisos_de_caja(client, cajero_headers, mesero_headers):
    """CP-SEG-42 | Caja | Sin sesión 401; el MESERO (sin permisos de pagos) no ve ni abre la caja."""
    assert client.get("/api/caja/turno").status_code == 401
    assert client.get("/api/caja/turno", headers=mesero_headers).status_code == 403
    assert _abrir(client, mesero_headers).status_code == 403
    assert _cerrar(client, mesero_headers, efectivo=0).status_code == 403
