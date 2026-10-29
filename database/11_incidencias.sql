-- =====================================================================
--  StockPot - Script 11: incidencias (RF-12), sugerencia de la sustentación.
--  Para bases creadas ANTES de este cambio. NO borra datos: solo agrega.
--  (Si creas la base desde cero con 01_schema.sql y 02_seed.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- ILF10 Códigos de incidencia (RF-12.1): catálogo de tipos de error.
-- Sugerencia de la docente en la sustentación del 2.º corte.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS codigos_incidencia (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    codigo         VARCHAR(10)  NOT NULL UNIQUE,        -- INV-01, VEN-02...
    modulo         ENUM('INVENTARIO','VENTAS','COMPRAS','OTRO') NOT NULL,
    nombre         VARCHAR(120) NOT NULL,
    corrige_stock  BOOLEAN      NOT NULL DEFAULT FALSE, -- RF-12.3 pide la cantidad real y ajusta
    activo         BOOLEAN      NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------
-- ILF11 Incidencias (RF-12.2 a RF-12.4): un error reportado sobre un registro.
-- El responsable es quien hizo el registro; quien reporta queda aparte.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incidencias (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    codigo                VARCHAR(20)   NOT NULL UNIQUE, -- INC-000001
    codigo_incidencia_id  INT           NOT NULL,
    movimiento_id         INT,                           -- el registro con el error: uno de los tres
    venta_id              INT,
    orden_compra_id       INT,
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
    CONSTRAINT fk_inc_responsable FOREIGN KEY (responsable_id)       REFERENCES usuarios(id),
    CONSTRAINT fk_inc_reporta     FOREIGN KEY (reportado_por_id)     REFERENCES usuarios(id),
    CONSTRAINT fk_inc_ajuste      FOREIGN KEY (ajuste_id)            REFERENCES movimientos_inventario(id)
);

-- Permisos nuevos: todos reportan; el administrador ve la bitácora y el catálogo
INSERT IGNORE INTO permisos (codigo, modulo, descripcion) VALUES
 ('incidencias.reportar',  'incidencias', 'Reportar errores en inventario, ventas y compras'),
 ('incidencias.ver',       'incidencias', 'Ver la bitácora de incidencias'),
 ('incidencias.gestionar', 'incidencias', 'Administrar el catálogo de códigos de incidencia');

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r JOIN permisos p
  ON (r.nombre = 'ADMINISTRADOR' AND p.modulo = 'incidencias')
  OR (r.nombre <> 'ADMINISTRADOR' AND p.codigo = 'incidencias.reportar');

-- RF-12.1 Catálogo inicial
INSERT IGNORE INTO codigos_incidencia (codigo, modulo, nombre, corrige_stock) VALUES
 ('INV-01', 'INVENTARIO', 'Cantidad registrada de más',          1),
 ('INV-02', 'INVENTARIO', 'Cantidad registrada de menos',        1),
 ('INV-03', 'INVENTARIO', 'Insumo equivocado',                   0),
 ('INV-04', 'INVENTARIO', 'Motivo del movimiento equivocado',    0),
 ('VEN-01', 'VENTAS',     'Método de pago equivocado',           0),
 ('VEN-02', 'VENTAS',     'Monto cobrado errado',                0),
 ('VEN-03', 'VENTAS',     'Producto equivocado en el pedido',    0),
 ('COM-01', 'COMPRAS',    'Precio o cantidad errados en la orden', 0),
 ('COM-02', 'COMPRAS',    'Proveedor equivocado',                0),
 ('OTR-01', 'OTRO',       'Otro error',                          0);

SELECT codigo, nombre FROM codigos_incidencia ORDER BY codigo;
