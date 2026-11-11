"""Punto de entrada para un servidor WSGI en Linux (por ejemplo, si algún día se publica en la nube).

En el PC del equipo se usa iniciar.bat (Waitress + ngrok): ver docs/despliegue/Guia_Despliegue_ngrok.md
"""

import os
import time

# Los servidores en la nube están en hora UTC; StockPot trabaja con la hora de Colombia
os.environ.setdefault("TZ", "America/Bogota")
if hasattr(time, "tzset"):  # solo existe en Linux (en Windows se usa la hora del equipo)
    time.tzset()

from app import create_app  # noqa: E402

application = create_app()
