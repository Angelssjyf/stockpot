-- =====================================================================
--  StockPot - Script 06: actualización para la Iteración 2 (productos y menú)
--  Para bases creadas ANTES de este cambio. NO borra datos: solo agrega.
--  (Si creas la base desde cero con 01_schema.sql, ya incluye todo esto.)
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- ILF06 Productos y platos (RF-04.1 a RF-04.3, RF-04.5 precio, RF-04.6 disponibilidad)
-- Lo que el restaurante vende: platos, bebidas, postres...
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS productos (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    codigo        VARCHAR(30)   NOT NULL UNIQUE,     -- ej: PRD-001
    nombre        VARCHAR(120)  NOT NULL,
    descripcion   VARCHAR(255),
    categoria     ENUM('ENTRADA','PLATO_FUERTE','BEBIDA','POSTRE','ADICIONAL') NOT NULL,
    precio_venta  DECIMAL(12,2) NOT NULL,            -- RF-04.5
    disponible    BOOLEAN       NOT NULL DEFAULT TRUE,  -- RF-04.6 se puede pedir hoy
    activo        BOOLEAN       NOT NULL DEFAULT TRUE,  -- sigue en la carta
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_producto_precio CHECK (precio_venta > 0)
);

-- ---------------------------------------------------------------------
-- ILF07 Recetas / composición (RF-04.4 Asociar insumos a productos)
-- Cuánto de cada insumo lleva UNA porción del producto. Con esto se
-- calcula el costo del plato y, al vender, el consumo de inventario.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recetas (
    producto_id  INT           NOT NULL,
    insumo_id    INT           NOT NULL,
    cantidad     DECIMAL(12,3) NOT NULL,             -- en la unidad del insumo
    PRIMARY KEY (producto_id, insumo_id),            -- un insumo no se repite en la receta
    CONSTRAINT fk_receta_producto FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    CONSTRAINT fk_receta_insumo   FOREIGN KEY (insumo_id)   REFERENCES insumos(id),
    CONSTRAINT chk_receta_cantidad CHECK (cantidad > 0)
);
