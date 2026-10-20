# StockPot

Sistema de gestión para restaurantes pequeños y medianos: controla el inventario de insumos,
gestiona los pedidos, comunica las áreas de atención y cocina, y genera información sobre
el consumo y las ventas.

```
Página web (HTML/CSS/JS)  ──HTTP/JSON + token JWT──►  API Flask (Python)  ──SQLAlchemy──►  MySQL 8.4
frontend/                                              backend/                             database/
```

| Capa | Tecnología |
|---|---|
| Base de datos | MySQL 8.4 LTS + MySQL Workbench |
| Backend (API REST) | Python 3.11, Flask, SQLAlchemy, Flask-JWT-Extended |
| Presentación (interfaz web) | HTML, CSS y JavaScript (sin frameworks) |
| Pruebas | pytest |
| Control de versiones | Git + GitHub con GitFlow |

## Equipo e iteraciones

| Iteración | Responsable | Módulos | Estado |
|---|---|---|---|
| 1 | Andrés Mateo Puentes | Usuarios y roles (RF-01) · Proveedores y compras (RF-02) | ✅ Terminado |
| 2 | Jhorman Caballero | Inventario (RF-03) · Productos y menú (RF-04) | ✅ Terminado |
| 3 | Yovany Peñaranda | Pedidos (RF-05) · Cocina (RF-06) · Reservas (RF-07) | ⏳ Pendiente (30 %) |
| 4 | Ángel David Rodríguez Vega (líder) | Domicilios (RF-08) · Pagos (RF-09) · Ventas y consumo (RF-10) · Reportes (RF-11) | ✅ Terminado |

**Entrega del 2.º corte (20/10/2026): 70 % del software** = Iteraciones 1, 2 y 4 → 233 de 330 puntos
de función (376 de 515 PFSA). 267 pruebas automáticas aprobadas (41 de ellas unitarias), 95 % de cobertura del backend.

## Gestión del proyecto

| Qué | Dónde |
|---|---|
| Cliente | Restaurante Sexto Sentido Café & Brunch |
| Tablero de tareas | [Jira – proyecto STOC](https://mateopuentes1227.atlassian.net/jira/software/projects/STOC/boards/34) |
| Cronograma | [Cronograma_StockPot.gan](docs/entrega-2do-corte/01_Plan_de_gestion_del_proyecto/Cronograma_StockPot.gan) (GanttProject) · [imagen](docs/entrega-2do-corte/01_Plan_de_gestion_del_proyecto/Cronograma_StockPot.png) |
| Duración | 10/08/2026 – 13/11/2026 · lunes a sábado, sin domingos ni festivos de Colombia |
| Estimación | Puntos de función y PERT ([Excel](docs/entrega-2do-corte/01_Plan_de_gestion_del_proyecto/Puntos_de_Funcion_y_PERT_StockPot.xlsx)) |

Estado del tablero de Jira al 19/10/2026 (166 tareas, una por cada fila del plan PERT):

| Iteración | Listo | En curso | Por hacer | Avance en el cronograma |
|---|---|---|---|---|
| 1 – Mateo | 32 | 0 | 0 | 100 % |
| 2 – Jhorman | 38 | 0 | 0 | 100 % |
| 3 – Yovany | 3 | 21 | 22 | 28 % (análisis y diseño en curso; codificación y pruebas pendientes) |
| 4 – Ángel | 50 | 0 | 0 | 100 % |
| **Total** | **123** | **21** | **22** | |

Hitos: **20/10/2026** entrega parcial del 70 % (2.º corte) · **21/10 – 13/11/2026** Iteración 3
(30 % restante), pruebas de aceptación y entrega final.

## Estructura del proyecto

```
stockpot/
├── database/            Scripts SQL
│   ├── 01_schema.sql    Crea la base y sus 19 tablas (instalación desde cero)
│   ├── 02_seed.sql      Roles y permisos iniciales
│   ├── 03_usuario_app.sql   Usuario de MySQL para la aplicación
│   ├── 04_datos_ejemplo.sql Datos de demostración (insumos, proveedores, carta, clientes)
│   └── 05 a 08_*.sql    Actualizan una base existente sin borrar datos
├── backend/             API Flask
│   ├── app/
│   │   ├── models/      Tablas como clases de Python
│   │   ├── modules/     Un módulo por cada requisito de la EDT (usuarios, inventario, pagos...)
│   │   ├── services/    Reglas compartidas (inventario, órdenes, pagos y ventas)
│   │   └── utils/       Código compartido (permisos, fechas)
│   └── tests/           Pruebas automáticas (casos CP-XX.X-n)
├── frontend/            Interfaz web (la sirve Flask)
│   ├── index.html       Inicio de sesión
│   ├── menu.html        Menú de módulos según el rol
│   ├── *.html           Una pantalla por módulo (usuarios, inventario, domicilios, caja...)
│   ├── css/estilos.css  Diseño de toda la interfaz
│   └── js/              Lógica de cada pantalla (api.js habla con la API)
└── docs/                Documentación (modelo de datos y entregables del 2.º corte)
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
4. *(Opcional)* `database/04_datos_ejemplo.sql`: insumos, proveedores, 8 platos con sus recetas y
   3 clientes de ejemplo. Se puede ejecutar más de una vez sin duplicar datos.

Verifica con `SHOW TABLES FROM stockpot;`: deben salir 19 tablas.

**¿Ya tenías la base creada de antes?** No vuelvas a ejecutar el `01` (borra todo). Ejecuta solo
los scripts de actualización que te falten, en orden: `05_iteracion2_inventario.sql`,
`06_iteracion2_productos.sql`, `07_iteracion4_domicilios.sql` y `08_iteracion4_pagos_ventas.sql`.
Solo agregan columnas y tablas; tus datos se conservan.

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

### 6. Ejecutar

1. Doble clic en **`iniciar.bat`**: enciende **todo de una vez**:
   - el servidor de producción **Waitress** (sin modo debug),
   - el **enlace público de ngrok**, si está instalado; aparece en verde y se copia al portapapeles,
   - y abre **http://127.0.0.1:5000** en tu navegador con la interfaz web.
2. Para apagar todo, cierra la ventana negra del servidor y la de ngrok.

La interfaz web no se compila: al cambiar un archivo de `frontend/`, basta con recargar el
navegador (F5).

> 🔄 **Si cambió algo de Python (`backend/`), cierra la ventana del servidor y vuelve a abrir
> `iniciar.bat`.** El servidor carga el código una sola vez al arrancar; si no lo reinicias, las
> pantallas nuevas muestran *"La ruta de la API no existe"*.

Para comprobar solo la API: http://127.0.0.1:5000/api/health debe responder con la versión de
MySQL y los 6 roles.

### Enlace público con ngrok

1. Instala [ngrok](https://ngrok.com/download) y vincula tu cuenta una sola vez:
   `ngrok config add-authtoken <tu-token>` (el token está en dashboard.ngrok.com).
2. **Enlace fijo (recomendado):** reclama tu dominio gratuito en dashboard.ngrok.com → *Domains*
   y escríbelo en un archivo `ngrok-dominio.txt` junto a `iniciar.bat` (solo el dominio, por ejemplo
   `mi-stockpot.ngrok-free.app`). Si no existe ese archivo, el enlace cambia cada vez.

Quien abra el enlace verá primero una advertencia de ngrok: debe tocar **Visit Site**.

> ⚠️ Mientras `iniciar.bat` esté abierto, cualquiera con el enlace puede ver la pantalla de
> login. Usa contraseñas fuertes y cierra las ventanas cuando no lo estén usando.

### Para programar

- **Backend con recarga automática:** en vez de `iniciar.bat`, ejecuta en `backend`:
  `python run.py` (modo debug, **solo local, nunca con ngrok**).
- **Interfaz web:** edita los archivos de `frontend/` y recarga el navegador (F5). Si no ves
  el cambio, recarga forzando con `Ctrl+F5`.

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
| GET/POST/PUT | `/api/proveedores` · `/api/proveedores/<id>/insumos` · `/compras` | RF-02.1 a RF-02.5 | `proveedores.*` |
| GET/POST/PATCH | `/api/ordenes-compra` · `/<id>/estado` | RF-02.6 a RF-02.8 | `compras.*` |
| GET/POST/PUT | `/api/insumos` · `/api/insumos/<id>/movimientos` | RF-03.1 a RF-03.5, RF-03.7 | `inventario.*` |
| GET | `/api/inventario/existencias` · `/api/inventario/alertas` | RF-03.6 y RF-03.8 | `inventario.ver` |
| GET/POST/PUT/PATCH | `/api/productos` · `/<id>/disponibilidad` | RF-04.1 a RF-04.6 | `productos.*` |
| GET/POST/PUT | `/api/clientes` · `/api/domicilios` (+ `asignar`, `estado`, `entrega`, `historial`) | RF-08.1 a RF-08.8 | `domicilios.*` |
| GET/POST/PATCH | `/api/ordenes/por-cobrar` · `/<id>/cuenta` · `/<id>/pagos` · `/<id>/comprobante` · `/api/pagos` | RF-09.1 a RF-09.7 | `pagos.*` |
| GET/POST | `/api/ventas` · `/mas-vendidos` · `/consumo` | RF-10.1 a RF-10.6 | `ventas.ver` / `pagos.gestionar` |
| GET | `/api/reportes/inventario` · `ventas` · `consumo` · `productos` · `historico` · `estadisticas` | RF-11.1 a RF-11.6 | `reportes.ver` |

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

---

## Documentación del 2.º corte

En [docs/entrega-2do-corte](docs/entrega-2do-corte) están los entregables, organizados según la
sección de procesos técnicos y de soporte de IEEE 1058 (ver su README):

| Carpeta | Contenido |
|---|---|
| `01_Plan_de_gestion_del_proyecto` | Acta de constitución (70 % entregado / 30 % pendiente) · cronograma de GanttProject con el avance de Jira · Excel de puntos de función y PERT · enlace de Jira |
| `02_Metodos_herramientas_y_tecnicas` | Prompts e inteligencia artificial utilizada |
| `03_Verificacion_y_validacion` | Plan de pruebas (casos CRUD) · matriz de criterios de aceptación v1 · informe de pruebas realizadas |
| `04_Aceptacion_del_producto` | Acta de aceptación del cliente (UAT, Formato 2) |
| `05_Demostracion` | Video del recorrido por los módulos del 70 % |
