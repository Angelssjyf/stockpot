"""Casos de prueba: incidencias (RF-12.1 a RF-12.4), sugerencia de la sustentación.

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def bodeguero_headers(client):
    crear_usuario("BODEGUERO", "bodega@stockpot.test")
    return iniciar_sesion(client, "bodega@stockpot.test")


@pytest.fixture()
def codigos(client, admin_headers):
    """Catálogo inicial: código -> id."""
    return {c["codigo"]: c["id"] for c in client.get("/api/codigos-incidencia", headers=admin_headers).get_json()}


@pytest.fixture()
def arroz(client, admin_headers):
    r = client.post("/api/insumos", headers=admin_headers,
                    json={"codigo": "INS-001", "nombre": "Arroz", "unidad_medida": "KG"})
    return r.get_json()["id"]


@pytest.fixture()
def entrada_de_50(client, bodeguero_headers, arroz):
    """El bodeguero registra por error 50 kg de arroz (eran 5); devuelve el id del movimiento."""
    r = client.post(f"/api/insumos/{arroz}/movimientos", headers=bodeguero_headers,
                    json={"tipo": "ENTRADA", "motivo": "COMPRA", "cantidad": 50})
    return r.get_json()["movimiento"]["id"]


def _reportar(client, headers, **datos):
    return client.post("/api/incidencias", headers=headers, json=datos)


# ------------------------------------------------------- RF-12.1 Catálogo de códigos


def test_cp_12_1_1_catalogo_inicial(client, admin_headers, codigos):
    """CP-12.1-1 | RF-12.1 | Hay 10 códigos iniciales; ?modulo=VENTAS trae los de ventas y el genérico OTR-01."""
    assert len(codigos) == 10
    r = client.get("/api/codigos-incidencia?modulo=ventas", headers=admin_headers)
    assert [c["codigo"] for c in r.get_json()] == ["OTR-01", "VEN-01", "VEN-02", "VEN-03"]


def test_cp_12_1_2_agregar_codigo(client, admin_headers, bodeguero_headers):
    """CP-12.1-2 | RF-12.1 | El administrador agrega un código; formato inválido → 422, repetido → 409, otro rol → 403."""
    nuevo = {"codigo": "inv-05", "nombre": "Unidad equivocada", "modulo": "INVENTARIO"}
    r = client.post("/api/codigos-incidencia", headers=admin_headers, json=nuevo)
    assert r.status_code == 201 and r.get_json()["codigo"] == "INV-05"
    assert client.post("/api/codigos-incidencia", headers=admin_headers, json=nuevo).status_code == 409
    malo = client.post("/api/codigos-incidencia", headers=admin_headers,
                       json={"codigo": "ERROR", "nombre": "x", "modulo": "OTRO"})
    assert malo.status_code == 422
    assert client.post("/api/codigos-incidencia", headers=bodeguero_headers, json=nuevo).status_code == 403


def test_cp_12_1_3_desactivar_codigo(client, admin_headers, codigos):
    """CP-12.1-3 | RF-12.1 | Un código desactivado ya no aparece para reportar."""
    client.put(f"/api/codigos-incidencia/{codigos['COM-02']}", headers=admin_headers, json={"activo": False})
    activos = [c["codigo"] for c in client.get("/api/codigos-incidencia", headers=admin_headers).get_json()]
    assert "COM-02" not in activos and len(activos) == 9


# ------------------------------------------------------- RF-12.2 Reportar


def test_cp_12_2_1_reportar_con_responsable(client, admin_headers, codigos, entrada_de_50):
    """CP-12.2-1 | RF-12.2 | El responsable es quien hizo el registro y quien reporta queda aparte; código INC-000001."""
    r = _reportar(client, admin_headers, codigo_id=codigos["INV-04"], movimiento_id=entrada_de_50,
                  observacion="Se registró como compra y era una devolución")
    assert r.status_code == 201
    datos = r.get_json()
    assert datos["codigo"] == "INC-000001"
    assert datos["responsable"] != datos["reportado_por"]
    assert datos["tipo"]["codigo"] == "INV-04"
    assert datos["registro"] == "Entrada de 50 KG de Arroz"
    assert datos["ajuste"] is None


def test_cp_12_2_2_validaciones(client, admin_headers, codigos, entrada_de_50):
    """CP-12.2-2 | RF-12.2 | Sin observación, sin registro o con un código de otro módulo → 422; registro inexistente → 404."""
    base = {"codigo_id": codigos["INV-03"], "movimiento_id": entrada_de_50, "observacion": "Era otro insumo"}
    assert _reportar(client, admin_headers, **{**base, "observacion": "x"}).status_code == 422
    assert _reportar(client, admin_headers, codigo_id=codigos["INV-03"], observacion="Era otro insumo").status_code == 422
    r = _reportar(client, admin_headers, **{**base, "codigo_id": codigos["VEN-01"]})
    assert r.status_code == 422 and "ventas" in r.get_json()["error"]
    assert _reportar(client, admin_headers, **{**base, "movimiento_id": 999}).status_code == 404


def test_cp_12_2_3_otro_sirve_para_cualquier_registro(client, admin_headers, codigos, entrada_de_50):
    """CP-12.2-3 | RF-12.2 | El código genérico OTR-01 se puede usar sobre un movimiento de inventario."""
    r = _reportar(client, admin_headers, codigo_id=codigos["OTR-01"], movimiento_id=entrada_de_50,
                  observacion="La observación quedó con el nombre de otro proveedor")
    assert r.status_code == 201


# ------------------------------------------------------- RF-12.3 Corregir el inventario


def test_cp_12_3_1_corregir_cantidad_de_mas(client, admin_headers, codigos, entrada_de_50, arroz):
    """CP-12.3-1 | RF-12.3 | Se registraron 50 kg y eran 5: se crea una salida de ajuste de 45 y el stock queda en 5."""
    r = _reportar(client, admin_headers, codigo_id=codigos["INV-01"], movimiento_id=entrada_de_50,
                  cantidad_real=5, observacion="Registré por equivocación más kilos de los que eran")
    assert r.status_code == 201
    assert r.get_json()["ajuste"]["tipo"] == "SALIDA" and r.get_json()["ajuste"]["cantidad"] == 45
    assert client.get(f"/api/insumos/{arroz}", headers=admin_headers).get_json()["stock_actual"] == 5
    otra = _reportar(client, admin_headers, codigo_id=codigos["INV-01"], movimiento_id=entrada_de_50,
                     cantidad_real=4, observacion="Otra vez el mismo")
    assert otra.status_code == 409


def test_cp_12_3_2_cantidad_incoherente(client, admin_headers, codigos, entrada_de_50):
    """CP-12.3-2 | RF-12.3 | INV-02 con una cantidad menor, una cantidad igual o sin cantidad → 422."""
    base = {"movimiento_id": entrada_de_50, "observacion": "Cantidad mal registrada"}
    assert _reportar(client, admin_headers, codigo_id=codigos["INV-02"], cantidad_real=5, **base).status_code == 422
    assert _reportar(client, admin_headers, codigo_id=codigos["INV-01"], cantidad_real=50, **base).status_code == 422
    assert _reportar(client, admin_headers, codigo_id=codigos["INV-01"], **base).status_code == 422


def test_cp_12_3_3_corregir_salida(client, admin_headers, bodeguero_headers, codigos, entrada_de_50, arroz):
    """CP-12.3-3 | RF-12.3 | Una salida de 10 que era de 4 se corrige con una entrada de ajuste de 6."""
    salida = client.post(f"/api/insumos/{arroz}/movimientos", headers=bodeguero_headers,
                         json={"tipo": "SALIDA", "motivo": "MERMA", "cantidad": 10}).get_json()["movimiento"]["id"]
    r = _reportar(client, admin_headers, codigo_id=codigos["INV-01"], movimiento_id=salida,
                  cantidad_real=4, observacion="La merma fue de 4 kg")
    assert r.get_json()["ajuste"] == {"id": r.get_json()["ajuste"]["id"], "tipo": "ENTRADA", "cantidad": 6.0}
    assert client.get(f"/api/insumos/{arroz}", headers=admin_headers).get_json()["stock_actual"] == 46


# ------------------------------------------------------- RF-12.4 Bitácora


def test_cp_12_4_1_bitacora_con_resumen(client, admin_headers, codigos, entrada_de_50):
    """CP-12.4-1 | RF-12.4 | La bitácora cuenta por responsable, por tipo y por módulo, y filtra por código."""
    _reportar(client, admin_headers, codigo_id=codigos["INV-01"], movimiento_id=entrada_de_50,
              cantidad_real=5, observacion="Eran 5 kg")
    _reportar(client, admin_headers, codigo_id=codigos["INV-04"], movimiento_id=entrada_de_50,
              observacion="Era una devolución")
    datos = client.get("/api/incidencias", headers=admin_headers).get_json()
    resumen = datos["resumen"]
    assert resumen["total"] == 2 and resumen["corregidas"] == 1
    assert resumen["por_usuario"][0]["total"] == 2
    assert {t["codigo"] for t in resumen["por_tipo"]} == {"INV-01", "INV-04"}
    assert resumen["por_modulo"] == {"INVENTARIO": 2}
    filtrada = client.get(f"/api/incidencias?codigo_id={codigos['INV-04']}", headers=admin_headers).get_json()
    assert [i["tipo"]["codigo"] for i in filtrada["incidencias"]] == ["INV-04"]


def test_cp_seg_23_solo_admin_ve_la_bitacora(client, bodeguero_headers, codigos, entrada_de_50):
    """CP-SEG-23 | Seguridad | Un BODEGUERO puede reportar, pero no ve la bitácora (403)."""
    r = _reportar(client, bodeguero_headers, codigo_id=codigos["INV-03"], movimiento_id=entrada_de_50,
                  observacion="Lo registré en el insumo equivocado")
    assert r.status_code == 201
    assert client.get("/api/incidencias", headers=bodeguero_headers).status_code == 403
