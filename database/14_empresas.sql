-- =====================================================================
--  StockPot - Script 14: varios restaurantes (empresas) y súper administrador, tercer corte.
--  NO borra datos: todo lo que ya existe pasa a ser del restaurante 1 («StockPot Restaurante»).
--  (Si creas la base desde cero con 01_schema.sql y 02_seed.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
--
--  Después de ejecutarlo:
--   1. Todos deben cerrar sesión y volver a entrar (los tokens anteriores ya no sirven).
--   2. Para crear el súper administrador, desde la carpeta backend:  flask crear-superadmin
-- =====================================================================
USE stockpot;
SET SQL_SAFE_UPDATES = 0;  -- MySQL Workbench no deja UPDATE sin llave; se restaura al final

-- 1. Tabla de empresas y el primer restaurante
CREATE TABLE IF NOT EXISTS empresas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(120) NOT NULL,
    nit         VARCHAR(20)  NOT NULL UNIQUE,
    telefono    VARCHAR(20),
    email       VARCHAR(120),
    direccion   VARCHAR(200),
    activa      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT IGNORE INTO empresas (id, nombre, nit) VALUES (1, 'StockPot Restaurante', '900000001-1');

-- 2. empresa_id en cada tabla del restaurante; lo que ya existe queda en el restaurante 1
-- roles
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'roles' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE roles ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna roles.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE roles SET empresa_id = 1 WHERE empresa_id IS NULL AND nombre <> 'SUPERADMIN';
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'roles' AND constraint_name = 'fk_roles_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE roles ADD CONSTRAINT fk_roles_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_roles_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
-- nombre pasa de único en todo StockPot a único en cada restaurante
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'roles' AND index_name = 'uq_roles_empresa_nombre');
SET @sql := IF(@existe = 0, "ALTER TABLE roles ADD UNIQUE KEY uq_roles_empresa_nombre (empresa_id, nombre)",
               'SELECT ''El índice uq_roles_empresa_nombre ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'roles' AND index_name = 'nombre');
SET @sql := IF(@existe > 0, 'ALTER TABLE roles DROP INDEX nombre',
               'SELECT ''El índice único roles.nombre ya no existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- usuarios
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'usuarios' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE usuarios ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna usuarios.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE usuarios SET empresa_id = 1 WHERE empresa_id IS NULL
  AND rol_id NOT IN (SELECT id FROM roles WHERE nombre = 'SUPERADMIN');
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'usuarios' AND constraint_name = 'fk_usuarios_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_usuarios_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- proveedores
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'proveedores' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE proveedores ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna proveedores.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE proveedores SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE proveedores MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'proveedores' AND constraint_name = 'fk_proveedores_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE proveedores ADD CONSTRAINT fk_proveedores_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_proveedores_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
-- nit pasa de único en todo StockPot a único en cada restaurante
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'proveedores' AND index_name = 'uq_proveedores_empresa_nit');
SET @sql := IF(@existe = 0, "ALTER TABLE proveedores ADD UNIQUE KEY uq_proveedores_empresa_nit (empresa_id, nit)",
               'SELECT ''El índice uq_proveedores_empresa_nit ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'proveedores' AND index_name = 'nit');
SET @sql := IF(@existe > 0, 'ALTER TABLE proveedores DROP INDEX nit',
               'SELECT ''El índice único proveedores.nit ya no existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- insumos
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'insumos' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE insumos ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna insumos.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE insumos SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE insumos MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'insumos' AND constraint_name = 'fk_insumos_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE insumos ADD CONSTRAINT fk_insumos_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_insumos_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
-- codigo pasa de único en todo StockPot a único en cada restaurante
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'insumos' AND index_name = 'uq_insumos_empresa_codigo');
SET @sql := IF(@existe = 0, "ALTER TABLE insumos ADD UNIQUE KEY uq_insumos_empresa_codigo (empresa_id, codigo)",
               'SELECT ''El índice uq_insumos_empresa_codigo ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'insumos' AND index_name = 'codigo');
SET @sql := IF(@existe > 0, 'ALTER TABLE insumos DROP INDEX codigo',
               'SELECT ''El índice único insumos.codigo ya no existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- ordenes_compra
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'ordenes_compra' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE ordenes_compra ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna ordenes_compra.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE ordenes_compra SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE ordenes_compra MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'ordenes_compra' AND constraint_name = 'fk_ordenes_compra_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE ordenes_compra ADD CONSTRAINT fk_ordenes_compra_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_ordenes_compra_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- movimientos_inventario
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'movimientos_inventario' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE movimientos_inventario ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna movimientos_inventario.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE movimientos_inventario SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE movimientos_inventario MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'movimientos_inventario' AND constraint_name = 'fk_movimientos_inventario_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE movimientos_inventario ADD CONSTRAINT fk_movimientos_inventario_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_movimientos_inventario_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- productos
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'productos' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE productos ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna productos.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE productos SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE productos MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'productos' AND constraint_name = 'fk_productos_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE productos ADD CONSTRAINT fk_productos_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_productos_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
-- codigo pasa de único en todo StockPot a único en cada restaurante
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'productos' AND index_name = 'uq_productos_empresa_codigo');
SET @sql := IF(@existe = 0, "ALTER TABLE productos ADD UNIQUE KEY uq_productos_empresa_codigo (empresa_id, codigo)",
               'SELECT ''El índice uq_productos_empresa_codigo ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'productos' AND index_name = 'codigo');
SET @sql := IF(@existe > 0, 'ALTER TABLE productos DROP INDEX codigo',
               'SELECT ''El índice único productos.codigo ya no existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- clientes
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'clientes' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE clientes ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna clientes.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE clientes SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE clientes MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'clientes' AND constraint_name = 'fk_clientes_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE clientes ADD CONSTRAINT fk_clientes_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_clientes_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
-- telefono pasa de único en todo StockPot a único en cada restaurante
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'clientes' AND index_name = 'uq_clientes_empresa_telefono');
SET @sql := IF(@existe = 0, "ALTER TABLE clientes ADD UNIQUE KEY uq_clientes_empresa_telefono (empresa_id, telefono)",
               'SELECT ''El índice uq_clientes_empresa_telefono ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'clientes' AND index_name = 'telefono');
SET @sql := IF(@existe > 0, 'ALTER TABLE clientes DROP INDEX telefono',
               'SELECT ''El índice único clientes.telefono ya no existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- ordenes
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'ordenes' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE ordenes ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna ordenes.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE ordenes SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE ordenes MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'ordenes' AND constraint_name = 'fk_ordenes_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE ordenes ADD CONSTRAINT fk_ordenes_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_ordenes_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- domicilios
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'domicilios' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE domicilios ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna domicilios.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE domicilios SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE domicilios MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'domicilios' AND constraint_name = 'fk_domicilios_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE domicilios ADD CONSTRAINT fk_domicilios_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_domicilios_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- mesas
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'mesas' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE mesas ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna mesas.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE mesas SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE mesas MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'mesas' AND constraint_name = 'fk_mesas_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE mesas ADD CONSTRAINT fk_mesas_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_mesas_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
-- numero pasa de único en todo StockPot a único en cada restaurante
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'mesas' AND index_name = 'uq_mesas_empresa_numero');
SET @sql := IF(@existe = 0, "ALTER TABLE mesas ADD UNIQUE KEY uq_mesas_empresa_numero (empresa_id, numero)",
               'SELECT ''El índice uq_mesas_empresa_numero ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'stockpot' AND table_name = 'mesas' AND index_name = 'numero');
SET @sql := IF(@existe > 0, 'ALTER TABLE mesas DROP INDEX numero',
               'SELECT ''El índice único mesas.numero ya no existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- pedidos_mesa
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'pedidos_mesa' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE pedidos_mesa ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna pedidos_mesa.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE pedidos_mesa SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE pedidos_mesa MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'pedidos_mesa' AND constraint_name = 'fk_pedidos_mesa_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE pedidos_mesa ADD CONSTRAINT fk_pedidos_mesa_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_pedidos_mesa_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- pagos
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'pagos' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE pagos ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna pagos.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE pagos SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE pagos MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'pagos' AND constraint_name = 'fk_pagos_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE pagos ADD CONSTRAINT fk_pagos_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_pagos_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- ventas
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'ventas' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE ventas ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna ventas.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE ventas SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE ventas MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'ventas' AND constraint_name = 'fk_ventas_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE ventas ADD CONSTRAINT fk_ventas_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_ventas_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- incidencias
SET @existe := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stockpot' AND table_name = 'incidencias' AND column_name = 'empresa_id');
SET @sql := IF(@existe = 0, "ALTER TABLE incidencias ADD COLUMN empresa_id INT NULL AFTER id",
               'SELECT ''La columna incidencias.empresa_id ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;
UPDATE incidencias SET empresa_id = 1 WHERE empresa_id IS NULL;
ALTER TABLE incidencias MODIFY empresa_id INT NOT NULL;
SET @existe := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'stockpot' AND table_name = 'incidencias' AND constraint_name = 'fk_incidencias_empresa');
SET @sql := IF(@existe = 0, "ALTER TABLE incidencias ADD CONSTRAINT fk_incidencias_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)",
               'SELECT ''La llave fk_incidencias_empresa ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

-- 3. Rol y permiso del súper administrador (no se le dan al ADMINISTRADOR de un restaurante)
INSERT IGNORE INTO permisos (codigo, modulo, descripcion) VALUES
 ('empresas.gestionar', 'empresas', 'Crear, modificar, activar y desactivar restaurantes');

INSERT INTO roles (empresa_id, nombre, descripcion)
SELECT NULL, 'SUPERADMIN', 'Administra los restaurantes (empresas); no ve sus datos'
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE nombre = 'SUPERADMIN' AND empresa_id IS NULL);

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r JOIN permisos p ON p.codigo = 'empresas.gestionar'
WHERE r.nombre = 'SUPERADMIN' AND r.empresa_id IS NULL;

-- Comprobación: todo debe quedar en el restaurante 1, salvo el rol SUPERADMIN
SELECT 'roles' AS tabla, empresa_id, COUNT(*) AS filas FROM roles GROUP BY empresa_id
UNION ALL SELECT 'usuarios', empresa_id, COUNT(*) FROM usuarios GROUP BY empresa_id
UNION ALL SELECT 'insumos', empresa_id, COUNT(*) FROM insumos GROUP BY empresa_id
UNION ALL SELECT 'ventas', empresa_id, COUNT(*) FROM ventas GROUP BY empresa_id;

SET SQL_SAFE_UPDATES = 1;
