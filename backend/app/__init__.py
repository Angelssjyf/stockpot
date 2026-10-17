"""Fábrica de la aplicación Flask de StockPot."""

from flask import Flask, jsonify
from sqlalchemy import text

from .config import Config
from .extensions import db, jwt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.ensure_ascii = False  # respuestas JSON con tildes legibles

    db.init_app(app)
    jwt.init_app(app)

    # Mensajes en español cuando falta el token, es inválido o venció (HTTP 401)
    @jwt.unauthorized_loader
    def sin_token(motivo):
        return jsonify(error="Debes iniciar sesión"), 401

    @jwt.invalid_token_loader
    def token_invalido(motivo):
        return jsonify(error="Token inválido"), 401

    @jwt.expired_token_loader
    def token_vencido(header, payload):
        return jsonify(error="La sesión venció, inicia sesión de nuevo"), 401

    # Módulos (blueprints): cada uno con su prefijo de URL
    from .modules.auth.routes import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from .cli import register_cli

    register_cli(app)

    @app.get("/api/health")
    def health():
        """Comprueba que la API está viva y que se conecta a MySQL."""
        try:
            version = db.session.execute(text("SELECT VERSION()")).scalar()
            roles = db.session.execute(text("SELECT nombre FROM roles ORDER BY id")).scalars().all()
            return jsonify(api="ok", mysql=version, roles=roles)
        except Exception as error:
            return jsonify(api="ok", mysql="error", detalle=str(error.__class__.__name__)), 500

    return app
