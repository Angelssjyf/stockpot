# StockPot — Entrega final (100 %)

Universidad Simón Bolívar, sede Cúcuta · Ingeniería del Software II · Prof. Nataly Duque Páez · 24 de noviembre de 2026

Los documentos están organizados según la sección de **procesos técnicos** del Plan de Gestión de Proyectos de
Software **IEEE 1058**, igual que en el 2.º y el 3.er corte. Incluye toda la documentación del 2.º corte con las
correcciones de la docente, actualizada al 100 %.

| Carpeta | Sección IEEE 1058 | Contenido |
|---|---|---|
| `01_Plan_de_gestion_del_proyecto` | 5. Planes del proceso de gestión (inicio, calendario, control) | **Acta de constitución (Project Charter) v1.0** con el título y los objetivos corregidos, el alcance al 100 %, VAN, TIR y relación beneficio/costo del estudio de viabilidad y **los mockups de las pantallas al final** · **Excel de puntos de función, PERT, COCOMO II y presupuesto** (BAC $205.875.739) · **Cronograma** (GanttProject) al 100 % · **Enlace de Jira** con las 166 tareas en Listo |
| `02_Metodos_herramientas_y_tecnicas` | 6.2 Métodos, herramientas y técnicas | Prompts e IA utilizada |
| `03_Verificacion_y_validacion` | 7.2 Plan de verificación y validación | **Plan de pruebas al 100 %: 88 casos CRUD** (78 del 3.er corte + 10 de Reservas) · **Informe de pruebas realizadas final** (11 módulos, 438 pruebas automatizadas, cobertura del 96 %, 12 defectos cerrados) · **Matriz de criterios de aceptación** (12 criterios aprobados) · **COCOMO II + EVM + SQA** (estimación, valor ganado por corte, matriz de riesgos de calidad y prueba de carga) · **Pruebas de usabilidad con Google Lighthouse** (14 pantallas, celular y escritorio) |
| `04_Aceptacion_del_producto` | 6.4 Plan de aceptación | **Acta de aceptación del cliente (FORMATO 2 – UAT)** con la prueba del 17/11/2026: 21 usuarios externos, 91 % de tareas sin problema y satisfacción de 4,32 de 5 |
| `05_Producto_desarrollado` | 6.3 Plan de infraestructura · producto | **Enlace del despliegue** · guía de despliegue con ngrok · código fuente de la versión entregada (v1.0.0) |
| `05_Demostracion` | Sustentación | **Presentación final** (28 diapositivas en PDF, por los 4 criterios de la rúbrica) · **video promocional** (1 minuto) · **video de demostración** del 2.º corte |

El resto de la estructura técnica está en la raíz del repositorio:

| Sección IEEE 1058 | Dónde está |
|---|---|
| 6.1 Modelo de proceso | Iteraciones incrementales (Scrum) y GitFlow: `README.md` → *Cómo trabajamos* |
| 6.3 Plan de infraestructura | `README.md` → *Instalación* · `iniciar.bat` (Waitress + ngrok) · `docs/despliegue/` |
| 7.1 Gestión de la configuración | Repositorio GitHub: ramas `main` (versiones entregadas), `develop` y una rama por requisito; versión entregada **v1.0.0** |
| 7.3 Documentación del software | `docs/modelo-datos.md` · docstrings `RF-XX.X` en el código · `README.md` → *API disponible* |
| Producto | `database/` (scripts SQL) · `backend/` (API Flask y pruebas automatizadas) · `frontend/` (interfaz web) |

## Resumen del avance

| | Módulos | PF transaccionales |
|---|---|---|
| **70 % — 2.º corte** | RF-01 Usuarios, RF-02 Proveedores, RF-03 Inventario, RF-04 Productos, RF-08 Domicilios, RF-09 Pagos, RF-10 Ventas, RF-11 Reportes | 233 de 330 (70,6 %) |
| **15 % — 3.er corte** | RF-05 Gestión de pedidos (en mesa) y RF-06 Gestión de cocina | 68 de 330 (20,6 %) |
| **15 % — entrega final** | **RF-07 Gestión de reservas** | 29 de 330 (8,8 %) |

Acumulado: **330 de 330 PF (100 %)**. Los 11 módulos están terminados, probados y aceptados por los usuarios.

## Pruebas (100 %)

- **Plan de pruebas (88 casos):** 53 de los módulos del 70 %, 25 de Pedidos y Cocina y **10 de Reservas** (casos 79 a 88).
  Cada caso trae precondiciones, pasos, resultado esperado y espacio para la evaluación de la docente.
- **Pruebas automatizadas:** 438 aprobadas (cobertura del 96 % del backend), con pruebas de seguridad por rol en cada
  módulo. Se ejecutan con `pytest` en la carpeta `backend` y en GitHub Actions en cada envío.
- **Aceptación de usuario (UAT):** 21 trabajadores de restaurante hicieron 12 tareas reales: 58 de 64 sin problema
  (91 %), satisfacción 4,32 de 5. El defecto que encontraron (cobro mixto) se corrigió y quedó cubierto por la prueba
  CP-09.1-4.
- **Usabilidad y carga:** Lighthouse 100 en rendimiento, accesibilidad, buenas prácticas y SEO en las 14 pantallas;
  con 50 usuarios simultáneos, 1.000 peticiones sin errores (percentil 95 de 0,48 s).

## Proyecto desarrollado (100 %)

- **Código fuente:** <https://github.com/Angelssjyf/stockpot> (rama `main`, versión `v1.0.0`). El archivo
  `StockPot_Codigo_Fuente_v1.0.0.zip` de la carpeta 05 es la misma versión.
- **En línea:** <https://shorts-undermost-avenue.ngrok-free.dev>, publicado con ngrok desde el equipo del proyecto
  (opción aprobada por la docente). Para la demostración se abre con `iniciar.bat`.
