"""Entrega la interfaz web (frontend/: HTML, CSS y JavaScript) desde el mismo servidor Flask.

Así la app y la API viven en la misma dirección: se abre http://127.0.0.1:5000 (o el
enlace de ngrok) y aparece la pantalla de login, con un solo servidor encendido.
"""

from pathlib import Path

from flask import jsonify, send_from_directory


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

        archivo = carpeta / ruta
        if archivo.is_file():
            return send_from_directory(carpeta, ruta)
        # Cualquier otra dirección la maneja la app Flutter
        return send_from_directory(carpeta, "index.html")
