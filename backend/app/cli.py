"""Comandos de consola propios de StockPot (se ejecutan con  flask <comando>)."""

import click

from .extensions import db
from .models import Empresa, Rol, Usuario


def register_cli(app):
    @app.cli.command("respaldar")
    def respaldar_cmd():
        """Copia de seguridad de la base de datos en database/respaldos (guarda las últimas 15)."""
        from .respaldos import RespaldoFallido, respaldar

        try:
            archivo = respaldar()
        except RespaldoFallido as error:
            raise click.ClickException(f"No se pudo hacer el respaldo: {error}")
        click.echo(f"Respaldo listo: database/respaldos/{archivo.name} ({archivo.stat().st_size // 1024} KB)")

    @app.cli.command("crear-admin")
    @click.option("--email", prompt="Correo del administrador")
    @click.option("--nombre", prompt="Nombre")
    @click.option("--apellido", prompt="Apellido")
    @click.password_option("--password", prompt="Contraseña (mínimo 8 caracteres)")
    @click.option("--empresa", default=1, show_default=True, help="Id del restaurante")
    def crear_admin(email, nombre, apellido, password, empresa):
        """Crea el administrador de un restaurante, o le restablece la contraseña si ya existe."""
        if len(password) < 8:
            raise click.ClickException("La contraseña debe tener al menos 8 caracteres")
        if db.session.get(Empresa, empresa) is None:
            raise click.ClickException(f"No existe la empresa {empresa}")

        rol = Rol.query.filter_by(nombre="ADMINISTRADOR", empresa_id=empresa).first()
        if rol is None:
            raise click.ClickException("No existe el rol ADMINISTRADOR. Ejecuta database/02_seed.sql")
        _guardar_usuario(email, nombre, apellido, password, rol, empresa, "Administrador")

    @app.cli.command("crear-superadmin")
    @click.option("--email", prompt="Correo del súper administrador")
    @click.option("--nombre", prompt="Nombre")
    @click.option("--apellido", prompt="Apellido")
    @click.password_option("--password", prompt="Contraseña (mínimo 12 caracteres)")
    def crear_superadmin(email, nombre, apellido, password):
        """Crea el súper administrador (solo gestiona restaurantes), o le restablece la contraseña."""
        if len(password) < 12:
            raise click.ClickException("La contraseña debe tener al menos 12 caracteres")
        rol = Rol.query.filter_by(nombre="SUPERADMIN", empresa_id=None).first()
        if rol is None:
            raise click.ClickException("No existe el rol SUPERADMIN. Ejecuta database/14_empresas.sql")
        _guardar_usuario(email, nombre, apellido, password, rol, None, "Súper administrador")

    def _guardar_usuario(email, nombre, apellido, password, rol, empresa_id, titulo):
        email = email.strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None:
            usuario = Usuario(email=email, nombre=nombre.strip(), apellido=apellido.strip())
            db.session.add(usuario)
            accion = "creado"
        else:
            accion = "actualizado"

        usuario.rol = rol
        usuario.empresa_id = empresa_id
        usuario.activo = True
        usuario.set_password(password)
        db.session.commit()
        click.echo(f"{titulo} {accion}: {email}")
