-- =====================================================================
--  StockPot - Sistema de gestión para restaurantes
--  Script 01: estructura de la base de datos (MySQL 8.4)
--
--  ⚠️ Este script BORRA la base stockpot y la crea de nuevo.
--     Úsalo solo para crear la base desde cero.
-- =====================================================================

DROP DATABASE IF EXISTS stockpot;

-- utf8mb4 permite guardar tildes, ñ y emojis sin problemas
CREATE DATABASE stockpot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stockpot;


-- =====================================================================
--  ITERACIÓN 1 - Parte 1: Usuarios y roles
-- =====================================================================

-- ---------------------------------------------------------------------
-- ILF02 Roles y permisos
-- Un rol agrupa lo que puede hacer un tipo de usuario (ADMINISTRADOR,
-- MESERO, COCINERO...). Un permiso es una acción concreta, por ejemplo
-- 'proveedores.gestionar'.
-- ---------------------------------------------------------------------
CREATE TABLE roles (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(50)  NOT NULL UNIQUE,
    descripcion  VARCHAR(255),
    activo       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE permisos (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    codigo       VARCHAR(60)  NOT NULL UNIQUE,   -- formato modulo.accion
    modulo       VARCHAR(40)  NOT NULL,
    descripcion  VARCHAR(255)
);

-- Tabla intermedia: un rol tiene muchos permisos y un permiso puede
-- pertenecer a muchos roles (relación muchos a muchos).
CREATE TABLE rol_permisos (
    rol_id       INT NOT NULL,
    permiso_id   INT NOT NULL,
    PRIMARY KEY (rol_id, permiso_id),            -- evita repetir el mismo par
    CONSTRAINT fk_rp_rol     FOREIGN KEY (rol_id)     REFERENCES roles(id)    ON DELETE CASCADE,
    CONSTRAINT fk_rp_permiso FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- ILF01 Usuarios
-- Cada persona que inicia sesión. Tiene exactamente un rol.
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(80)  NOT NULL,
    apellido       VARCHAR(80)  NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,  -- con él se inicia sesión
    password_hash  VARCHAR(255) NOT NULL,         -- contraseña cifrada, nunca en texto plano
    telefono       VARCHAR(20),
    rol_id         INT          NOT NULL,
    activo         BOOLEAN      NOT NULL DEFAULT TRUE,  -- desactivar en vez de borrar
    ultimo_acceso  DATETIME,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_rol FOREIGN KEY (rol_id) REFERENCES roles(id)
);


-- =====================================================================
--  ITERACIÓN 1 - Parte 2: Proveedores y órdenes de compra
-- =====================================================================

-- ---------------------------------------------------------------------
-- ILF03 Proveedores
-- Empresas o personas a las que el restaurante les compra insumos.
-- ---------------------------------------------------------------------
CREATE TABLE proveedores (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nit           VARCHAR(20)  NOT NULL UNIQUE,
    razon_social  VARCHAR(150) NOT NULL,
    contacto      VARCHAR(100),                   -- persona con quien se habla
    telefono      VARCHAR(20),
    email         VARCHAR(120),
    direccion     VARCHAR(200),
    activo        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- ILF04 Insumos
-- Materias primas que se compran y se gastan al preparar los platos.
-- Se crea ahora porque las órdenes de compra necesitan saber qué se compra.
-- ---------------------------------------------------------------------
CREATE TABLE insumos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    codigo          VARCHAR(30)    NOT NULL UNIQUE,  -- ej: INS-001
    nombre          VARCHAR(120)   NOT NULL,
    unidad_medida   ENUM('KG','G','L','ML','UNIDAD') NOT NULL,
    stock_actual    DECIMAL(12,3)  NOT NULL DEFAULT 0,
    stock_minimo    DECIMAL(12,3)  NOT NULL DEFAULT 0,  -- RF-03.7 nivel de alerta
    costo_unitario  DECIMAL(12,2)  NOT NULL DEFAULT 0,  -- último costo de compra
    activo          BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_insumo_stock CHECK (stock_actual >= 0)  -- nunca stock negativo
);

-- ---------------------------------------------------------------------
-- RF-02.4 Productos suministrados: qué insumos vende cada proveedor.
-- Muchos a muchos: un proveedor vende varios insumos y un insumo puede
-- comprarse a varios proveedores.
-- ---------------------------------------------------------------------
CREATE TABLE proveedor_insumos (
    proveedor_id       INT NOT NULL,
    insumo_id          INT NOT NULL,
    precio_referencia  DECIMAL(12,2),               -- precio habitual del proveedor
    PRIMARY KEY (proveedor_id, insumo_id),
    CONSTRAINT fk_pi_proveedor FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE CASCADE,
    CONSTRAINT fk_pi_insumo    FOREIGN KEY (insumo_id)    REFERENCES insumos(id)     ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- ILF17 Órdenes de compra
-- Encabezado: a quién se le compra, quién la registró y en qué estado va.
-- ---------------------------------------------------------------------
CREATE TABLE ordenes_compra (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    codigo                  VARCHAR(20)   NOT NULL UNIQUE,  -- ej: OC-000001
    proveedor_id            INT           NOT NULL,
    usuario_id              INT           NOT NULL,         -- quién la registró
    fecha_orden             DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega_estimada  DATE,
    fecha_recepcion         DATETIME,                       -- se llena al recibirla
    estado                  ENUM('PENDIENTE','ENVIADA','RECIBIDA','CANCELADA')
                            NOT NULL DEFAULT 'PENDIENTE',
    total                   DECIMAL(14,2) NOT NULL DEFAULT 0,
    observaciones           VARCHAR(255),
    created_at              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_oc_proveedor FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
    CONSTRAINT fk_oc_usuario   FOREIGN KEY (usuario_id)   REFERENCES usuarios(id)
);

-- Detalle: cada línea de la orden (qué insumo, cuánto y a qué precio).
CREATE TABLE detalle_orden_compra (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    orden_compra_id  INT           NOT NULL,
    insumo_id        INT           NOT NULL,
    cantidad         DECIMAL(12,3) NOT NULL,
    precio_unitario  DECIMAL(12,2) NOT NULL,
    subtotal         DECIMAL(14,2) NOT NULL,          -- cantidad x precio_unitario
    CONSTRAINT fk_doc_orden  FOREIGN KEY (orden_compra_id) REFERENCES ordenes_compra(id) ON DELETE CASCADE,
    CONSTRAINT fk_doc_insumo FOREIGN KEY (insumo_id)       REFERENCES insumos(id),
    CONSTRAINT chk_doc_cantidad CHECK (cantidad > 0)
);


-- =====================================================================
--  ITERACIÓN 2 - Inventario completo
-- =====================================================================

-- ---------------------------------------------------------------------
-- ILF05 Movimientos de inventario (RF-03.4 entradas, RF-03.5 salidas)
-- Cada cambio de stock deja un registro: qué, cuánto, por qué, quién y cuándo.
-- ---------------------------------------------------------------------
CREATE TABLE movimientos_inventario (
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


-- =====================================================================
--  ITERACIÓN 2 - Productos y menú
-- =====================================================================

-- ---------------------------------------------------------------------
-- ILF06 Productos y platos (RF-04.1 a RF-04.3, RF-04.5 precio, RF-04.6 disponibilidad)
-- Lo que el restaurante vende: platos, bebidas, postres...
-- ---------------------------------------------------------------------
CREATE TABLE productos (
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
CREATE TABLE recetas (
    producto_id  INT           NOT NULL,
    insumo_id    INT           NOT NULL,
    cantidad     DECIMAL(12,3) NOT NULL,             -- en la unidad del insumo
    PRIMARY KEY (producto_id, insumo_id),            -- un insumo no se repite en la receta
    CONSTRAINT fk_receta_producto FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    CONSTRAINT fk_receta_insumo   FOREIGN KEY (insumo_id)   REFERENCES insumos(id),
    CONSTRAINT chk_receta_cantidad CHECK (cantidad > 0)
);


-- =====================================================================
--  ITERACIÓN 4 - Domicilios (con las órdenes que reutiliza la Iteración 3)
-- =====================================================================

-- ---------------------------------------------------------------------
-- ILF12 Clientes (RF-08.2 Registrar información del cliente)
-- El teléfono identifica al cliente: al llamar, se busca por su número.
-- ---------------------------------------------------------------------
CREATE TABLE clientes (
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
CREATE TABLE ordenes (
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
CREATE TABLE detalle_ordenes (
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
CREATE TABLE domicilios (
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
