"""Extensiones compartidas por toda la aplicación."""

from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

# Objeto único de conexión a la base de datos. Los modelos y las rutas lo importan de aquí.
db = SQLAlchemy()

# Maneja la creación y verificación de los tokens de inicio de sesión
jwt = JWTManager()
