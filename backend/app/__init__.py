"""Fábrica de la aplicación Flask de StockPot."""

from flask import Flask, jsonify
from sqlalchemy import text

from .config import Config
from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

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
