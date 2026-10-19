-- =====================================================================
--  StockPot - Script 05: actualización para la Iteración 2 (inventario)
--  Para bases creadas ANTES de este cambio. NO borra datos: solo agrega.
--  (Si creas la base desde cero con 01_schema.sql, ya incluye todo esto.)
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- RF-03.7 Niveles mínimos de stock y costo de cada insumo
-- ---------------------------------------------------------------------
ALTER TABLE insumos
    ADD COLUMN stock_minimo   DECIMAL(12,3) NOT NULL DEFAULT 0 AFTER stock_actual,
    ADD COLUMN costo_unitario DECIMAL(12,2) NOT NULL DEFAULT 0 AFTER stock_minimo;

-- ---------------------------------------------------------------------
-- ILF05 Movimientos de inventario (RF-03.4 entradas, RF-03.5 salidas)
-- Cada cambio de stock deja un registro: qué, cuánto, por qué, quién y cuándo.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    insumo_id         INT           NOT NULL,
    tipo              ENUM('ENTRADA','SALIDA') NOT NULL,
    motivo            ENUM('COMPRA','AJUSTE','DEVOLUCION','CONSUMO','MERMA') NOT NULL,
    cantidad          DECIMAL(12,3) NOT NULL,
    stock_resultante  DECIMAL(12,3) NOT NULL,       -- stock después del movimiento
    orden_compra_id   INT,                          -- si viene de una compra recibida
    usuario_id        INT           NOT NULL,       -- quién lo registró
    observacion       VARCHAR(255),
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mov_insumo  FOREIGN KEY (insumo_id)       REFERENCES insumos(id),
    CONSTRAINT fk_mov_oc      FOREIGN KEY (orden_compra_id) REFERENCES ordenes_compra(id),
    CONSTRAINT fk_mov_usuario FOREIGN KEY (usuario_id)      REFERENCES usuarios(id),
    CONSTRAINT chk_mov_cantidad CHECK (cantidad > 0),
    INDEX idx_mov_fecha (created_at)
);
