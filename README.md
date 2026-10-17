# StockPot

Sistema de gestión para restaurantes pequeños y medianos: controla el inventario de insumos,
gestiona los pedidos, comunica las áreas de atención y cocina, y genera información sobre
el consumo y las ventas.

```
App Flutter  ──HTTP/JSON + token JWT──►  API Flask (Python)  ──SQLAlchemy──►  MySQL 8.4
(web / Android)                          backend/                             database/
```

| Capa | Tecnología |
|---|---|
| Base de datos | MySQL 8.4 LTS + MySQL Workbench |
| Backend (API REST) | Python 3.11, Flask, SQLAlchemy, Flask-JWT-Extended |
| App cliente | Flutter / Dart *(en construcción)* |
| Pruebas | pytest |
| Control de versiones | Git + GitHub con GitFlow |

## Equipo e iteraciones

| Iteración | Responsable | Módulos | Estado |
|---|---|---|---|
| 1 | Mateo | Usuarios y roles (RF-01) · Proveedores (RF-02) | 🟡 RF-01 terminado, RF-02 en curso |
| 2 | Jorman | Inventario (RF-03) · Productos y menú (RF-04) | ⏳ |
| 3 | Yovany | Pedidos (RF-05) · Cocina (RF-06) · Reservas (RF-07) | ⏳ |
| 4 | Ángel | Domicilios (RF-08) · Pagos (RF-09) · Ventas y consumo (RF-10) · Reportes (RF-11) | ⏳ |

## Estructura del proyecto

```
stockpot/
├── database/            Scripts SQL (ejecutar en orden)
│   ├── 01_schema.sql    Crea la base y las tablas
│   ├── 02_seed.sql      Roles y permisos iniciales
│   └── 03_usuario_app.sql   Usuario de MySQL para la aplicación
├── backend/             API Flask
│   ├── app/
│   │   ├── models/      Tablas como clases de Python
│   │   ├── modules/     Un módulo por cada requisito de la EDT (auth, usuarios...)
│   │   └── utils/       Código compartido (control de permisos)
│   └── tests/           Pruebas automáticas (casos CP-XX.X-n)
└── docs/                Documentación (modelo de datos)
```

---

## Instalación (para cada integrante)

### 1. Requisitos
Instala: **Python 3.11**, **Git**, **MySQL Server 8.4 LTS**, **MySQL Workbench** y **VS Code**.

### 2. Clonar el repositorio

```powershell
git clone https://github.com/Angelssjyf/stockpot.git
cd stockpot
git checkout develop
```

### 3. Crear la base de datos
En MySQL Workbench, conectado como `root`, ejecuta en este orden (rayo ⚡):

1. `database/01_schema.sql`: crea la base `stockpot`. ⚠️ Borra la base si ya existe.
2. `database/02_seed.sql`: roles y permisos.
3. `database/03_usuario_app.sql`: **antes de ejecutarlo**, cambia `CAMBIA_ESTA_CLAVE` por una
   contraseña tuya, solo en el editor de Workbench. No guardes el archivo con la clave.

Verifica con `SHOW TABLES FROM stockpot;`: deben salir 9 tablas.

### 4. Configurar el backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Abre `backend/.env` y llena `DB_PASSWORD` (la clave de `stockpot_app`) y `SECRET_KEY`. Para
generar la `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

> 🔒 El archivo `.env` **nunca se sube** a GitHub (está en `.gitignore`). No compartas su contenido.

Si PowerShell no deja activar el entorno (*"la ejecución de scripts está deshabilitada"*), ejecuta
primero `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`.

### 5. Crear tu usuario administrador

```powershell
flask crear-admin
```

Te pedirá correo, nombre y contraseña (mínimo 8 caracteres). Con ese usuario inicias sesión.

### 6. Compilar la app y ejecutar

Necesitas además **Flutter** instalado (`flutter --version`).

1. Doble clic en **`compilar-app.bat`**: compila la app web. Solo hace falta la primera vez y
   cada vez que cambie el código de `mobile/`.
2. Doble clic en **`iniciar.bat`**: enciende el servidor y abre **http://127.0.0.1:5000** con la
   pantalla de login. Para apagarlo, cierra la ventana negra.

Flask entrega la app y la API desde la misma dirección. Para comprobar solo la API:
http://127.0.0.1:5000/api/health debe responder con la versión de MySQL y los 6 roles.

**Para programar la app** con recarga instantánea, en vez de compilar: deja `iniciar.bat`
abierto y en otra terminal ejecuta `cd mobile` y luego `flutter run -d chrome`.

### Publicar con un enlace (ngrok)

Para que el equipo o el docente abran StockPot desde su celular o PC:

1. Instala [ngrok](https://ngrok.com/download) y vincula tu cuenta una sola vez:
   `ngrok config add-authtoken <tu-token>` (el token está en dashboard.ngrok.com).
2. Cierra `iniciar.bat` si está abierto.
3. Doble clic en **`publicar.bat`**: abre el servidor de producción (Waitress, **sin modo debug**)
   y ngrok. Comparte el enlace `https://...` que aparece en **Forwarding**.
4. Para dejar de publicar, cierra las dos ventanas.

**Enlace fijo (opcional):** reclama tu dominio gratuito en dashboard.ngrok.com → *Domains* y
escríbelo en un archivo `ngrok-dominio.txt` junto a `publicar.bat` (solo el dominio, por ejemplo
`mi-stockpot.ngrok-free.app`). Así el enlace no cambia cada vez.

> ⚠️ Mientras el enlace esté activo, cualquiera que lo tenga puede ver la pantalla de login.
> Usa contraseñas fuertes y cierra `publicar.bat` cuando no lo estén usando.

### 7. Correr las pruebas

```powershell
pytest -v
```

Las pruebas usan una base SQLite temporal en memoria: no tocan tu base MySQL.

---

## API disponible

Todas las rutas, excepto `login` y `health`, requieren el encabezado
`Authorization: Bearer <token>`.

| Método | Ruta | Requisito | Permiso |
|---|---|---|---|
| GET | `/api/health` | Estado de la API y de la base de datos | — |
| POST | `/api/auth/login` | RF-01.4 Iniciar sesión | — |
| GET | `/api/auth/me` | Usuario de la sesión | Sesión iniciada |
| GET | `/api/usuarios?q=` | RF-01.2 Consultar usuarios | `usuarios.ver` |
| GET | `/api/usuarios/<id>` | RF-01.2 Detalle de un usuario | `usuarios.ver` |
| POST | `/api/usuarios` | RF-01.1 Registrar usuarios | `usuarios.gestionar` |
| PUT | `/api/usuarios/<id>` | RF-01.3 Modificar usuarios | `usuarios.gestionar` |
| PATCH | `/api/usuarios/<id>/rol` | RF-01.5 Asignar roles | `roles.gestionar` |
| GET | `/api/roles` | RF-01.6 Roles con sus permisos | `usuarios.ver` |
| GET | `/api/permisos` | RF-01.6 Permisos disponibles | `roles.gestionar` |
| PUT | `/api/roles/<id>/permisos` | RF-01.6 Gestionar permisos de un rol | `roles.gestionar` |

Códigos de respuesta: `200/201` correcto · `401` sin sesión · `403` sin permiso ·
`404` no existe · `409` conflicto (duplicado o regla de negocio) · `422` datos inválidos.

---

## Cómo trabajamos (GitFlow)

| Rama | Para qué |
|---|---|
| `main` | Versiones entregadas, una por iteración terminada |
| `develop` | Integración del trabajo del equipo |
| `feature/RF-XX-nombre` | Un requisito o módulo; sale de `develop` y vuelve por Pull Request |

```powershell
git checkout develop
git pull
git checkout -b feature/RF-02-proveedores
# ... programar, probar ...
git add .
git commit -m "feat(proveedores): registrar proveedores [RF-02.1]"
git push -u origin feature/RF-02-proveedores
```

Después abre un **Pull Request hacia `develop`** en GitHub para que otro integrante lo revise.

**Mensajes de commit:** `tipo(módulo): qué hace [RF-XX.X]`. Tipos: `feat` (funcionalidad),
`fix` (corrección), `test` (pruebas), `docs` (documentación), `db` (scripts SQL).

**Antes de cada Pull Request:**
- [ ] `pytest` pasa completo.
- [ ] Cada ruta nueva indica en su docstring el `RF-XX.X` que implementa.
- [ ] Cada requisito nuevo tiene al menos un caso de prueba `CP-XX.X-n`.
- [ ] Si cambiaste tablas, actualizaste `database/01_schema.sql` **y** `backend/app/models/`.
