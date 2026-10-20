"""Comandos de consola propios de StockPot (se ejecutan con  flask <comando>)."""

import click

from .extensions import db
from .models import Rol, Usuario


def register_cli(app):
    @app.cli.command("crear-admin")
    @click.option("--email", prompt="Correo del administrador")
    @click.option("--nombre", prompt="Nombre")
    @click.option("--apellido", prompt="Apellido")
    @click.password_option("--password", prompt="Contraseña (mínimo 8 caracteres)")
    def crear_admin(email, nombre, apellido, password):
        """Crea el usuario administrador, o le restablece la contraseña si ya existe."""
        if len(password) < 8:
            raise click.ClickException("La contraseña debe tener al menos 8 caracteres")

        rol = Rol.query.filter_by(nombre="ADMINISTRADOR").first()
        if rol is None:
            raise click.ClickException("No existe el rol ADMINISTRADOR. Ejecuta database/02_seed.sql")

        email = email.strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None:
            usuario = Usuario(email=email, nombre=nombre.strip(), apellido=apellido.strip())
            db.session.add(usuario)
            accion = "creado"
        else:
            accion = "actualizado"

        usuario.rol = rol
        usuario.activo = True
        usuario.set_password(password)
        db.session.commit()
        click.echo(f"Administrador {accion}: {email}")
