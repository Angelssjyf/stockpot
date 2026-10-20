"""Casos de prueba: domicilios y clientes (RF-08.1 a RF-08.8).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import Domicilio, Insumo, Orden, Producto, Receta

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def cajero_headers(client):
    crear_usuario("CAJERO", "caja@stockpot.test")
    return iniciar_sesion(client, "caja@stockpot.test")


@pytest.fixture()
def domiciliario(client):
    """Un domiciliario y su sesión."""
    usuario = crear_usuario("DOMICILIARIO", "moto@stockpot.test")
    return {"id": usuario.id, "headers": iniciar_sesion(client, "moto@stockpot.test")}


@pytest.fixture()
def carta():
    """Bandeja ($22.000, lleva 0,25 KG de pollo) y limonada ($6.000, sin receta).
    Hay 1 KG de pollo: alcanza para 4 bandejas."""
    pollo = Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG", stock_actual=1)
    bandeja = Producto(codigo="PRD-001", nombre="Bandeja", categoria="PLATO_FUERTE",
                       precio_venta=22000)
    bandeja.receta = [Receta(insumo=pollo, cantidad=0.25)]
    limonada = Producto(codigo="PRD-007", nombre="Limonada", categoria="BEBIDA",
                        precio_venta=6000)
    db.session.add_all([pollo, bandeja, limonada])
    db.session.commit()
    return {"bandeja": bandeja.id, "limonada": limonada.id}


@pytest.fixture()
def cliente(client, cajero_headers):
    r = client.post("/api/clientes", headers=cajero_headers, json={
        "nombre": "María Gómez", "telefono": "300 123 4567",
        "direccion": "Calle 45 # 27-30", "barrio": "Cabecera",
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _pedir(client, headers, cliente, carta, **extra):
    datos = {"cliente_id": cliente["id"], "costo_envio": 3000,
             "items": [{"producto_id": carta["bandeja"], "cantidad": 2, "observacion": "sin cebolla"},
                       {"producto_id": carta["limonada"], "cantidad": 1}]}
    return client.post("/api/domicilios", headers=headers, json={**datos, **extra})


@pytest.fixture()
def pedido(client, cajero_headers, cliente, carta):
    r = _pedir(client, cajero_headers, cliente, carta)
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _estado(client, headers, domicilio_id, estado):
    return client.patch(f"/api/domicilios/{domicilio_id}/estado", headers=headers,
                        json={"estado": estado})


def _asignar(client, headers, domicilio_id, domiciliario_id):
    return client.patch(f"/api/domicilios/{domicilio_id}/asignar", headers=headers,
                        json={"domiciliario_id": domiciliario_id})


def _hasta_en_camino(client, headers, pedido, domiciliario_id):
    _asignar(client, headers, pedido["id"], domiciliario_id)
    for estado in ("EN_PREPARACION", "LISTO", "EN_CAMINO"):
        assert _estado(client, headers, pedido["id"], estado).status_code == 200


# ------------------------------------------------------- RF-08.2 Clientes


def test_cp_08_2_1_registrar_cliente(cliente):
    """CP-08.2-1 | RF-08.2 | Registra el cliente; el teléfono se guarda sin espacios."""
    assert cliente["telefono"] == "3001234567"
    assert cliente["direccion"] == "Calle 45 # 27-30"


@pytest.mark.parametrize("telefono, codigo", [("3001234567", 409), ("abc", 422), ("123", 422)])
def test_cp_08_2_2_telefono_invalido_o_repetido(client, cajero_headers, cliente, telefono, codigo):
    """CP-08.2-2 | RF-08.2 | Teléfono repetido → 409; con letras o muy corto → 422."""
    r = client.post("/api/clientes", headers=cajero_headers,
                    json={"nombre": "Otro", "telefono": telefono})
    assert r.status_code == codigo


def test_cp_08_2_3_buscar_y_modificar_cliente(client, cajero_headers, cliente):
    """CP-08.2-3 | RF-08.2 | Busca por parte del teléfono y actualiza la dirección."""
    encontrados = client.get("/api/clientes?q=4567", headers=cajero_headers).get_json()
    assert [c["nombre"] for c in encontrados] == ["María Gómez"]
    r = client.put(f"/api/clientes/{cliente['id']}", headers=cajero_headers,
                   json={"direccion": "Carrera 27 # 10-05"})
    assert r.get_json()["direccion"] == "Carrera 27 # 10-05"


# ------------------------------------------------------- RF-08.1 Registrar pedido


def test_cp_08_1_1_registrar_domicilio(pedido):
    """CP-08.1-1 | RF-08.1, RF-08.3 | Crea el pedido con código, precios del menú, envío y la
    dirección habitual del cliente."""
    assert pedido["codigo"] == "PED-000001"
    assert pedido["estado"] == "RECIBIDO"
    assert pedido["direccion"] == "Calle 45 # 27-30"
    assert pedido["barrio"] == "Cabecera"
    assert pedido["telefono_contacto"] == "3001234567"
    assert pedido["orden"]["subtotal"] == 50000.0   # 2 × 22.000 + 6.000
    assert pedido["total"] == 53000.0               # + 3.000 de envío
    linea = pedido["orden"]["detalles"][0]
    assert (linea["producto"], linea["cantidad"], linea["observacion"]) == ("Bandeja", 2, "sin cebolla")


def test_cp_08_1_2_el_precio_queda_fijo(client, admin_headers, pedido, carta):
    """CP-08.1-2 | RF-08.1 | Si luego cambia el precio del menú, el pedido conserva el suyo."""
    client.put(f"/api/productos/{carta['bandeja']}", headers=admin_headers,
               json={"precio_venta": 30000})
    detalle = client.get(f"/api/domicilios/{pedido['id']}", headers=admin_headers).get_json()
    assert detalle["orden"]["detalles"][0]["precio_unitario"] == 22000.0


@pytest.mark.parametrize("items, codigo", [
    ([], 422),
    ([{"producto_id": 999, "cantidad": 1}], 422),
    ([{"producto_id": 1, "cantidad": 0}], 422),
    ([{"producto_id": 1, "cantidad": 1.5}], 422),
])
def test_cp_08_1_3_items_invalidos(client, cajero_headers, cliente, carta, items, codigo):
    """CP-08.1-3 | RF-08.1 | Sin productos, producto inexistente o cantidad no entera → 422."""
    r = _pedir(client, cajero_headers, cliente, carta, items=items)
    assert r.status_code == codigo
    assert Orden.query.count() == 0


def test_cp_08_1_4_producto_no_disponible(client, cajero_headers, admin_headers, cliente, carta):
    """CP-08.1-4 | RF-08.1, RF-04.6 | Un producto agotado por hoy no se puede pedir → 409."""
    client.patch(f"/api/productos/{carta['limonada']}/disponibilidad", headers=admin_headers,
                 json={"disponible": False})
    r = _pedir(client, cajero_headers, cliente, carta)
    assert r.status_code == 409
    assert "no está disponible" in r.get_json()["error"]


def test_cp_08_1_5_inventario_insuficiente(client, cajero_headers, cliente, carta):
    """CP-08.1-5 | RF-08.1, RF-04.4 | Si no alcanza el inventario para la receta → 409 y no se crea."""
    r = _pedir(client, cajero_headers, cliente, carta,
               items=[{"producto_id": carta["bandeja"], "cantidad": 5}])  # 1,25 KG de pollo
    assert r.status_code == 409
    assert "No alcanza 'Pollo'" in r.get_json()["error"]
    assert Domicilio.query.count() == 0


# ------------------------------------------------------- RF-08.3 Dirección de entrega


def test_cp_08_3_1_direccion_distinta(client, cajero_headers, cliente, carta):
    """CP-08.3-1 | RF-08.3 | El pedido puede ir a otra dirección sin cambiar la del cliente."""
    r = _pedir(client, cajero_headers, cliente, carta, direccion="Oficina: Calle 36 # 15-20",
               barrio="Centro", referencia="Piso 3")
    assert r.get_json()["direccion"] == "Oficina: Calle 36 # 15-20"
    assert r.get_json()["barrio"] == "Centro"
    datos = client.get("/api/clientes?q=María", headers=cajero_headers).get_json()[0]
    assert datos["direccion"] == "Calle 45 # 27-30"


def test_cp_08_3_2_sin_direccion(client, cajero_headers, carta):
    """CP-08.3-2 | RF-08.3 | Un cliente sin dirección y un pedido sin dirección → 422."""
    sin_direccion = client.post("/api/clientes", headers=cajero_headers,
                                json={"nombre": "Pedro", "telefono": "3110000000"}).get_json()
    r = _pedir(client, cajero_headers, sin_direccion, carta)
    assert r.status_code == 422
    assert "dirección" in r.get_json()["error"]


# ------------------------------------------------------- RF-08.4 Consultar


def test_cp_08_4_1_consultar_en_curso(client, cajero_headers, cliente, carta, pedido):
    """CP-08.4-1 | RF-08.4 | Lista los pedidos en curso del más antiguo al más reciente y filtra por estado."""
    segundo = _pedir(client, cajero_headers, cliente, carta,
                     items=[{"producto_id": carta["limonada"], "cantidad": 1}]).get_json()
    _estado(client, cajero_headers, segundo["id"], "EN_PREPARACION")

    lista = client.get("/api/domicilios", headers=cajero_headers).get_json()
    assert [d["codigo"] for d in lista] == ["PED-000001", "PED-000002"]
    en_preparacion = client.get("/api/domicilios?estado=en_preparacion",
                                headers=cajero_headers).get_json()
    assert [d["codigo"] for d in en_preparacion] == ["PED-000002"]


# ------------------------------------------------------- RF-08.5 Asignar


def test_cp_08_5_1_asignar_domiciliario(client, cajero_headers, pedido, domiciliario):
    """CP-08.5-1 | RF-08.5 | Asigna el pedido a un domiciliario y guarda la hora."""
    r = _asignar(client, cajero_headers, pedido["id"], domiciliario["id"])
    assert r.status_code == 200
    assert r.get_json()["domiciliario"] == "Prueba Domiciliario"
    assert r.get_json()["fecha_asignacion"] is not None
    lista = client.get("/api/domiciliarios", headers=cajero_headers).get_json()
    assert [d["id"] for d in lista] == [domiciliario["id"]]


def test_cp_08_5_2_asignar_a_quien_no_es_domiciliario(client, cajero_headers, pedido):
    """CP-08.5-2 | RF-08.5 | Asignar a un usuario que no es DOMICILIARIO → 422."""
    mesero = crear_usuario("MESERO", "mesero2@stockpot.test")
    assert _asignar(client, cajero_headers, pedido["id"], mesero.id).status_code == 422


# ------------------------------------------------------- RF-08.6 Estados


def test_cp_08_6_1_flujo_de_estados(client, cajero_headers, pedido, domiciliario):
    """CP-08.6-1 | RF-08.6 | RECIBIDO → EN_PREPARACION → LISTO → EN_CAMINO guarda la hora de salida."""
    _hasta_en_camino(client, cajero_headers, pedido, domiciliario["id"])
    detalle = client.get(f"/api/domicilios/{pedido['id']}", headers=cajero_headers).get_json()
    assert detalle["estado"] == "EN_CAMINO"
    assert detalle["fecha_salida"] is not None


def test_cp_08_6_2_transiciones_invalidas(client, cajero_headers, pedido):
    """CP-08.6-2 | RF-08.6 | Saltarse estados → 409; salir sin domiciliario → 409; estado raro → 422."""
    assert _estado(client, cajero_headers, pedido["id"], "LISTO").status_code == 409
    _estado(client, cajero_headers, pedido["id"], "EN_PREPARACION")
    _estado(client, cajero_headers, pedido["id"], "LISTO")
    r = _estado(client, cajero_headers, pedido["id"], "EN_CAMINO")
    assert r.status_code == 409
    assert "asigna un domiciliario" in r.get_json()["error"]
    assert _estado(client, cajero_headers, pedido["id"], "VOLANDO").status_code == 422
    assert _estado(client, cajero_headers, pedido["id"], "ENTREGADO").status_code == 422


def test_cp_08_6_3_cancelar(client, cajero_headers, pedido):
    """CP-08.6-3 | RF-08.6 | Cancelar el domicilio cancela la orden y ya no se puede mover."""
    assert _estado(client, cajero_headers, pedido["id"], "CANCELADO").status_code == 200
    assert db.session.get(Orden, pedido["orden"]["id"]).estado == "CANCELADA"
    assert _estado(client, cajero_headers, pedido["id"], "EN_PREPARACION").status_code == 409
    assert client.get("/api/domicilios", headers=cajero_headers).get_json() == []


# ------------------------------------------------------- RF-08.7 Entrega


def test_cp_08_7_1_registrar_entrega(client, cajero_headers, pedido, domiciliario):
    """CP-08.7-1 | RF-08.7 | Registra quién recibió y la hora; exige un domicilio EN_CAMINO."""
    url = f"/api/domicilios/{pedido['id']}/entrega"
    assert client.post(url, headers=cajero_headers, json={"recibido_por": "María"}).status_code == 409

    _hasta_en_camino(client, cajero_headers, pedido, domiciliario["id"])
    assert client.post(url, headers=cajero_headers, json={"recibido_por": " "}).status_code == 422
    r = client.post(url, headers=cajero_headers,
                    json={"recibido_por": "María Gómez", "observacion": "Pagó en efectivo"})
    assert r.status_code == 200
    assert r.get_json()["estado"] == "ENTREGADO"
    assert r.get_json()["recibido_por"] == "María Gómez"
    assert r.get_json()["fecha_entrega"] is not None


# ------------------------------------------------------- RF-08.8 Historial


def test_cp_08_8_1_historial(client, cajero_headers, cliente, carta, pedido, domiciliario):
    """CP-08.8-1 | RF-08.8 | El historial trae entregados y cancelados con su resumen y filtros."""
    _hasta_en_camino(client, cajero_headers, pedido, domiciliario["id"])
    client.post(f"/api/domicilios/{pedido['id']}/entrega", headers=cajero_headers,
                json={"recibido_por": "María"})
    cancelado = _pedir(client, cajero_headers, cliente, carta).get_json()
    _estado(client, cajero_headers, cancelado["id"], "CANCELADO")
    _pedir(client, cajero_headers, cliente, carta)  # en curso: no sale en el historial

    r = client.get("/api/domicilios/historial", headers=cajero_headers).get_json()
    assert [d["codigo"] for d in r["domicilios"]] == ["PED-000002", "PED-000001"]
    assert r["resumen"] == {"entregados": 1, "cancelados": 1, "total_entregado": 53000.0}

    r = client.get(f"/api/domicilios/historial?domiciliario_id={domiciliario['id']}",
                   headers=cajero_headers).get_json()
    assert [d["codigo"] for d in r["domicilios"]] == ["PED-000001"]
    r = client.get("/api/domicilios/historial?desde=2000-01-01&hasta=2000-01-31",
                   headers=cajero_headers).get_json()
    assert r["domicilios"] == []
    assert client.get("/api/domicilios/historial?desde=ayer",
                      headers=cajero_headers).status_code == 422


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_19_domiciliario_solo_lo_suyo(client, cajero_headers, cliente, carta, pedido,
                                              domiciliario):
    """CP-SEG-19 | Seguridad | El DOMICILIARIO solo ve y entrega sus pedidos; no crea, no cancela."""
    ajeno = _pedir(client, cajero_headers, cliente, carta,
                   items=[{"producto_id": carta["limonada"], "cantidad": 1}]).get_json()
    _asignar(client, cajero_headers, pedido["id"], domiciliario["id"])
    for estado in ("EN_PREPARACION", "LISTO"):
        _estado(client, cajero_headers, pedido["id"], estado)
    moto = domiciliario["headers"]

    assert [d["codigo"] for d in client.get("/api/domicilios", headers=moto).get_json()] == \
        ["PED-000001"]
    assert client.get(f"/api/domicilios/{ajeno['id']}", headers=moto).status_code == 404
    assert _pedir(client, moto, cliente, carta).status_code == 403
    assert _estado(client, moto, pedido["id"], "CANCELADO").status_code == 403
    assert _estado(client, moto, pedido["id"], "EN_CAMINO").status_code == 200
    r = client.post(f"/api/domicilios/{pedido['id']}/entrega", headers=moto,
                    json={"recibido_por": "Portería"})
    assert r.status_code == 200
