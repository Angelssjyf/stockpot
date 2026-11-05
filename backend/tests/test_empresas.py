"""Casos de prueba: varios restaurantes (empresas) y súper administrador (tercer corte).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import re

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Empresa, Rol, Usuario
from app.services.empresas import PLANTILLA_ROLES

from .conftest import CLAVE, SEED_SQL, iniciar_sesion

NUEVA = {"nombre": "La Fonda de Mateo", "nit": "901234567-8", "telefono": "3001234567",
         "direccion": "Calle 10 # 5-20",
         "admin": {"nombre": "Mateo", "apellido": "Puentes", "email": "admin@fonda.test", "password": CLAVE}}


@pytest.fixture()
def super_headers(client):
    """Súper administrador: sin empresa y con un solo permiso, empresas.gestionar."""
    rol = Rol.query.execution_options(todas_las_empresas=True).filter_by(nombre="SUPERADMIN").one()
    usuario = Usuario(nombre="Súper", apellido="Admin", email="super@stockpot.test", rol=rol)
    usuario.set_password(CLAVE)
    db.session.add(usuario)
    db.session.flush()
    usuario.empresa_id = None  # al crearlo quedó en la empresa de la prueba; el súper administrador no tiene
    db.session.commit()
    return iniciar_sesion(client, "super@stockpot.test")


@pytest.fixture()
def fonda(client, super_headers):
    """Segundo restaurante creado por el súper administrador, con la sesión de su administrador."""
    r = client.post("/api/empresas", headers=super_headers, json=NUEVA)
    assert r.status_code == 201, r.get_json()
    return {"id": r.get_json()["id"], "headers": iniciar_sesion(client, "admin@fonda.test")}


def _insumo(client, headers, nombre):
    datos = {"codigo": "INS-001", "nombre": nombre, "unidad_medida": "KG", "stock_minimo": 1, "costo_unitario": 1000}
    r = client.post("/api/insumos", headers=headers, json=datos)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


# ------------------------------------------------------- Súper administrador


def test_cp_emp_1_crear_restaurante(client, super_headers):
    """CP-EMP-1 | Empresas | El súper administrador crea un restaurante con sus 6 roles y su administrador,
    que entra con su propio restaurante."""
    r = client.post("/api/empresas", headers=super_headers, json=NUEVA)
    assert r.status_code == 201, r.get_json()
    empresa = r.get_json()
    assert (empresa["nombre"], empresa["activa"], empresa["usuarios"]) == ("La Fonda de Mateo", True, 1)
    assert empresa["administradores"] == [{"nombre": "Mateo Puentes", "email": "admin@fonda.test", "activo": True}]

    login = client.post("/api/auth/login", json={"email": "admin@fonda.test", "password": CLAVE}).get_json()
    assert login["usuario"]["empresa"] == "La Fonda de Mateo" and "empresas.gestionar" not in login["usuario"]["permisos"]
    roles = client.get("/api/roles", headers={"Authorization": f"Bearer {login['access_token']}"}).get_json()
    assert sorted(r["nombre"] for r in roles) == sorted(PLANTILLA_ROLES)


def test_cp_emp_2_plantilla_igual_al_seed(app):
    """CP-EMP-2 | Empresas | Los roles de un restaurante nuevo son los mismos del seed (02_seed.sql)."""
    roles = Rol.query.filter_by(empresa_id=1).all()
    for rol in roles:
        descripcion, codigos = PLANTILLA_ROLES[rol.nombre]
        assert rol.descripcion == descripcion
        if codigos is not None:
            assert sorted(p.codigo for p in rol.permisos) == sorted(codigos), rol.nombre
    assert len(roles) == len(PLANTILLA_ROLES)
    assert "('empresas.gestionar'" in SEED_SQL.read_text(encoding="utf-8")


@pytest.mark.parametrize("cambios, codigo, mensaje", [
    ({"nombre": ""}, 422, "nombre del restaurante es obligatorio"),
    ({"nit": "900000001-1"}, 409, "Ya existe un restaurante con ese NIT"),
    ({"admin": {"nombre": "Ana"}}, 422, "Faltan datos del administrador"),
    ({"admin": {**NUEVA["admin"], "password": "corta"}}, 422, "al menos 8 caracteres"),
    ({"admin": {**NUEVA["admin"], "email": "admin@stockpot.test"}}, 409, "Ya existe un usuario con ese correo"),
])
def test_cp_emp_3_datos_invalidos(client, super_headers, admin_headers, cambios, codigo, mensaje):
    """CP-EMP-3 | Empresas | Nombre y NIT obligatorios, NIT y correo del administrador sin repetir en todo
    StockPot y contraseña de 8 caracteres o más."""
    r = client.post("/api/empresas", headers=super_headers, json={**NUEVA, **cambios})
    assert r.status_code == codigo and mensaje in r.get_json()["error"]


def test_cp_emp_4_modificar_y_listar(client, super_headers, fonda):
    """CP-EMP-4 | Empresas | El súper administrador ve los datos generales de cada restaurante y los modifica."""
    r = client.put(f"/api/empresas/{fonda['id']}", headers=super_headers, json={"telefono": "3109998877"})
    assert r.status_code == 200 and r.get_json()["telefono"] == "3109998877"
    r = client.put(f"/api/empresas/{fonda['id']}", headers=super_headers, json={"nit": "900000001-1"})
    assert r.status_code == 409
    assert client.put("/api/empresas/999", headers=super_headers, json={}).status_code == 404
    empresas = client.get("/api/empresas", headers=super_headers).get_json()
    assert [e["nombre"] for e in empresas] == ["La Fonda de Mateo", "StockPot Restaurante"]
    assert set(empresas[0]) >= {"nit", "telefono", "direccion", "activa", "usuarios", "administradores"}
    assert not {"ventas", "insumos", "total"} & set(empresas[0])  # nada del negocio


def test_cp_emp_5_desactivar_restaurante(client, super_headers, fonda):
    """CP-EMP-5 | Empresas | Desactivado, sus usuarios no entran y la sesión abierta deja de funcionar;
    al activarlo de nuevo vuelven a trabajar."""
    r = client.patch(f"/api/empresas/{fonda['id']}/estado", headers=super_headers, json={"activa": False})
    assert r.status_code == 200 and r.get_json()["activa"] is False
    r = client.post("/api/auth/login", json={"email": "admin@fonda.test", "password": CLAVE})
    assert r.status_code == 403 and "restaurante está desactivado" in r.get_json()["error"]
    assert client.get("/api/insumos", headers=fonda["headers"]).status_code == 403
    assert client.get("/api/auth/me", headers=fonda["headers"]).status_code == 403

    client.patch(f"/api/empresas/{fonda['id']}/estado", headers=super_headers, json={"activa": True})
    assert client.get("/api/insumos", headers=fonda["headers"]).status_code == 200
    r = client.patch(f"/api/empresas/{fonda['id']}/estado", headers=super_headers, json={"activa": "no"})
    assert r.status_code == 422


# ------------------------------------------------------- Aislamiento entre restaurantes


def test_cp_emp_6_cada_restaurante_ve_lo_suyo(client, admin_headers, fonda):
    """CP-EMP-6 | Empresas | Dos restaurantes pueden usar el mismo código; cada uno ve solo sus insumos,
    y el de otro restaurante no existe para él (404 al verlo o modificarlo)."""
    propio = _insumo(client, admin_headers, "Arroz de StockPot")
    ajeno = _insumo(client, fonda["headers"], "Arroz de la Fonda")  # mismo código INS-001: se permite
    assert [i["nombre"] for i in client.get("/api/insumos", headers=admin_headers).get_json()] == ["Arroz de StockPot"]
    assert [i["nombre"] for i in client.get("/api/insumos", headers=fonda["headers"]).get_json()] == ["Arroz de la Fonda"]
    assert client.get(f"/api/insumos/{ajeno}", headers=admin_headers).status_code == 404
    assert client.put(f"/api/insumos/{propio}", headers=fonda["headers"], json={"nombre": "Robado"}).status_code == 404
    r = client.post(f"/api/insumos/{propio}/movimientos", headers=fonda["headers"],
                    json={"tipo": "ENTRADA", "motivo": "COMPRA", "cantidad": 5})
    assert r.status_code == 404


def test_cp_emp_7_usuarios_y_roles_propios(client, admin_headers, roles, fonda):
    """CP-EMP-7 | Empresas | El administrador solo ve los usuarios y roles de su restaurante y no puede
    darle a un usuario un rol de otro restaurante."""
    usuarios = client.get("/api/usuarios", headers=fonda["headers"]).get_json()
    assert [u["email"] for u in usuarios] == ["admin@fonda.test"]
    nombres = [r["nombre"] for r in client.get("/api/roles", headers=fonda["headers"]).get_json()]
    assert "SUPERADMIN" not in nombres and len(nombres) == len(PLANTILLA_ROLES)
    r = client.post("/api/usuarios", headers=fonda["headers"],
                    json={"nombre": "Ana", "apellido": "Ruiz", "email": "ana@fonda.test", "password": CLAVE,
                          "rol_id": roles["MESERO"]})  # rol del restaurante 1
    assert r.status_code == 422


def test_cp_emp_8_reportes_separados(client, admin_headers, fonda):
    """CP-EMP-8 | Empresas | Los reportes y las alertas de un restaurante no cuentan lo del otro."""
    _insumo(client, admin_headers, "Arroz de StockPot")
    inventario = client.get("/api/reportes/inventario", headers=fonda["headers"]).get_json()
    assert inventario["resumen"]["insumos"] == 0


# ------------------------------------------------------- Seguridad


def test_cp_seg_25_superadmin_no_ve_restaurantes(client, super_headers, admin_headers):
    """CP-SEG-25 | Empresas | El súper administrador no ve inventario, ventas ni usuarios de los restaurantes,
    y un administrador de restaurante no gestiona empresas."""
    for ruta in ("/api/insumos", "/api/ventas", "/api/usuarios", "/api/reportes/ventas", "/api/pagos"):
        assert client.get(ruta, headers=super_headers).status_code == 403, ruta
    assert client.get("/api/empresas", headers=admin_headers).status_code == 403
    assert client.get("/api/auth/me", headers=super_headers).get_json()["rol"] == "SUPERADMIN"


def test_cp_seg_26_permiso_de_empresas_no_se_asigna(client, admin_headers, roles):
    """CP-SEG-26 | Empresas | El permiso empresas.gestionar no aparece ni se le puede dar a un rol del restaurante."""
    codigos = [p["codigo"] for p in client.get("/api/permisos", headers=admin_headers).get_json()]
    assert "empresas.gestionar" not in codigos
    r = client.put(f"/api/roles/{roles['MESERO']}/permisos", headers=admin_headers,
                   json={"permisos": ["pedidos.ver", "empresas.gestionar"]})
    assert r.status_code == 422 and r.get_json()["desconocidos"] == ["empresas.gestionar"]


def test_cp_seg_27_token_anterior(client, app, admin_headers):
    """CP-SEG-27 | Empresas | Un token de antes de las empresas (sin restaurante) ya no sirve: pide iniciar sesión."""
    usuario = Usuario.query.filter_by(email="admin@stockpot.test").one()
    viejo = create_access_token(identity=str(usuario.id), additional_claims={"rol": "ADMINISTRADOR",
                                                                             "permisos": ["inventario.ver"]})
    r = client.get("/api/insumos", headers={"Authorization": f"Bearer {viejo}"})
    assert r.status_code == 401 and "inicia sesión de nuevo" in r.get_json()["error"]


def test_cp_emp_9_esquema_con_empresa(app):
    """CP-EMP-9 | Empresas | El esquema de MySQL tiene la tabla empresas y empresa_id en las tablas del restaurante."""
    esquema = (SEED_SQL.parent / "01_schema.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE empresas" in esquema
    for tabla in ("usuarios", "roles", "insumos", "productos", "proveedores", "ordenes", "ventas", "pagos", "mesas"):
        bloque = re.search(rf"CREATE TABLE {tabla} \((.*?)\n\);", esquema, re.S).group(1)
        assert "empresa_id" in bloque, tabla
    assert db.session.get(Empresa, 1).nombre == "StockPot Restaurante"
