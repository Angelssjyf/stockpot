"""Casos de prueba: Flask entrega la interfaz web en la misma dirección que la API."""

import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture()
def client_con_app(tmp_path):
    """Cliente con una app web falsa (index.html + app.js) en una carpeta temporal."""
    (tmp_path / "index.html").write_text("<html>StockPot app</html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.log('app')", encoding="utf-8")

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
    r = client_con_app.get("/app.js")
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
    assert b"frontend/index.html" in r.data


# ------------------------------------------------- Interfaz web real (carpeta frontend/)


@pytest.fixture()
def client_real():
    """Cliente que sirve la carpeta frontend/ real del proyecto."""
    return create_app(TestConfig).test_client()


@pytest.mark.parametrize(
    "pagina",
    ["/", "/menu.html", "/empresas.html", "/usuarios.html", "/insumos.html", "/proveedores.html", "/compras.html",
     "/pedidos.html", "/comanda.html", "/cocina.html", "/reservas.html"],
)
def test_cp_web_6_paginas_existen(client_real, pagina):
    """CP-WEB-6 | Interfaz web | Las páginas de la interfaz existen y se entregan."""
    r = client_real.get(pagina)
    assert r.status_code == 200
    assert r.mimetype == "text/html"
    assert b"StockPot" in r.data


@pytest.mark.parametrize(
    "archivo",
    ["/js/api.js", "/js/ui.js", "/js/login.js", "/js/menu.js", "/js/usuarios.js",
     "/js/insumos.js", "/js/proveedores.js", "/js/compras.js", "/js/pedidos.js", "/js/comanda.js"],
)
def test_cp_web_7_javascript_con_tipo_correcto(client_real, archivo):
    """CP-WEB-7 | Interfaz web | Los .js se entregan como JavaScript (si no, el navegador no los ejecuta)."""
    r = client_real.get(archivo)
    assert r.status_code == 200
    assert r.mimetype == "text/javascript"


def test_cp_web_8_css_con_tipo_correcto(client_real):
    """CP-WEB-8 | Interfaz web | Los estilos se entregan como CSS."""
    r = client_real.get("/css/estilos.css")
    assert r.status_code == 200
    assert r.mimetype == "text/css"


# ------------------------------------------------------- Cabeceras de seguridad HTTP (OWASP)


def test_cp_seg_40_cabeceras_en_la_interfaz(client_con_app):
    """CP-SEG-40 | RNF-01 | Las páginas llegan con CSP estricta, sin iframes de otros sitios
    y sin que el navegador adivine el tipo de archivo."""
    r = client_con_app.get("/")
    csp = r.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp and "'unsafe-inline'" not in csp
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "same-origin"
    assert "camera=()" in r.headers["Permissions-Policy"]
    assert "Strict-Transport-Security" not in r.headers  # por HTTP local no aplica


def test_cp_seg_41_api_sin_cache_y_hsts_por_https(client_con_app):
    """CP-SEG-41 | RNF-01 | Las respuestas de la API no se guardan en caché y, si se entra por
    HTTPS (enlace de ngrok), el navegador queda obligado a usar HTTPS."""
    r = client_con_app.get("/api/auth/yo")
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    r = client_con_app.get("/", headers={"X-Forwarded-Proto": "https"})
    assert r.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "Cache-Control" not in r.headers or r.headers["Cache-Control"] != "no-store"
