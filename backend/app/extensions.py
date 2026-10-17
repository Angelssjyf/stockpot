"""Extensiones compartidas por toda la aplicación."""

from flask_sqlalchemy import SQLAlchemy

# Objeto único de conexión a la base de datos. Los modelos y las rutas lo importan de aquí.
db = SQLAlchemy()
