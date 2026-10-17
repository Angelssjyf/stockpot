"""Piezas compartidas por todas las pruebas (fixtures de pytest).

Cada prueba recibe una base de datos nueva en memoria con:
- las tablas creadas a partir de los modelos, y
- los roles y permisos cargados desde el mismo database/02_seed.sql que usa MySQL.
"""

from pathlib import Path

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Rol, Usuario

SEED_SQL = Path(__file__).resolve().parents[2] / "database" / "02_seed.sql"
CLAVE = "ClaveDePrueba123"


def _cargar_seed():
    """Ejecuta 02_seed.sql en SQLite (se quita la línea USE, que es solo de MySQL)."""
    sql = "\n".join(
        linea
        for linea in SEED_SQL.read_text(encoding="utf-8").splitlines()
        if not linea.strip().upper().startswith("USE ")
    )
    conexion = db.engine.raw_connection()
    try:
        conexion.executescript(sql)
        conexion.commit()
    finally:
        conexion.close()


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        _cargar_seed()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Cliente que hace peticiones HTTP a la API sin levantar el servidor."""
    return app.test_client()


def crear_usuario(rol_nombre, email, password=CLAVE):
    """Crea un usuario directamente en la base de pruebas."""
    rol = Rol.query.filter_by(nombre=rol_nombre).one()
    usuario = Usuario(nombre="Prueba", apellido=rol_nombre.title(), email=email, rol=rol)
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def iniciar_sesion(client, email, password=CLAVE):
    """Hace login y devuelve el encabezado Authorization listo para usar."""
    respuesta = client.post("/api/auth/login", json={"email": email, "password": password})
    assert respuesta.status_code == 200, respuesta.get_json()
    return {"Authorization": f"Bearer {respuesta.get_json()['access_token']}"}


@pytest.fixture()
def admin_headers(client):
    crear_usuario("ADMINISTRADOR", "admin@stockpot.test")
    return iniciar_sesion(client, "admin@stockpot.test")


@pytest.fixture()
def mesero_headers(client):
    crear_usuario("MESERO", "mesero@stockpot.test")
    return iniciar_sesion(client, "mesero@stockpot.test")


@pytest.fixture()
def roles(app):
    """Diccionario nombre del rol -> id, por ejemplo roles['MESERO']."""
    return {r.nombre: r.id for r in Rol.query.all()}
