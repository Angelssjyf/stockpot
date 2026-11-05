"""Casos de prueba: preparación del despliegue en la nube (PythonAnywhere).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]


def _generador():
    spec = importlib.util.spec_from_file_location("generador", BASE / "database" / "generar_instalacion_nube.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_cp_dep_1_scripts_de_la_nube_al_dia():
    """CP-DEP-1 | Despliegue | Los scripts de la nube coinciden con 01, 02 y 04 (si fallan, ejecutar
    python database/generar_instalacion_nube.py) y no crean, borran ni cambian de base."""
    generador = _generador()
    for nombre, (titulo, origenes) in generador.ARCHIVOS.items():
        guardado = (BASE / "database" / nombre).read_text(encoding="utf-8")
        assert guardado == generador.contenido(nombre, titulo, origenes), f"{nombre} desactualizado"
        assert not any(generador.QUITAR.match(linea) for linea in guardado.splitlines())
    assert "CREATE TABLE empresas" in (BASE / "database" / "nube_1_instalar.sql").read_text(encoding="utf-8")


def test_cp_dep_2_wsgi(monkeypatch):
    """CP-DEP-2 | Despliegue | wsgi.py entrega la aplicación lista para el servidor de la nube."""
    import wsgi

    assert wsgi.application.name == "app" and "/api/auth/login" in {r.rule for r in wsgi.application.url_map.iter_rules()}
