# StockPot — Entregables del 3.er corte (avance 70 % + 15 %)

Universidad Simón Bolívar, sede Cúcuta · Ingeniería del Software II · Prof. Nataly Duque Páez · 13 de noviembre de 2026

Los documentos están organizados según la sección de **procesos técnicos** del Plan de Gestión de Proyectos de
Software **IEEE 1058**, igual que en la entrega del 2.º corte.

| Carpeta | Sección IEEE 1058 | Contenido |
|---|---|---|
| `01_Plan_de_gestion_del_proyecto` | 5. Planes del proceso de gestión (inicio, calendario, control) | **Acta de constitución (Project Charter) v0.3** con el **70 % entregado en el 2.º corte, el 15 % entregado en este corte y el 15 % pendiente**, cronograma de hitos actualizado y evidencias |
| `03_Verificacion_y_validacion` | 7.2 Plan de verificación y validación | **Plan de pruebas al 75 % (50 % + 25 %)**: los 33 casos CRUD del 2.º corte y **25 casos nuevos** de Pedidos y Cocina (58 en total, formato de la docente) · **Informe de pruebas automatizadas del 15 %** (43 pruebas de pytest, todas aprobadas) |
| `05_Producto_desarrollado` | 6.3 Plan de infraestructura · producto | **Proyecto desarrollado (70 % + 15 %)**: guía de despliegue con ngrok y el código fuente de la versión entregada |

Siguen vigentes, sin cambios, los documentos del 2.º corte que no hacen parte de esta entrega (en
[`../entrega-2do-corte`](../entrega-2do-corte)): cronograma y Excel de puntos de función (5), métodos, herramientas e
IA utilizada (6.2), matriz de criterios de aceptación y acta UAT (6.4).

El resto de la estructura técnica está en la raíz del repositorio:

| Sección IEEE 1058 | Dónde está |
|---|---|
| 6.1 Modelo de proceso | Iteraciones incrementales (Scrum) y GitFlow: `README.md` → *Cómo trabajamos* |
| 6.3 Plan de infraestructura | `README.md` → *Instalación* · `iniciar.bat` (Waitress + ngrok) · `docs/despliegue/` |
| 7.1 Gestión de la configuración | Repositorio GitHub: ramas `main` (versiones entregadas), `develop` y una rama por requisito; versión entregada **v0.8.3** |
| 7.3 Documentación del software | `docs/modelo-datos.md` · docstrings `RF-XX.X` en el código · `README.md` → *API disponible* |
| Producto | `database/` (scripts SQL) · `backend/` (API Flask y pruebas automatizadas) · `frontend/` (interfaz web) |

## Resumen del avance

| | Módulos | PF transaccionales |
|---|---|---|
| **70 % — entregado en el 2.º corte** | RF-01 Usuarios, RF-02 Proveedores, RF-03 Inventario, RF-04 Productos, RF-08 Domicilios, RF-09 Pagos, RF-10 Ventas, RF-11 Reportes | 233 de 330 (70,6 %) |
| **15 % — entregado en este corte** | **RF-05 Gestión de pedidos (en mesa)** y **RF-06 Gestión de cocina** | 68 de 330 (20,6 %) |
| **15 % — pendiente (entrega final)** | RF-07 Gestión de reservas | 29 de 330 (8,8 %) |

Acumulado: **301 de 330 PF (91,2 %)**. Pedidos y Cocina se entregan juntos porque son un solo flujo: el mesero toma
el pedido en la mesa, lo confirma y lo envía a cocina; la cocina lo ve por orden de llegada, lo prepara y avisa cuando
está listo; el mesero lo entrega y se cobra en caja (RF-09).

## Pruebas (50 % + 25 %)

- **Plan de pruebas al 75 %:** casos 1 a 33 (2.º corte) + casos 34 a 58 (este corte): 15 de Gestión de pedidos y 10 de
  Gestión de cocina, con precondiciones, pasos, resultado esperado y espacio para la evaluación de la docente.
- **Pruebas automatizadas:** 402 aprobadas en todo el sistema (95 % de cobertura del backend); 43 de ellas verifican
  Pedidos (33) y Cocina (10). Se ejecutan con `pytest` en la carpeta `backend` (ver el informe).

## Proyecto desarrollado (70 % + 15 %)

- **Código fuente:** <https://github.com/Angelssjyf/stockpot> (rama `main`, versión `v0.8.3`). El archivo
  `StockPot_Codigo_Fuente_v0.8.3.zip` de esta carpeta es la misma versión.
- **En línea:** publicado con ngrok desde el equipo del proyecto, opción aprobada por la docente (ver la guía de
  despliegue). Para la demostración se abre con `iniciar.bat`.
