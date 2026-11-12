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
--  Varios restaurantes (tercer corte)
-- =====================================================================

-- ---------------------------------------------------------------------
-- Empresas: cada restaurante que usa StockPot. Sus datos llevan empresa_id
-- y la aplicación filtra cada consulta por el restaurante de la sesión.
-- El súper administrador (sin empresa) solo crea y activa restaurantes.
-- ---------------------------------------------------------------------
CREATE TABLE empresas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(120) NOT NULL,
    nit         VARCHAR(20)  NOT NULL UNIQUE,
    telefono    VARCHAR(20),
    email       VARCHAR(120),
    direccion   VARCHAR(200),
    activa      BOOLEAN      NOT NULL DEFAULT TRUE,   -- desactivada: sus usuarios no pueden entrar
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);


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
    empresa_id  INT NULL,      -- NULL: súper administrador
    nombre       VARCHAR(50)  NOT NULL,
    descripcion  VARCHAR(255),
    activo       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_roles_empresa_nombre (empresa_id, nombre),  -- único en cada restaurante
    CONSTRAINT fk_roles_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
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
    empresa_id  INT NULL,      -- NULL: súper administrador
    nombre         VARCHAR(80)  NOT NULL,
    apellido       VARCHAR(80)  NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,  -- con él se inicia sesión
    password_hash  VARCHAR(255) NOT NULL,         -- contraseña cifrada, nunca en texto plano
    pin_hash       VARCHAR(255),                -- PIN personal cifrado (cobrar, anular, salidas)
    telefono       VARCHAR(20),
    rol_id         INT          NOT NULL,
    activo         BOOLEAN      NOT NULL DEFAULT TRUE,  -- desactivar en vez de borrar
    ultimo_acceso  DATETIME,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_rol FOREIGN KEY (rol_id) REFERENCES roles(id),
    CONSTRAINT fk_usuarios_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ---------------------------------------------------------------------
-- Sesiones seguras (tercer corte): cada inicio de sesión queda guardado para
-- poder bloquearla, cerrarla por inactividad o al salir aunque el token no haya vencido.
-- ---------------------------------------------------------------------
CREATE TABLE sesiones (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    jti               VARCHAR(36)  NOT NULL UNIQUE,   -- identificador del token
    usuario_id        INT          NOT NULL,
    creada            DATETIME     NOT NULL,
    ultima_actividad  DATETIME     NOT NULL,          -- a los 30 min sin uso se cierra
    bloqueada         BOOLEAN      NOT NULL DEFAULT FALSE,
    intentos_pin      INT          NOT NULL DEFAULT 0, -- al quinto PIN equivocado se cierra
    cerrada           DATETIME,                       -- NULL = abierta
    motivo_cierre     ENUM('SALIDA','INACTIVIDAD','PIN','USUARIO'),
    CONSTRAINT fk_sesion_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_sesion_usuario (usuario_id)
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
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
    nit           VARCHAR(20)  NOT NULL,
    razon_social  VARCHAR(150) NOT NULL,
    contacto      VARCHAR(100),                   -- persona con quien se habla
    telefono      VARCHAR(20),
    email         VARCHAR(120),
    direccion     VARCHAR(200),
    activo        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_proveedores_empresa_nit (empresa_id, nit),  -- único en cada restaurante
    CONSTRAINT fk_proveedores_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ---------------------------------------------------------------------
-- ILF04 Insumos
-- Materias primas que se compran y se gastan al preparar los platos.
-- Se crea ahora porque las órdenes de compra necesitan saber qué se compra.
-- ---------------------------------------------------------------------
CREATE TABLE insumos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
    codigo          VARCHAR(30)    NOT NULL,  -- ej: INS-001
    nombre          VARCHAR(120)   NOT NULL,
    categoria       ENUM('CARNES','GRANOS','LACTEOS','FRUTAS_VERDURAS','BEBIDAS','ABARROTES','DESECHABLES','LIMPIEZA','MOBILIARIO','OTROS')
                    NOT NULL DEFAULT 'OTROS',  -- RF-03.10 (y RF-02.9 proveedores)
    unidad_medida   ENUM('KG','G','L','ML','UNIDAD') NOT NULL,
    stock_actual    DECIMAL(12,3)  NOT NULL DEFAULT 0,
    stock_minimo    DECIMAL(12,3)  NOT NULL DEFAULT 0,  -- RF-03.7 nivel de alerta
    costo_unitario  DECIMAL(12,2)  NOT NULL DEFAULT 0,  -- último costo de compra
    activo          BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_insumo_stock CHECK (stock_actual >= 0),  -- nunca stock negativo
    UNIQUE KEY uq_insumos_empresa_codigo (empresa_id, codigo),  -- único en cada restaurante
    CONSTRAINT fk_insumos_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
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
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
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
    CONSTRAINT fk_oc_usuario   FOREIGN KEY (usuario_id)   REFERENCES usuarios(id),
    CONSTRAINT fk_ordenes_compra_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
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
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
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
    INDEX idx_mov_fecha (created_at),
    CONSTRAINT fk_movimientos_inventario_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
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
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
    codigo        VARCHAR(30)   NOT NULL,     -- ej: PRD-001
    nombre        VARCHAR(120)  NOT NULL,
    descripcion   VARCHAR(255),
    categoria     ENUM('ENTRADA','PLATO_FUERTE','BEBIDA','POSTRE','ADICIONAL') NOT NULL,
    precio_venta  DECIMAL(12,2) NOT NULL,            -- RF-04.5
    disponible    BOOLEAN       NOT NULL DEFAULT TRUE,  -- RF-04.6 se puede pedir hoy
    activo        BOOLEAN       NOT NULL DEFAULT TRUE,  -- sigue en la carta
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_producto_precio CHECK (precio_venta > 0),
    UNIQUE KEY uq_productos_empresa_codigo (empresa_id, codigo),  -- único en cada restaurante
    CONSTRAINT fk_productos_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
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
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
    nombre      VARCHAR(120) NOT NULL,
    telefono    VARCHAR(20)  NOT NULL,
    email       VARCHAR(120),
    direccion   VARCHAR(200),                    -- dirección habitual (se propone al pedir)
    barrio      VARCHAR(80),
    referencia  VARCHAR(200),                    -- ej: "casa esquinera, portón negro"
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_clientes_empresa_telefono (empresa_id, telefono),  -- único en cada restaurante
    CONSTRAINT fk_clientes_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ---------------------------------------------------------------------
-- ILF09 Órdenes: un pedido de productos. Sirve para domicilios (Iteración 4)
-- y para los pedidos en mesa de la Iteración 3 (tipo MESA).
-- ---------------------------------------------------------------------
CREATE TABLE ordenes (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
    codigo         VARCHAR(20)   NOT NULL UNIQUE,      -- PED-000001
    tipo           ENUM('MESA','DOMICILIO','LLEVAR') NOT NULL,
    estado         ENUM('ABIERTA','CERRADA','CANCELADA') NOT NULL DEFAULT 'ABIERTA',
    cliente_id     INT,
    usuario_id     INT           NOT NULL,             -- quién la registró
    subtotal       DECIMAL(14,2) NOT NULL DEFAULT 0,   -- suma de las líneas
    observaciones  VARCHAR(255),
    incluye_propina BOOLEAN      NOT NULL DEFAULT TRUE,  -- propina sugerida del 10 % en mesa (Ley 1935/2018)
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orden_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    CONSTRAINT fk_orden_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_orden_fecha (created_at),
    CONSTRAINT fk_ordenes_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
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
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
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
    INDEX idx_domicilio_estado (estado),
    CONSTRAINT fk_domicilios_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);


-- =====================================================================
--  ITERACIÓN 4 - Pagos, ventas y consumo
-- =====================================================================

-- ---------------------------------------------------------------------
-- ILF08 Mesas del restaurante (RF-05.2; también las usarán las reservas, RF-07).
-- Que una mesa esté ocupada no se guarda: se calcula con sus pedidos abiertos.
-- ---------------------------------------------------------------------
CREATE TABLE mesas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
    numero      INT          NOT NULL,          -- número visible en el salón
    capacidad   INT          NOT NULL DEFAULT 4,       -- cuántas personas caben
    ubicacion   VARCHAR(60),                           -- Salón, Terraza, Barra...
    activa      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_mesa_numero    CHECK (numero > 0),
    CONSTRAINT chk_mesa_capacidad CHECK (capacidad > 0),
    UNIQUE KEY uq_mesas_empresa_numero (empresa_id, numero),  -- único en cada restaurante
    CONSTRAINT fk_mesas_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ---------------------------------------------------------------------
-- ILF09 Pedidos (complemento de ordenes para los pedidos en mesa, RF-05.1 a RF-05.9). Las líneas y el total viven en
-- su orden (ordenes, tipo MESA); aquí van la mesa, los comensales y el recorrido:
-- REGISTRADO -> CONFIRMADO -> EN_COCINA -> EN_PREPARACION -> LISTO -> ENTREGADO
-- (o CANCELADO antes de ir a cocina). Se cobra en la caja como cualquier orden.
-- ---------------------------------------------------------------------
CREATE TABLE pedidos_mesa (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
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
    INDEX idx_pedido_mesa_estado (estado),
    CONSTRAINT fk_pedidos_mesa_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ---------------------------------------------------------------------
-- ILF11 Reservas (RF-07.1 a RF-07.8): una mesa apartada para un cliente.
-- Las PENDIENTE y CONFIRMADA ocupan la mesa desde fecha_hora durante
-- duracion_minutos; la aplicación no deja que dos se crucen (RF-07.7).
-- ---------------------------------------------------------------------
CREATE TABLE reservas (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id        INT NOT NULL,                       -- restaurante dueño de la fila
    codigo            VARCHAR(20)   NOT NULL UNIQUE,      -- RES-000001
    mesa_id           INT           NOT NULL,             -- RF-07.6
    cliente           VARCHAR(120)  NOT NULL,
    telefono          VARCHAR(20)   NOT NULL,
    personas          INT           NOT NULL,
    fecha_hora        DATETIME      NOT NULL,             -- RF-07.5
    duracion_minutos  INT           NOT NULL DEFAULT 120, -- cuánto se aparta la mesa
    estado            ENUM('PENDIENTE','CONFIRMADA','CUMPLIDA','NO_ASISTIO','CANCELADA')
                      NOT NULL DEFAULT 'PENDIENTE',       -- RF-07.8
    observaciones     VARCHAR(255),
    usuario_id        INT           NOT NULL,             -- quién la registró
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_reserva_personas CHECK (personas > 0),
    CONSTRAINT chk_reserva_duracion CHECK (duracion_minutos BETWEEN 30 AND 360),
    CONSTRAINT fk_reserva_mesa    FOREIGN KEY (mesa_id)    REFERENCES mesas(id),
    CONSTRAINT fk_reserva_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_reservas_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    INDEX idx_reserva_fecha (fecha_hora),
    INDEX idx_reserva_mesa_fecha (mesa_id, fecha_hora)
);

-- ---------------------------------------------------------------------
-- ILF14 Pagos (RF-09.1 a RF-09.7). Una orden se puede pagar en partes y
-- con varios métodos; cuando lo pagado completa el total, se registra la venta.
-- ---------------------------------------------------------------------
CREATE TABLE pagos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
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
    INDEX idx_pago_fecha (created_at),
    CONSTRAINT fk_pagos_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ---------------------------------------------------------------------
-- ILF15 Ventas (RF-10.1, RF-10.2, RF-10.4): una orden pagada por completo.
-- Los productos vendidos son las líneas de la orden (detalle_ordenes).
-- ---------------------------------------------------------------------
CREATE TABLE ventas (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
    codigo         VARCHAR(20)   NOT NULL UNIQUE,      -- VTA-000001 (n.º del comprobante)
    orden_id       INT           NOT NULL UNIQUE,
    subtotal       DECIMAL(14,2) NOT NULL,             -- productos
    costo_envio    DECIMAL(12,2) NOT NULL DEFAULT 0,
    total          DECIMAL(14,2) NOT NULL,
    costo_insumos  DECIMAL(14,2) NOT NULL DEFAULT 0,   -- lo que costaron los insumos gastados
    propina        DECIMAL(12,2) NOT NULL DEFAULT 0,   -- del personal: no es venta ni ganancia
    usuario_id     INT           NOT NULL,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_venta_orden   FOREIGN KEY (orden_id)   REFERENCES ordenes(id),
    CONSTRAINT fk_venta_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_venta_fecha (created_at),
    CONSTRAINT fk_ventas_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ---------------------------------------------------------------------
-- ILF16 Consumo (RF-10.3): insumos gastados en cada venta según las recetas.
-- Cada línea tiene su SALIDA por CONSUMO en movimientos_inventario.
-- ---------------------------------------------------------------------
CREATE TABLE consumos (
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

-- ---------------------------------------------------------------------
-- ILF10 Códigos de incidencia (RF-12.1): catálogo de tipos de error.
-- Sugerencia de la docente en la sustentación del 2.º corte.
-- ---------------------------------------------------------------------
CREATE TABLE codigos_incidencia (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    codigo         VARCHAR(10)  NOT NULL UNIQUE,        -- INV-01, VEN-02...
    modulo         ENUM('INVENTARIO','VENTAS','COMPRAS','DOMICILIOS','OTRO') NOT NULL,
    nombre         VARCHAR(120) NOT NULL,
    corrige_stock  BOOLEAN      NOT NULL DEFAULT FALSE, -- RF-12.3 pide la cantidad real y ajusta
    causa_externa  BOOLEAN      NOT NULL DEFAULT FALSE, -- RF-12.5 no cuenta contra el personal
    activo         BOOLEAN      NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------
-- ILF11 Incidencias (RF-12.2 a RF-12.4): un error reportado sobre un registro.
-- El responsable es quien hizo el registro; quien reporta queda aparte.
-- ---------------------------------------------------------------------
CREATE TABLE incidencias (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id  INT NOT NULL,  -- restaurante dueño de la fila
    codigo                VARCHAR(20)   NOT NULL UNIQUE, -- INC-000001
    codigo_incidencia_id  INT           NOT NULL,
    movimiento_id         INT,                           -- el registro con el error: uno de los tres
    venta_id              INT,
    orden_compra_id       INT,
    domicilio_id          INT,                           -- RF-12.5
    responsable_id        INT           NOT NULL,
    reportado_por_id      INT           NOT NULL,
    observacion           VARCHAR(500)  NOT NULL,
    cantidad_registrada   DECIMAL(12,3),                 -- RF-12.3 corrección de inventario
    cantidad_real         DECIMAL(12,3),
    ajuste_id             INT,                           -- movimiento de ajuste que lo corrigió
    created_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_inc_codigo      FOREIGN KEY (codigo_incidencia_id) REFERENCES codigos_incidencia(id),
    CONSTRAINT fk_inc_movimiento  FOREIGN KEY (movimiento_id)        REFERENCES movimientos_inventario(id),
    CONSTRAINT fk_inc_venta       FOREIGN KEY (venta_id)             REFERENCES ventas(id),
    CONSTRAINT fk_inc_orden       FOREIGN KEY (orden_compra_id)      REFERENCES ordenes_compra(id),
    CONSTRAINT fk_inc_domicilio   FOREIGN KEY (domicilio_id)         REFERENCES domicilios(id),
    CONSTRAINT fk_inc_responsable FOREIGN KEY (responsable_id)       REFERENCES usuarios(id),
    CONSTRAINT fk_inc_reporta     FOREIGN KEY (reportado_por_id)     REFERENCES usuarios(id),
    CONSTRAINT fk_inc_ajuste      FOREIGN KEY (ajuste_id)            REFERENCES movimientos_inventario(id),
    CONSTRAINT fk_incidencias_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ---------------------------------------------------------------------
-- Turnos y cierre de caja (arqueo): la base de efectivo, lo esperado por
-- método de pago y lo que contó el cajero al cerrar.
-- ---------------------------------------------------------------------
CREATE TABLE turnos_caja (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id              INT NOT NULL,                      -- restaurante dueño de la fila
    estado                  ENUM('ABIERTO','CERRADO') NOT NULL DEFAULT 'ABIERTO',
    base_inicial            DECIMAL(14,2) NOT NULL DEFAULT 0,  -- efectivo con el que empieza la caja
    abierto_por_id          INT           NOT NULL,
    abierto_en              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cerrado_por_id          INT,
    cerrado_en              DATETIME,
    esperado_efectivo       DECIMAL(14,2),                     -- base + pagos en efectivo
    esperado_tarjeta        DECIMAL(14,2),
    esperado_transferencia  DECIMAL(14,2),
    contado_efectivo        DECIMAL(14,2),                     -- lo que contó el cajero
    contado_tarjeta         DECIMAL(14,2),
    contado_transferencia   DECIMAL(14,2),
    num_pagos               INT           NOT NULL DEFAULT 0,
    propinas                DECIMAL(12,2) NOT NULL DEFAULT 0,  -- del personal, incluidas en lo recibido
    observacion             VARCHAR(255),                      -- obligatoria si no cuadra
    CONSTRAINT chk_turno_base CHECK (base_inicial >= 0),
    CONSTRAINT fk_turno_abre   FOREIGN KEY (abierto_por_id) REFERENCES usuarios(id),
    CONSTRAINT fk_turno_cierra FOREIGN KEY (cerrado_por_id) REFERENCES usuarios(id),
    CONSTRAINT fk_turnos_caja_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    INDEX idx_turno_estado (empresa_id, estado),
    INDEX idx_turno_cierre (cerrado_en)
);
