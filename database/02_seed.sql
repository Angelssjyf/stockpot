-- =====================================================================
--  StockPot - Script 02: datos iniciales (roles y permisos)
--  Ejecutar DESPUÉS de 01_schema.sql.
--
--  El usuario administrador NO se crea aquí: su contraseña debe guardarse
--  cifrada, y eso lo hará la aplicación Flask (paso 3).
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- 1. Roles del restaurante
-- ---------------------------------------------------------------------
INSERT INTO roles (nombre, descripcion) VALUES
 ('ADMINISTRADOR', 'Dueño o administrador: acceso total al sistema'),
 ('MESERO',        'Toma pedidos en mesa y gestiona reservas'),
 ('COCINERO',      'Ve y actualiza las órdenes en cocina'),
 ('CAJERO',        'Registra pagos, ventas y domicilios'),
 ('BODEGUERO',     'Gestiona inventario, proveedores y compras'),
 ('DOMICILIARIO',  'Consulta y entrega los pedidos a domicilio');

-- ---------------------------------------------------------------------
-- 2. Permisos: uno para consultar (.ver) y otro para modificar
--    (.gestionar) en cada módulo. Se cargan todos desde ahora para que
--    los roles queden completos; cada módulo los usará en su iteración.
-- ---------------------------------------------------------------------
INSERT INTO permisos (codigo, modulo, descripcion) VALUES
 -- Iteración 1
 ('usuarios.ver',          'usuarios',    'Consultar usuarios'),
 ('usuarios.gestionar',    'usuarios',    'Registrar, modificar y desactivar usuarios'),
 ('roles.gestionar',       'usuarios',    'Asignar roles y gestionar permisos'),
 ('proveedores.ver',       'proveedores', 'Consultar proveedores'),
 ('proveedores.gestionar', 'proveedores', 'Registrar y modificar proveedores'),
 ('compras.ver',           'proveedores', 'Consultar órdenes de compra'),
 ('compras.gestionar',     'proveedores', 'Registrar y actualizar órdenes de compra'),
 -- Iteración 2
 ('inventario.ver',        'inventario',  'Consultar insumos y existencias'),
 ('inventario.gestionar',  'inventario',  'Registrar insumos, entradas y salidas'),
 ('productos.ver',         'productos',   'Consultar productos y menú'),
 ('productos.gestionar',   'productos',   'Registrar productos, recetas y precios'),
 -- Iteración 3
 ('pedidos.ver',           'pedidos',     'Consultar pedidos'),
 ('pedidos.gestionar',     'pedidos',     'Registrar y modificar pedidos'),
 ('cocina.ver',            'cocina',      'Ver órdenes pendientes en cocina'),
 ('cocina.gestionar',      'cocina',      'Actualizar el estado de preparación'),
 ('reservas.ver',          'reservas',    'Consultar reservas'),
 ('reservas.gestionar',    'reservas',    'Registrar, modificar y cancelar reservas'),
 -- Iteración 4
 ('domicilios.ver',        'domicilios',  'Consultar domicilios'),
 ('domicilios.gestionar',  'domicilios',  'Registrar y asignar domicilios'),
 ('pagos.ver',             'pagos',       'Consultar pagos'),
 ('pagos.gestionar',       'pagos',       'Registrar pagos y generar comprobantes'),
 ('ventas.ver',            'ventas',      'Consultar ventas y consumo'),
 ('reportes.ver',          'reportes',    'Generar reportes y estadísticas');

-- ---------------------------------------------------------------------
-- 3. Permisos de cada rol (tabla rol_permisos)
--    Se buscan los id por nombre y código, así no dependemos de qué
--    número le asignó MySQL a cada registro.
-- ---------------------------------------------------------------------

-- ADMINISTRADOR: todos los permisos
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r CROSS JOIN permisos p
WHERE r.nombre = 'ADMINISTRADOR';

-- Resto de roles: solo lo que necesitan para su trabajo
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p ON (
     (r.nombre = 'MESERO'       AND p.codigo IN ('productos.ver', 'pedidos.ver', 'pedidos.gestionar',
                                                 'reservas.ver', 'reservas.gestionar'))
  OR (r.nombre = 'COCINERO'     AND p.codigo IN ('cocina.ver', 'cocina.gestionar',
                                                 'productos.ver', 'inventario.ver'))
  OR (r.nombre = 'CAJERO'       AND p.codigo IN ('pedidos.ver', 'pedidos.gestionar', 'productos.ver',
                                                 'pagos.ver', 'pagos.gestionar', 'ventas.ver',
                                                 'domicilios.ver', 'domicilios.gestionar'))
  OR (r.nombre = 'BODEGUERO'    AND p.codigo IN ('inventario.ver', 'inventario.gestionar',
                                                 'proveedores.ver', 'proveedores.gestionar',
                                                 'compras.ver', 'compras.gestionar', 'productos.ver'))
  OR (r.nombre = 'DOMICILIARIO' AND p.codigo IN ('domicilios.ver'))
);
