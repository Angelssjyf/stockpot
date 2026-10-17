"""Casos de prueba: inicio de sesión (RF-01.4) y control de acceso (RNF de seguridad).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

from .conftest import CLAVE, crear_usuario


def test_cp_01_4_1_login_correcto(client):
    """CP-01.4-1 | RF-01.4 | Credenciales correctas: token, datos del usuario y permisos."""
    crear_usuario("BODEGUERO", "bodega@stockpot.test")
    r = client.post("/api/auth/login", json={"email": "bodega@stockpot.test", "password": CLAVE})

    assert r.status_code == 200
    body = r.get_json()
    assert body["access_token"]
    assert body["usuario"]["rol"] == "BODEGUERO"
    assert "proveedores.gestionar" in body["usuario"]["permisos"]
    assert "password_hash" not in body["usuario"]


def test_cp_01_4_2_clave_incorrecta(client):
    """CP-01.4-2 | RF-01.4 | Contraseña incorrecta → 401."""
    crear_usuario("MESERO", "mesero@stockpot.test")
    r = client.post("/api/auth/login", json={"email": "mesero@stockpot.test", "password": "mala"})
    assert r.status_code == 401


def test_cp_01_4_3_correo_inexistente_mismo_mensaje(client):
    """CP-01.4-3 | RF-01.4 | Correo inexistente → 401 con el mismo mensaje que clave incorrecta."""
    crear_usuario("MESERO", "mesero@stockpot.test")
    clave_mala = client.post("/api/auth/login", json={"email": "mesero@stockpot.test", "password": "x"})
    no_existe = client.post("/api/auth/login", json={"email": "nadie@stockpot.test", "password": "x"})

    assert no_existe.status_code == 401
    assert no_existe.get_json() == clave_mala.get_json()


def test_cp_01_4_4_campos_vacios(client):
    """CP-01.4-4 | RF-01.4 | Login sin correo ni contraseña → 400."""
    assert client.post("/api/auth/login", json={}).status_code == 400


def test_cp_01_4_5_correo_sin_importar_mayusculas(client):
    """CP-01.4-5 | RF-01.4 | El correo se acepta escrito con mayúsculas."""
    crear_usuario("CAJERO", "caja@stockpot.test")
    r = client.post("/api/auth/login", json={"email": "Caja@StockPot.TEST", "password": CLAVE})
    assert r.status_code == 200


def test_cp_01_4_6_usuario_desactivado(client):
    """CP-01.4-6 | RF-01.4 | Un usuario desactivado no puede iniciar sesión → 403."""
    usuario = crear_usuario("MESERO", "inactivo@stockpot.test")
    usuario.activo = False
    from app.extensions import db

    db.session.commit()
    r = client.post("/api/auth/login", json={"email": "inactivo@stockpot.test", "password": CLAVE})
    assert r.status_code == 403


def test_cp_01_4_7_me_con_token(client, admin_headers):
    """CP-01.4-7 | RF-01.4 | /me con token devuelve el usuario dueño del token."""
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.get_json()["email"] == "admin@stockpot.test"
    assert len(r.get_json()["permisos"]) == 23


def test_cp_seg_1_sin_token(client):
    """CP-SEG-1 | Seguridad | Ruta protegida sin token → 401."""
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/usuarios").status_code == 401


def test_cp_seg_2_token_falso(client):
    """CP-SEG-2 | Seguridad | Token inventado o alterado → 401."""
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401


def test_cp_seg_3_contrasena_cifrada(app):
    """CP-SEG-3 | Seguridad | La contraseña se guarda cifrada, nunca en texto plano."""
    usuario = crear_usuario("MESERO", "cifrado@stockpot.test", password="MiClave123")
    assert usuario.password_hash != "MiClave123"
    assert usuario.password_hash.startswith("scrypt:")
    assert usuario.check_password("MiClave123")
    assert not usuario.check_password("otra")


def test_cp_seg_8_cors_permite_flutter_local(client):
    """CP-SEG-8 | Seguridad | La app Flutter web en localhost (cualquier puerto) puede llamar a la API."""
    r = client.options("/api/auth/login", headers={
        "Origin": "http://localhost:54321", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://localhost:54321"


def test_cp_seg_9_cors_bloquea_otros_sitios(client):
    """CP-SEG-9 | Seguridad | Una página de otro dominio no recibe permiso CORS."""
    r = client.options("/api/auth/login", headers={
        "Origin": "https://sitio-malicioso.com", "Access-Control-Request-Method": "POST"})
    assert "Access-Control-Allow-Origin" not in r.headers
