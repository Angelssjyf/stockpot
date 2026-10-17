"""Modelos de ILF01 Usuarios e ILF02 Roles y permisos (Iteración 1).

Cada clase corresponde a una tabla creada en database/01_schema.sql.
"""

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db

# Tabla intermedia rol_permisos (muchos a muchos). No necesita clase propia
# porque solo guarda las dos llaves foráneas.
rol_permisos = db.Table(
    "rol_permisos",
    db.Column("rol_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permiso_id", db.Integer, db.ForeignKey("permisos.id"), primary_key=True),
)


class Permiso(db.Model):
    __tablename__ = "permisos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(60), nullable=False, unique=True)
    modulo = db.Column(db.String(40), nullable=False)
    descripcion = db.Column(db.String(255))


class Rol(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(255))
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # rol.permisos devuelve la lista de objetos Permiso del rol
    permisos = db.relationship("Permiso", secondary=rol_permisos)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "activo": self.activo,
            "permisos": sorted(p.codigo for p in self.permisos),
        }


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(20))
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_acceso = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # usuario.rol devuelve el objeto Rol del usuario
    rol = db.relationship("Rol")

    def set_password(self, password):
        """Guarda la contraseña cifrada (hash). Nunca se guarda el texto original."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Compara una contraseña escrita con el hash guardado."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        # password_hash NO se incluye: nunca se envía al cliente
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "email": self.email,
            "telefono": self.telefono,
            "rol": self.rol.nombre if self.rol else None,
            "activo": self.activo,
        }
