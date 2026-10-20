"""Casos de prueba: pagos y comprobantes (RF-09.1 a RF-09.7).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import Insumo, MovimientoInventario, Orden, Pago, Producto, Receta, Venta

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def cajero_headers(client):
    crear_usuario("CAJERO", "caja@stockpot.test")
    return iniciar_sesion(client, "caja@stockpot.test")


@pytest.fixture()
def carta():
    """Bandeja ($22.000: 0,25 KG de pollo) y limonada ($6.000: 0,1 KG de limón)."""
    pollo = Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG",
                   stock_actual=2, costo_unitario=12000)
    limon = Insumo(codigo="INS-012", nombre="Limón", unidad_medida="KG",
                   stock_actual=1, costo_unitario=4000)
    bandeja = Producto(codigo="PRD-001", nombre="Bandeja", categoria="PLATO_FUERTE",
                       precio_venta=22000, receta=[Receta(insumo=pollo, cantidad=0.25)])
    limonada = Producto(codigo="PRD-007", nombre="Limonada", categoria="BEBIDA",
                        precio_venta=6000, receta=[Receta(insumo=limon, cantidad=0.1)])
    db.session.add_all([pollo, limon, bandeja, limonada])
    db.session.commit()
    return {"bandeja": bandeja.id, "limonada": limonada.id, "pollo": pollo.id, "limon": limon.id}


@pytest.fixture()
def domicilio(client, cajero_headers, carta):
    """Pedido a domicilio: 2 bandejas + 1 limonada + $3.000 de envío = $53.000."""
    cliente = client.post("/api/clientes", headers=cajero_headers, json={
        "nombre": "María Gómez", "telefono": "3001234567", "direccion": "Calle 45 # 27-30",
    }).get_json()
    r = client.post("/api/domicilios", headers=cajero_headers, json={
        "cliente_id": cliente["id"], "costo_envio": 3000,
        "items": [{"producto_id": carta["bandeja"], "cantidad": 2},
                  {"producto_id": carta["limonada"], "cantidad": 1}],
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _pagar(client, headers, orden_id, **datos):
    return client.post(f"/api/ordenes/{orden_id}/pagos", headers=headers, json=datos)


def _cuenta(client, headers, orden_id):
    return client.get(f"/api/ordenes/{orden_id}/cuenta", headers=headers).get_json()


# ------------------------------------------------------- RF-09.3 Total del pedido


def test_cp_09_3_1_calcular_total(client, cajero_headers, domicilio):
    """CP-09.3-1 | RF-09.3, RF-09.4 | La cuenta suma productos y envío e informa el impoconsumo incluido."""
    cuenta = _cuenta(client, cajero_headers, domicilio["orden"]["id"])
    assert cuenta["subtotal"] == 50000.0
    assert cuenta["costo_envio"] == 3000.0
    assert cuenta["total"] == 53000.0
    assert cuenta["impoconsumo_incluido"] == 3703.7  # 50.000 − 50.000 / 1,08
    assert (cuenta["pagado"], cuenta["saldo"], cuenta["estado_pago"]) == (0.0, 53000.0, "PENDIENTE")


# ------------------------------------------------------- RF-09.1 / RF-09.2 Registrar pagos


def test_cp_09_1_1_pago_parcial_en_efectivo(client, cajero_headers, domicilio):
    """CP-09.1-1 | RF-09.1, RF-09.2, RF-09.5 | Un abono en efectivo calcula el cambio y deja saldo."""
    orden_id = domicilio["orden"]["id"]
    r = _pagar(client, cajero_headers, orden_id, metodo="efectivo", monto=20000, recibido=50000)
    assert r.status_code == 201
    pago, cuenta = r.get_json()["pago"], r.get_json()["cuenta"]
    assert (pago["metodo"], pago["monto"], pago["cambio"]) == ("EFECTIVO", 20000.0, 30000.0)
    assert (cuenta["saldo"], cuenta["estado_pago"], cuenta["venta"]) == (33000.0, "PARCIAL", None)
    assert db.session.get(Orden, orden_id).estado == "ABIERTA"


def test_cp_09_1_2_completar_pago_registra_venta(client, cajero_headers, domicilio, carta):
    """CP-09.1-2 | RF-09.1, RF-10.1, RF-10.3 | Completar el total cierra la orden, crea la venta
    y descuenta el inventario de las recetas."""
    orden_id = domicilio["orden"]["id"]
    _pagar(client, cajero_headers, orden_id, metodo="EFECTIVO", monto=20000)
    r = _pagar(client, cajero_headers, orden_id, metodo="TRANSFERENCIA", monto=33000,
               referencia="M-778899")
    cuenta = r.get_json()["cuenta"]
    assert (cuenta["estado_pago"], cuenta["saldo"], cuenta["venta"]) == ("PAGADO", 0.0, "VTA-000001")
    assert r.get_json()["pago"]["referencia"] == "M-778899"
    assert db.session.get(Orden, orden_id).estado == "CERRADA"

    assert float(db.session.get(Insumo, carta["pollo"]).stock_actual) == 1.5  # 2 − 2 × 0,25
    assert float(db.session.get(Insumo, carta["limon"]).stock_actual) == 0.9
    salidas = MovimientoInventario.query.filter_by(tipo="SALIDA", motivo="CONSUMO").all()
    assert len(salidas) == 2
    assert all("VTA-000001" in m.observacion for m in salidas)


@pytest.mark.parametrize("datos, mensaje", [
    ({"metodo": "BITCOIN", "monto": 1000}, "Método de pago inválido"),
    ({"metodo": "EFECTIVO", "monto": 60000}, "supera el saldo"),
    ({"metodo": "EFECTIVO", "monto": 20000, "recibido": 10000}, "no alcanza"),
    ({"metodo": "TARJETA", "monto": 0}, "mayor que cero"),
    ({"metodo": "TARJETA", "monto": "mucho"}, "debe ser un número"),
])
def test_cp_09_2_1_pago_invalido(client, cajero_headers, domicilio, datos, mensaje):
    """CP-09.2-1 | RF-09.2 | Método inválido, monto mayor al saldo o efectivo insuficiente → 422."""
    r = _pagar(client, cajero_headers, domicilio["orden"]["id"], **datos)
    assert r.status_code == 422
    assert mensaje in r.get_json()["error"]
    assert Pago.query.count() == 0


def test_cp_09_1_3_stock_insuficiente_al_cerrar(client, cajero_headers, admin_headers, domicilio,
                                                 carta):
    """CP-09.1-3 | RF-09.1, RF-10.3 | Si al cobrar ya no alcanza un insumo → 409 y no queda el pago."""
    client.post(f"/api/insumos/{carta['pollo']}/movimientos", headers=admin_headers,
                json={"tipo": "SALIDA", "motivo": "MERMA", "cantidad": 1.8})  # quedan 0,2 KG
    r = _pagar(client, cajero_headers, domicilio["orden"]["id"], metodo="TARJETA", monto=53000)
    assert r.status_code == 409
    assert "Stock insuficiente de 'Pollo'" in r.get_json()["error"]
    assert Pago.query.count() == 0
    assert Venta.query.count() == 0


# ------------------------------------------------------- RF-09.4 Estado y anulación


def test_cp_09_4_1_anular_pago(client, cajero_headers, domicilio):
    """CP-09.4-1 | RF-09.4 | Anular un abono devuelve el saldo; no se anula dos veces ni tras cerrar."""
    orden_id = domicilio["orden"]["id"]
    pago = _pagar(client, cajero_headers, orden_id, metodo="EFECTIVO", monto=10000).get_json()["pago"]
    r = client.patch(f"/api/pagos/{pago['id']}/anular", headers=cajero_headers)
    assert r.status_code == 200
    assert (r.get_json()["cuenta"]["saldo"], r.get_json()["cuenta"]["estado_pago"]) == \
        (53000.0, "PENDIENTE")
    assert client.patch(f"/api/pagos/{pago['id']}/anular", headers=cajero_headers).status_code == 409

    total = _pagar(client, cajero_headers, orden_id, metodo="TARJETA", monto=53000).get_json()["pago"]
    assert client.patch(f"/api/pagos/{total['id']}/anular", headers=cajero_headers).status_code == 409
    assert _pagar(client, cajero_headers, orden_id, metodo="EFECTIVO", monto=1).status_code == 409


def test_cp_09_4_2_ordenes_por_cobrar(client, cajero_headers, domicilio):
    """CP-09.4-2 | RF-09.4 | Las órdenes abiertas aparecen con su saldo y salen al quedar pagadas."""
    orden_id = domicilio["orden"]["id"]
    _pagar(client, cajero_headers, orden_id, metodo="EFECTIVO", monto=13000)
    lista = client.get("/api/ordenes/por-cobrar", headers=cajero_headers).get_json()
    assert [(o["codigo"], o["saldo"], o["estado_domicilio"]) for o in lista] == \
        [("PED-000001", 40000.0, "RECIBIDO")]
    _pagar(client, cajero_headers, orden_id, metodo="EFECTIVO", monto=40000)
    assert client.get("/api/ordenes/por-cobrar", headers=cajero_headers).get_json() == []


def test_cp_09_4_3_domicilio_cancelado_no_se_cobra(client, cajero_headers, domicilio):
    """CP-09.4-3 | RF-09.4 | Un domicilio cancelado no se puede cobrar → 409."""
    client.patch(f"/api/domicilios/{domicilio['id']}/estado", headers=cajero_headers,
                 json={"estado": "CANCELADO"})
    r = _pagar(client, cajero_headers, domicilio["orden"]["id"], metodo="EFECTIVO", monto=1000)
    assert r.status_code == 409


# ------------------------------------------------------- RF-09.6 Comprobante


def test_cp_09_6_1_comprobante(client, cajero_headers, domicilio):
    """CP-09.6-1 | RF-09.6 | Sin pagos → 409; pagada → comprobante con número de venta y pagos."""
    orden_id = domicilio["orden"]["id"]
    url = f"/api/ordenes/{orden_id}/comprobante"
    assert client.get(url, headers=cajero_headers).status_code == 409

    _pagar(client, cajero_headers, orden_id, metodo="EFECTIVO", monto=53000, recibido=60000)
    comprobante = client.get(url, headers=cajero_headers).get_json()
    assert comprobante["numero"] == "VTA-000001"
    assert comprobante["restaurante"] == "StockPot Restaurante"
    assert comprobante["direccion"] == "Calle 45 # 27-30"
    assert [(p["metodo"], p["cambio"]) for p in comprobante["pagos"]] == [("EFECTIVO", 7000.0)]
    assert len(comprobante["productos"]) == 2


# ------------------------------------------------------- RF-09.7 Historial


def test_cp_09_7_1_historial_de_pagos(client, cajero_headers, domicilio):
    """CP-09.7-1 | RF-09.7 | El historial trae los pagos con su total por método y filtros."""
    orden_id = domicilio["orden"]["id"]
    anulado = _pagar(client, cajero_headers, orden_id, metodo="TARJETA", monto=5000).get_json()["pago"]
    client.patch(f"/api/pagos/{anulado['id']}/anular", headers=cajero_headers)
    _pagar(client, cajero_headers, orden_id, metodo="EFECTIVO", monto=23000)
    _pagar(client, cajero_headers, orden_id, metodo="TRANSFERENCIA", monto=30000)

    r = client.get("/api/pagos", headers=cajero_headers).get_json()
    assert len(r["pagos"]) == 3
    assert r["resumen"] == {"total": 53000.0, "anulados": 1,
                            "por_metodo": {"EFECTIVO": 23000.0, "TARJETA": 0.0,
                                           "TRANSFERENCIA": 30000.0}}
    efectivo = client.get("/api/pagos?metodo=efectivo", headers=cajero_headers).get_json()
    assert [p["monto"] for p in efectivo["pagos"]] == [23000.0]
    assert client.get("/api/pagos?desde=2000-01-01&hasta=2000-01-02",
                      headers=cajero_headers).get_json()["pagos"] == []
    assert client.get("/api/pagos?hasta=mañana", headers=cajero_headers).status_code == 422


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_20_quien_puede_cobrar(client, domicilio, mesero_headers):
    """CP-SEG-20 | Seguridad | El MESERO no ve cuentas y el DOMICILIARIO no puede cobrar → 403."""
    orden_id = domicilio["orden"]["id"]
    assert client.get(f"/api/ordenes/{orden_id}/cuenta", headers=mesero_headers).status_code == 403
    crear_usuario("DOMICILIARIO", "moto@stockpot.test")
    moto = iniciar_sesion(client, "moto@stockpot.test")
    assert _pagar(client, moto, orden_id, metodo="EFECTIVO", monto=1000).status_code == 403
