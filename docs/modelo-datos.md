# Modelo de datos — StockPot

Diagrama entidad-relación de la base `stockpot` (MySQL 8.4), generado a partir de
[`database/01_schema.sql`](../database/01_schema.sql). Si cambia el script, se actualiza
también este diagrama.

**Convenciones:** `PK` llave primaria · `FK` llave foránea · `UK` valor único.

## Iteración 1 — Usuarios y roles + Proveedores

![Diagrama entidad-relación de la Iteración 1](img/modelo-datos-iteracion1.svg)

<details>
<summary>Código fuente del diagrama (Mermaid)</summary>

La imagen de arriba se genera a partir de este código. Si cambian las tablas, se edita
este bloque y se vuelve a generar la imagen.

```mermaid
erDiagram
    ROLES ||--o{ USUARIOS : "tiene"
    ROLES ||--o{ ROL_PERMISOS : "agrupa"
    PERMISOS ||--o{ ROL_PERMISOS : "se asigna en"
    PROVEEDORES ||--o{ PROVEEDOR_INSUMOS : "suministra"
    INSUMOS ||--o{ PROVEEDOR_INSUMOS : "es suministrado en"
    PROVEEDORES ||--o{ ORDENES_COMPRA : "recibe"
    USUARIOS ||--o{ ORDENES_COMPRA : "registra"
    ORDENES_COMPRA ||--|{ DETALLE_ORDEN_COMPRA : "contiene"
    INSUMOS ||--o{ DETALLE_ORDEN_COMPRA : "se compra en"

    ROLES {
        int id PK
        varchar nombre UK
        varchar descripcion
        boolean activo
        datetime created_at
    }
    PERMISOS {
        int id PK
        varchar codigo UK "modulo.accion"
        varchar modulo
        varchar descripcion
    }
    ROL_PERMISOS {
        int rol_id PK, FK
        int permiso_id PK, FK
    }
    USUARIOS {
        int id PK
        varchar nombre
        varchar apellido
        varchar email UK
        varchar password_hash "cifrada"
        varchar telefono
        int rol_id FK
        boolean activo
        datetime ultimo_acceso
        datetime created_at
        datetime updated_at
    }
    PROVEEDORES {
        int id PK
        varchar nit UK
        varchar razon_social
        varchar contacto
        varchar telefono
        varchar email
        varchar direccion
        boolean activo
        datetime created_at
        datetime updated_at
    }
    INSUMOS {
        int id PK
        varchar codigo UK
        varchar nombre
        enum unidad_medida "KG, G, L, ML, UNIDAD"
        decimal stock_actual "mayor o igual a 0"
        boolean activo
        datetime created_at
    }
    PROVEEDOR_INSUMOS {
        int proveedor_id PK, FK
        int insumo_id PK, FK
        decimal precio_referencia
    }
    ORDENES_COMPRA {
        int id PK
        varchar codigo UK "OC-000001"
        int proveedor_id FK
        int usuario_id FK
        datetime fecha_orden
        date fecha_entrega_estimada
        datetime fecha_recepcion
        enum estado "PENDIENTE, ENVIADA, RECIBIDA, CANCELADA"
        decimal total
        varchar observaciones
        datetime created_at
        datetime updated_at
    }
    DETALLE_ORDEN_COMPRA {
        int id PK
        int orden_compra_id FK
        int insumo_id FK
        decimal cantidad "mayor que 0"
        decimal precio_unitario
        decimal subtotal
    }
```

</details>

## Multiplicidades

| Relación | Multiplicidad | Lectura |
|---|---|---|
| Rol – Usuario | 1 — 0..* | Un rol lo tienen cero o muchos usuarios; cada usuario tiene exactamente un rol |
| Rol – Permiso | * — * | Un rol tiene muchos permisos y un permiso puede estar en muchos roles (tabla `rol_permisos`) |
| Proveedor – Insumo | * — * | Un proveedor suministra varios insumos y un insumo puede comprarse a varios proveedores (tabla `proveedor_insumos`) |
| Proveedor – Orden de compra | 1 — 0..* | Un proveedor recibe cero o muchas órdenes; cada orden es para un solo proveedor |
| Usuario – Orden de compra | 1 — 0..* | Un usuario registra cero o muchas órdenes; cada orden la registra un solo usuario |
| Orden de compra – Detalle | 1 — 1..* | Una orden tiene una o más líneas; cada línea pertenece a una sola orden |
| Insumo – Detalle | 1 — 0..* | Un insumo aparece en cero o muchas líneas de compra; cada línea es de un solo insumo |

## Correspondencia ILF → tablas

| ILF (Análisis de Puntos de Función) | Tablas | Iteración |
|---|---|---|
| ILF01 Usuarios | `usuarios` | 1 |
| ILF02 Roles y permisos | `roles`, `permisos`, `rol_permisos` | 1 |
| ILF03 Proveedores | `proveedores`, `proveedor_insumos` | 1 |
| ILF04 Insumos | `insumos` (versión básica; se completa en la Iteración 2) | 1 → 2 |
| ILF17 Órdenes de compra | `ordenes_compra`, `detalle_orden_compra` | 1 |
