"""Casos de prueba: gestión de usuarios (RF-01.1, RF-01.2) y permisos por rol.

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest


@pytest.fixture()
def nuevo_mesero(roles):
    return {
        "nombre": "Ana",
        "apellido": "Pérez",
        "email": "Ana@StockPot.test",
        "password": "Clave12345",
        "rol_id": roles["MESERO"],
    }


# ------------------------------------------------------- RF-01.1 Registrar


def test_cp_01_1_1_registrar_usuario(client, admin_headers, nuevo_mesero):
    """CP-01.1-1 | RF-01.1 | El admin registra un usuario: 201, correo en minúsculas, sin hash."""
    r = client.post("/api/usuarios", headers=admin_headers, json=nuevo_mesero)

    assert r.status_code == 201
    body = r.get_json()
    assert body["email"] == "ana@stockpot.test"
    assert body["rol"] == "MESERO"
    assert "password" not in body and "password_hash" not in body


def test_cp_01_1_2_campos_obligatorios(client, admin_headers):
    """CP-01.1-2 | RF-01.1 | Sin datos → 422 con la lista de campos faltantes."""
    r = client.post("/api/usuarios", headers=admin_headers, json={})
    assert r.status_code == 422
    assert set(r.get_json()["faltantes"]) == {"nombre", "apellido", "email", "password", "rol_id"}


def test_cp_01_1_3_clave_corta(client, admin_headers, nuevo_mesero):
    """CP-01.1-3 | RF-01.1 | Contraseña de 7 caracteres → 422 (límite: 8)."""
    nuevo_mesero["password"] = "1234567"
    r = client.post("/api/usuarios", headers=admin_headers, json=nuevo_mesero)
    assert r.status_code == 422


def test_cp_01_1_4_correo_duplicado(client, admin_headers, nuevo_mesero):
    """CP-01.1-4 | RF-01.1 | Registrar un correo que ya existe → 409."""
    client.post("/api/usuarios", headers=admin_headers, json=nuevo_mesero)
    nuevo_mesero["email"] = "ana@stockpot.test"
    r = client.post("/api/usuarios", headers=admin_headers, json=nuevo_mesero)
    assert r.status_code == 409


def test_cp_01_1_5_rol_inexistente(client, admin_headers, nuevo_mesero):
    """CP-01.1-5 | RF-01.1 | Asignar un rol que no existe → 422."""
    nuevo_mesero["rol_id"] = 999
    r = client.post("/api/usuarios", headers=admin_headers, json=nuevo_mesero)
    assert r.status_code == 422


def test_cp_01_1_6_usuario_creado_puede_iniciar_sesion(client, admin_headers, nuevo_mesero):
    """CP-01.1-6 | RF-01.1, RF-01.4 | El usuario registrado puede iniciar sesión."""
    client.post("/api/usuarios", headers=admin_headers, json=nuevo_mesero)
    r = client.post("/api/auth/login", json={"email": "ana@stockpot.test", "password": "Clave12345"})
    assert r.status_code == 200


# ------------------------------------------------------- RF-01.2 Consultar


def test_cp_01_2_1_listar_usuarios(client, admin_headers, nuevo_mesero):
    """CP-01.2-1 | RF-01.2 | El admin ve todos los usuarios."""
    client.post("/api/usuarios", headers=admin_headers, json=nuevo_mesero)
    r = client.get("/api/usuarios", headers=admin_headers)
    assert r.status_code == 200
    assert {u["email"] for u in r.get_json()} == {"admin@stockpot.test", "ana@stockpot.test"}


def test_cp_01_2_2_buscar_usuarios(client, admin_headers, nuevo_mesero):
    """CP-01.2-2 | RF-01.2 | La búsqueda ?q= filtra por nombre, apellido o correo."""
    client.post("/api/usuarios", headers=admin_headers, json=nuevo_mesero)
    assert len(client.get("/api/usuarios?q=pérez", headers=admin_headers).get_json()) == 1
    assert len(client.get("/api/usuarios?q=zzz", headers=admin_headers).get_json()) == 0


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_4_mesero_no_lista_usuarios(client, mesero_headers):
    """CP-SEG-4 | Seguridad | Un MESERO (sin usuarios.ver) no puede listar usuarios → 403."""
    assert client.get("/api/usuarios", headers=mesero_headers).status_code == 403


def test_cp_seg_5_mesero_no_crea_usuarios(client, mesero_headers, nuevo_mesero):
    """CP-SEG-5 | Seguridad | Un MESERO (sin usuarios.gestionar) no puede crear usuarios → 403."""
    r = client.post("/api/usuarios", headers=mesero_headers, json=nuevo_mesero)
    assert r.status_code == 403
