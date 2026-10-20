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
    from .modules.compras.routes import bp as compras_bp
    from .modules.domicilios.routes import bp as domicilios_bp
    from .modules.inventario.routes import bp as inventario_bp
    from .modules.pagos.routes import bp as pagos_bp
    from .modules.pedidos.routes import bp as pedidos_bp
    from .modules.productos.routes import bp as productos_bp
    from .modules.proveedores.routes import bp as proveedores_bp
    from .modules.reportes.routes import bp as reportes_bp
    from .modules.usuarios.routes import bp as usuarios_bp
    from .modules.ventas.routes import bp as ventas_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(usuarios_bp, url_prefix="/api")
    app.register_blueprint(proveedores_bp, url_prefix="/api")
    app.register_blueprint(compras_bp, url_prefix="/api")
    app.register_blueprint(inventario_bp, url_prefix="/api")
    app.register_blueprint(productos_bp, url_prefix="/api")
    app.register_blueprint(pedidos_bp, url_prefix="/api")
    app.register_blueprint(domicilios_bp, url_prefix="/api")
    app.register_blueprint(pagos_bp, url_prefix="/api")
    app.register_blueprint(ventas_bp, url_prefix="/api")
    app.register_blueprint(reportes_bp, url_prefix="/api")

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

    # La interfaz web (frontend/) se entrega en "/" (debe ir al final, después de la API)
    from .frontend import register_frontend

    register_frontend(app)

    return app
