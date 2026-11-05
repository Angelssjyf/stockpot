-- =====================================================================
--  StockPot - Script 02: datos iniciales (roles y permisos)
--  Ejecutar DESPUÉS de 01_schema.sql.
--
--  El usuario administrador NO se crea aquí: su contraseña debe guardarse
--  cifrada, y eso lo hará la aplicación Flask (paso 3).
-- =====================================================================
USE stockpot;

-- ---------------------------------------------------------------------
-- 0. El primer restaurante (empresa 1). Cada restaurante tiene sus propios
--    roles y datos; el súper administrador solo crea y activa empresas.
-- ---------------------------------------------------------------------
INSERT INTO empresas (id, nombre, nit) VALUES (1, 'StockPot Restaurante', '900000001-1');

-- ---------------------------------------------------------------------
-- 1. Roles del restaurante (empresa 1) y el del súper administrador (sin empresa)
-- ---------------------------------------------------------------------
INSERT INTO roles (empresa_id, nombre, descripcion) VALUES
 (1, 'ADMINISTRADOR', 'Dueño o administrador: acceso total al sistema'),
 (1, 'MESERO',        'Toma pedidos en mesa y gestiona reservas'),
 (1, 'COCINERO',      'Ve y actualiza las órdenes en cocina'),
 (1, 'CAJERO',        'Registra pagos, ventas y domicilios'),
 (1, 'BODEGUERO',     'Gestiona inventario, proveedores y compras'),
 (1, 'DOMICILIARIO',  'Consulta y entrega los pedidos a domicilio'),
 (NULL, 'SUPERADMIN', 'Administra los restaurantes (empresas); no ve sus datos');

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
 ('reportes.ver',          'reportes',    'Generar reportes y estadísticas'),
 -- Incidencias (RF-12, sugerencia de la sustentación del 2.º corte)
 ('incidencias.reportar',  'incidencias', 'Reportar errores en inventario, ventas y compras'),
 ('incidencias.ver',       'incidencias', 'Ver la bitácora de incidencias'),
 ('incidencias.gestionar', 'incidencias', 'Administrar el catálogo de códigos de incidencia'),
 -- Varios restaurantes (tercer corte): solo para el súper administrador
 ('empresas.gestionar',    'empresas',    'Crear, modificar, activar y desactivar restaurantes');

-- ---------------------------------------------------------------------
-- 3. Permisos de cada rol (tabla rol_permisos)
--    Se buscan los id por nombre y código, así no dependemos de qué
--    número le asignó MySQL a cada registro.
-- ---------------------------------------------------------------------

-- ADMINISTRADOR: todos los permisos del restaurante
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r CROSS JOIN permisos p
WHERE r.nombre = 'ADMINISTRADOR' AND p.modulo <> 'empresas';

-- SUPERADMIN: solo administrar empresas
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r JOIN permisos p ON p.codigo = 'empresas.gestionar'
WHERE r.nombre = 'SUPERADMIN';

-- Resto de roles: solo lo que necesitan para su trabajo
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p ON (
     (r.nombre = 'MESERO'       AND p.codigo IN ('productos.ver', 'pedidos.ver', 'pedidos.gestionar',
                                                 'reservas.ver', 'reservas.gestionar', 'incidencias.reportar'))
  OR (r.nombre = 'COCINERO'     AND p.codigo IN ('cocina.ver', 'cocina.gestionar',
                                                 'productos.ver', 'inventario.ver', 'incidencias.reportar'))
  OR (r.nombre = 'CAJERO'       AND p.codigo IN ('pedidos.ver', 'pedidos.gestionar', 'productos.ver',
                                                 'pagos.ver', 'pagos.gestionar', 'ventas.ver',
                                                 'domicilios.ver', 'domicilios.gestionar', 'incidencias.reportar'))
  OR (r.nombre = 'BODEGUERO'    AND p.codigo IN ('inventario.ver', 'inventario.gestionar',
                                                 'proveedores.ver', 'proveedores.gestionar',
                                                 'compras.ver', 'compras.gestionar', 'productos.ver',
                                                 'incidencias.reportar'))
  OR (r.nombre = 'DOMICILIARIO' AND p.codigo IN ('domicilios.ver', 'incidencias.reportar'))
);

-- ---------------------------------------------------------------------
-- 4. RF-12.1 Catálogo inicial de códigos de incidencia
--    corrige_stock = 1: al reportarlo se indica la cantidad real y se hace el ajuste.
-- ---------------------------------------------------------------------
INSERT INTO codigos_incidencia (codigo, modulo, nombre, corrige_stock) VALUES
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

-- RF-12.5 Domicilios. causa_externa = 1: lo causa el cliente y no se le cuenta al domiciliario
INSERT INTO codigos_incidencia (codigo, modulo, nombre, corrige_stock, causa_externa) VALUES
 ('DOM-01', 'DOMICILIOS', 'El cliente no salió o no contestó', 0, 1),
 ('DOM-02', 'DOMICILIOS', 'Dirección errada o incompleta', 0, 1),
 ('DOM-03', 'DOMICILIOS', 'Pedido incompleto o equivocado', 0, 0),
 ('DOM-04', 'DOMICILIOS', 'Pedido llegó dañado o derramado', 0, 0),
 ('DOM-05', 'DOMICILIOS', 'Demora en la entrega', 0, 0),
 ('DOM-06', 'DOMICILIOS', 'El cliente no pagó o rechazó el pedido', 0, 1);
