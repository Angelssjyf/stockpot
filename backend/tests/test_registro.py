"""Casos de prueba: registro de eventos (logs) y respuesta ante errores inesperados.

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import logging

import pytest

from app import create_app
from app.config import TestConfig

from .conftest import CLAVE, crear_usuario


@pytest.fixture()
def app_con_falla(app):
    """Una ruta de la API que falla sin control (simula un error de programación)."""
    def ruta_que_falla():
        raise RuntimeError("detalle técnico interno")

    app.add_url_rule("/api/prueba-falla", view_func=ruta_que_falla)
    app.add_url_rule("/prueba-falla", view_func=ruta_que_falla, endpoint="pagina_que_falla")
    return app


def test_cp_log_1_error_inesperado_en_la_api(app_con_falla, client, caplog):
    """CP-LOG-1 | RNF-08 | Un error inesperado responde JSON con un código y queda en el
    registro con el detalle técnico; el usuario no ve el detalle."""
    with caplog.at_level(logging.ERROR):
        r = client.get("/api/prueba-falla")

    assert r.status_code == 500
    cuerpo = r.get_json()
    assert cuerpo["codigo"] in cuerpo["error"] and "detalle técnico" not in cuerpo["error"]
    registro = next(rec for rec in caplog.records if rec.levelno == logging.ERROR)
    assert cuerpo["codigo"] in registro.getMessage() and "/api/prueba-falla" in registro.getMessage()
    assert registro.exc_info and "detalle técnico interno" in str(registro.exc_info[1])


def test_cp_log_2_error_en_pagina(app_con_falla, client):
    """CP-LOG-2 | RNF-08 | Fuera de la API el error se muestra como página con su código."""
    r = client.get("/prueba-falla")
    assert r.status_code == 500 and b"error inesperado" in r.data


def test_cp_log_3_eventos_de_seguridad_sin_claves(client, caplog):
    """CP-LOG-3 | RNF-01, RNF-08 | Un inicio de sesión fallido y un acceso sin sesión quedan como
    advertencia de seguridad, sin la contraseña ni el token."""
    crear_usuario("MESERO", "mesero@stockpot.test")
    with caplog.at_level(logging.WARNING):
        client.post("/api/auth/login", json={"email": "mesero@stockpot.test", "password": "ClaveEquivocada9"})
        client.get("/api/usuarios", headers={"Authorization": "Bearer token-falso"})

    mensajes = [rec.getMessage() for rec in caplog.records if rec.levelno == logging.WARNING]
    assert any("POST /api/auth/login → 401" in m for m in mensajes)
    assert any("GET /api/usuarios → 401" in m for m in mensajes)
    texto = " ".join(mensajes)
    assert "ClaveEquivocada9" not in texto and CLAVE not in texto and "token-falso" not in texto


def test_cp_log_4_permiso_negado_con_usuario(client, mesero_headers, caplog):
    """CP-LOG-4 | RNF-02, RNF-08 | Un 403 queda registrado con el id del usuario que lo intentó."""
    with caplog.at_level(logging.WARNING):
        client.get("/api/usuarios", headers=mesero_headers)
    assert any("→ 403 (usuario=" in rec.getMessage() for rec in caplog.records)


def test_cp_log_5_archivo_de_registro(tmp_path):
    """CP-LOG-5 | RNF-08 | Con LOG_DIR configurado se crea stockpot.log y se anota el arranque."""
    class Config(TestConfig):
        LOG_DIR = tmp_path / "logs"

    app = create_app(Config)
    for manejador in app.logger.handlers:
        manejador.flush()
    archivo = tmp_path / "logs" / "stockpot.log"
    assert archivo.is_file() and "StockPot iniciado" in archivo.read_text(encoding="utf-8")
    for manejador in list(app.logger.handlers):  # suelta el archivo (Windows no deja borrarlo abierto)
        if getattr(manejador, "baseFilename", None):
            manejador.close()
            app.logger.removeHandler(manejador)
