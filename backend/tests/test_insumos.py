"""Casos de prueba: insumos del inventario (RF-03.1 a RF-03.3).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def arroz(client, admin_headers):
    """Insumo ya registrado; devuelve su JSON (incluye el id)."""
    r = client.post("/api/insumos", headers=admin_headers,
                    json={"codigo": "ins-001", "nombre": "Arroz", "unidad_medida": "kg"})
    return r.get_json()


# ------------------------------------------------------- RF-03.1 Registrar


def test_cp_03_1_1_registrar_insumo(arroz):
    """CP-03.1-1 | RF-03.1 | Registrar un insumo: código y unidad en mayúsculas, stock 0, activo."""
    assert arroz["id"]
    assert arroz["codigo"] == "INS-001"
    assert arroz["unidad_medida"] == "KG"
    assert arroz["stock_actual"] == 0
    assert arroz["activo"] is True


def test_cp_03_1_2_campos_obligatorios(client, admin_headers):
    """CP-03.1-2 | RF-03.1 | Sin código, nombre ni unidad → 422 con los campos faltantes."""
    r = client.post("/api/insumos", headers=admin_headers, json={})
    assert r.status_code == 422
    assert set(r.get_json()["faltantes"]) == {"codigo", "nombre", "unidad_medida"}


def test_cp_03_1_3_codigo_duplicado(client, admin_headers, arroz):
    """CP-03.1-3 | RF-03.1 | Registrar un código que ya existe (sin importar mayúsculas) → 409."""
    r = client.post("/api/insumos", headers=admin_headers,
                    json={"codigo": "INS-001", "nombre": "Otro", "unidad_medida": "KG"})
    assert r.status_code == 409


def test_cp_03_1_4_unidad_invalida(client, admin_headers):
    """CP-03.1-4 | RF-03.1 | Una unidad de medida que no existe → 422."""
    r = client.post("/api/insumos", headers=admin_headers,
                    json={"codigo": "INS-002", "nombre": "Pollo", "unidad_medida": "LIBRAS"})
    assert r.status_code == 422


def test_cp_03_1_5_no_se_fija_el_stock(client, admin_headers):
    """CP-03.1-5 | RF-03.1 | No se puede crear un insumo con stock inicial → 422."""
    r = client.post("/api/insumos", headers=admin_headers, json={
        "codigo": "INS-003", "nombre": "Aceite", "unidad_medida": "L", "stock_actual": 50})
    assert r.status_code == 422


# ------------------------------------------------------- RF-03.2 Consultar


def test_cp_03_2_1_buscar_insumos(client, admin_headers, arroz):
    """CP-03.2-1 | RF-03.2 | Buscar por código o nombre, en orden alfabético."""
    client.post("/api/insumos", headers=admin_headers,
                json={"codigo": "INS-002", "nombre": "Aceite", "unidad_medida": "L"})

    def buscar(texto):
        r = client.get(f"/api/insumos?q={texto}", headers=admin_headers)
        return [i["nombre"] for i in r.get_json()]

    assert buscar("") == ["Aceite", "Arroz"]
    assert buscar("arr") == ["Arroz"]
    assert buscar("ins-002") == ["Aceite"]
    assert buscar("zzz") == []


def test_cp_03_2_2_filtrar_activos(client, admin_headers, arroz):
    """CP-03.2-2 | RF-03.2 | ?activo=true muestra solo los insumos activos."""
    client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers, json={"activo": False})
    assert client.get("/api/insumos?activo=true", headers=admin_headers).get_json() == []
    inactivos = client.get("/api/insumos?activo=false", headers=admin_headers).get_json()
    assert [i["id"] for i in inactivos] == [arroz["id"]]


def test_cp_03_2_3_detalle_insumo(client, admin_headers, arroz):
    """CP-03.2-3 | RF-03.2 | Consultar un insumo; si no existe → 404."""
    r = client.get(f"/api/insumos/{arroz['id']}", headers=admin_headers)
    assert r.get_json()["nombre"] == "Arroz"
    assert client.get("/api/insumos/999", headers=admin_headers).status_code == 404


# ------------------------------------------------------- RF-03.3 Modificar


def test_cp_03_3_1_modificar_insumo(client, admin_headers, arroz):
    """CP-03.3-1 | RF-03.3 | Modificar nombre y unidad; lo demás no cambia."""
    r = client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers,
                   json={"nombre": "Arroz blanco", "unidad_medida": "g"})
    assert r.status_code == 200
    assert r.get_json()["nombre"] == "Arroz blanco"
    assert r.get_json()["unidad_medida"] == "G"
    assert r.get_json()["codigo"] == "INS-001"


def test_cp_03_3_2_no_modificar_stock(client, admin_headers, arroz):
    """CP-03.3-2 | RF-03.3 | El stock no se cambia al modificar un insumo → 422."""
    r = client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers,
                   json={"stock_actual": 100})
    assert r.status_code == 422


def test_cp_03_3_3_error_no_guarda_cambios(client, admin_headers, arroz):
    """CP-03.3-3 | RF-03.3 | Si un dato es inválido no se guarda ningún cambio."""
    r = client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers,
                   json={"nombre": "Cambiado", "unidad_medida": "BULTOS"})
    assert r.status_code == 422
    actual = client.get(f"/api/insumos/{arroz['id']}", headers=admin_headers).get_json()
    assert actual["nombre"] == "Arroz"


def test_cp_03_3_4_codigo_de_otro_insumo(client, admin_headers, arroz):
    """CP-03.3-4 | RF-03.3 | Cambiar el código por el de otro insumo → 409."""
    otro = client.post("/api/insumos", headers=admin_headers,
                       json={"codigo": "INS-002", "nombre": "Pollo", "unidad_medida": "KG"})
    r = client.put(f"/api/insumos/{otro.get_json()['id']}", headers=admin_headers,
                   json={"codigo": "INS-001"})
    assert r.status_code == 409


def test_cp_03_3_5_insumo_inactivo_no_se_compra(client, admin_headers, arroz):
    """CP-03.3-5 | RF-03.3, RF-02.6 | Un insumo desactivado no se puede usar en órdenes de compra."""
    client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers, json={"activo": False})
    proveedor = client.post("/api/proveedores", headers=admin_headers,
                            json={"nit": "900", "razon_social": "La Cosecha"}).get_json()
    r = client.post("/api/ordenes-compra", headers=admin_headers, json={
        "proveedor_id": proveedor["id"],
        "detalles": [{"insumo_id": arroz["id"], "cantidad": 10, "precio_unitario": 4200}],
    })
    assert r.status_code == 422


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_14_cocinero_consulta_pero_no_registra(client):
    """CP-SEG-14 | Seguridad | Un COCINERO (inventario.ver) consulta insumos pero no registra → 403."""
    crear_usuario("COCINERO", "cocina@stockpot.test")
    headers = iniciar_sesion(client, "cocina@stockpot.test")
    assert client.get("/api/insumos", headers=headers).status_code == 200
    r = client.post("/api/insumos", headers=headers,
                    json={"codigo": "INS-009", "nombre": "Sal", "unidad_medida": "G"})
    assert r.status_code == 403


def test_cp_seg_15_bodeguero_registra_insumos(client):
    """CP-SEG-15 | Seguridad | Un BODEGUERO (inventario.gestionar) registra insumos."""
    crear_usuario("BODEGUERO", "bodega@stockpot.test")
    headers = iniciar_sesion(client, "bodega@stockpot.test")
    r = client.post("/api/insumos", headers=headers,
                    json={"codigo": "INS-009", "nombre": "Sal", "unidad_medida": "G"})
    assert r.status_code == 201


def test_cp_seg_16_mesero_no_ve_insumos(client, mesero_headers):
    """CP-SEG-16 | Seguridad | Un MESERO (sin permisos de inventario) no consulta insumos → 403."""
    assert client.get("/api/insumos", headers=mesero_headers).status_code == 403


# ------------------------------------------------------- RF-03.10 Categorías


def test_cp_03_10_1_categoria_por_defecto_y_elegida(client, admin_headers, arroz):
    """CP-03.10-1 | RF-03.10 | Sin categoría el insumo queda en OTROS; se puede elegir otra al crear o editar."""
    assert arroz["categoria"] == "OTROS"
    r = client.post("/api/insumos", headers=admin_headers, json={
        "codigo": "INS-002", "nombre": "Carne de cerdo", "unidad_medida": "KG", "categoria": "carnes"})
    assert r.status_code == 201
    assert r.get_json()["categoria"] == "CARNES"
    r = client.put(f"/api/insumos/{arroz['id']}", headers=admin_headers, json={"categoria": "GRANOS"})
    assert r.get_json()["categoria"] == "GRANOS"


def test_cp_03_10_2_categoria_invalida(client, admin_headers):
    """CP-03.10-2 | RF-03.10 | Una categoría que no existe → 422 con las opciones."""
    r = client.post("/api/insumos", headers=admin_headers, json={
        "codigo": "INS-009", "nombre": "Silla", "unidad_medida": "UNIDAD", "categoria": "MUEBLES"})
    assert r.status_code == 422
    assert "MOBILIARIO" in r.get_json()["error"]


def test_cp_03_10_3_filtrar_por_categoria(client, admin_headers, arroz):
    """CP-03.10-3 | RF-03.10 | ?categoria= devuelve solo los insumos de esa categoría."""
    client.post("/api/insumos", headers=admin_headers, json={
        "codigo": "INS-002", "nombre": "Silla plástica", "unidad_medida": "UNIDAD", "categoria": "MOBILIARIO"})
    r = client.get("/api/insumos?categoria=mobiliario", headers=admin_headers)
    assert [i["nombre"] for i in r.get_json()] == ["Silla plástica"]
