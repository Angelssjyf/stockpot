"""Casos de prueba: Flask entrega la app Flutter compilada en la misma dirección que la API."""

import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture()
def client_con_app(tmp_path):
    """Cliente con una app web falsa (index.html + main.dart.js) en una carpeta temporal."""
    (tmp_path / "index.html").write_text("<html>StockPot app</html>", encoding="utf-8")
    (tmp_path / "main.dart.js").write_text("console.log('app')", encoding="utf-8")

    class Config(TestConfig):
        FRONTEND_DIR = tmp_path

    return create_app(Config).test_client()


def test_cp_web_1_raiz_entrega_la_app(client_con_app):
    """CP-WEB-1 | Despliegue | Abrir "/" entrega la página de la app."""
    r = client_con_app.get("/")
    assert r.status_code == 200
    assert b"StockPot app" in r.data


def test_cp_web_2_entrega_archivos_de_la_app(client_con_app):
    """CP-WEB-2 | Despliegue | Los archivos de la app (JavaScript) se entregan tal cual."""
    r = client_con_app.get("/main.dart.js")
    assert r.status_code == 200
    assert b"console.log" in r.data


def test_cp_web_3_otras_direcciones_abren_la_app(client_con_app):
    """CP-WEB-3 | Despliegue | Una dirección desconocida (no API) abre la app."""
    assert b"StockPot app" in client_con_app.get("/inventario").data


def test_cp_web_4_api_inexistente_responde_json(client_con_app):
    """CP-WEB-4 | Despliegue | Una ruta /api/ que no existe responde 404 en JSON, no la página."""
    r = client_con_app.get("/api/no-existe")
    assert r.status_code == 404
    assert r.get_json()["error"]


def test_cp_web_5_sin_compilar_avisa(tmp_path):
    """CP-WEB-5 | Despliegue | Si la app no está compilada, se explica cómo compilarla (503)."""

    class Config(TestConfig):
        FRONTEND_DIR = tmp_path / "no-existe"

    r = create_app(Config).test_client().get("/")
    assert r.status_code == 503
    assert b"flutter build web" in r.data
