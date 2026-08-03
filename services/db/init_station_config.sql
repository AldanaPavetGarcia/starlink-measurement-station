-- ============================================================
-- init_station_config.sql — DB: station_config (ADR-10, semana 7)
-- PostgreSQL plano, SIN extensión TimescaleDB: station_metadata y
-- sensor_catalog son catálogos relacionales chicos, no series temporales
-- (docs/06_DER.md §5.1-§5.2, "sin CAGG"). Idempotente: IF NOT EXISTS.
-- ============================================================

CREATE TABLE IF NOT EXISTS station_metadata (
    node_id           VARCHAR(64)   PRIMARY KEY,
    location_name     VARCHAR(128)  NOT NULL,
    latitude          FLOAT8        NOT NULL,
    longitude         FLOAT8        NOT NULL,
    altitude_m        FLOAT8,
    deployed_at       TIMESTAMPTZ   NOT NULL,
    hardware_version  VARCHAR(32),
    status            VARCHAR(32)   NOT NULL,
    notes             TEXT,
    CONSTRAINT chk_station_latitude
        CHECK (latitude >= -90 AND latitude <= 90),
    CONSTRAINT chk_station_longitude
        CHECK (longitude >= -180 AND longitude <= 180),
    CONSTRAINT chk_station_status
        CHECK (status IN ('active', 'inactive', 'maintenance'))
);

CREATE INDEX IF NOT EXISTS idx_station_status
    ON station_metadata (status);

CREATE TABLE IF NOT EXISTS sensor_catalog (
    sensor_id           SERIAL       PRIMARY KEY,
    node_id             VARCHAR(64)  NOT NULL,
    sensor_model        VARCHAR(64)  NOT NULL,
    sensor_type         VARCHAR(32)  NOT NULL,
    bus_protocol        VARCHAR(8)   NOT NULL,
    bus_address         VARCHAR(4),
    calibration_offset  FLOAT8,
    calibration_scale   FLOAT8,
    last_calibrated_at  TIMESTAMPTZ,
    registered_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    is_active           BOOLEAN      NOT NULL,
    CONSTRAINT chk_sensor_type
        CHECK (sensor_type IN ('temperature', 'humidity', 'pressure', 'multi')),
    CONSTRAINT chk_sensor_bus
        CHECK (bus_protocol IN ('I2C', 'SPI', 'UART', 'WiFi', 'USB')),
    CONSTRAINT fk_sensor_node
        FOREIGN KEY (node_id)
        REFERENCES station_metadata (node_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sensor_node_active
    ON sensor_catalog (node_id, is_active)
    WHERE is_active = TRUE;

-- Seed del único nodo desplegado hasta ahora (RF-24) -- coordenadas del LIT,
-- FCEFyN/UNC. ON CONFLICT DO NOTHING: reinicios/docker-compose down-up (CA-03)
-- no deben pisar cambios manuales de status/notes hechos en producción.
INSERT INTO station_metadata (
    node_id, location_name, latitude, longitude, altitude_m,
    deployed_at, hardware_version, status, notes
) VALUES (
    'lit-cordoba-01',
    'Laboratorio LIT — FCEFyN, UNC, Córdoba',
    -31.4335,
    -64.1878,
    490.0,
    now(),
    NULL,
    'active',
    'Nodo de desarrollo — todavía sobre mock, hardware real recién en semana 10 (CLAUDE.md §1.1).'
)
ON CONFLICT (node_id) DO NOTHING;
