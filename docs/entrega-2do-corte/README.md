# StockPot — Entregables del 2.º corte (70 %)

Universidad Simón Bolívar, sede Cúcuta · Ingeniería del Software II · 20 de octubre de 2026

Los documentos están organizados según la estructura del **Plan de Gestión de Proyectos de
Software IEEE 1058** (secciones de procesos de gestión, procesos técnicos y procesos de soporte).

| Carpeta | Sección IEEE 1058 | Contenido |
|---|---|---|
| `01_Plan_de_gestion_del_proyecto` | 5. Planes del proceso de gestión (inicio, calendario, control) | Acta de constitución (Project Charter) con el **70 % entregado y el 30 % pendiente** · Cronograma de GanttProject (`.gan`, con imagen `.png` para verlo sin instalar nada) con el avance real tomado de Jira · Excel de puntos de función y PERT con la hoja **Avance 2.º corte** · Enlace de Jira |
| `02_Metodos_herramientas_y_tecnicas` | 6.2 Métodos, herramientas y técnicas | Prompts utilizados y herramientas de IA (Claude Code y ChatGPT) |
| `03_Verificacion_y_validacion` | 7.2 Plan de verificación y validación | Plan de pruebas (casos CRUD, formato de la docente) · Matriz de criterios de aceptación v1 · Informe de pruebas realizadas |
| `04_Aceptacion_del_producto` | 6.4 Plan de aceptación del producto | FORMATO 2: Acta de Aceptación del Cliente (UAT), lista para firmar en la sustentación |

El resto de la estructura técnica está en la raíz del repositorio:

| Sección IEEE 1058 | Dónde está |
|---|---|
| 6.1 Modelo de proceso | Iteraciones incrementales (Scrum) y GitFlow: `README.md` → *Cómo trabajamos* |
| 6.3 Plan de infraestructura | `README.md` → *Instalación* · `iniciar.bat` · `backend/requirements.txt` |
| 7.1 Gestión de la configuración | Repositorio GitHub (ramas `main`, `develop`, `feature/RF-XX-…`) |
| 7.3 Documentación del software | `docs/modelo-datos.md` · docstrings `RF-XX.X` en el código |
| Producto | `database/` (scripts SQL) · `backend/` (API Flask y 226 pruebas) · `frontend/` (interfaz web) |

## Resumen del 70 %

| | Módulos | PF transaccionales |
|---|---|---|
| **Entregado (70 %)** | RF-01, RF-02, RF-03, RF-04, RF-08, RF-09, RF-10, RF-11 | 233 de 330 (70,6 %) |
| **Pendiente (30 %)** | RF-05 Pedidos en mesa, RF-06 Cocina, RF-07 Reservas | 97 de 330 (29,4 %) |

## Video de demostración

`05_Demostracion/StockPot_Demostracion_70.mp4` (4 min): recorrido por los 8 módulos entregados, en orden
de uso real: inicio de sesión → usuarios y roles → proveedores y orden de compra (al recibirla sube el
inventario) → inventario (alertas y entradas) → menú con recetas → domicilio de principio a fin → cobro
en dos pagos con comprobante y venta de mostrador → ventas y consumo automático → reportes y estadísticas.
