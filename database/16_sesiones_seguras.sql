-- =====================================================================
--  StockPot - Script 16: sesiones seguras (tercer corte).
--  PIN personal para cobrar, anular pagos y sacar inventario, y sesiones guardadas para
--  bloquear la pantalla y cerrar por inactividad. NO borra datos.
--  (Si creas la base desde cero con 01_schema.sql y 02_seed.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
--
--  Después de ejecutarlo todos deben iniciar sesión de nuevo, y cada persona que cobre o
--  saque inventario crea su PIN (la aplicación se lo pide la primera vez).
-- =====================================================================
USE stockpot;

SET @existe := (SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'stockpot' AND table_name = 'usuarios' AND column_name = 'pin_hash');
SET @sql := IF(@existe = 0, "ALTER TABLE usuarios ADD COLUMN pin_hash VARCHAR(255) NULL AFTER password_hash",
               'SELECT ''La columna usuarios.pin_hash ya existe'' AS aviso');
PREPARE paso FROM @sql; EXECUTE paso; DEALLOCATE PREPARE paso;

CREATE TABLE IF NOT EXISTS sesiones (
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

SELECT COUNT(*) AS columnas_de_sesiones FROM information_schema.columns
WHERE table_schema = 'stockpot' AND table_name = 'sesiones';
