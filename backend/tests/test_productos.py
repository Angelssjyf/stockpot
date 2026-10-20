"""Casos de prueba: productos y menú (RF-04.1 a RF-04.6).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from app.extensions import db
from app.models import Insumo, Receta

from .conftest import crear_usuario, iniciar_sesion


@pytest.fixture()
def insumos():
    """Arroz (10 KG a $4.200) y pollo (5 KG a $13.000)."""
    arroz = Insumo(codigo="INS-001", nombre="Arroz", unidad_medida="KG",
                   stock_actual=10, costo_unitario=4200)
    pollo = Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG",
                   stock_actual=5, costo_unitario=13000)
    db.session.add_all([arroz, pollo])
    db.session.commit()
    return {"arroz": arroz.id, "pollo": pollo.id}


@pytest.fixture()
def bandeja(client, admin_headers, insumos):
    """Plato con receta: 0,15 KG de arroz y 0,25 KG de pollo por porción."""
    r = client.post("/api/productos", headers=admin_headers, json={
        "codigo": "prd-001", "nombre": "Bandeja de pollo", "categoria": "PLATO_FUERTE",
        "precio_venta": 22000, "descripcion": "Con arroz",
        "receta": [{"insumo_id": insumos["arroz"], "cantidad": 0.15},
                   {"insumo_id": insumos["pollo"], "cantidad": 0.25}],
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _crear(client, headers, **datos):
    base = {"codigo": "PRD-009", "nombre": "Gaseosa", "categoria": "BEBIDA", "precio_venta": 4500}
    return client.post("/api/productos", headers=headers, json={**base, **datos})


# ------------------------------------------------------- RF-04.1 Registrar


def test_cp_04_1_1_registrar_con_receta(bandeja):
    """CP-04.1-1 | RF-04.1, RF-04.4 | Registra el plato con su receta, costo, margen y porciones."""
    assert bandeja["codigo"] == "PRD-001"  # se guarda en mayúsculas
    assert len(bandeja["receta"]) == 2
    assert bandeja["costo"] == 3880.0        # 0,15 × 4.200 + 0,25 × 13.000
    assert bandeja["margen"] == 18120.0      # 22.000 − 3.880
    assert bandeja["porciones_posibles"] == 20  # el pollo alcanza para 5 / 0,25 = 20
    assert bandeja["disponible"] is True


def test_cp_04_1_2_campos_obligatorios(client, admin_headers):
    """CP-04.1-2 | RF-04.1 | Sin nombre, categoría ni precio → 422 con la lista de faltantes."""
    r = client.post("/api/productos", headers=admin_headers, json={"codigo": "PRD-010"})
    assert r.status_code == 422
    assert r.get_json()["faltantes"] == ["nombre", "categoria", "precio_venta"]


def test_cp_04_1_3_codigo_repetido(client, admin_headers, bandeja):
    """CP-04.1-3 | RF-04.1 | Un código que ya existe → 409."""
    assert _crear(client, admin_headers, codigo="PRD-001").status_code == 409


def test_cp_04_1_4_categoria_invalida(client, admin_headers):
    """CP-04.1-4 | RF-04.1 | Una categoría que no existe → 422."""
    assert _crear(client, admin_headers, categoria="SOPA_MAGICA").status_code == 422


# ------------------------------------------------------- RF-04.2 Consultar


def test_cp_04_2_1_consultar_con_filtros(client, admin_headers, bandeja):
    """CP-04.2-1 | RF-04.2 | Filtra por texto y categoría; la carta solo trae lo disponible y activo."""
    _crear(client, admin_headers)  # Gaseosa (BEBIDA)
    _crear(client, admin_headers, codigo="PRD-011", nombre="Jugo", disponible=False)
    _crear(client, admin_headers, codigo="PRD-012", nombre="Malta", activo=False)

    nombres = lambda url: [p["nombre"] for p in client.get(url, headers=admin_headers).get_json()]  # noqa: E731
    assert nombres("/api/productos") == ["Bandeja de pollo", "Gaseosa", "Jugo", "Malta"]
    assert nombres("/api/productos?q=band") == ["Bandeja de pollo"]
    assert nombres("/api/productos?categoria=bebida") == ["Gaseosa", "Jugo", "Malta"]
    assert nombres("/api/productos?disponible=true") == ["Bandeja de pollo", "Gaseosa"]


def test_cp_04_2_2_detalle(client, admin_headers, bandeja):
    """CP-04.2-2 | RF-04.2 | El detalle trae la receta con el costo de cada insumo; uno inexistente → 404."""
    r = client.get(f"/api/productos/{bandeja['id']}", headers=admin_headers)
    receta = {linea["insumo"]: linea for linea in r.get_json()["receta"]}
    assert receta["Pollo"]["cantidad"] == 0.25
    assert receta["Pollo"]["costo"] == 3250.0
    assert client.get("/api/productos/999", headers=admin_headers).status_code == 404


# ------------------------------------------------------- RF-04.3 Modificar


def test_cp_04_3_1_modificar(client, admin_headers, bandeja):
    """CP-04.3-1 | RF-04.3 | Modifica nombre y descripción sin tocar la receta."""
    r = client.put(f"/api/productos/{bandeja['id']}", headers=admin_headers,
                   json={"nombre": "Bandeja especial", "descripcion": ""})
    assert r.status_code == 200
    assert r.get_json()["nombre"] == "Bandeja especial"
    assert r.get_json()["descripcion"] is None
    assert len(r.get_json()["receta"]) == 2


# ------------------------------------------------------- RF-04.4 Recetas


def test_cp_04_4_1_reemplazar_receta(client, admin_headers, bandeja, insumos):
    """CP-04.4-1 | RF-04.4 | La receta nueva reemplaza a la anterior (quita y cambia cantidades)."""
    r = client.put(f"/api/productos/{bandeja['id']}", headers=admin_headers,
                   json={"receta": [{"insumo_id": insumos["pollo"], "cantidad": 0.3}]})
    assert r.status_code == 200
    assert [(l["insumo"], l["cantidad"]) for l in r.get_json()["receta"]] == [("Pollo", 0.3)]
    assert Receta.query.count() == 1


@pytest.mark.parametrize("receta, mensaje", [
    ([{"insumo_id": "ARROZ", "cantidad": 1}], "no existe"),
    ([{"insumo_id": 999, "cantidad": 1}], "no existe"),
    ([{"insumo_id": 1, "cantidad": 0}], "mayor que cero"),
    ([{"insumo_id": 1, "cantidad": "poco"}], "debe ser un número"),
    ([{"insumo_id": 1, "cantidad": 1}, {"insumo_id": 1, "cantidad": 2}], "repetido"),
    ("arroz", "debe ser una lista"),
])
def test_cp_04_4_2_receta_invalida(client, admin_headers, bandeja, receta, mensaje):
    """CP-04.4-2 | RF-04.4 | Insumo inexistente, cantidad inválida o repetido → 422 y la receta no cambia."""
    r = client.put(f"/api/productos/{bandeja['id']}", headers=admin_headers,
                   json={"nombre": "No debe guardarse", "receta": receta})
    assert r.status_code == 422
    assert mensaje in r.get_json()["error"]
    detalle = client.get(f"/api/productos/{bandeja['id']}", headers=admin_headers).get_json()
    assert detalle["nombre"] == "Bandeja de pollo"
    assert len(detalle["receta"]) == 2


# ------------------------------------------------------- RF-04.5 Precios


def test_cp_04_5_1_cambiar_precio(client, admin_headers, bandeja):
    """CP-04.5-1 | RF-04.5 | Cambiar el precio recalcula el margen."""
    r = client.put(f"/api/productos/{bandeja['id']}", headers=admin_headers,
                   json={"precio_venta": 24000})
    assert r.get_json()["precio_venta"] == 24000.0
    assert r.get_json()["margen"] == 20120.0


@pytest.mark.parametrize("precio", [0, -100, "caro"])
def test_cp_04_5_2_precio_invalido(client, admin_headers, bandeja, precio):
    """CP-04.5-2 | RF-04.5 | Precio en cero, negativo o no numérico → 422."""
    r = client.put(f"/api/productos/{bandeja['id']}", headers=admin_headers,
                   json={"precio_venta": precio})
    assert r.status_code == 422


# ------------------------------------------------------- RF-04.6 Disponibilidad


def test_cp_04_6_1_marcar_agotado(client, admin_headers, bandeja):
    """CP-04.6-1 | RF-04.6 | Un plato marcado como no disponible sale de la carta."""
    r = client.patch(f"/api/productos/{bandeja['id']}/disponibilidad", headers=admin_headers,
                     json={"disponible": False})
    assert r.status_code == 200
    assert r.get_json()["disponible"] is False
    carta = client.get("/api/productos?disponible=true", headers=admin_headers).get_json()
    assert carta == []

    r = client.patch(f"/api/productos/{bandeja['id']}/disponibilidad", headers=admin_headers,
                     json={"disponible": "no"})
    assert r.status_code == 422


def test_cp_04_6_2_cocina_cambia_disponibilidad(client, bandeja):
    """CP-04.6-2 | RF-04.6 | La cocina puede marcar un plato agotado, pero no modificarlo."""
    crear_usuario("COCINERO", "cocina@stockpot.test")
    headers = iniciar_sesion(client, "cocina@stockpot.test")
    url = f"/api/productos/{bandeja['id']}"
    assert client.patch(f"{url}/disponibilidad", headers=headers,
                        json={"disponible": False}).status_code == 200
    assert client.put(url, headers=headers, json={"precio_venta": 1}).status_code == 403


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_18_mesero_ve_la_carta(client, mesero_headers, bandeja):
    """CP-SEG-18 | Seguridad | Un MESERO ve la carta pero no puede registrar productos → 403."""
    assert client.get("/api/productos?disponible=true", headers=mesero_headers).status_code == 200
    assert _crear(client, mesero_headers).status_code == 403
