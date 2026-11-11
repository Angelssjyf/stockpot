"""Casos de prueba: punto de entrada para servidores WSGI.

Formato del docstring:  ID del caso | requisito | qué se verifica
"""


def test_cp_dep_1_wsgi():
    """CP-DEP-1 | Despliegue | wsgi.py entrega la aplicación lista para un servidor WSGI."""
    import wsgi

    assert wsgi.application.name == "app" and "/api/auth/login" in {r.rule for r in wsgi.application.url_map.iter_rules()}
