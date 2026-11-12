"""Casos de prueba: copia de seguridad automática de la base de datos (flask respaldar).

No se llama a mysqldump de verdad: se reemplaza por una función que simula su resultado.
Formato del docstring:  ID del caso | requisito | qué se verifica
"""

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app import respaldos
from app.respaldos import PREFIJO, RespaldoFallido, respaldar, rotar


@pytest.fixture(autouse=True)
def mysqldump_falso(monkeypatch, tmp_path):
    exe = tmp_path / "mysqldump.exe"
    exe.write_text("")
    monkeypatch.setattr(respaldos, "buscar_mysqldump", lambda: str(exe))
    monkeypatch.setenv("DB_USER", "stockpot_app")
    monkeypatch.setenv("DB_PASSWORD", 'cla"ve\\secreta')
    monkeypatch.setenv("DB_NAME", "stockpot")


def _simular(contenido, codigo=0, error=""):
    """Imita mysqldump: escribe el archivo de --result-file y guarda los argumentos."""
    llamadas = []

    def ejecutar(argumentos, **_):
        opciones = Path(argumentos[1].split("=", 1)[1])
        llamadas.append((argumentos, opciones.read_text(encoding="utf-8")))
        destino = next(a.split("=", 1)[1] for a in argumentos if a.startswith("--result-file="))
        Path(destino).write_text(contenido, encoding="utf-8")
        return subprocess.CompletedProcess(argumentos, codigo, "", error)

    return ejecutar, llamadas


def test_cp_res_1_respaldo_completo(tmp_path):
    """CP-RES-1 | RNF-08 | La copia se guarda con fecha y hora; la contraseña no va en la línea
    de comandos y el archivo temporal de opciones se borra al terminar."""
    ejecutar, llamadas = _simular("CREATE TABLE x;\n-- Dump completed on 2026-11-12\n")
    archivo = respaldar(tmp_path, ahora=datetime(2026, 11, 12, 8, 30, 5), ejecutar=ejecutar)

    assert archivo.name == f"{PREFIJO}2026-11-12_083005.sql"
    argumentos, opciones = llamadas[0]
    assert "--single-transaction" in argumentos and argumentos[-1] == "stockpot"
    assert not any("secreta" in a for a in argumentos)  # la clave no se ve en los procesos
    assert 'password="cla\\"ve\\\\secreta"' in opciones and "user=stockpot_app" in opciones
    assert not Path(argumentos[1].split("=", 1)[1]).exists()  # opciones borradas


def test_cp_res_2_error_de_mysqldump(tmp_path):
    """CP-RES-2 | RNF-08 | Si mysqldump falla, se avisa con su mensaje y no queda archivo a medias."""
    ejecutar, _ = _simular("parcial", codigo=2, error="Access denied for user")
    with pytest.raises(RespaldoFallido, match="Access denied"):
        respaldar(tmp_path, ejecutar=ejecutar)
    assert not list(tmp_path.glob(f"{PREFIJO}*.sql"))


def test_cp_res_3_copia_incompleta(tmp_path):
    """CP-RES-3 | RNF-08 | Una copia sin la marca final de mysqldump se descarta."""
    ejecutar, _ = _simular("CREATE TABLE x;\n")
    with pytest.raises(RespaldoFallido, match="incompleta"):
        respaldar(tmp_path, ejecutar=ejecutar)
    assert not list(tmp_path.glob(f"{PREFIJO}*.sql"))


def test_cp_res_4_rotacion(tmp_path):
    """CP-RES-4 | RNF-08 | Se conservan las últimas copias automáticas; las manuales no se tocan."""
    for dia in range(1, 6):
        (tmp_path / f"{PREFIJO}2026-11-0{dia}_080000.sql").write_text("x")
    manual = tmp_path / "stockpot_2026-10-20.sql"
    manual.write_text("x")

    borradas = rotar(tmp_path, conservar=3)

    assert [b.name for b in borradas] == [f"{PREFIJO}2026-11-01_080000.sql", f"{PREFIJO}2026-11-02_080000.sql"]
    assert sorted(p.name for p in tmp_path.glob(f"{PREFIJO}*.sql")) == [
        f"{PREFIJO}2026-11-0{dia}_080000.sql" for dia in (3, 4, 5)]
    assert manual.exists()
