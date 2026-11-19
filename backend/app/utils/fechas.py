"""Filtro por rango de fechas (?desde=AAAA-MM-DD&hasta=AAAA-MM-DD) compartido por las consultas."""

from datetime import date, timedelta


def filtrar_por_fechas(consulta, columna, args):
    """Aplica ?desde y ?hasta (ambos incluidos) a la consulta sobre la columna de fecha.

    Lanza ValueError si una fecha no tiene el formato AAAA-MM-DD.
    """
    if args.get("desde"):
        consulta = consulta.filter(columna >= date.fromisoformat(args["desde"]))
    if args.get("hasta"):
        # hasta el final de ese día: menor que el día siguiente
        consulta = consulta.filter(columna < date.fromisoformat(args["hasta"]) + timedelta(days=1))
    return consulta


def hoy_bd():
    """La fecha de hoy según el reloj de la base de datos, el mismo que fecha las ventas
    (en SQLite ese reloj está en UTC; en MySQL, en la zona horaria configurada)."""
    from sqlalchemy import func, select

    from ..extensions import db

    return date.fromisoformat(str(db.session.scalar(select(func.current_date())))[:10])
