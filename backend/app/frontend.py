"""Entrega la interfaz web (frontend/: HTML, CSS y JavaScript) desde el mismo servidor Flask.

Así la interfaz y la API viven en la misma dirección: se abre http://127.0.0.1:5000 (o el
enlace de ngrok) y aparece la pantalla de login, con un solo servidor encendido.
"""

import mimetypes
from pathlib import Path

from flask import jsonify, send_from_directory

# En algunos Windows el registro asocia .js a "text/plain" y el navegador se niega a
# ejecutar los módulos JavaScript. Se fijan los tipos correctos.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


def register_frontend(app):
    carpeta = Path(app.config["FRONTEND_DIR"])

    @app.get("/")
    @app.get("/<path:ruta>")
    def frontend(ruta="index.html"):
        if ruta.startswith("api/"):
            # Una ruta de la API que no existe responde en JSON, no con la página
            return jsonify(error="La ruta de la API no existe"), 404

        if not (carpeta / "index.html").exists():
            return (
                "<h2>No se encontró la interfaz web.</h2>"
                "<p>Falta el archivo <code>frontend/index.html</code>.</p>",
                503,
            )

        if (carpeta / ruta).is_file():
            return send_from_directory(carpeta, ruta)
        # Una dirección que no existe lleva a la pantalla de inicio de sesión
        return send_from_directory(carpeta, "index.html")
