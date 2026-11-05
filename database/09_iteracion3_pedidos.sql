-- =====================================================================
--  StockPot - Script 09: actualización para la Iteración 3 (pedidos en mesa)
--  Para bases creadas ANTES de este cambio. NO borra datos: solo agrega.
--  (Si creas la base desde cero con 01_schema.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- ILF08 Mesas del restaurante (RF-05.2; también las usarán las reservas, RF-07).
-- Que una mesa esté ocupada no se guarda: se calcula con sus pedidos abiertos.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mesas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    numero      INT          NOT NULL UNIQUE,          -- número visible en el salón
    capacidad   INT          NOT NULL DEFAULT 4,       -- cuántas personas caben
    ubicacion   VARCHAR(60),                           -- Salón, Terraza, Barra...
    activa      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_mesa_numero    CHECK (numero > 0),
    CONSTRAINT chk_mesa_capacidad CHECK (capacidad > 0)
);

-- ---------------------------------------------------------------------
-- ILF09 Pedidos (complemento de ordenes para los pedidos en mesa, RF-05.1 a RF-05.9). Las líneas y el total viven en
-- su orden (ordenes, tipo MESA); aquí van la mesa, los comensales y el recorrido:
-- REGISTRADO -> CONFIRMADO -> EN_COCINA -> EN_PREPARACION -> LISTO -> ENTREGADO
-- (o CANCELADO antes de ir a cocina). Se cobra en la caja como cualquier orden.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedidos_mesa (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    orden_id            INT      NOT NULL UNIQUE,
    mesa_id             INT      NOT NULL,             -- RF-05.2
    comensales          INT      NOT NULL DEFAULT 1,
    estado              ENUM('REGISTRADO','CONFIRMADO','EN_COCINA','EN_PREPARACION','LISTO',
                             'ENTREGADO','CANCELADO') NOT NULL DEFAULT 'REGISTRADO',
    fecha_confirmacion  DATETIME,                      -- RF-05.7
    fecha_envio_cocina  DATETIME,                      -- RF-05.8
    fecha_listo         DATETIME,                      -- RF-06 (cocina)
    fecha_entrega       DATETIME,                      -- RF-06 (cocina)
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pedido_mesa_orden FOREIGN KEY (orden_id) REFERENCES ordenes(id),
    CONSTRAINT fk_pedido_mesa_mesa  FOREIGN KEY (mesa_id)  REFERENCES mesas(id),
    CONSTRAINT chk_pedido_comensales CHECK (comensales > 0),
    INDEX idx_pedido_mesa_estado (estado)
);

-- ---------------------------------------------------------------------
-- Mesas iniciales del salón (si ya existen, no se repiten)
-- ---------------------------------------------------------------------
INSERT IGNORE INTO mesas (numero, capacidad, ubicacion) VALUES
 (1, 4, 'Salón'), (2, 4, 'Salón'), (3, 2, 'Salón'), (4, 6, 'Salón'),
 (5, 4, 'Terraza'), (6, 2, 'Terraza'), (7, 8, 'Terraza'), (8, 2, 'Barra');

-- Verificación: deben salir 21 tablas y 8 mesas
SELECT COUNT(*) AS tablas FROM information_schema.tables WHERE table_schema = 'stockpot';
SELECT numero, capacidad, ubicacion FROM mesas ORDER BY numero;
