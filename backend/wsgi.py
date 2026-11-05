"""Punto de entrada para un servidor web en la nube (PythonAnywhere u otro con WSGI).

El archivo WSGI de PythonAnywhere solo tiene que agregar esta carpeta a sys.path y hacer
    from wsgi import application
Ver docs/despliegue/Guia_Despliegue_PythonAnywhere.md
"""

import os
import time

# Los servidores en la nube están en hora UTC; StockPot trabaja con la hora de Colombia
os.environ.setdefault("TZ", "America/Bogota")
if hasattr(time, "tzset"):  # solo existe en Linux (en Windows se usa la hora del equipo)
    time.tzset()

from app import create_app  # noqa: E402

application = create_app()
