"""Casos de prueba: asignar roles (RF-01.5) y gestionar permisos de acceso (RF-01.6).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest

from .conftest import CLAVE, crear_usuario, iniciar_sesion


@pytest.fixture()
def ana(app):
    """Usuaria MESERO para cambiarle el rol."""
    return crear_usuario("MESERO", "ana@stockpot.test")


# ------------------------------------------------------- RF-01.5 Asignar roles


def test_cp_01_5_1_asignar_rol(client, admin_headers, ana, roles):
    """CP-01.5-1 | RF-01.5 | Cambiar el rol de MESERO a CAJERO."""
    r = client.patch(f"/api/usuarios/{ana.id}/rol", headers=admin_headers,
                     json={"rol_id": roles["CAJERO"]})
    assert r.status_code == 200
    assert r.get_json()["rol"] == "CAJERO"


def test_cp_01_5_2_nuevo_rol_aplica_al_iniciar_sesion(client, admin_headers, ana, roles):
    """CP-01.5-2 | RF-01.5 | Tras el cambio, el nuevo login trae los permisos del nuevo rol."""
    client.patch(f"/api/usuarios/{ana.id}/rol", headers=admin_headers,
                 json={"rol_id": roles["BODEGUERO"]})
    r = client.post("/api/auth/login", json={"email": "ana@stockpot.test", "password": CLAVE})
    permisos = r.get_json()["usuario"]["permisos"]
    assert "proveedores.gestionar" in permisos
    assert "pedidos.gestionar" not in permisos


def test_cp_01_5_3_rol_inexistente(client, admin_headers, ana):
    """CP-01.5-3 | RF-01.5 | Asignar un rol que no existe → 422."""
    r = client.patch(f"/api/usuarios/{ana.id}/rol", headers=admin_headers, json={"rol_id": 999})
    assert r.status_code == 422


def test_cp_01_5_4_no_quitar_rol_al_ultimo_admin(client, admin_headers, roles):
    """CP-01.5-4 | RF-01.5 | Quitarle el rol al único administrador activo → 409."""
    yo = client.get("/api/auth/me", headers=admin_headers).get_json()
    r = client.patch(f"/api/usuarios/{yo['id']}/rol", headers=admin_headers,
                     json={"rol_id": roles["MESERO"]})
    assert r.status_code == 409


def test_cp_01_5_5_con_dos_admins_si_se_puede(client, admin_headers, roles):
    """CP-01.5-5 | RF-01.5 | Si hay otro administrador activo, sí se puede cambiar el rol."""
    otro = crear_usuario("ADMINISTRADOR", "admin2@stockpot.test")
    r = client.patch(f"/api/usuarios/{otro.id}/rol", headers=admin_headers,
                     json={"rol_id": roles["CAJERO"]})
    assert r.status_code == 200


def test_cp_01_5_6_usuario_inexistente(client, admin_headers, roles):
    """CP-01.5-6 | RF-01.5 | Cambiar el rol de un usuario que no existe → 404."""
    r = client.patch("/api/usuarios/999/rol", headers=admin_headers, json={"rol_id": roles["CAJERO"]})
    assert r.status_code == 404


# ------------------------------------------- RF-01.6 Gestionar permisos de acceso


def test_cp_01_6_1_listar_roles_con_permisos(client, admin_headers):
    """CP-01.6-1 | RF-01.6 | Listar los 6 roles con sus permisos."""
    r = client.get("/api/roles", headers=admin_headers)
    assert r.status_code == 200
    roles = {rol["nombre"]: rol["permisos"] for rol in r.get_json()}
    assert len(roles) == 6
    assert len(roles["ADMINISTRADOR"]) == 26
    assert roles["DOMICILIARIO"] == ["domicilios.ver", "incidencias.reportar"]


def test_cp_01_6_2_listar_permisos(client, admin_headers):
    """CP-01.6-2 | RF-01.6 | Listar los 26 permisos disponibles (23 + 3 de incidencias, RF-12)."""
    r = client.get("/api/permisos", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.get_json()) == 26


def test_cp_01_6_3_cambiar_permisos_de_rol(client, admin_headers, roles):
    """CP-01.6-3 | RF-01.6 | Reemplazar los permisos del MESERO."""
    r = client.put(f"/api/roles/{roles['MESERO']}/permisos", headers=admin_headers,
                   json={"permisos": ["pedidos.ver", "reservas.ver"]})
    assert r.status_code == 200
    assert r.get_json()["permisos"] == ["pedidos.ver", "reservas.ver"]


def test_cp_01_6_4_permisos_nuevos_aplican_al_iniciar_sesion(client, admin_headers, ana, roles):
    """CP-01.6-4 | RF-01.6 | Un permiso agregado al rol se puede usar tras un nuevo login."""
    mesero = iniciar_sesion(client, "ana@stockpot.test")
    assert client.get("/api/usuarios", headers=mesero).status_code == 403

    client.put(f"/api/roles/{roles['MESERO']}/permisos", headers=admin_headers,
               json={"permisos": ["pedidos.ver", "usuarios.ver"]})

    mesero = iniciar_sesion(client, "ana@stockpot.test")
    assert client.get("/api/usuarios", headers=mesero).status_code == 200


def test_cp_01_6_5_permiso_inexistente(client, admin_headers, roles):
    """CP-01.6-5 | RF-01.6 | Códigos de permiso que no existen → 422 y se indican cuáles."""
    r = client.put(f"/api/roles/{roles['MESERO']}/permisos", headers=admin_headers,
                   json={"permisos": ["pedidos.ver", "volar.ver"]})
    assert r.status_code == 422
    assert r.get_json()["desconocidos"] == ["volar.ver"]


def test_cp_01_6_6_no_modificar_admin(client, admin_headers, roles):
    """CP-01.6-6 | RF-01.6 | Los permisos del ADMINISTRADOR no se pueden modificar → 409."""
    r = client.put(f"/api/roles/{roles['ADMINISTRADOR']}/permisos", headers=admin_headers,
                   json={"permisos": []})
    assert r.status_code == 409


def test_cp_01_6_7_formato_invalido(client, admin_headers, roles):
    """CP-01.6-7 | RF-01.6 | 'permisos' que no es una lista → 422."""
    r = client.put(f"/api/roles/{roles['MESERO']}/permisos", headers=admin_headers,
                   json={"permisos": "pedidos.ver"})
    assert r.status_code == 422


# ------------------------------------------------------- Permisos por rol


def test_cp_seg_7_mesero_no_gestiona_roles(client, mesero_headers, ana, roles):
    """CP-SEG-7 | Seguridad | Un MESERO no puede asignar roles ni cambiar permisos → 403."""
    r1 = client.patch(f"/api/usuarios/{ana.id}/rol", headers=mesero_headers,
                      json={"rol_id": roles["ADMINISTRADOR"]})
    r2 = client.put(f"/api/roles/{roles['MESERO']}/permisos", headers=mesero_headers,
                    json={"permisos": ["usuarios.gestionar"]})
    assert r1.status_code == 403
    assert r2.status_code == 403
