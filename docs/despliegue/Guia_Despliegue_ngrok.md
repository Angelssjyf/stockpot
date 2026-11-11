# Despliegue de StockPot con ngrok

StockPot se publica en la web desde el computador del equipo: **Waitress** sirve la aplicación y
**ngrok** crea un enlace público con HTTPS para entrar desde cualquier celular o computador.
Es la opción aprobada por la docente para el proyecto de aula.

## Arquitectura

```
Celular o computador (cualquier red)
        │  HTTPS  https://DOMINIO.ngrok-free.app
        ▼
   Servidores de ngrok (túnel cifrado)
        │
        ▼
PC del equipo ── ngrok (agente) ──► Waitress 127.0.0.1:5000 ──► Flask (API /api + interfaz web)
                                                                   │
                                                                   ▼
                                                     MySQL 8.4 (solo en el PC: 127.0.0.1:3306)
```

- Solo se publica el puerto **5000** de la aplicación. **MySQL no se expone**: solo lo usa la aplicación dentro del PC.
- **Waitress** es un servidor de producción: no tiene el modo *debug* de Flask, que nunca debe quedar público.
- La interfaz (HTML, CSS y JavaScript) y la API salen de la misma dirección.

## Requisitos (una sola vez)

1. StockPot instalado y funcionando en el PC (pasos 1 a 5 del [README](../../README.md)): base MySQL, `backend/.env` y usuario administrador.
2. Cuenta gratuita en <https://ngrok.com> y el programa instalado.
3. Vincular la cuenta en una terminal (el token está en *dashboard.ngrok.com → Your Authtoken*):

```powershell
ngrok config add-authtoken TU_TOKEN
```

4. **Dominio fijo gratuito:** en *dashboard.ngrok.com → Domains* reclamar el dominio gratis y escribirlo, solo el dominio, en el archivo `ngrok-dominio.txt` junto a `iniciar.bat` (por ejemplo `mi-stockpot.ngrok-free.app`). Así el enlace no cambia cada vez.

> `ngrok-dominio.txt` y `backend/.env` no se suben a GitHub.

## Publicar

1. Doble clic en **`iniciar.bat`**. Abre dos ventanas:
   - **StockPot – servidor** (Waitress), con el enlace público en verde, ya copiado al portapapeles;
   - **StockPot – ngrok**, con el estado del túnel (*Session Status: online*).
2. Comparte el enlace `https://DOMINIO.ngrok-free.app`.
3. La primera vez, ngrok muestra una página de advertencia: tocar **Visit Site**.

**Para apagar:** cerrar las dos ventanas. El enlace deja de funcionar al instante.

## Comprobar que quedó en línea

- [ ] `https://DOMINIO.ngrok-free.app/api/health` responde `"api": "ok"` y la versión de MySQL.
- [ ] Iniciar sesión desde un **celular con datos móviles**, no con el wifi del PC.
- [ ] Tomar un pedido, enviarlo a cocina y cobrarlo.
- [ ] En la ventana de ngrok aparecen las peticiones (`GET /`, `POST /api/auth/login`…).

## Seguridad mientras está publicado

- Cualquiera con el enlace ve la pantalla de inicio de sesión: usar **contraseñas fuertes** y no compartir usuarios.
- Las sesiones se cierran solas tras un rato sin uso, y la pantalla se puede **bloquear** con el candado. Cobrar, anular pagos y sacar inventario piden el **PIN** de quien tiene la sesión.
- Varios intentos fallidos de inicio de sesión bloquean ese correo por unos minutos.
- **No** usar `python run.py` (modo debug) con ngrok.
- Cerrar las ventanas cuando no se esté usando.

## Actualizar a una versión nueva

1. Cerrar las dos ventanas.
2. En una terminal, en la carpeta del proyecto:

```powershell
git checkout main
git pull
backend\.venv\Scripts\pip install -r backend\requirements.txt
```

3. Si la versión trae scripts SQL nuevos en `database/`, ejecutarlos en MySQL Workbench en orden numérico (solo agregan; no borran datos).
4. Abrir de nuevo `iniciar.bat`.

## Copia de seguridad de la base

En MySQL Workbench: *Server → Data Export* → base `stockpot` → *Export to Self-Contained File* → guardar en `database/respaldos/stockpot_AAAA-MM-DD.sql`. Esa carpeta no se sube a GitHub.

## Problemas frecuentes

| Qué pasa | Qué hacer |
|---|---|
| «El puerto 5000 ya está en uso» | StockPot ya está abierto en otra ventana, u otro programa usa el puerto (por ejemplo, el software de cámaras). Cerrarlo y volver a abrir `iniciar.bat`. |
| El enlace muestra *ERR_NGROK_…* o no carga | La ventana de ngrok se cerró o perdió internet: cerrar todo y abrir `iniciar.bat` otra vez. |
| «La ruta de la API no existe» después de actualizar | El servidor tiene el código viejo: cerrar la ventana del servidor y abrir `iniciar.bat`. |
| «La sesión se cerró…» | Pasó el tiempo sin uso o se cerró desde otro lado: iniciar sesión de nuevo. |
| ngrok pide verificar la cuenta o el dominio | Entrar a dashboard.ngrok.com con la cuenta del equipo y revisar el aviso. |

## Limitaciones

- El enlace funciona **solo mientras el PC esté prendido** y con `iniciar.bat` abierto.
- El plan gratuito de ngrok muestra la página de advertencia la primera vez y limita el tráfico mensual; alcanza de sobra para la demostración y las pruebas de aceptación.
