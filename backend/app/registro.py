"""Registro de eventos (logs) y manejo de errores inesperados.

Todo queda en backend/logs/stockpot.log (ignorada por git). El archivo rota al llegar a 1 MB
y se guardan 5 anteriores, así nunca llena el disco.

Qué se registra:
- ERROR: cualquier falla inesperada, con el detalle técnico (traceback), quién la tuvo y un
  código corto. El usuario ve "Ocurrió un error inesperado (código A1B2C3)" y con ese código
  se encuentra el detalle en el archivo.
- WARNING: eventos de seguridad (401 sin sesión, 403 sin permiso, 423 sesión bloqueada,
  428 falta el PIN, 429 demasiados intentos) y peticiones lentas (más de 2 segundos).
- INFO: arranque del servidor.

Nunca se registran contraseñas, tokens ni el contenido de las peticiones.
"""

import logging
import secrets
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import g, jsonify, request
from werkzeug.exceptions import HTTPException

from .extensions import db

FORMATO = "%(asctime)s %(levelname)-7s %(message)s"
LENTA_SEGUNDOS = 2.0
SEGURIDAD = {401, 403, 423, 428, 429}


def origen():
    """IP de quien hizo la petición (detrás de ngrok viene en X-Forwarded-For)."""
    return (request.headers.get("X-Forwarded-For") or request.remote_addr or "?").split(",")[0].strip()


def quien():
    """Usuario de la sesión, si la petición ya la abrió (nunca el token)."""
    usuario = getattr(g, "usuario", None)
    return f"usuario={usuario.id}" if usuario is not None and getattr(usuario, "id", None) else "sin sesión"


def register_registro(app):
    carpeta = app.config.get("LOG_DIR")
    if carpeta:
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        ruta = (Path(carpeta) / "stockpot.log").resolve()
        # El logger de Flask es global: si la app se crea dos veces, no se duplica el archivo
        if not any(getattr(h, "baseFilename", None) == str(ruta) for h in app.logger.handlers):
            archivo = RotatingFileHandler(ruta, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
            archivo.setFormatter(logging.Formatter(FORMATO))
            archivo.setLevel(logging.INFO)
            app.logger.addHandler(archivo)
        app.logger.setLevel(logging.INFO)
        app.logger.info("StockPot iniciado")

    @app.before_request
    def marcar_inicio():
        g.inicio_peticion = time.perf_counter()

    @app.after_request
    def registrar_peticion(respuesta):
        if not request.path.startswith("/api/"):
            return respuesta
        duracion = time.perf_counter() - getattr(g, "inicio_peticion", time.perf_counter())
        if respuesta.status_code in SEGURIDAD:
            app.logger.warning("Seguridad %s %s → %s (%s, ip %s)", request.method, request.path,
                               respuesta.status_code, quien(), origen())
        if duracion > LENTA_SEGUNDOS:
            app.logger.warning("Lenta %s %s → %s en %.1f s (%s)", request.method, request.path,
                               respuesta.status_code, duracion, quien())
        return respuesta

    @app.errorhandler(Exception)
    def error_inesperado(error):
        if isinstance(error, HTTPException):
            return error  # 404, 405, etc. siguen su camino normal
        codigo = secrets.token_hex(3).upper()
        db.session.rollback()  # que la falla no deje nada a medias
        app.logger.error("Error %s en %s %s (%s, ip %s)", codigo, request.method, request.path, quien(), origen(),
                         exc_info=error)
        mensaje = f"Ocurrió un error inesperado (código {codigo}). Intenta de nuevo; si se repite, avisa al administrador."
        if request.path.startswith("/api/"):
            return jsonify(error=mensaje, codigo=codigo), 500
        return f"<h2>{mensaje}</h2>", 500
