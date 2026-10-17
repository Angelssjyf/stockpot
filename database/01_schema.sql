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
-- ILF04 Insumos (versión básica; se completa en la Iteración 2)
-- Materias primas que se compran y se gastan al preparar los platos.
-- Se crea ahora porque las órdenes de compra necesitan saber qué se compra.
-- ---------------------------------------------------------------------
CREATE TABLE insumos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    codigo          VARCHAR(30)    NOT NULL UNIQUE,  -- ej: INS-001
    nombre          VARCHAR(120)   NOT NULL,
    unidad_medida   ENUM('KG','G','L','ML','UNIDAD') NOT NULL,
    stock_actual    DECIMAL(12,3)  NOT NULL DEFAULT 0,
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
