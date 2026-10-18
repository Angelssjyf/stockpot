"""Casos de prueba: gestión de proveedores (RF-02.1 a RF-02.5).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Insumo, OrdenCompra, Usuario

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def insumos(app):
    """Tres insumos de ejemplo; devuelve un diccionario nombre -> id."""
    lista = [
        Insumo(codigo="INS-001", nombre="Arroz", unidad_medida="KG"),
        Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG"),
        Insumo(codigo="INS-003", nombre="Aceite", unidad_medida="L"),
    ]
    db.session.add_all(lista)
    db.session.commit()
    return {i.nombre: i.id for i in lista}


@pytest.fixture()
def cosecha(client, admin_headers):
    """Proveedor ya registrado; devuelve su JSON (incluye el id)."""
    r = client.post("/api/proveedores", headers=admin_headers, json={
        "nit": "900123456-7", "razon_social": "Distribuidora La Cosecha",
        "contacto": "Carlos Ruiz", "telefono": "6075551234", "email": "Ventas@LaCosecha.co",
    })
    return r.get_json()


# ------------------------------------------------------- RF-02.1 Registrar


def test_cp_02_1_1_registrar_proveedor(cosecha):
    """CP-02.1-1 | RF-02.1 | Registrar un proveedor: 201, activo y correo en minúsculas."""
    assert cosecha["id"]
    assert cosecha["razon_social"] == "Distribuidora La Cosecha"
    assert cosecha["email"] == "ventas@lacosecha.co"
    assert cosecha["activo"] is True


def test_cp_02_1_2_campos_obligatorios(client, admin_headers):
    """CP-02.1-2 | RF-02.1 | Sin NIT ni razón social → 422 con los campos faltantes."""
    r = client.post("/api/proveedores", headers=admin_headers, json={"contacto": "Ana"})
    assert r.status_code == 422
    assert set(r.get_json()["faltantes"]) == {"nit", "razon_social"}


def test_cp_02_1_3_nit_duplicado(client, admin_headers, cosecha):
    """CP-02.1-3 | RF-02.1 | Registrar un NIT que ya existe → 409."""
    r = client.post("/api/proveedores", headers=admin_headers,
                    json={"nit": "900123456-7", "razon_social": "Otra empresa"})
    assert r.status_code == 409


def test_cp_02_1_4_correo_invalido(client, admin_headers):
    """CP-02.1-4 | RF-02.1 | Un correo sin @ → 422."""
    r = client.post("/api/proveedores", headers=admin_headers,
                    json={"nit": "800", "razon_social": "Lácteos", "email": "correo-malo"})
    assert r.status_code == 422


# ------------------------------------------------------- RF-02.2 Consultar


def test_cp_02_2_1_buscar_proveedores(client, admin_headers, cosecha):
    """CP-02.2-1 | RF-02.2 | Buscar por razón social, NIT o contacto."""
    client.post("/api/proveedores", headers=admin_headers,
                json={"nit": "800555", "razon_social": "Lácteos del Norte"})

    def buscar(texto):
        r = client.get(f"/api/proveedores?q={texto}", headers=admin_headers)
        return [p["razon_social"] for p in r.get_json()]

    assert buscar("") == ["Distribuidora La Cosecha", "Lácteos del Norte"]  # orden alfabético
    assert buscar("cosecha") == ["Distribuidora La Cosecha"]
    assert buscar("800555") == ["Lácteos del Norte"]
    assert buscar("carlos") == ["Distribuidora La Cosecha"]
    assert buscar("zzz") == []


def test_cp_02_2_2_filtrar_activos(client, admin_headers, cosecha):
    """CP-02.2-2 | RF-02.2 | ?activo=true muestra solo los activos."""
    client.put(f"/api/proveedores/{cosecha['id']}", headers=admin_headers, json={"activo": False})
    activos = client.get("/api/proveedores?activo=true", headers=admin_headers).get_json()
    inactivos = client.get("/api/proveedores?activo=false", headers=admin_headers).get_json()
    assert activos == []
    assert [p["id"] for p in inactivos] == [cosecha["id"]]


def test_cp_02_2_3_detalle_proveedor(client, admin_headers, cosecha):
    """CP-02.2-3 | RF-02.2 | El detalle trae los datos y la lista de insumos (vacía al inicio)."""
    r = client.get(f"/api/proveedores/{cosecha['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.get_json()["nit"] == "900123456-7"
    assert r.get_json()["insumos"] == []


def test_cp_02_2_4_proveedor_inexistente(client, admin_headers):
    """CP-02.2-4 | RF-02.2 | Consultar un proveedor que no existe → 404."""
    assert client.get("/api/proveedores/999", headers=admin_headers).status_code == 404


# ------------------------------------------------------- RF-02.3 Modificar


def test_cp_02_3_1_modificar_proveedor(client, admin_headers, cosecha):
    """CP-02.3-1 | RF-02.3 | Modificar contacto y teléfono; lo demás no cambia."""
    r = client.put(f"/api/proveedores/{cosecha['id']}", headers=admin_headers,
                   json={"contacto": "Marta Gómez", "telefono": "3109998877"})
    assert r.status_code == 200
    assert r.get_json()["contacto"] == "Marta Gómez"
    assert r.get_json()["razon_social"] == "Distribuidora La Cosecha"


def test_cp_02_3_2_nit_de_otro_proveedor(client, admin_headers, cosecha):
    """CP-02.3-2 | RF-02.3 | Cambiar el NIT por el de otro proveedor → 409."""
    otro = client.post("/api/proveedores", headers=admin_headers,
                       json={"nit": "800", "razon_social": "Lácteos"}).get_json()
    r = client.put(f"/api/proveedores/{otro['id']}", headers=admin_headers,
                   json={"nit": "900123456-7"})
    assert r.status_code == 409


def test_cp_02_3_3_error_no_guarda_cambios(client, admin_headers, cosecha):
    """CP-02.3-3 | RF-02.3 | Si un dato es inválido no se guarda ningún cambio."""
    r = client.put(f"/api/proveedores/{cosecha['id']}", headers=admin_headers,
                   json={"contacto": "Cambiado", "razon_social": "  "})
    assert r.status_code == 422
    actual = client.get(f"/api/proveedores/{cosecha['id']}", headers=admin_headers).get_json()
    assert actual["contacto"] == "Carlos Ruiz"


def test_cp_02_3_4_desactivar_proveedor(client, admin_headers, cosecha):
    """CP-02.3-4 | RF-02.3 | Desactivar un proveedor (no se borra)."""
    r = client.put(f"/api/proveedores/{cosecha['id']}", headers=admin_headers,
                   json={"activo": False})
    assert r.get_json()["activo"] is False


# ------------------------------------------------------- RF-02.4 Productos suministrados


def test_cp_02_4_1_asignar_insumos(client, admin_headers, cosecha, insumos):
    """CP-02.4-1 | RF-02.4 | Registrar los insumos que vende el proveedor con su precio."""
    r = client.put(f"/api/proveedores/{cosecha['id']}/insumos", headers=admin_headers, json={
        "insumos": [
            {"insumo_id": insumos["Arroz"], "precio_referencia": 4200},
            {"insumo_id": insumos["Pollo"], "precio_referencia": 13000.5},
        ]
    })
    assert r.status_code == 200
    vendidos = {i["insumo"]: i["precio_referencia"] for i in r.get_json()["insumos"]}
    assert vendidos == {"Arroz": 4200.0, "Pollo": 13000.5}


def test_cp_02_4_2_reemplazar_insumos(client, admin_headers, cosecha, insumos):
    """CP-02.4-2 | RF-02.4 | Enviar la lista otra vez la reemplaza: cambia precios, agrega y quita."""
    url = f"/api/proveedores/{cosecha['id']}/insumos"
    client.put(url, headers=admin_headers, json={"insumos": [
        {"insumo_id": insumos["Arroz"], "precio_referencia": 4200},
        {"insumo_id": insumos["Pollo"], "precio_referencia": 13000},
    ]})
    r = client.put(url, headers=admin_headers, json={"insumos": [
        {"insumo_id": insumos["Arroz"], "precio_referencia": 4500},   # cambia el precio
        {"insumo_id": insumos["Aceite"]},                              # nuevo, sin precio
    ]})                                                                # Pollo se quita
    vendidos = {i["insumo"]: i["precio_referencia"] for i in r.get_json()["insumos"]}
    assert vendidos == {"Arroz": 4500.0, "Aceite": None}


def test_cp_02_4_3_insumo_inexistente(client, admin_headers, cosecha):
    """CP-02.4-3 | RF-02.4 | Un insumo que no existe → 422."""
    r = client.put(f"/api/proveedores/{cosecha['id']}/insumos", headers=admin_headers,
                   json={"insumos": [{"insumo_id": 999}]})
    assert r.status_code == 422


def test_cp_02_4_4_datos_invalidos(client, admin_headers, cosecha, insumos):
    """CP-02.4-4 | RF-02.4 | Insumo repetido, precio negativo o formato incorrecto → 422."""
    url = f"/api/proveedores/{cosecha['id']}/insumos"
    arroz = insumos["Arroz"]
    repetido = {"insumos": [{"insumo_id": arroz}, {"insumo_id": arroz}]}
    negativo = {"insumos": [{"insumo_id": arroz, "precio_referencia": -5}]}
    for cuerpo in (repetido, negativo, {"insumos": "Arroz"}):
        assert client.put(url, headers=admin_headers, json=cuerpo).status_code == 422


def test_cp_02_4_5_error_no_cambia_precios(client, admin_headers, cosecha, insumos):
    """CP-02.4-5 | RF-02.4 | Si una línea es inválida, no se guarda ningún cambio de la lista."""
    url = f"/api/proveedores/{cosecha['id']}/insumos"
    client.put(url, headers=admin_headers,
               json={"insumos": [{"insumo_id": insumos["Arroz"], "precio_referencia": 4200}]})

    r = client.put(url, headers=admin_headers, json={"insumos": [
        {"insumo_id": insumos["Arroz"], "precio_referencia": 9999},  # cambio válido...
        {"insumo_id": 999},                                           # ...pero esta línea falla
    ]})
    assert r.status_code == 422
    detalle = client.get(f"/api/proveedores/{cosecha['id']}", headers=admin_headers).get_json()
    assert detalle["insumos"][0]["precio_referencia"] == 4200.0


# ------------------------------------------------------- RF-02.5 Historial de compras


def test_cp_02_5_1_historial_de_compras(client, admin_headers, cosecha):
    """CP-02.5-1 | RF-02.5 | El historial muestra las órdenes del proveedor, la más reciente primero."""
    admin = Usuario.query.filter_by(email="admin@stockpot.test").one()
    for codigo, total in (("OC-000001", 84000), ("OC-000002", 97500)):
        db.session.add(OrdenCompra(codigo=codigo, proveedor_id=cosecha["id"], usuario=admin,
                                   total=Decimal(total)))
    db.session.commit()

    r = client.get(f"/api/proveedores/{cosecha['id']}/compras", headers=admin_headers)
    assert r.status_code == 200
    assert [o["codigo"] for o in r.get_json()] == ["OC-000002", "OC-000001"]
    assert r.get_json()[0]["total"] == 97500.0
    assert "detalles" not in r.get_json()[0]  # la lista no trae las líneas


def test_cp_02_5_2_historial_vacio(client, admin_headers, cosecha):
    """CP-02.5-2 | RF-02.5 | Un proveedor sin compras devuelve una lista vacía."""
    r = client.get(f"/api/proveedores/{cosecha['id']}/compras", headers=admin_headers)
    assert r.get_json() == []


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_10_bodeguero_gestiona_proveedores(client):
    """CP-SEG-10 | Seguridad | Un BODEGUERO (proveedores.gestionar) puede registrar proveedores."""
    crear_usuario("BODEGUERO", "bodega@stockpot.test")
    headers = iniciar_sesion(client, "bodega@stockpot.test")
    r = client.post("/api/proveedores", headers=headers,
                    json={"nit": "700", "razon_social": "Carnes Premium"})
    assert r.status_code == 201


def test_cp_seg_11_mesero_no_ve_proveedores(client, mesero_headers):
    """CP-SEG-11 | Seguridad | Un MESERO (sin proveedores.ver) no puede consultar ni registrar → 403."""
    assert client.get("/api/proveedores", headers=mesero_headers).status_code == 403
    r = client.post("/api/proveedores", headers=mesero_headers,
                    json={"nit": "700", "razon_social": "X"})
    assert r.status_code == 403