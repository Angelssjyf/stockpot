"""Casos de prueba: sesiones seguras (tercer corte).

Bloqueo de pantalla, cierre por inactividad, PIN para cobrar, anular y sacar inventario, y
permisos y estado del usuario leídos de la base de datos en cada petición.

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import Insumo, Rol, Sesion, Usuario

from .conftest import CLAVE, crear_usuario, iniciar_sesion
from .test_pagos import cajero_headers, carta, domicilio  # noqa: F401  (fixtures)

PIN = "4826"


@pytest.fixture()
def con_pin(app):
    """Activa el PIN (las pruebas de los demás módulos lo tienen apagado)."""
    app.config["EXIGIR_PIN"] = True
    yield
    app.config["EXIGIR_PIN"] = False


def _sesion(email):
    usuario = Usuario.query.filter_by(email=email).one()
    return Sesion.query.filter_by(usuario_id=usuario.id).order_by(Sesion.id.desc()).first()


def _crear_pin(client, headers, pin=PIN, password=CLAVE):
    return client.put("/api/auth/pin", headers=headers, json={"password": password, "pin": pin})


# ------------------------------------------------------- Sesiones en la base de datos


def test_cp_seg_30_cerrar_sesion(client, admin_headers):
    """CP-SEG-30 | RF-01.4 | Al cerrar sesión el token deja de servir aunque no haya vencido."""
    assert client.get("/api/usuarios", headers=admin_headers).status_code == 200
    assert client.post("/api/auth/logout", headers=admin_headers).status_code == 200
    r = client.get("/api/usuarios", headers=admin_headers)
    assert r.status_code == 401 and r.get_json()["codigo"] == "SESION_CERRADA"
    assert _sesion("admin@stockpot.test").motivo_cierre == "SALIDA"


def test_cp_seg_31_inactividad(client, admin_headers):
    """CP-SEG-31 | RF-01.4 | Con 30 minutos sin uso el servidor cierra la sesión; las consultas automáticas
    (X-Segundo-Plano) no cuentan como uso."""
    sesion = _sesion("admin@stockpot.test")
    sesion.ultima_actividad = datetime.now() - timedelta(minutes=10)
    db.session.commit()
    client.get("/api/usuarios", headers={**admin_headers, "X-Segundo-Plano": "1"})
    assert datetime.now() - _sesion("admin@stockpot.test").ultima_actividad >= timedelta(minutes=10)
    client.get("/api/usuarios", headers=admin_headers)  # uso real: se renueva
    assert datetime.now() - _sesion("admin@stockpot.test").ultima_actividad < timedelta(minutes=1)

    _sesion("admin@stockpot.test").ultima_actividad = datetime.now() - timedelta(minutes=31)
    db.session.commit()
    r = client.get("/api/usuarios", headers=admin_headers)
    assert r.status_code == 401 and r.get_json()["codigo"] == "INACTIVIDAD"


def test_cp_seg_32_bloquear_y_desbloquear(client, admin_headers):
    """CP-SEG-32 | RF-01.4 | Bloqueada, nada responde (423) salvo /auth/me; se vuelve con el PIN o, si no
    tiene PIN, con la contraseña."""
    assert client.post("/api/auth/bloquear", headers=admin_headers).status_code == 200
    r = client.get("/api/usuarios", headers=admin_headers)
    assert r.status_code == 423 and r.get_json()["codigo"] == "SESION_BLOQUEADA"
    yo = client.get("/api/auth/me", headers=admin_headers).get_json()
    assert yo["bloqueada"] is True and yo["tiene_pin"] is False and yo["bloqueo_minutos"] == 10

    r = client.post("/api/auth/desbloquear", headers=admin_headers, json={"pin": "1234"})
    assert r.status_code == 403  # no tiene PIN todavía
    r = client.post("/api/auth/desbloquear", headers=admin_headers, json={"password": CLAVE})
    assert r.status_code == 200 and client.get("/api/usuarios", headers=admin_headers).status_code == 200

    _crear_pin(client, admin_headers)
    client.post("/api/auth/bloquear", headers=admin_headers)
    assert client.post("/api/auth/desbloquear", headers=admin_headers, json={}).status_code == 422
    r = client.post("/api/auth/desbloquear", headers=admin_headers, json={"pin": PIN})
    assert r.status_code == 200 and r.get_json()["bloqueada"] is False


def test_cp_seg_33_intentos_fallidos(client, admin_headers):
    """CP-SEG-33 | RF-01.4 | Cada PIN equivocado avisa cuántos intentos quedan; al quinto se cierra la sesión."""
    _crear_pin(client, admin_headers)
    client.post("/api/auth/bloquear", headers=admin_headers)
    for quedan in (4, 3, 2, 1):
        r = client.post("/api/auth/desbloquear", headers=admin_headers, json={"pin": "9999"})
        assert r.status_code == 403 and f"te quedan {quedan} intento" in r.get_json()["error"]
    r = client.post("/api/auth/desbloquear", headers=admin_headers, json={"pin": "9999"})
    assert r.status_code == 401 and r.get_json()["codigo"] == "SESION_CERRADA"
    assert _sesion("admin@stockpot.test").motivo_cierre == "PIN"
    assert client.get("/api/auth/me", headers=admin_headers).status_code == 401


@pytest.mark.parametrize("pin, password, codigo, mensaje", [
    ("4826", "otra-clave", 403, "Contraseña incorrecta"),
    ("12a4", CLAVE, 422, "de 4 a 6 números"),
    ("123", CLAVE, 422, "de 4 a 6 números"),
    ("1234567", CLAVE, 422, "de 4 a 6 números"),
    ("7777", CLAVE, 422, "fácil de adivinar"),
    ("3456", CLAVE, 422, "fácil de adivinar"),
    ("6543", CLAVE, 422, "fácil de adivinar"),
])
def test_cp_seg_34_crear_pin_invalido(client, admin_headers, pin, password, codigo, mensaje):
    """CP-SEG-34 | RF-01.4 | El PIN se crea con la contraseña; de 4 a 6 números y no trivial (valores límite)."""
    r = _crear_pin(client, admin_headers, pin=pin, password=password)
    assert r.status_code == codigo and mensaje in r.get_json()["error"]


def test_cp_seg_34b_crear_pin(client, admin_headers):
    """CP-SEG-34 | RF-01.4 | Un PIN válido de 4 y de 6 números se guarda cifrado."""
    assert _crear_pin(client, admin_headers, pin="4826").status_code == 200
    assert _crear_pin(client, admin_headers, pin="482619").status_code == 200
    usuario = Usuario.query.filter_by(email="admin@stockpot.test").one()
    assert usuario.pin_hash and "482619" not in usuario.pin_hash and usuario.check_pin("482619")
    assert client.get("/api/auth/me", headers=admin_headers).get_json()["tiene_pin"] is True


# ------------------------------------------------------- PIN en las operaciones sensibles


def test_cp_seg_35_cobrar_con_pin(client, con_pin, cajero_headers, domicilio):
    """CP-SEG-35 | RF-09.1 | Cobrar pide el PIN: sin PIN creado, sin escribirlo o equivocado no se cobra."""
    pagar = lambda **extra: client.post(f"/api/ordenes/{domicilio['orden']['id']}/pagos", headers=cajero_headers,  # noqa: E731
                                        json={"metodo": "EFECTIVO", "monto": 10000, **extra})
    r = pagar()
    assert r.status_code == 428 and r.get_json()["codigo"] == "PIN_NO_CONFIGURADO"
    _crear_pin(client, cajero_headers)
    assert pagar().get_json()["codigo"] == "PIN_REQUERIDO"
    r = pagar(pin="1111")
    assert r.status_code == 403 and r.get_json()["codigo"] == "PIN_INCORRECTO"
    r = pagar(pin=PIN)
    assert r.status_code == 201, r.get_json()

    pago = r.get_json()["pago"]["id"]
    r = client.patch(f"/api/pagos/{pago}/anular", headers=cajero_headers, json={})
    assert r.status_code == 428  # anular también lo pide
    assert client.patch(f"/api/pagos/{pago}/anular", headers=cajero_headers, json={"pin": PIN}).status_code == 200


def test_cp_seg_36_salida_con_pin(client, con_pin, admin_headers):
    """CP-SEG-36 | RF-03.5 | Sacar inventario pide el PIN; registrar una entrada no."""
    insumo = Insumo(codigo="INS-001", nombre="Arroz", unidad_medida="KG", stock_actual=10, costo_unitario=4000)
    db.session.add(insumo)
    db.session.commit()
    mover = lambda tipo, motivo, **extra: client.post(f"/api/insumos/{insumo.id}/movimientos",  # noqa: E731
                                                      headers=admin_headers, json={"tipo": tipo, "motivo": motivo,
                                                                                   "cantidad": 1, **extra})
    assert mover("ENTRADA", "COMPRA").status_code == 201
    assert mover("SALIDA", "MERMA").status_code == 428
    _crear_pin(client, admin_headers)
    assert mover("SALIDA", "MERMA", pin=PIN).status_code == 201


# ------------------------------------------------------- Usuario y permisos desde la base de datos


def test_cp_seg_37_permisos_al_instante(client, admin_headers, roles):
    """CP-SEG-37 | RF-01.5, RF-01.6 | Si el administrador le quita un permiso al rol, aplica en la siguiente
    petición (ya no hay que esperar a que el usuario vuelva a iniciar sesión)."""
    crear_usuario("BODEGUERO", "bodega@stockpot.test")
    bodega = iniciar_sesion(client, "bodega@stockpot.test")
    assert client.get("/api/proveedores", headers=bodega).status_code == 200
    rol = db.session.get(Rol, roles["BODEGUERO"])
    client.put(f"/api/roles/{rol.id}/permisos", headers=admin_headers,
               json={"permisos": ["inventario.ver", "inventario.gestionar"]})
    assert client.get("/api/proveedores", headers=bodega).status_code == 403
    assert "proveedores.ver" not in client.get("/api/auth/me", headers=bodega).get_json()["permisos"]


def test_cp_seg_38_usuario_desactivado_o_nueva_clave(client, admin_headers):
    """CP-SEG-38 | RF-01.3 | Al desactivar a un usuario o cambiarle la contraseña, sus sesiones abiertas se
    cierran; el administrador puede quitarle el PIN si lo olvidó."""
    mesero = crear_usuario("MESERO", "mesero2@stockpot.test")
    sesion_mesero = iniciar_sesion(client, "mesero2@stockpot.test")
    _crear_pin(client, sesion_mesero)
    r = client.put(f"/api/usuarios/{mesero.id}", headers=admin_headers, json={"quitar_pin": True})
    assert r.get_json()["tiene_pin"] is False

    client.put(f"/api/usuarios/{mesero.id}", headers=admin_headers, json={"password": "NuevaClave2026"})
    assert client.get("/api/auth/me", headers=sesion_mesero).status_code == 401

    otra = iniciar_sesion(client, "mesero2@stockpot.test", "NuevaClave2026")
    client.put(f"/api/usuarios/{mesero.id}", headers=admin_headers, json={"activo": False})
    assert client.get("/api/pedidos", headers=otra).status_code == 401
