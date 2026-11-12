-- =====================================================================
--  StockPot - Script 17: turnos y cierre de caja (arqueo).
--  Requiere el script 14 (empresas). NO borra datos: solo crea la tabla turnos_caja.
--  (Si creas la base desde cero con 01_schema.sql y 02_seed.sql, ya incluye todo esto.)
--  Se puede ejecutar más de una vez sin duplicar nada.
--  Usa los permisos que ya existen: pagos.gestionar (abrir y cerrar) y pagos.ver (consultar).
-- =====================================================================
USE stockpot;

CREATE TABLE IF NOT EXISTS turnos_caja (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id              INT NOT NULL,                      -- restaurante dueño de la fila
    estado                  ENUM('ABIERTO','CERRADO') NOT NULL DEFAULT 'ABIERTO',
    base_inicial            DECIMAL(14,2) NOT NULL DEFAULT 0,  -- efectivo con el que empieza la caja
    abierto_por_id          INT           NOT NULL,
    abierto_en              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cerrado_por_id          INT,
    cerrado_en              DATETIME,
    esperado_efectivo       DECIMAL(14,2),                     -- base + pagos en efectivo
    esperado_tarjeta        DECIMAL(14,2),
    esperado_transferencia  DECIMAL(14,2),
    contado_efectivo        DECIMAL(14,2),                     -- lo que contó el cajero
    contado_tarjeta         DECIMAL(14,2),
    contado_transferencia   DECIMAL(14,2),
    num_pagos               INT           NOT NULL DEFAULT 0,
    propinas                DECIMAL(12,2) NOT NULL DEFAULT 0,  -- del personal, incluidas en lo recibido
    observacion             VARCHAR(255),                      -- obligatoria si no cuadra
    CONSTRAINT chk_turno_base CHECK (base_inicial >= 0),
    CONSTRAINT fk_turno_abre   FOREIGN KEY (abierto_por_id) REFERENCES usuarios(id),
    CONSTRAINT fk_turno_cierra FOREIGN KEY (cerrado_por_id) REFERENCES usuarios(id),
    CONSTRAINT fk_turnos_caja_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    INDEX idx_turno_estado (empresa_id, estado),
    INDEX idx_turno_cierre (cerrado_en)
);

SELECT COUNT(*) AS columnas_de_turnos_caja FROM information_schema.columns
WHERE table_schema = 'stockpot' AND table_name = 'turnos_caja';
