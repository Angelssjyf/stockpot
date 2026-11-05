-- =====================================================================
--  StockPot - Script 15: reservas (RF-07.1 a RF-07.8), tercer corte.
--  Requiere el script 14 (empresas). NO borra datos: solo crea la tabla reservas.
--  (Si creas la base desde cero con 01_schema.sql y 02_seed.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
--  Los permisos reservas.ver y reservas.gestionar ya existen desde el script 02 (MESERO y ADMINISTRADOR).
-- =====================================================================
USE stockpot;

CREATE TABLE IF NOT EXISTS reservas (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id        INT NOT NULL,                       -- restaurante dueño de la fila
    codigo            VARCHAR(20)   NOT NULL UNIQUE,      -- RES-000001
    mesa_id           INT           NOT NULL,             -- RF-07.6
    cliente           VARCHAR(120)  NOT NULL,
    telefono          VARCHAR(20)   NOT NULL,
    personas          INT           NOT NULL,
    fecha_hora        DATETIME      NOT NULL,             -- RF-07.5
    duracion_minutos  INT           NOT NULL DEFAULT 120, -- cuánto se aparta la mesa
    estado            ENUM('PENDIENTE','CONFIRMADA','CUMPLIDA','NO_ASISTIO','CANCELADA')
                      NOT NULL DEFAULT 'PENDIENTE',       -- RF-07.8
    observaciones     VARCHAR(255),
    usuario_id        INT           NOT NULL,             -- quién la registró
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_reserva_personas CHECK (personas > 0),
    CONSTRAINT chk_reserva_duracion CHECK (duracion_minutos BETWEEN 30 AND 360),
    CONSTRAINT fk_reserva_mesa    FOREIGN KEY (mesa_id)    REFERENCES mesas(id),
    CONSTRAINT fk_reserva_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_reservas_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    INDEX idx_reserva_fecha (fecha_hora),
    INDEX idx_reserva_mesa_fecha (mesa_id, fecha_hora)
);

SELECT COUNT(*) AS columnas_de_reservas FROM information_schema.columns
WHERE table_schema = 'stockpot' AND table_name = 'reservas';
