"""Casos de prueba: comandos de consola (flask crear-admin, flask crear-superadmin, flask respaldar).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import pytest
from flask import g

from app import respaldos
from app.extensions import db
from app.models import Rol, Usuario

from .conftest import CLAVE, crear_usuario, iniciar_sesion

CLAVE_SUPER = "ClaveDelSuper2026"


@pytest.fixture()
def consola(app):
    """Ejecuta un comando de flask como si se escribiera en la terminal: allí no hay sesión de
    ningún restaurante (las pruebas marcan el restaurante 1 en g, así que se quita mientras corre)."""
    runner = app.test_cli_runner()

    def ejecutar(*args):
        empresa = g.pop("empresa_id", None)
        try:
            return runner.invoke(args=list(args))
        finally:
            g.empresa_id = empresa
    return ejecutar


def _usuario(email):
    db.session.expire_all()
    return Usuario.query.execution_options(todas_las_empresas=True).filter_by(email=email).first()


def test_cp_cli_1_crear_admin(consola, client):
    """CP-CLI-1 | RF-01.1 | crear-admin crea el administrador del restaurante 1 y puede iniciar sesión."""
    r = consola("crear-admin", "--email", " Dueno@Fonda.test ", "--nombre", "Ana", "--apellido", "Ruiz",
                "--password", CLAVE)
    assert r.exit_code == 0 and "Administrador creado: dueno@fonda.test" in r.output
    usuario = _usuario("dueno@fonda.test")  # el correo se guarda sin espacios y en minúscula
    assert usuario.rol.nombre == "ADMINISTRADOR" and usuario.empresa_id == 1 and usuario.activo
    assert iniciar_sesion(client, "dueno@fonda.test")


@pytest.mark.parametrize("cambios, mensaje", [
    ({"--password": "corta"}, "al menos 8 caracteres"),
    ({"--empresa": "99"}, "No existe la empresa 99"),
])
def test_cp_cli_2_crear_admin_invalido(consola, cambios, mensaje):
    """CP-CLI-2 | RF-01.1 | Con una contraseña corta o un restaurante que no existe, no crea nada."""
    opciones = {"--email": "malo@fonda.test", "--nombre": "Ana", "--apellido": "Ruiz", "--password": CLAVE, **cambios}
    r = consola("crear-admin", *[x for par in opciones.items() for x in par])
    assert r.exit_code != 0 and mensaje in r.output
    assert _usuario("malo@fonda.test") is None


def test_cp_cli_3_restablecer_contrasena(consola, client):
    """CP-CLI-3 | RF-01.1 | Con un correo que ya existe, le cambia la contraseña y le conserva el PIN
    (es la misma persona con el mismo rol); también lo reactiva."""
    usuario = crear_usuario("ADMINISTRADOR", "olvido@stockpot.test")
    usuario.set_pin("4826")
    usuario.activo = False
    db.session.commit()
    r = consola("crear-admin", "--email", "olvido@stockpot.test", "--nombre", "Ana", "--apellido", "Ruiz",
                "--password", "OtraClave2026")
    assert r.exit_code == 0 and "Administrador actualizado" in r.output and "PIN" not in r.output
    usuario = _usuario("olvido@stockpot.test")
    assert usuario.activo and usuario.check_password("OtraClave2026") and usuario.check_pin("4826")
    assert iniciar_sesion(client, "olvido@stockpot.test", "OtraClave2026")


def test_cp_cli_4_crear_superadmin(consola, client):
    """CP-CLI-4 | Empresas | crear-superadmin crea el súper administrador sin restaurante (mínimo 12 caracteres)."""
    r = consola("crear-superadmin", "--email", "super@stockpot.test", "--nombre", "Súper", "--apellido", "Admin",
                "--password", "Corta12345")
    assert r.exit_code != 0 and "al menos 12 caracteres" in r.output and _usuario("super@stockpot.test") is None
    r = consola("crear-superadmin", "--email", "super@stockpot.test", "--nombre", "Súper", "--apellido", "Admin",
                "--password", CLAVE_SUPER)
    assert r.exit_code == 0 and "Súper administrador creado" in r.output
    usuario = _usuario("super@stockpot.test")
    assert usuario.rol.nombre == "SUPERADMIN" and usuario.empresa_id is None and usuario.pin_hash is None
    encabezados = iniciar_sesion(client, "super@stockpot.test", CLAVE_SUPER)
    assert client.get("/api/empresas", headers=encabezados).status_code == 200


def test_cp_cli_5_superadmin_no_hereda_pin(consola):
    """CP-CLI-5 | Seguridad | Si se usa el correo de un administrador con PIN para el súper
    administrador, el PIN viejo se quita: el nuevo dueño crea el suyo."""
    usuario = crear_usuario("ADMINISTRADOR", "reuso@stockpot.test")
    usuario.set_pin("4826")
    db.session.commit()
    r = consola("crear-superadmin", "--email", "reuso@stockpot.test", "--nombre", "Súper", "--apellido", "Admin",
                "--password", CLAVE_SUPER)
    assert r.exit_code == 0 and "se le quitó el PIN anterior" in r.output
    usuario = _usuario("reuso@stockpot.test")
    assert usuario.pin_hash is None and usuario.empresa_id is None
    assert usuario.rol_id == Rol.query.execution_options(todas_las_empresas=True).filter_by(nombre="SUPERADMIN").one().id


def test_cp_cli_6_respaldar(consola, monkeypatch, tmp_path):
    """CP-CLI-6 | Respaldos | flask respaldar avisa dónde quedó la copia, o por qué falló."""
    copia = tmp_path / "stockpot_auto_2026-11-18_220000.sql"
    copia.write_text("-- copia de prueba\n" * 100, encoding="utf-8")
    monkeypatch.setattr(respaldos, "respaldar", lambda: copia)
    r = consola("respaldar")
    assert r.exit_code == 0 and f"Respaldo listo: database/respaldos/{copia.name}" in r.output

    def falla():
        raise respaldos.RespaldoFallido("No se encontró mysqldump")
    monkeypatch.setattr(respaldos, "respaldar", falla)
    r = consola("respaldar")
    assert r.exit_code != 0 and "No se pudo hacer el respaldo: No se encontró mysqldump" in r.output
