"""Casos de prueba: cocina (RF-06.1 a RF-06.7).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import PedidoMesa

from .conftest import crear_usuario, iniciar_sesion
from .test_domicilios import carta as carta_domicilio  # noqa: F401  (fixture)
from .test_domicilios import cajero_headers, cliente  # noqa: F401  (fixtures)
from .test_domicilios import _pedir as pedir_domicilio
from .test_pedidos import _accion, _pedir, carta, mesas  # noqa: F401  (fixtures)


@pytest.fixture()
def cocinero_headers(client):
    crear_usuario("COCINERO", "cocina@stockpot.test")
    return iniciar_sesion(client, "cocina@stockpot.test")


@pytest.fixture()
def en_cocina(client, mesero_headers, mesas, carta):
    """Pedido de la mesa 1 confirmado y enviado a cocina."""
    r = _pedir(client, mesero_headers, mesas[1], carta)
    pedido = r.get_json()
    _accion(client, mesero_headers, pedido["id"], "confirmar")
    assert _accion(client, mesero_headers, pedido["id"], "enviar-cocina").status_code == 200
    return pedido


def _ordenes(client, headers):
    r = client.get("/api/cocina/ordenes", headers=headers)
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _avanzar(client, headers, tipo, orden_id, estado):
    return client.patch(f"/api/cocina/ordenes/{tipo}/{orden_id}/estado", headers=headers, json={"estado": estado})


def test_cp_06_1_1_recibir_ordenes(client, cocinero_headers, mesero_headers, mesas, carta, en_cocina):
    """CP-06.1-1 | RF-06.1, RF-06.2 | La cocina recibe el pedido enviado con su mesa, productos y
    observaciones (sin precios); un pedido sin enviar todavía no aparece."""
    _pedir(client, mesero_headers, mesas[2], carta, comensales=1)  # registrado, no enviado
    datos = _ordenes(client, cocinero_headers)
    assert [o["codigo"] for o in datos["ordenes"]] == [en_cocina["codigo"]]
    orden = datos["ordenes"][0]
    assert (orden["tipo"], orden["origen"], orden["estado"], orden["columna"]) == ("MESA", "Mesa 1", "EN_COCINA", "POR_PREPARAR")
    assert orden["productos"][0] == {"cantidad": 2, "producto": "Bandeja", "observacion": "sin cebolla"}
    assert "total" not in orden and datos["resumen"]["POR_PREPARAR"] == 1


def test_cp_06_3_1_por_orden_de_llegada(client, cocinero_headers, mesero_headers, mesas, carta, en_cocina):
    """CP-06.3-1 | RF-06.3 | Las órdenes se organizan por llegada: la que más espera va primero."""
    segundo = _pedir(client, mesero_headers, mesas[2], carta, comensales=1).get_json()
    _accion(client, mesero_headers, segundo["id"], "confirmar")
    _accion(client, mesero_headers, segundo["id"], "enviar-cocina")
    db.session.get(PedidoMesa, segundo["id"]).fecha_envio_cocina = datetime.now() - timedelta(minutes=20)
    db.session.commit()
    datos = _ordenes(client, cocinero_headers)
    assert [o["codigo"] for o in datos["ordenes"]] == [segundo["codigo"], en_cocina["codigo"]]
    assert datos["ordenes"][0]["minutos"] >= 20 and datos["resumen"]["espera_maxima"] >= 20


def test_cp_06_4_1_preparar_y_listo(client, cocinero_headers, en_cocina):
    """CP-06.4-1 | RF-06.4, RF-06.5 | La cocina pasa el pedido a EN_PREPARACION y luego a LISTO
    (queda la hora en que estuvo listo)."""
    r = _avanzar(client, cocinero_headers, "mesa", en_cocina["id"], "EN_PREPARACION")
    assert r.status_code == 200 and r.get_json()["columna"] == "PREPARANDO"
    r = _avanzar(client, cocinero_headers, "mesa", en_cocina["id"], "LISTO")
    assert r.status_code == 200 and r.get_json()["listo"] is not None
    estado = client.get(f"/api/pedidos/{en_cocina['id']}/estado", headers=cocinero_headers)
    assert estado.status_code == 403  # el cocinero no ve el módulo de pedidos


@pytest.mark.parametrize("estado, mensaje", [
    ("LISTO", "solo puede pasar a EN_PREPARACION"),
    ("ENTREGADO", "solo puede pasar a EN_PREPARACION"),
    ("", "solo puede pasar a EN_PREPARACION"),
])
def test_cp_06_4_2_un_paso_a_la_vez(client, cocinero_headers, en_cocina, estado, mensaje):
    """CP-06.4-2 | RF-06.4 | No se salta pasos: de EN_COCINA solo se pasa a EN_PREPARACION."""
    r = _avanzar(client, cocinero_headers, "MESA", en_cocina["id"], estado)
    assert r.status_code == 409 and mensaje in r.get_json()["error"]


def test_cp_06_6_1_mesero_entrega(client, cocinero_headers, mesero_headers, en_cocina):
    """CP-06.6-1 | RF-06.6 | El mesero marca entregado el pedido listo y sale de la cocina;
    pero no puede cambiar los estados de preparación."""
    assert _avanzar(client, mesero_headers, "MESA", en_cocina["id"], "EN_PREPARACION").status_code == 403
    _avanzar(client, cocinero_headers, "MESA", en_cocina["id"], "EN_PREPARACION")
    _avanzar(client, cocinero_headers, "MESA", en_cocina["id"], "LISTO")
    r = _avanzar(client, mesero_headers, "MESA", en_cocina["id"], "ENTREGADO")
    assert r.status_code == 200 and r.get_json()["estado"] == "ENTREGADO"
    assert _ordenes(client, cocinero_headers)["ordenes"] == []
    linea = client.get(f"/api/pedidos/{en_cocina['id']}/estado", headers=mesero_headers).get_json()["linea_de_tiempo"]
    assert [p["estado"] for p in linea] == ["REGISTRADO", "CONFIRMADO", "EN_COCINA", "LISTO", "ENTREGADO"]
    assert _avanzar(client, mesero_headers, "MESA", en_cocina["id"], "ENTREGADO").status_code == 409


def test_cp_06_1_2_domicilios_en_cocina(client, cocinero_headers, cajero_headers, cliente, carta_domicilio):
    """CP-06.1-2 | RF-06.1, RF-06.5 | Los domicilios llegan a la cocina desde que se registran; la cocina
    los prepara hasta LISTO y de ahí siguen en el módulo de domicilios."""
    domicilio = pedir_domicilio(client, cajero_headers, cliente, carta_domicilio).get_json()
    orden = _ordenes(client, cocinero_headers)["ordenes"][0]
    assert (orden["tipo"], orden["origen"], orden["detalle"], orden["estado"]) == ("DOMICILIO", "Domicilio", "Cabecera", "RECIBIDO")
    assert _avanzar(client, cocinero_headers, "domicilio", orden["id"], "EN_PREPARACION").status_code == 200
    r = _avanzar(client, cocinero_headers, "domicilio", orden["id"], "LISTO")
    assert r.status_code == 200 and r.get_json()["siguiente"] is None
    assert client.get(f"/api/domicilios/{domicilio['id']}", headers=cajero_headers).get_json()["estado"] == "LISTO"
    assert _avanzar(client, cocinero_headers, "domicilio", orden["id"], "ENTREGADO").status_code == 409


def test_cp_06_7_1_novedades(client, cocinero_headers, mesero_headers, mesas, carta):
    """CP-06.7-1 | RF-06.7 | Notificar cambio de estado: la cocina se entera de los pedidos nuevos y
    el mesero de los que quedaron listos desde la última consulta."""
    antes = (datetime.now() - timedelta(seconds=1)).isoformat()
    pedido = _pedir(client, mesero_headers, mesas[1], carta).get_json()
    _accion(client, mesero_headers, pedido["id"], "confirmar")
    _accion(client, mesero_headers, pedido["id"], "enviar-cocina")
    r = client.get(f"/api/cocina/novedades?desde={antes}", headers=cocinero_headers).get_json()
    assert r["nuevos"] == [{"codigo": pedido["codigo"], "origen": "Mesa 1"}] and r["listos"] == []

    _avanzar(client, cocinero_headers, "MESA", pedido["id"], "EN_PREPARACION")
    _avanzar(client, cocinero_headers, "MESA", pedido["id"], "LISTO")
    r = client.get(f"/api/cocina/novedades?desde={antes}", headers=mesero_headers).get_json()
    assert r["listos"] == [{"id": pedido["id"], "codigo": pedido["codigo"], "mesa": 1}]
    despues = client.get(f"/api/cocina/novedades?desde={r['hora']}", headers=mesero_headers).get_json()
    assert despues["nuevos"] == [] and despues["listos"] == []
    assert client.get("/api/cocina/novedades?desde=ayer", headers=mesero_headers).status_code == 422
    primera = client.get("/api/cocina/novedades", headers=mesero_headers).get_json()
    assert primera["hora"] and primera["listos"] == []


def test_cp_seg_28_permisos_de_cocina(client, mesero_headers, cocinero_headers, en_cocina):
    """CP-SEG-28 | RF-06 | Solo cocina (cocina.ver) ve el tablero; un tipo o una orden que no existen → 404."""
    assert client.get("/api/cocina/ordenes", headers=mesero_headers).status_code == 403
    assert _avanzar(client, cocinero_headers, "llevar", en_cocina["id"], "EN_PREPARACION").status_code == 404
    assert _avanzar(client, cocinero_headers, "MESA", 999, "EN_PREPARACION").status_code == 404
