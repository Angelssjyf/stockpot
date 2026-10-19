-- =====================================================================
--  StockPot - Script 08: actualización para la Iteración 4 (pagos y ventas)
--  Para bases creadas ANTES de este cambio. NO borra datos: solo agrega.
--  (Si creas la base desde cero con 01_schema.sql, ya incluye todo esto.)
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- ILF14 Pagos (RF-09.1 a RF-09.7). Una orden se puede pagar en partes y
-- con varios métodos; cuando lo pagado completa el total, se registra la venta.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    orden_id    INT           NOT NULL,                -- RF-09.5 pago asociado al pedido
    metodo      ENUM('EFECTIVO','TARJETA','TRANSFERENCIA') NOT NULL,   -- RF-09.2
    monto       DECIMAL(14,2) NOT NULL,                -- lo que abona a la cuenta
    recibido    DECIMAL(14,2),                         -- efectivo entregado por el cliente
    cambio      DECIMAL(14,2) NOT NULL DEFAULT 0,      -- recibido - monto
    referencia  VARCHAR(60),                           -- n.º de aprobación o de transferencia
    estado      ENUM('APROBADO','ANULADO') NOT NULL DEFAULT 'APROBADO',
    usuario_id  INT           NOT NULL,                -- quién cobró
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pago_orden   FOREIGN KEY (orden_id)   REFERENCES ordenes(id),
    CONSTRAINT fk_pago_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT chk_pago_monto CHECK (monto > 0),
    INDEX idx_pago_fecha (created_at)
);

-- ---------------------------------------------------------------------
-- ILF15 Ventas (RF-10.1, RF-10.2, RF-10.4): una orden pagada por completo.
-- Los productos vendidos son las líneas de la orden (detalle_ordenes).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ventas (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    codigo         VARCHAR(20)   NOT NULL UNIQUE,      -- VTA-000001 (n.º del comprobante)
    orden_id       INT           NOT NULL UNIQUE,
    subtotal       DECIMAL(14,2) NOT NULL,             -- productos
    costo_envio    DECIMAL(12,2) NOT NULL DEFAULT 0,
    total          DECIMAL(14,2) NOT NULL,
    costo_insumos  DECIMAL(14,2) NOT NULL DEFAULT 0,   -- lo que costaron los insumos gastados
    usuario_id     INT           NOT NULL,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_venta_orden   FOREIGN KEY (orden_id)   REFERENCES ordenes(id),
    CONSTRAINT fk_venta_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_venta_fecha (created_at)
);

-- ---------------------------------------------------------------------
-- ILF16 Consumo (RF-10.3): insumos gastados en cada venta según las recetas.
-- Cada línea tiene su SALIDA por CONSUMO en movimientos_inventario.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS consumos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    venta_id        INT           NOT NULL,
    insumo_id       INT           NOT NULL,
    cantidad        DECIMAL(12,3) NOT NULL,
    costo_unitario  DECIMAL(12,2) NOT NULL,            -- costo del insumo al momento de vender
    movimiento_id   INT           NOT NULL,
    CONSTRAINT fk_consumo_venta      FOREIGN KEY (venta_id)      REFERENCES ventas(id),
    CONSTRAINT fk_consumo_insumo     FOREIGN KEY (insumo_id)     REFERENCES insumos(id),
    CONSTRAINT fk_consumo_movimiento FOREIGN KEY (movimiento_id) REFERENCES movimientos_inventario(id)
);
