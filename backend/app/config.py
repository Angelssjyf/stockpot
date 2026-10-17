"""Configuración de la aplicación. Los valores secretos se leen del archivo .env."""

import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()  # carga las variables del archivo .env


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Cadena de conexión: mysql+pymysql://usuario:clave@host:puerto/base
    # quote_plus protege la clave si tiene caracteres especiales (@, :, /, #...)
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{quote_plus(os.getenv('DB_PASSWORD', ''))}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}"
        f"/{os.getenv('DB_NAME', 'stockpot')}?charset=utf8mb4"
    )

    # Revisa que la conexión siga viva antes de usarla (MySQL cierra las inactivas)
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Tokens JWT del inicio de sesión: se firman con la misma SECRET_KEY
    # y vencen a las 8 horas (una jornada de trabajo).
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
