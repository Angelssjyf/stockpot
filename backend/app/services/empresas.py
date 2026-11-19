"""Servicio de empresas: crear un restaurante nuevo con sus roles y su administrador."""

from datetime import datetime, timedelta

from ..extensions import db
from ..models import Empresa, Permiso, Rol, Sesion, Usuario

MODULO_SUPERADMIN = "empresas"

# Los mismos roles y permisos con los que arranca el restaurante del seed (database/02_seed.sql).
# None = todos los permisos de un restaurante. Luego cada restaurante los ajusta a su gusto.
PLANTILLA_ROLES = {
    "ADMINISTRADOR": ("Dueño o administrador: acceso total al sistema", None),
    "MESERO": ("Toma pedidos en mesa y gestiona reservas",
               ["productos.ver", "pedidos.ver", "pedidos.gestionar", "reservas.ver", "reservas.gestionar",
                "incidencias.reportar"]),
    "COCINERO": ("Ve y actualiza las órdenes en cocina",
                 ["cocina.ver", "cocina.gestionar", "productos.ver", "inventario.ver", "incidencias.reportar"]),
    "CAJERO": ("Registra pagos, ventas y domicilios",
               ["pedidos.ver", "pedidos.gestionar", "productos.ver", "pagos.ver", "pagos.gestionar", "ventas.ver",
                "domicilios.ver", "domicilios.gestionar", "incidencias.reportar"]),
    "BODEGUERO": ("Gestiona inventario, proveedores y compras",
                  ["inventario.ver", "inventario.gestionar", "proveedores.ver", "proveedores.gestionar",
                   "compras.ver", "compras.gestionar", "productos.ver", "incidencias.reportar"]),
    "DOMICILIARIO": ("Consulta y entrega los pedidos a domicilio", ["domicilios.ver", "incidencias.reportar"]),
}


def crear_empresa(datos, admin):
    """Crea la empresa, sus roles según la plantilla y su primer administrador. No hace commit.

    datos: nombre, nit, telefono, email, direccion. admin: nombre, apellido, email, password.
    """
    empresa = Empresa(**datos)
    db.session.add(empresa)
    db.session.flush()  # para tener empresa.id

    permisos = Permiso.query.filter(Permiso.modulo != MODULO_SUPERADMIN).all()
    roles = {}
    for nombre, (descripcion, codigos) in PLANTILLA_ROLES.items():
        roles[nombre] = Rol(empresa_id=empresa.id, nombre=nombre, descripcion=descripcion,
                            permisos=[p for p in permisos if codigos is None or p.codigo in codigos])
        db.session.add(roles[nombre])

    usuario = Usuario(empresa_id=empresa.id, rol=roles["ADMINISTRADOR"], nombre=admin["nombre"],
                      apellido=admin["apellido"], email=admin["email"])
    usuario.set_password(admin["password"])
    db.session.add(usuario)
    return empresa, usuario


def resumen(empresa):
    """Datos generales de la empresa para el súper administrador: sin inventario ni ventas."""
    usuarios = Usuario.query.execution_options(todas_las_empresas=True).filter_by(empresa_id=empresa.id).all()
    administradores = [u for u in usuarios if u.rol.nombre == "ADMINISTRADOR"]
    sesiones = Sesion.query.filter(Sesion.usuario_id.in_([u.id for u in usuarios])).all() if usuarios else []
    ultima = max((s.ultima_actividad for s in sesiones), default=None)
    hace_un_rato = datetime.now() - timedelta(minutes=15)
    return {
        **empresa.to_dict(),
        "usuarios": len(usuarios),
        "usuarios_activos": sum(1 for u in usuarios if u.activo),
        "administradores": [{"nombre": f"{u.nombre} {u.apellido}", "email": u.email, "activo": u.activo}
                            for u in administradores],
        # Uso de la plataforma (no datos del negocio): última actividad y quién está conectado ahora
        "ultima_actividad": ultima.isoformat(timespec="minutes") if ultima else None,
        "conectados": len({s.usuario_id for s in sesiones if s.cerrada is None and s.ultima_actividad >= hace_un_rato}),
    }
