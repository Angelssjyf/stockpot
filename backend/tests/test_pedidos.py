"""Casos de prueba: pedidos en mesa y mesas (RF-05.1 a RF-05.9).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import Insumo, Mesa, MovimientoInventario, Orden, Producto, Receta

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def cocinero_headers(client):
    crear_usuario("COCINERO", "cocina@stockpot.test")
    return iniciar_sesion(client, "cocina@stockpot.test")


@pytest.fixture()
def carta():
    """Bandeja ($22.000, lleva 0,25 KG de pollo y 0,15 KG de arroz) y limonada ($6.000, sin
    receta). Hay 1 KG de pollo (alcanza para 4 bandejas) y 3 KG de arroz."""
    pollo = Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG", stock_actual=1, costo_unitario=13000)
    arroz = Insumo(codigo="INS-001", nombre="Arroz", unidad_medida="KG", stock_actual=3, costo_unitario=4200)
    bandeja = Producto(codigo="PRD-001", nombre="Bandeja", categoria="PLATO_FUERTE", precio_venta=22000)
    bandeja.receta = [Receta(insumo=pollo, cantidad=0.25), Receta(insumo=arroz, cantidad=0.15)]
    limonada = Producto(codigo="PRD-007", nombre="Limonada", categoria="BEBIDA", precio_venta=6000)
    db.session.add_all([pollo, arroz, bandeja, limonada])
    db.session.commit()
    return {"bandeja": bandeja.id, "limonada": limonada.id, "pollo": pollo.id}


@pytest.fixture()
def mesas():
    """Mesa 1 para 4 personas (salón) y mesa 2 para 2 (terraza)."""
    m1 = Mesa(numero=1, capacidad=4, ubicacion="Salón")
    m2 = Mesa(numero=2, capacidad=2, ubicacion="Terraza")
    db.session.add_all([m1, m2])
    db.session.commit()
    return {1: m1.id, 2: m2.id}


def _pedir(client, headers, mesa, carta, **extra):
    datos = {"mesa_id": mesa, "comensales": 2, "observaciones": "Cumpleaños",
             "items": [{"producto_id": carta["bandeja"], "cantidad": 2, "observacion": "sin cebolla"},
                       {"producto_id": carta["limonada"], "cantidad": 1}]}
    return client.post("/api/pedidos", headers=headers, json={**datos, **extra})


@pytest.fixture()
def pedido(client, mesero_headers, mesas, carta):
    r = _pedir(client, mesero_headers, mesas[1], carta)
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _accion(client, headers, pedido_id, accion, **datos):
    return client.patch(f"/api/pedidos/{pedido_id}/{accion}", headers=headers, json=datos)


def _mesa(client, headers, numero):
    return next(m for m in client.get("/api/mesas", headers=headers).get_json() if m["numero"] == numero)


# ------------------------------------------------------- Mesas (base de RF-05.2)


def test_cp_05_2_1_listar_mesas(client, mesero_headers, mesas, pedido):
    """CP-05.2-1 | RF-05.2 | Las mesas se listan por número con su estado: la del pedido ocupada, la otra libre."""
    lista = client.get("/api/mesas", headers=mesero_headers).get_json()
    assert [m["numero"] for m in lista] == [1, 2]
    assert lista[0]["ocupada"] is True and lista[0]["pedido"]["codigo"] == pedido["codigo"]
    assert lista[0]["pedido"]["productos"] == 3
    assert lista[1]["ocupada"] is False and lista[1]["pedido"] is None


def test_cp_05_2_2_crear_mesa(client, admin_headers, mesas):
    """CP-05.2-2 | RF-05.2 | Se agrega una mesa; el número repetido da 409 y la capacidad inválida 422."""
    r = client.post("/api/mesas", headers=admin_headers, json={"numero": 9, "capacidad": 6, "ubicacion": " Barra "})
    assert r.status_code == 201
    assert r.get_json() | {"id": 0} == {"id": 0, "numero": 9, "capacidad": 6, "ubicacion": "Barra", "activa": True,
                                         "ocupada": False, "pedido": None}
    assert client.post("/api/mesas", headers=admin_headers, json={"numero": 1}).status_code == 409
    assert client.post("/api/mesas", headers=admin_headers, json={"numero": 10, "capacidad": 0}).status_code == 422
    assert client.post("/api/mesas", headers=admin_headers, json={"numero": "diez"}).status_code == 422


def test_cp_05_2_3_desactivar_mesa(client, admin_headers, mesas, pedido):
    """CP-05.2-3 | RF-05.2 | Una mesa con pedido abierto no se desactiva; una libre sí y deja de listarse."""
    r = client.put(f"/api/mesas/{mesas[1]}", headers=admin_headers, json={"activa": False})
    assert r.status_code == 409 and "pedido abierto" in r.get_json()["error"]
    r = client.put(f"/api/mesas/{mesas[2]}", headers=admin_headers, json={"activa": False, "capacidad": 3})
    assert r.status_code == 200 and r.get_json()["activa"] is False
    assert [m["numero"] for m in client.get("/api/mesas", headers=admin_headers).get_json()] == [1]
    assert len(client.get("/api/mesas?todas=true", headers=admin_headers).get_json()) == 2
    assert client.put("/api/mesas/999", headers=admin_headers, json={}).status_code == 404


def test_cp_05_2_4_permisos(client, cocinero_headers, mesas, carta):
    """CP-SEG-05-1 | RF-05.1, RF-01.6 | Sin sesión 401; el COCINERO no ve mesas ni registra pedidos (403)."""
    assert client.get("/api/mesas").status_code == 401
    assert client.get("/api/mesas", headers=cocinero_headers).status_code == 403
    assert _pedir(client, cocinero_headers, mesas[1], carta).status_code == 403


# ------------------------------------------------------- RF-05.1 Registrar, RF-05.2 Mesa y RF-05.3 Productos


def test_cp_05_1_1_registrar_pedido(client, mesero_headers, pedido, mesas):
    """CP-05.1-1 | RF-05.1, RF-05.2, RF-05.3 | El mesero registra el pedido de la mesa 1: código PED-, REGISTRADO y total."""
    assert pedido["codigo"].startswith("PED-")
    assert pedido["estado"] == "REGISTRADO" and pedido["editable"] is True
    assert pedido["mesa"]["numero"] == 1 and pedido["comensales"] == 2
    assert pedido["mesero"] == "Prueba Mesero"
    assert pedido["total"] == 50000.0  # 2 × 22.000 + 6.000
    assert [(d["producto"], d["cantidad"], d["observacion"]) for d in pedido["detalles"]] == [
        ("Bandeja", 2, "sin cebolla"), ("Limonada", 1, None)]
    assert db.session.get(Orden, pedido["orden_id"]).tipo == "MESA"


@pytest.mark.parametrize("cambios, mensaje", [
    ({"items": []}, "al menos un producto"),
    ({"mesa_id": 999}, "La mesa no existe"),
    ({"mesa_id": "1"}, "La mesa no existe"),
    ({"comensales": 0}, "Los comensales"),
    ({"items": [{"producto_id": 1, "cantidad": 1.5}]}, "número entero"),
])
def test_cp_05_1_2_datos_invalidos(client, mesero_headers, mesas, carta, cambios, mensaje):
    """CP-05.1-2 | RF-05.1 | Sin productos, mesa inexistente, comensales o cantidades inválidas → 422."""
    r = _pedir(client, mesero_headers, mesas[1], carta, **cambios)
    assert r.status_code == 422 and mensaje in r.get_json()["error"]
    assert Orden.query.count() == 0


def test_cp_05_1_3_comensales_de_mas(client, mesero_headers, mesas, carta):
    """CP-05.1-3 | RF-05.2 | Más comensales que la capacidad de la mesa → 422."""
    r = _pedir(client, mesero_headers, mesas[2], carta, comensales=3)
    assert r.status_code == 422 and r.get_json()["error"] == "La mesa 2 es para 2 personas"


def test_cp_05_2_5_mesa_ocupada(client, mesero_headers, mesas, carta, pedido):
    """CP-05.2-5 | RF-05.2 | Una mesa con un pedido abierto no recibe otro pedido → 409 con el código."""
    r = _pedir(client, mesero_headers, mesas[1], carta)
    assert r.status_code == 409
    assert r.get_json()["error"] == f"La mesa 1 ya tiene el pedido {pedido['codigo']}"


# ------------------------------------------------------- RF-05.6 Validar disponibilidad de insumos


def test_cp_05_6_1_no_alcanza_al_registrar(client, mesero_headers, mesas, carta):
    """CP-05.6-1 | RF-05.6 | Si el inventario no alcanza (5 bandejas, hay pollo para 4) no se registra nada."""
    r = _pedir(client, mesero_headers, mesas[1], carta, items=[{"producto_id": carta["bandeja"], "cantidad": 5}])
    assert r.status_code == 409 and "No alcanza 'Pollo'" in r.get_json()["error"]
    assert Orden.query.count() == 0
    assert _mesa(client, mesero_headers, 1)["ocupada"] is False


def test_cp_05_6_2_consultar_disponibilidad(client, mesero_headers, carta):
    """CP-05.6-2 | RF-05.6 | La consulta lista todos los insumos que faltan, sin guardar nada."""
    r = client.post("/api/pedidos/disponibilidad", headers=mesero_headers,
                    json={"items": [{"producto_id": carta["bandeja"], "cantidad": 30}]})
    assert r.status_code == 200
    body = r.get_json()
    assert body["disponible"] is False and body["subtotal"] == 660000.0
    assert [(f["insumo"], f["necesita"], f["falta"]) for f in body["faltantes"]] == [
        ("Pollo", 7.5, 6.5), ("Arroz", 4.5, 1.5)]  # primero el que más falta
    assert Orden.query.count() == 0


def test_cp_05_6_3_disponible(client, mesero_headers, carta):
    """CP-05.6-3 | RF-05.6 | Si alcanza, responde disponible con el subtotal; un producto inválido da 422."""
    r = client.post("/api/pedidos/disponibilidad", headers=mesero_headers,
                    json={"items": [{"producto_id": carta["bandeja"], "cantidad": 4},
                                    {"producto_id": carta["limonada"], "cantidad": 2}]})
    assert r.get_json() == {"disponible": True, "subtotal": 100000.0, "faltantes": []}
    r = client.post("/api/pedidos/disponibilidad", headers=mesero_headers, json={"items": [{"producto_id": 99, "cantidad": 1}]})
    assert r.status_code == 422


# ------------------------------------------------------- RF-05.5 Consultar pedidos


def test_cp_05_5_1_consultar_activos(client, mesero_headers, mesas, carta, pedido):
    """CP-05.5-1 | RF-05.5 | Lista los pedidos sin cobrar, del más antiguo al más reciente, con filtros."""
    otro = _pedir(client, mesero_headers, mesas[2], carta, comensales=1,
                  items=[{"producto_id": carta["limonada"], "cantidad": 2}]).get_json()
    _accion(client, mesero_headers, otro["id"], "confirmar")
    lista = client.get("/api/pedidos", headers=mesero_headers).get_json()
    assert [p["codigo"] for p in lista] == [pedido["codigo"], otro["codigo"]]
    assert [p["codigo"] for p in client.get("/api/pedidos?estado=confirmado", headers=mesero_headers).get_json()] \
        == [otro["codigo"]]
    assert [p["id"] for p in client.get(f"/api/pedidos?mesa_id={mesas[1]}", headers=mesero_headers).get_json()] \
        == [pedido["id"]]
    assert len(client.get(f"/api/pedidos?q={otro['codigo']}", headers=mesero_headers).get_json()) == 1


def test_cp_05_5_2_filtros_invalidos(client, mesero_headers, pedido):
    """CP-05.5-2 | RF-05.5 | Un estado inexistente o una fecha mal escrita → 422; un pedido inexistente → 404."""
    assert client.get("/api/pedidos?estado=VOLANDO", headers=mesero_headers).status_code == 422
    assert client.get("/api/pedidos?vista=historial&desde=19/10/2026", headers=mesero_headers).status_code == 422
    assert client.get("/api/pedidos/999", headers=mesero_headers).status_code == 404


def test_cp_05_5_3_historial(client, mesero_headers, pedido):
    """CP-05.5-3 | RF-05.5 | El historial incluye los cancelados, que ya no salen entre los activos."""
    _accion(client, mesero_headers, pedido["id"], "cancelar", motivo="El cliente se fue")
    assert client.get("/api/pedidos", headers=mesero_headers).get_json() == []
    historial = client.get("/api/pedidos?vista=historial", headers=mesero_headers).get_json()
    assert [(p["codigo"], p["estado"], p["estado_orden"]) for p in historial] == [
        (pedido["codigo"], "CANCELADO", "CANCELADA")]
    assert "Cancelado: El cliente se fue" in historial[0]["observaciones"]


# ------------------------------------------------------- RF-05.4 Modificar pedidos


def test_cp_05_4_1_modificar(client, mesero_headers, pedido, carta):
    """CP-05.4-1 | RF-05.4 | Se cambian comensales, observaciones y productos; el total se recalcula."""
    r = client.put(f"/api/pedidos/{pedido['id']}", headers=mesero_headers, json={
        "comensales": 4, "observaciones": "Sin prisa",
        "items": [{"producto_id": carta["bandeja"], "cantidad": 1}, {"producto_id": carta["limonada"], "cantidad": 3}]})
    assert r.status_code == 200
    body = r.get_json()
    assert (body["comensales"], body["observaciones"], body["total"]) == (4, "Sin prisa", 40000.0)
    assert [(d["producto"], d["cantidad"]) for d in body["detalles"]] == [("Bandeja", 1), ("Limonada", 3)]


def test_cp_05_4_2_cambiar_de_mesa(client, mesero_headers, pedido, mesas):
    """CP-05.4-2 | RF-05.2, RF-05.4 | Al cambiar el pedido de mesa, la anterior queda libre."""
    r = client.put(f"/api/pedidos/{pedido['id']}", headers=mesero_headers, json={"mesa_id": mesas[2]})
    assert r.status_code == 200 and r.get_json()["mesa"]["numero"] == 2
    assert _mesa(client, mesero_headers, 1)["ocupada"] is False
    assert _mesa(client, mesero_headers, 2)["pedido"]["id"] == pedido["id"]


def test_cp_05_4_3_confirmado_vuelve_a_registrado(client, mesero_headers, pedido):
    """CP-05.4-3 | RF-05.4, RF-05.7 | Si se modifica un pedido confirmado, vuelve a REGISTRADO para confirmarlo otra vez."""
    _accion(client, mesero_headers, pedido["id"], "confirmar")
    r = client.put(f"/api/pedidos/{pedido['id']}", headers=mesero_headers, json={"comensales": 3})
    assert r.get_json()["estado"] == "REGISTRADO" and r.get_json()["fecha_confirmacion"] is None


def test_cp_05_4_4_en_cocina_no_se_modifica(client, mesero_headers, pedido, carta):
    """CP-05.4-4 | RF-05.4 | Un pedido en cocina ya no se modifica, ni se le agregan productos, ni se cancela → 409."""
    _accion(client, mesero_headers, pedido["id"], "confirmar")
    _accion(client, mesero_headers, pedido["id"], "enviar-cocina")
    r = client.put(f"/api/pedidos/{pedido['id']}", headers=mesero_headers, json={"comensales": 3})
    assert r.status_code == 409 and "ya está en cocina" in r.get_json()["error"]
    r = client.post(f"/api/pedidos/{pedido['id']}/productos", headers=mesero_headers,
                    json={"items": [{"producto_id": carta["limonada"], "cantidad": 1}]})
    assert r.status_code == 409
    assert _accion(client, mesero_headers, pedido["id"], "cancelar").status_code == 409


def test_cp_05_4_5_cambio_sin_inventario(client, mesero_headers, pedido, carta):
    """CP-05.4-5 | RF-05.4, RF-05.6 | Si los productos nuevos no alcanzan → 409 y el pedido queda como estaba."""
    r = client.put(f"/api/pedidos/{pedido['id']}", headers=mesero_headers,
                   json={"items": [{"producto_id": carta["bandeja"], "cantidad": 9}]})
    assert r.status_code == 409
    actual = client.get(f"/api/pedidos/{pedido['id']}", headers=mesero_headers).get_json()
    assert actual["total"] == 50000.0 and len(actual["detalles"]) == 2


def test_cp_05_4_6_cancelar(client, mesero_headers, pedido):
    """CP-05.4-6 | RF-05.4 | Cancelar deja el pedido CANCELADO, la orden CANCELADA y la mesa libre."""
    r = _accion(client, mesero_headers, pedido["id"], "cancelar")
    assert r.status_code == 200 and r.get_json()["estado"] == "CANCELADO"
    assert _mesa(client, mesero_headers, 1)["ocupada"] is False
    assert _accion(client, mesero_headers, pedido["id"], "cancelar").status_code == 409  # ya cancelado


# ------------------------------------------------------- RF-05.3 Agregar productos


def test_cp_05_3_1_agregar_productos(client, mesero_headers, pedido, carta):
    """CP-05.3-1 | RF-05.3 | Lo mismo sin observación suma la cantidad; con otra observación va en otra línea."""
    r = client.post(f"/api/pedidos/{pedido['id']}/productos", headers=mesero_headers, json={"items": [
        {"producto_id": carta["limonada"], "cantidad": 2},
        {"producto_id": carta["bandeja"], "cantidad": 1, "observacion": "bien asada"}]})
    assert r.status_code == 200
    assert [(d["producto"], d["cantidad"], d["observacion"]) for d in r.get_json()["detalles"]] == [
        ("Bandeja", 2, "sin cebolla"), ("Limonada", 3, None), ("Bandeja", 1, "bien asada")]
    assert r.get_json()["total"] == 84000.0  # 3 × 22.000 + 3 × 6.000


def test_cp_05_3_2_agregar_invalido(client, mesero_headers, pedido, carta):
    """CP-05.3-2 | RF-05.3, RF-05.6 | Sin productos → 422; si el pedido completo ya no alcanza → 409 sin cambios."""
    ruta = f"/api/pedidos/{pedido['id']}/productos"
    assert client.post(ruta, headers=mesero_headers, json={"items": []}).status_code == 422
    r = client.post(ruta, headers=mesero_headers, json={"items": [{"producto_id": carta["bandeja"], "cantidad": 3}]})
    assert r.status_code == 409 and "Pollo" in r.get_json()["error"]  # 2 + 3 = 5 bandejas, hay para 4
    assert client.get(f"/api/pedidos/{pedido['id']}", headers=mesero_headers).get_json()["total"] == 50000.0
    assert client.post("/api/pedidos/999/productos", headers=mesero_headers, json={}).status_code == 404


# ------------------------------------------------------- RF-05.7 Confirmar


def test_cp_05_7_1_confirmar(client, mesero_headers, pedido):
    """CP-05.7-1 | RF-05.7 | Confirmar pasa de REGISTRADO a CONFIRMADO con su hora; dos veces → 409."""
    r = _accion(client, mesero_headers, pedido["id"], "confirmar")
    assert r.status_code == 200
    assert r.get_json()["estado"] == "CONFIRMADO" and r.get_json()["fecha_confirmacion"]
    assert _accion(client, mesero_headers, pedido["id"], "confirmar").status_code == 409


def test_cp_05_7_2_confirmar_sin_inventario(client, mesero_headers, pedido, carta):
    """CP-05.7-2 | RF-05.6, RF-05.7 | Si el inventario bajó después de registrar, no se confirma (409 con faltantes)."""
    db.session.get(Insumo, carta["pollo"]).stock_actual = 0.3  # alcanza para 1 bandeja y se piden 2
    db.session.commit()
    r = _accion(client, mesero_headers, pedido["id"], "confirmar")
    assert r.status_code == 409
    assert r.get_json()["faltantes"][0]["insumo"] == "Pollo"
    assert client.get(f"/api/pedidos/{pedido['id']}", headers=mesero_headers).get_json()["estado"] == "REGISTRADO"


# ------------------------------------------------------- RF-05.8 Enviar a cocina


def test_cp_05_8_1_enviar_a_cocina(client, mesero_headers, pedido):
    """CP-05.8-1 | RF-05.8 | Sin confirmar no va a cocina (409); confirmado pasa a EN_COCINA y ya no es editable."""
    r = _accion(client, mesero_headers, pedido["id"], "enviar-cocina")
    assert r.status_code == 409 and r.get_json()["error"] == "Primero confirma el pedido con el cliente"
    _accion(client, mesero_headers, pedido["id"], "confirmar")
    r = _accion(client, mesero_headers, pedido["id"], "enviar-cocina")
    assert r.status_code == 200
    assert r.get_json()["estado"] == "EN_COCINA" and r.get_json()["editable"] is False
    assert _accion(client, mesero_headers, pedido["id"], "enviar-cocina").status_code == 409


def test_cp_05_8_2_comanda(client, mesero_headers, pedido):
    """CP-05.8-2 | RF-05.8 | La comanda solo existe tras enviar a cocina y trae mesa y productos sin precios."""
    assert client.get(f"/api/pedidos/{pedido['id']}/comanda", headers=mesero_headers).status_code == 409
    _accion(client, mesero_headers, pedido["id"], "confirmar")
    _accion(client, mesero_headers, pedido["id"], "enviar-cocina")
    comanda = client.get(f"/api/pedidos/{pedido['id']}/comanda", headers=mesero_headers).get_json()
    assert (comanda["mesa"], comanda["comensales"], comanda["observaciones"]) == (1, 2, "Cumpleaños")
    assert comanda["productos"] == [{"cantidad": 2, "producto": "Bandeja", "observacion": "sin cebolla"},
                                    {"cantidad": 1, "producto": "Limonada", "observacion": None}]
    assert "total" not in comanda


# ------------------------------------------------------- RF-05.9 Estado del pedido


def test_cp_05_9_1_estado_del_pedido(client, mesero_headers, pedido):
    """CP-05.9-1 | RF-05.9 | El estado muestra la mesa, si está cobrado y los pasos recorridos con su hora."""
    _accion(client, mesero_headers, pedido["id"], "confirmar")
    _accion(client, mesero_headers, pedido["id"], "enviar-cocina")
    r = client.get(f"/api/pedidos/{pedido['id']}/estado", headers=mesero_headers)
    body = r.get_json()
    assert (body["codigo"], body["mesa"], body["estado"], body["cobrado"]) == (pedido["codigo"], 1, "EN_COCINA", False)
    assert [p["estado"] for p in body["linea_de_tiempo"]] == ["REGISTRADO", "CONFIRMADO", "EN_COCINA"]
    assert body["minutos"] >= 0


def test_cp_05_9_2_cobro_en_caja(client, mesero_headers, admin_headers, pedido, carta):
    """CP-05.9-2 | RF-05.7, RF-09.1, RF-10.3 | Sin confirmar no se cobra; confirmado aparece en caja con su mesa y al
    pagarlo se registra la venta, se descuentan los insumos y la mesa queda libre."""
    orden_id = pedido["orden_id"]
    por_cobrar = lambda: client.get("/api/ordenes/por-cobrar", headers=admin_headers).get_json()  # noqa: E731
    assert por_cobrar() == []
    r = client.post(f"/api/ordenes/{orden_id}/pagos", headers=admin_headers, json={"metodo": "EFECTIVO", "monto": 50000})
    assert r.status_code == 409 and "Confirma el pedido" in r.get_json()["error"]

    _accion(client, mesero_headers, pedido["id"], "confirmar")
    assert [(o["codigo"], o["tipo"], o["mesa"]) for o in por_cobrar()] == [(pedido["codigo"], "MESA", 1)]
    r = client.post(f"/api/ordenes/{orden_id}/pagos", headers=admin_headers, json={"metodo": "TARJETA", "monto": 50000})
    assert r.status_code == 201, r.get_json()

    assert db.session.get(Insumo, carta["pollo"]).stock_actual == 0.5  # 1 − 2 × 0,25
    assert MovimientoInventario.query.filter_by(motivo="CONSUMO").count() == 2
    assert _mesa(client, mesero_headers, 1)["ocupada"] is False
    estado = client.get(f"/api/pedidos/{pedido['id']}/estado", headers=mesero_headers).get_json()
    assert estado["cobrado"] is True


def test_cp_05_9_3_producto_agotado(client, mesero_headers, mesas, carta):
    """CP-05.6-4 | RF-05.6, RF-04.6 | Un producto marcado como no disponible no se puede pedir → 409."""
    db.session.get(Producto, carta["limonada"]).disponible = False
    db.session.commit()
    r = _pedir(client, mesero_headers, mesas[1], carta)
    assert r.status_code == 409 and "no está disponible" in r.get_json()["error"]
