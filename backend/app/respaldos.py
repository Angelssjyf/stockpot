"""Respaldo de la base de datos MySQL con mysqldump (comando  flask respaldar).

iniciar.bat lo ejecuta cada vez que se enciende StockPot, antes de abrir el servidor: así
queda una copia por cada sesión de trabajo o demostración. Se guardan en database/respaldos
(ignorada por git) y se conservan las últimas CONSERVAR copias automáticas.

La contraseña no se pasa en la línea de comandos (otro programa podría verla): va en un
archivo temporal de opciones que solo existe mientras corre mysqldump.

Restaurar una copia:  mysql -u root -p stockpot < database/respaldos/<archivo>.sql
"""

import glob
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parents[2] / "database" / "respaldos"
PREFIJO = "stockpot_auto_"
CONSERVAR = 15
RUTAS_WINDOWS = "C:/Program Files/MySQL/MySQL Server */bin/mysqldump.exe"


class RespaldoFallido(Exception):
    """mysqldump no está, no se pudo conectar o la copia quedó incompleta."""


def buscar_mysqldump():
    """MYSQLDUMP del .env, el PATH o la instalación estándar de MySQL en Windows."""
    for candidato in (os.getenv("MYSQLDUMP"), shutil.which("mysqldump"), *sorted(glob.glob(RUTAS_WINDOWS), reverse=True)):
        if candidato and Path(candidato).is_file():
            return candidato
    raise RespaldoFallido("No se encontró mysqldump. Instala MySQL Server o pon su ruta en MYSQLDUMP dentro de .env")


def rotar(carpeta, conservar=CONSERVAR):
    """Borra las copias automáticas más viejas y deja las últimas `conservar`. Las copias
    hechas a mano (otro nombre) nunca se tocan. Devuelve los archivos borrados."""
    copias = sorted(Path(carpeta).glob(f"{PREFIJO}*.sql"))
    viejas = copias[:-conservar] if conservar else copias
    for archivo in viejas:
        archivo.unlink()
    return viejas


def respaldar(carpeta=CARPETA, ahora=None, ejecutar=subprocess.run):
    """Hace la copia y devuelve su ruta. Lanza RespaldoFallido si algo sale mal."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{PREFIJO}{(ahora or datetime.now()):%Y-%m-%d_%H%M%S}.sql"
    mysqldump = buscar_mysqldump()

    opciones = tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False, encoding="utf-8")
    try:
        with opciones:
            opciones.write("[client]\n")
            opciones.write(f"user={os.getenv('DB_USER', '')}\n")
            # En los archivos de opciones de MySQL, dentro de comillas se escapan \ y "
            clave = os.getenv("DB_PASSWORD", "").replace("\\", "\\\\").replace('"', '\\"')
            opciones.write(f'password="{clave}"\n')
            opciones.write(f"host={os.getenv('DB_HOST') or 'localhost'}\n")
            opciones.write(f"port={os.getenv('DB_PORT') or '3306'}\n")
        resultado = ejecutar(
            [mysqldump, f"--defaults-extra-file={opciones.name}",
             "--single-transaction",       # copia consistente sin bloquear las tablas
             "--no-tablespaces",           # no pide el permiso PROCESS
             "--skip-triggers",            # el usuario de la app no tiene permiso TRIGGER (no hay triggers)
             "--default-character-set=utf8mb4",
             f"--result-file={destino}", os.getenv("DB_NAME") or "stockpot"],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(opciones.name)

    if resultado.returncode != 0:
        destino.unlink(missing_ok=True)
        raise RespaldoFallido((resultado.stderr or "mysqldump terminó con error").strip())
    if not destino.is_file() or "-- Dump completed" not in destino.read_text(encoding="utf-8", errors="ignore")[-300:]:
        destino.unlink(missing_ok=True)
        raise RespaldoFallido("La copia quedó incompleta")
    rotar(carpeta)
    return destino
