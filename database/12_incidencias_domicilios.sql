-- =====================================================================
--  StockPot - Script 12: incidencias de domicilios (RF-12.5), recomendación del tercer corte.
--  Requiere el script 11. NO borra datos: solo agrega.
--  (Si creas la base desde cero con 01_schema.sql y 02_seed.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
-- =====================================================================
USE stockpot;

-- El catálogo acepta el módulo DOMICILIOS
ALTER TABLE codigos_incidencia MODIFY modulo ENUM('INVENTARIO','VENTAS','COMPRAS','DOMICILIOS','OTRO') NOT NULL;

-- Causa externa: el inconveniente lo causa el cliente y no se le cuenta al personal
SET @existe := (SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'stockpot' AND table_name = 'codigos_incidencia' AND column_name = 'causa_externa');
SET @sql := IF(@existe = 0, "ALTER TABLE codigos_incidencia ADD COLUMN causa_externa BOOLEAN NOT NULL DEFAULT FALSE AFTER corrige_stock",
               'SELECT ''La columna codigos_incidencia.causa_externa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- La incidencia puede ser sobre un domicilio
SET @existe := (SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'stockpot' AND table_name = 'incidencias' AND column_name = 'domicilio_id');
SET @sql := IF(@existe = 0, "ALTER TABLE incidencias ADD COLUMN domicilio_id INT NULL AFTER orden_compra_id",
               'SELECT ''La columna incidencias.domicilio_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints
                WHERE table_schema = 'stockpot' AND table_name = 'incidencias' AND constraint_name = 'fk_inc_domicilio');
SET @sql := IF(@existe = 0, 'ALTER TABLE incidencias ADD CONSTRAINT fk_inc_domicilio FOREIGN KEY (domicilio_id) REFERENCES domicilios(id)',
               'SELECT ''La llave fk_inc_domicilio ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- Códigos de domicilios
INSERT IGNORE INTO codigos_incidencia (codigo, modulo, nombre, corrige_stock, causa_externa) VALUES
 ('DOM-01', 'DOMICILIOS', 'El cliente no salió o no contestó', 0, 1),
 ('DOM-02', 'DOMICILIOS', 'Dirección errada o incompleta', 0, 1),
 ('DOM-03', 'DOMICILIOS', 'Pedido incompleto o equivocado', 0, 0),
 ('DOM-04', 'DOMICILIOS', 'Pedido llegó dañado o derramado', 0, 0),
 ('DOM-05', 'DOMICILIOS', 'Demora en la entrega', 0, 0),
 ('DOM-06', 'DOMICILIOS', 'El cliente no pagó o rechazó el pedido', 0, 1);

SELECT codigo, nombre, causa_externa FROM codigos_incidencia WHERE modulo = 'DOMICILIOS' ORDER BY codigo;
