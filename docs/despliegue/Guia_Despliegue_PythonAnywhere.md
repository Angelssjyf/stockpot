# Despliegue de StockPot en PythonAnywhere (gratis)

StockPot queda publicado en `https://USUARIO.pythonanywhere.com`, con su propia base MySQL en la nube.
En esta guía, **USUARIO** es el nombre de usuario que elijas al crear la cuenta (por ejemplo `stockpot`).

> **Reglas de seguridad**
> - Las contraseñas (cuenta, MySQL, administrador) y la `SECRET_KEY` las escribes **tú** directamente en PythonAnywhere. No se mandan por chat ni se suben a GitHub.
> - El archivo `.env` nunca se sube a GitHub.
> - En la nube **no** se usa `python run.py` (es el modo de desarrollo con *debug*).

**Tiempo aproximado:** 40 minutos.

---

## Paso 1. Crear la cuenta

1. Entra a <https://www.pythonanywhere.com> → **Pricing & signup** → **Create a Beginner account** (gratis).
2. Elige el nombre de usuario (será parte de la dirección: `USUARIO.pythonanywhere.com`), el correo del proyecto y una contraseña.
3. Confirma el correo.

## Paso 2. Crear la base de datos MySQL

1. Pestaña **Databases**.
2. En **MySQL password** escribe una contraseña nueva para la base y pulsa **Set MySQL password**. Guárdala; la necesitas en el paso 5.
3. En **Create a database** escribe `stockpot` y pulsa **Create**. La base queda con el nombre `USUARIO$stockpot`.
4. Anota los datos que aparecen arriba: **Database host address** (`USUARIO.mysql.pythonanywhere-services.com`) y **Username** (`USUARIO`).

## Paso 3. Descargar el código

1. Pestaña **Consoles** → **Bash**.
2. Escribe (una línea a la vez):

```bash
git clone https://github.com/Angelssjyf/stockpot.git
cd stockpot
git checkout main
```

## Paso 4. Crear el entorno virtual e instalar las dependencias

En la misma consola Bash:

```bash
mkvirtualenv --python=/usr/bin/python3.11 stockpot
pip install -r ~/stockpot/backend/requirements.txt
```

Tarda unos minutos. Al terminar, la consola muestra `(stockpot)` al inicio de la línea.

## Paso 5. Crear el archivo `.env` (la configuración secreta)

1. Genera la clave secreta. En la consola Bash:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

   Copia el resultado (64 letras y números).

2. Pestaña **Files** → entra a `stockpot/backend/` → en **New file** escribe `.env` → **New file**.
3. Pega esto y reemplaza lo que está en MAYÚSCULAS:

```
DB_HOST=USUARIO.mysql.pythonanywhere-services.com
DB_PORT=3306
DB_NAME='USUARIO$stockpot'
DB_USER=USUARIO
DB_PASSWORD=LA_CONTRASEÑA_DE_MYSQL_DEL_PASO_2
DB_TIME_ZONE=-05:00
SECRET_KEY=LA_CLAVE_QUE_GENERASTE
```

   - `DB_NAME` va entre comillas sencillas por el signo `$`.
   - `DB_TIME_ZONE=-05:00` hace que MySQL use la hora de Colombia (el servidor está en hora UTC).

4. Pulsa **Save**.

## Paso 6. Crear las tablas y los datos iniciales

1. Pestaña **Databases** → en la lista, pulsa sobre **`USUARIO$stockpot`**. Se abre la consola de MySQL.
2. Escribe (cambia USUARIO):

```sql
source /home/USUARIO/stockpot/database/nube_1_instalar.sql;
```

   Debe terminar sin líneas que digan `ERROR`. Crea las 26 tablas, el restaurante 1, los roles, los permisos y los códigos de incidencia.

3. **Opcional**, solo si quieres los datos de ejemplo para la demostración (insumos, proveedores, productos, mesas):

```sql
source /home/USUARIO/stockpot/database/nube_2_datos_ejemplo.sql;
```

4. Comprueba:

```sql
SELECT nombre FROM roles;
```

   Deben salir los 6 roles del restaurante y `SUPERADMIN`. Escribe `exit` para salir.

> Si aparece un error, **no repitas el paso**: copia el mensaje de error (no contraseñas) y revísalo antes de seguir.

## Paso 7. Crear la aplicación web

1. Pestaña **Web** → **Add a new web app** → **Next**.
2. Elige **Manual configuration** (no "Flask") → **Python 3.11** → **Next**.
3. En la página de la aplicación, sección **Code**:
   - **Source code:** `/home/USUARIO/stockpot/backend`
   - **Working directory:** `/home/USUARIO/stockpot/backend`
4. Sección **Virtualenv:** escribe `/home/USUARIO/.virtualenvs/stockpot` y confirma.
5. Sección **Code** → abre el enlace del **WSGI configuration file** (`/var/www/USUARIO_pythonanywhere_com_wsgi.py`).
   **Borra todo** lo que tiene y deja solo esto (cambia USUARIO):

```python
import sys

ruta = "/home/USUARIO/stockpot/backend"
if ruta not in sys.path:
    sys.path.insert(0, ruta)

from wsgi import application  # noqa: E402,F401
```

   Pulsa **Save**.

6. **Opcional, para que cargue más rápido** — sección **Static files**, agrega:

| URL     | Directory                                |
|---------|------------------------------------------|
| `/css/` | `/home/USUARIO/stockpot/frontend/css/`   |
| `/js/`  | `/home/USUARIO/stockpot/frontend/js/`    |

7. Sección **Security:** activa **Force HTTPS**.
8. Arriba, pulsa el botón verde **Reload USUARIO.pythonanywhere.com**.

## Paso 8. Crear los usuarios iniciales

En la consola **Bash** (pestaña Consoles):

```bash
workon stockpot
cd ~/stockpot/backend
flask crear-admin
```

Te pide correo, nombre, apellido y contraseña del administrador del restaurante (la contraseña no se ve al escribirla; es normal).

Si vas a administrar varios restaurantes, crea también el súper administrador (contraseña de 12 caracteres o más):

```bash
flask crear-superadmin
```

## Paso 9. Probar

1. Abre `https://USUARIO.pythonanywhere.com`.
2. Comprueba que la API y la base responden: `https://USUARIO.pythonanywhere.com/api/health` debe mostrar `"api": "ok"` y la versión de MySQL.
3. Inicia sesión con el administrador del paso 8 y revisa:
   - [ ] El menú muestra «StockPot Restaurante».
   - [ ] Crear un insumo, un producto con receta y una mesa.
   - [ ] Tomar un pedido, enviarlo a cocina y cobrarlo (pedirá crear el PIN).
   - [ ] La hora del pedido y de la venta es la hora de Colombia.
   - [ ] Bloquear la pantalla con el candado y desbloquear con el PIN.
   - [ ] Abrirlo desde un celular con datos móviles (no desde el wifi de la casa).

Si algo falla, en la pestaña **Web** están los registros: **Error log** (errores de Python) y **Server log**.

---

## Actualizar a una versión nueva

Cuando haya cambios en GitHub (rama `main`):

```bash
workon stockpot
cd ~/stockpot
git pull
pip install -r backend/requirements.txt
```

Luego, en la pestaña **Web**, pulsa **Reload**. Si la versión nueva trae un script SQL de cambios, se ejecuta en la consola MySQL antes del Reload.

## Mantener la cuenta gratis activa

- La aplicación gratis se apaga si no se renueva: en la pestaña **Web**, pulsa **Run until 3 months from today** al menos una vez cada 3 meses (PythonAnywhere avisa por correo).
- La cuenta gratis no tiene copias de seguridad automáticas de MySQL. Para guardar una copia, en la consola Bash:

```bash
mysqldump -u USUARIO -h USUARIO.mysql.pythonanywhere-services.com --no-tablespaces 'USUARIO$stockpot' > ~/respaldo_stockpot.sql
```

  (pide la contraseña de MySQL). Luego descarga el archivo desde la pestaña **Files**.

## Arquitectura del despliegue

```
Navegador (computador o celular)
        │  HTTPS
        ▼
PythonAnywhere ── servidor web (uWSGI) ── wsgi.py ── Flask (API /api y la interfaz web)
                                                        │
                                                        ▼
                                          MySQL 8 (USUARIO$stockpot)
```

- La interfaz (HTML, CSS y JavaScript) y la API salen del mismo servidor y la misma dirección.
- Las contraseñas, los PIN y la `SECRET_KEY` quedan cifrados o en el `.env` del servidor.
- En el computador del equipo, `iniciar.bat` (Waitress + ngrok) sigue sirviendo como respaldo para demostraciones.
