-- =====================================================================
--  StockPot - Script 13: propina sugerida del 10 % en mesa (Ley 1935 de 2018), tercer corte.
--  NO borra datos: solo agrega dos columnas.
--  (Si creas la base desde cero con 01_schema.sql y 02_seed.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
-- =====================================================================
USE stockpot;

-- Si el cliente acepta la propina sugerida (por defecto sí; el cajero la quita si no la quiere)
SET @existe := (SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'stockpot' AND table_name = 'ordenes' AND column_name = 'incluye_propina');
SET @sql := IF(@existe = 0, "ALTER TABLE ordenes ADD COLUMN incluye_propina BOOLEAN NOT NULL DEFAULT TRUE AFTER observaciones",
               'SELECT ''La columna ordenes.incluye_propina ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- La propina cobrada en cada venta: es del personal, no es venta ni ganancia
SET @existe := (SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'stockpot' AND table_name = 'ventas' AND column_name = 'propina');
SET @sql := IF(@existe = 0, "ALTER TABLE ventas ADD COLUMN propina DECIMAL(12,2) NOT NULL DEFAULT 0 AFTER costo_insumos",
               'SELECT ''La columna ventas.propina ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

SELECT table_name, column_name, column_default FROM information_schema.columns
WHERE table_schema = 'stockpot' AND ((table_name = 'ordenes' AND column_name = 'incluye_propina')
                                  OR (table_name = 'ventas' AND column_name = 'propina'));
