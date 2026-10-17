-- =====================================================================
--  StockPot - Script 03: usuario de MySQL para la aplicación Flask
--  Ejecutar DESPUÉS de 01_schema.sql y 02_seed.sql, conectado como root.
--
--  ⚠️ Antes de ejecutarlo, cambia 'CAMBIA_ESTA_CLAVE' por una contraseña
--     propia SOLO en el editor de Workbench. No guardes la contraseña real
--     en este archivo: se sube a GitHub y la vería todo el mundo.
-- =====================================================================

-- Usuario que solo puede conectarse desde este mismo PC (localhost)
CREATE USER IF NOT EXISTS 'stockpot_app'@'localhost' IDENTIFIED BY 'CAMBIA_ESTA_CLAVE';

-- Mínimo privilegio: solo leer y modificar datos de la base stockpot.
-- No puede crear ni borrar tablas, ni tocar otras bases, ni crear usuarios.
GRANT SELECT, INSERT, UPDATE, DELETE ON stockpot.* TO 'stockpot_app'@'localhost';

FLUSH PRIVILEGES;
