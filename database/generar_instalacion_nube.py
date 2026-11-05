"""Genera los scripts para instalar la base en la nube (PythonAnywhere).

Allá la base ya existe (se crea desde la página, con el nombre USUARIO$stockpot) y no se puede
borrar ni crear con SQL, así que se quitan las líneas DROP DATABASE, CREATE DATABASE y USE.

    python database/generar_instalacion_nube.py

Crea:
- nube_1_instalar.sql      = 01_schema.sql + 02_seed.sql  (tablas, roles, permisos y códigos)
- nube_2_datos_ejemplo.sql = 04_datos_ejemplo.sql         (opcional, para la demostración)

Se vuelve a ejecutar cada vez que cambie 01, 02 o 04 (la prueba test_despliegue.py lo revisa).
"""

import re
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
QUITAR = re.compile(r"^\s*(DROP DATABASE|CREATE DATABASE|USE)\b", re.IGNORECASE)

ENCABEZADO = """-- =====================================================================
--  StockPot - {titulo} (GENERADO: no editar a mano)
--  Generado por database/generar_instalacion_nube.py a partir de {origen}.
--  Para la base de PythonAnywhere (USUARIO$stockpot), que ya debe existir y estar vacía.
--  En la consola MySQL de PythonAnywhere:  source /home/USUARIO/stockpot/database/{nombre};
-- =====================================================================

"""


def sin_base(texto):
    return "\n".join(linea for linea in texto.splitlines() if not QUITAR.match(linea)) + "\n"


def contenido(nombre, titulo, origenes):
    partes = [ENCABEZADO.format(titulo=titulo, origen=" + ".join(origenes), nombre=nombre)]
    for origen in origenes:
        partes.append(f"-- ===================== {origen} =====================\n")
        partes.append(sin_base((CARPETA / origen).read_text(encoding="utf-8")))
    return "".join(partes)


ARCHIVOS = {
    "nube_1_instalar.sql": ("instalación en la nube", ["01_schema.sql", "02_seed.sql"]),
    "nube_2_datos_ejemplo.sql": ("datos de ejemplo en la nube (opcional)", ["04_datos_ejemplo.sql"]),
}

if __name__ == "__main__":
    for nombre, (titulo, origenes) in ARCHIVOS.items():
        (CARPETA / nombre).write_text(contenido(nombre, titulo, origenes), encoding="utf-8", newline="\n")
        print("Generado", nombre)
