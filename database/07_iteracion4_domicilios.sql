-- =====================================================================
--  StockPot - Script 07: actualización para la Iteración 4 (domicilios)
--  Para bases creadas ANTES de este cambio. NO borra datos: solo agrega.
--  (Si creas la base desde cero con 01_schema.sql, ya incluye todo esto.)
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- ILF12 Clientes (RF-08.2 Registrar información del cliente)
-- El teléfono identifica al cliente: al llamar, se busca por su número.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(120) NOT NULL,
    telefono    VARCHAR(20)  NOT NULL UNIQUE,
    email       VARCHAR(120),
    direccion   VARCHAR(200),                    -- dirección habitual (se propone al pedir)
    barrio      VARCHAR(80),
    referencia  VARCHAR(200),                    -- ej: "casa esquinera, portón negro"
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- ILF09 Órdenes: un pedido de productos. Sirve para domicilios (Iteración 4)
-- y para los pedidos en mesa de la Iteración 3 (tipo MESA).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ordenes (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    codigo         VARCHAR(20)   NOT NULL UNIQUE,      -- PED-000001
    tipo           ENUM('MESA','DOMICILIO','LLEVAR') NOT NULL,
    estado         ENUM('ABIERTA','CERRADA','CANCELADA') NOT NULL DEFAULT 'ABIERTA',
    cliente_id     INT,
    usuario_id     INT           NOT NULL,             -- quién la registró
    subtotal       DECIMAL(14,2) NOT NULL DEFAULT 0,   -- suma de las líneas
    observaciones  VARCHAR(255),
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orden_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    CONSTRAINT fk_orden_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_orden_fecha (created_at)
);

-- ---------------------------------------------------------------------
-- ILF10 Detalle de órdenes: cada producto pedido, cuántos y a qué precio.
-- El precio se copia del menú al pedir: si luego cambia, el pedido no.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detalle_ordenes (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    orden_id         INT           NOT NULL,
    producto_id      INT           NOT NULL,
    cantidad         INT           NOT NULL,
    precio_unitario  DECIMAL(12,2) NOT NULL,
    subtotal         DECIMAL(14,2) NOT NULL,           -- cantidad x precio_unitario
    observacion      VARCHAR(150),                     -- ej: "sin cebolla"
    CONSTRAINT fk_detalle_orden    FOREIGN KEY (orden_id)    REFERENCES ordenes(id) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_producto FOREIGN KEY (producto_id) REFERENCES productos(id),
    CONSTRAINT chk_detalle_cantidad CHECK (cantidad > 0)
);

-- ---------------------------------------------------------------------
-- ILF13 Domicilios (RF-08.1 a RF-08.8): la entrega de una orden.
-- RECIBIDO -> EN_PREPARACION -> LISTO -> EN_CAMINO -> ENTREGADO (o CANCELADO)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS domicilios (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    orden_id             INT           NOT NULL UNIQUE,
    cliente_id           INT           NOT NULL,
    direccion            VARCHAR(200)  NOT NULL,       -- RF-08.3 dirección de entrega
    barrio               VARCHAR(80),
    referencia           VARCHAR(200),
    telefono_contacto    VARCHAR(20)   NOT NULL,
    costo_envio          DECIMAL(12,2) NOT NULL DEFAULT 0,
    estado               ENUM('RECIBIDO','EN_PREPARACION','LISTO','EN_CAMINO','ENTREGADO','CANCELADO')
                         NOT NULL DEFAULT 'RECIBIDO',
    domiciliario_id      INT,                          -- RF-08.5 quién lo lleva
    fecha_asignacion     DATETIME,
    fecha_salida         DATETIME,
    fecha_entrega        DATETIME,                     -- RF-08.7
    recibido_por         VARCHAR(120),
    observacion_entrega  VARCHAR(255),
    created_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_domicilio_orden        FOREIGN KEY (orden_id)        REFERENCES ordenes(id),
    CONSTRAINT fk_domicilio_cliente      FOREIGN KEY (cliente_id)      REFERENCES clientes(id),
    CONSTRAINT fk_domicilio_domiciliario FOREIGN KEY (domiciliario_id) REFERENCES usuarios(id),
    CONSTRAINT chk_domicilio_envio CHECK (costo_envio >= 0),
    INDEX idx_domicilio_estado (estado)
);
