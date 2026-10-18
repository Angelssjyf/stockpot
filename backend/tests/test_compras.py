"""Casos de prueba: órdenes de compra (RF-02.6 a RF-02.8).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import Insumo, OrdenCompra, Proveedor

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def datos(app):
    """Un proveedor activo, uno inactivo y dos insumos con stock inicial."""
    arroz = Insumo(codigo="INS-001", nombre="Arroz", unidad_medida="KG", stock_actual=5)
    pollo = Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG", stock_actual=0)
    cosecha = Proveedor(nit="900123456-7", razon_social="Distribuidora La Cosecha")
    cerrado = Proveedor(nit="800", razon_social="Proveedor Cerrado", activo=False)
    db.session.add_all([arroz, pollo, cosecha, cerrado])
    db.session.commit()
    return {"arroz": arroz.id, "pollo": pollo.id, "cosecha": cosecha.id, "cerrado": cerrado.id}


def _orden_valida(datos):
    return {
        "proveedor_id": datos["cosecha"],
        "fecha_entrega_estimada": "2026-10-20",
        "observaciones": "Entregar en la mañana",
        "detalles": [
            {"insumo_id": datos["arroz"], "cantidad": 20, "precio_unitario": 4200},
            {"insumo_id": datos["pollo"], "cantidad": 7.5, "precio_unitario": 13000},
        ],
    }


@pytest.fixture()
def orden(client, admin_headers, datos):
    """Orden de compra ya registrada (PENDIENTE); devuelve su JSON."""
    return client.post("/api/ordenes-compra", headers=admin_headers,
                       json=_orden_valida(datos)).get_json()


def _cambiar_estado(client, headers, orden_id, estado):
    return client.patch(f"/api/ordenes-compra/{orden_id}/estado", headers=headers,
                        json={"estado": estado})


# ------------------------------------------------------- RF-02.6 Registrar


def test_cp_02_6_1_registrar_orden(orden):
    """CP-02.6-1 | RF-02.6 | Registrar una orden: código consecutivo, subtotales y total calculados."""
    assert orden["codigo"] == f"OC-{orden['id']:06d}"
    assert orden["estado"] == "PENDIENTE"
    assert [d["subtotal"] for d in orden["detalles"]] == [84000.0, 97500.0]
    assert orden["total"] == 181500.0
    assert orden["fecha_entrega_estimada"] == "2026-10-20"
    assert orden["usuario"] == "Prueba Administrador"  # quién la registró


def test_cp_02_6_2_codigos_consecutivos(client, admin_headers, datos, orden):
    """CP-02.6-2 | RF-02.6 | Cada orden nueva recibe el siguiente código."""
    segunda = client.post("/api/ordenes-compra", headers=admin_headers,
                          json=_orden_valida(datos)).get_json()
    assert segunda["codigo"] == f"OC-{orden['id'] + 1:06d}"


def test_cp_02_6_3_orden_sin_insumos(client, admin_headers, datos):
    """CP-02.6-3 | RF-02.6 | Una orden sin líneas → 422 y no se guarda nada."""
    cuerpo = {**_orden_valida(datos), "detalles": []}
    assert client.post("/api/ordenes-compra", headers=admin_headers, json=cuerpo).status_code == 422
    assert OrdenCompra.query.count() == 0


def test_cp_02_6_4_proveedor_invalido(client, admin_headers, datos):
    """CP-02.6-4 | RF-02.6 | Proveedor inexistente o inactivo → 422."""
    for proveedor_id in (999, datos["cerrado"]):
        cuerpo = {**_orden_valida(datos), "proveedor_id": proveedor_id}
        r = client.post("/api/ordenes-compra", headers=admin_headers, json=cuerpo)
        assert r.status_code == 422


@pytest.mark.parametrize("linea_mala", [
    {"insumo_id": 999, "cantidad": 1, "precio_unitario": 1},       # insumo inexistente
    {"insumo_id": "arroz", "cantidad": 0, "precio_unitario": 1},    # cantidad en cero
    {"insumo_id": "arroz", "cantidad": -3, "precio_unitario": 1},   # cantidad negativa
    {"insumo_id": "arroz", "cantidad": "diez", "precio_unitario": 1},  # no es número
    {"insumo_id": "arroz", "cantidad": 1, "precio_unitario": -100},    # precio negativo
])
def test_cp_02_6_5_lineas_invalidas(client, admin_headers, datos, linea_mala):
    """CP-02.6-5 | RF-02.6 | Líneas con datos inválidos → 422 y no se guarda la orden."""
    if linea_mala["insumo_id"] == "arroz":
        linea_mala = {**linea_mala, "insumo_id": datos["arroz"]}
    cuerpo = {**_orden_valida(datos), "detalles": [linea_mala]}
    assert client.post("/api/ordenes-compra", headers=admin_headers, json=cuerpo).status_code == 422
    assert OrdenCompra.query.count() == 0


def test_cp_02_6_6_insumo_repetido(client, admin_headers, datos):
    """CP-02.6-6 | RF-02.6 | El mismo insumo dos veces en la orden → 422."""
    linea = {"insumo_id": datos["arroz"], "cantidad": 1, "precio_unitario": 1}
    cuerpo = {**_orden_valida(datos), "detalles": [linea, linea]}
    assert client.post("/api/ordenes-compra", headers=admin_headers, json=cuerpo).status_code == 422


def test_cp_02_6_7_fecha_invalida(client, admin_headers, datos):
    """CP-02.6-7 | RF-02.6 | Una fecha de entrega con formato incorrecto → 422."""
    cuerpo = {**_orden_valida(datos), "fecha_entrega_estimada": "20/10/2026"}
    assert client.post("/api/ordenes-compra", headers=admin_headers, json=cuerpo).status_code == 422


def test_cp_02_6_8_consultar_ordenes(client, admin_headers, datos, orden):
    """CP-02.6-8 | RF-02.6 | Consultar la lista (sin líneas) y el detalle (con líneas)."""
    lista = client.get("/api/ordenes-compra", headers=admin_headers).get_json()
    assert [o["codigo"] for o in lista] == [orden["codigo"]]
    assert "detalles" not in lista[0]

    detalle = client.get(f"/api/ordenes-compra/{orden['id']}", headers=admin_headers).get_json()
    assert len(detalle["detalles"]) == 2
    assert client.get("/api/ordenes-compra/999", headers=admin_headers).status_code == 404


def test_cp_02_6_9_filtrar_por_estado(client, admin_headers, datos, orden):
    """CP-02.6-9 | RF-02.6 | Filtrar la lista por estado."""
    _cambiar_estado(client, admin_headers, orden["id"], "ENVIADA")
    enviadas = client.get("/api/ordenes-compra?estado=enviada", headers=admin_headers).get_json()
    pendientes = client.get("/api/ordenes-compra?estado=PENDIENTE",
                            headers=admin_headers).get_json()
    assert len(enviadas) == 1
    assert pendientes == []


# ------------------------------------------------------- RF-02.7 Actualizar estado


def test_cp_02_7_1_flujo_completo(client, admin_headers, orden):
    """CP-02.7-1 | RF-02.7 | PENDIENTE → ENVIADA → RECIBIDA."""
    assert _cambiar_estado(client, admin_headers, orden["id"], "ENVIADA").get_json()["estado"] \
        == "ENVIADA"
    recibida = _cambiar_estado(client, admin_headers, orden["id"], "RECIBIDA").get_json()
    assert recibida["estado"] == "RECIBIDA"
    assert recibida["fecha_recepcion"] is not None


@pytest.mark.parametrize("estados, invalido", [
    ([], "RECIBIDA"),                       # no se puede recibir sin enviar
    (["CANCELADA"], "ENVIADA"),             # una cancelada no se reabre
    (["ENVIADA", "RECIBIDA"], "CANCELADA"),  # una recibida no se cancela
    (["ENVIADA"], "PENDIENTE"),             # no se devuelve a pendiente
    ([], "INVENTADO"),                      # estado que no existe
])
def test_cp_02_7_2_transiciones_invalidas(client, admin_headers, orden, estados, invalido):
    """CP-02.7-2 | RF-02.7 | Saltos o retrocesos de estado no permitidos → 409."""
    for estado in estados:
        _cambiar_estado(client, admin_headers, orden["id"], estado)
    assert _cambiar_estado(client, admin_headers, orden["id"], invalido).status_code == 409


def test_cp_02_7_3_cancelar_pendiente(client, admin_headers, orden):
    """CP-02.7-3 | RF-02.7 | Una orden pendiente se puede cancelar."""
    r = _cambiar_estado(client, admin_headers, orden["id"], "CANCELADA")
    assert r.get_json()["estado"] == "CANCELADA"


# ------------------------------------------------------- RF-02.8 Relación con inventario


def test_cp_02_8_1_recibir_suma_stock(client, admin_headers, datos, orden):
    """CP-02.8-1 | RF-02.8 | Al recibir la orden, el stock de cada insumo aumenta."""
    _cambiar_estado(client, admin_headers, orden["id"], "ENVIADA")
    _cambiar_estado(client, admin_headers, orden["id"], "RECIBIDA")

    assert float(db.session.get(Insumo, datos["arroz"]).stock_actual) == 25.0  # 5 + 20
    assert float(db.session.get(Insumo, datos["pollo"]).stock_actual) == 7.5   # 0 + 7.5


def test_cp_02_8_2_cancelar_no_cambia_stock(client, admin_headers, datos, orden):
    """CP-02.8-2 | RF-02.8 | Enviar o cancelar una orden no cambia el stock."""
    _cambiar_estado(client, admin_headers, orden["id"], "ENVIADA")
    _cambiar_estado(client, admin_headers, orden["id"], "CANCELADA")
    assert float(db.session.get(Insumo, datos["arroz"]).stock_actual) == 5.0


def test_cp_02_8_3_no_se_recibe_dos_veces(client, admin_headers, datos, orden):
    """CP-02.8-3 | RF-02.8 | Una orden recibida no puede volver a sumar stock."""
    for estado in ("ENVIADA", "RECIBIDA", "RECIBIDA"):
        _cambiar_estado(client, admin_headers, orden["id"], estado)
    assert float(db.session.get(Insumo, datos["arroz"]).stock_actual) == 25.0


def test_cp_02_8_4_historial_del_proveedor(client, admin_headers, datos, orden):
    """CP-02.8-4 | RF-02.5, RF-02.6 | La orden registrada aparece en el historial del proveedor."""
    r = client.get(f"/api/proveedores/{datos['cosecha']}/compras", headers=admin_headers)
    assert [o["codigo"] for o in r.get_json()] == [orden["codigo"]]


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_12_bodeguero_gestiona_compras(client, datos):
    """CP-SEG-12 | Seguridad | Un BODEGUERO (compras.gestionar) registra y recibe órdenes."""
    crear_usuario("BODEGUERO", "bodega@stockpot.test")
    headers = iniciar_sesion(client, "bodega@stockpot.test")
    orden = client.post("/api/ordenes-compra", headers=headers, json=_orden_valida(datos))
    assert orden.status_code == 201
    assert orden.get_json()["usuario"] == "Prueba Bodeguero"
    _cambiar_estado(client, headers, orden.get_json()["id"], "ENVIADA")
    assert _cambiar_estado(client, headers, orden.get_json()["id"], "RECIBIDA").status_code == 200


def test_cp_seg_13_cajero_no_ve_compras(client, datos):
    """CP-SEG-13 | Seguridad | Un CAJERO (sin compras.ver) no puede consultar ni registrar → 403."""
    crear_usuario("CAJERO", "caja@stockpot.test")
    headers = iniciar_sesion(client, "caja@stockpot.test")
    assert client.get("/api/ordenes-compra", headers=headers).status_code == 403
    r = client.post("/api/ordenes-compra", headers=headers, json=_orden_valida(datos))
    assert r.status_code == 403
