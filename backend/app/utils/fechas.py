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
