-- =====================================================================
--  StockPot - Script 10: categorías de insumos (RF-03.10) para subdividir
--  a los proveedores y buscarlos por lo que venden (RF-02.9).
--  Para bases creadas ANTES de este cambio. NO borra datos: solo agrega.
--  (Si creas la base desde cero con 01_schema.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
-- =====================================================================
USE stockpot;

-- La columna se agrega solo si todavía no existe
SET @existe := (SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'stockpot' AND table_name = 'insumos' AND column_name = 'categoria');
SET @sql := IF(@existe = 0,
    "ALTER TABLE insumos ADD COLUMN categoria ENUM('CARNES','GRANOS','LACTEOS','FRUTAS_VERDURAS','BEBIDAS','ABARROTES','DESECHABLES','LIMPIEZA','MOBILIARIO','OTROS') NOT NULL DEFAULT 'OTROS' AFTER nombre",
    'SELECT ''La columna categoria ya existe'' AS aviso');
PREPARE paso FROM @sql;
EXECUTE paso;
DEALLOCATE PREPARE paso;

-- Categoría de los insumos de ejemplo (solo si siguen en OTROS)
UPDATE insumos SET categoria = 'GRANOS' WHERE codigo = 'INS-001' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'CARNES' WHERE codigo = 'INS-002' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'CARNES' WHERE codigo = 'INS-003' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'FRUTAS_VERDURAS' WHERE codigo = 'INS-004' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'FRUTAS_VERDURAS' WHERE codigo = 'INS-005' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'FRUTAS_VERDURAS' WHERE codigo = 'INS-006' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'ABARROTES' WHERE codigo = 'INS-007' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'ABARROTES' WHERE codigo = 'INS-008' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'LACTEOS' WHERE codigo = 'INS-009' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'LACTEOS' WHERE codigo = 'INS-010' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'BEBIDAS' WHERE codigo = 'INS-011' AND categoria = 'OTROS';
UPDATE insumos SET categoria = 'FRUTAS_VERDURAS' WHERE codigo = 'INS-012' AND categoria = 'OTROS';

SELECT categoria, COUNT(*) AS insumos FROM insumos GROUP BY categoria ORDER BY categoria;
