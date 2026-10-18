-- =====================================================================
--  StockPot - Script 04: datos de ejemplo (insumos y proveedores)
--  Opcional: sirve para probar el sistema y para la demostración.
--  Ejecutar DESPUÉS de 01, 02 y 03. Se puede ejecutar más de una vez:
--  INSERT IGNORE salta los registros que ya existen (mismo código o NIT).
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- Insumos con su inventario inicial (el conteo con el que arranca el
-- restaurante). Desde aquí, el stock solo cambia con compras recibidas
-- y con las entradas y salidas de inventario.
-- ---------------------------------------------------------------------
INSERT IGNORE INTO insumos (codigo, nombre, unidad_medida, stock_actual) VALUES
 ('INS-001', 'Arroz blanco',        'KG',     25.000),
 ('INS-002', 'Pechuga de pollo',    'KG',     12.500),
 ('INS-003', 'Carne de res',        'KG',      8.000),
 ('INS-004', 'Papa pastusa',        'KG',     30.000),
 ('INS-005', 'Tomate chonto',       'KG',      6.000),
 ('INS-006', 'Cebolla cabezona',    'KG',      5.000),
 ('INS-007', 'Aceite vegetal',      'L',      10.000),
 ('INS-008', 'Sal',                 'KG',      3.000),
 ('INS-009', 'Huevo',               'UNIDAD', 90.000),
 ('INS-010', 'Leche entera',        'L',       8.000),
 ('INS-011', 'Gaseosa 400 ml',      'UNIDAD', 48.000),
 ('INS-012', 'Limón',               'KG',      2.000);

-- ---------------------------------------------------------------------
-- Proveedores
-- ---------------------------------------------------------------------
INSERT IGNORE INTO proveedores (nit, razon_social, contacto, telefono, email, direccion) VALUES
 ('900123456-7', 'Distribuidora La Cosecha',  'Carlos Ruiz',   '6075551234', 'ventas@lacosecha.co',   'Cl. 10 #5-20, Cúcuta'),
 ('900765432-1', 'Avícola El Gallo de Oro',   'Marta Gómez',   '3109998877', 'pedidos@gallodeoro.co', 'Av. 4 #12-45, Cúcuta'),
 ('901112233-4', 'Bebidas y Lácteos del Norte', 'Jorge Pérez', '3155556677', 'jorge@lacteosnorte.co', 'Zona Industrial, Cúcuta');

-- ---------------------------------------------------------------------
-- Insumos que vende cada proveedor (RF-02.4), con su precio habitual.
-- Se buscan por NIT y código, así no dependemos de los id.
-- ---------------------------------------------------------------------
INSERT IGNORE INTO proveedor_insumos (proveedor_id, insumo_id, precio_referencia)
SELECT p.id, i.id, d.precio
FROM (
  SELECT '900123456-7' AS nit, 'INS-001' AS codigo, 4200 AS precio UNION ALL
  SELECT '900123456-7', 'INS-004', 1800 UNION ALL
  SELECT '900123456-7', 'INS-005', 3500 UNION ALL
  SELECT '900123456-7', 'INS-006', 2800 UNION ALL
  SELECT '900123456-7', 'INS-007', 9500 UNION ALL
  SELECT '900123456-7', 'INS-008', 1500 UNION ALL
  SELECT '900123456-7', 'INS-012', 4000 UNION ALL
  SELECT '900765432-1', 'INS-002', 13000 UNION ALL
  SELECT '900765432-1', 'INS-003', 26000 UNION ALL
  SELECT '900765432-1', 'INS-009', 550 UNION ALL
  SELECT '901112233-4', 'INS-010', 4800 UNION ALL
  SELECT '901112233-4', 'INS-011', 2200
) AS d
JOIN proveedores p ON p.nit = d.nit
JOIN insumos i ON i.codigo = d.codigo;
