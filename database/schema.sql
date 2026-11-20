-- AIR QUALITY INTELLIGENCE - Esquema de base de datos (SQLite)
-- Versión equivalente para PostgreSQL: schema_postgresql.sql

CREATE TABLE IF NOT EXISTS filtros (
    codigo        TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    descripcion   TEXT
);

-- Una sesión = un lote de aire que entra, se purifica y se valida
CREATE TABLE IF NOT EXISTS sesiones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_ingreso    TEXT NOT NULL,             -- fecha y hora de ingreso (ISO 8601)
    fuente           TEXT NOT NULL,             -- origen del aire
    ubicacion        TEXT,
    estado           TEXT NOT NULL DEFAULT 'INGRESADO', -- INGRESADO | PURIFICADO
    filtros          TEXT,                      -- códigos separados por coma
    minutos          INTEGER,                   -- tiempo de purificación
    nivel_inicial    INTEGER,                   -- 0 Buena ... 5 Peligrosa
    nivel_final      INTEGER,
    resultado        TEXT                       -- Excelente | Satisfactorio | Parcial | Insuficiente
);

-- Mediciones de entrada, durante el proceso y de salida
CREATE TABLE IF NOT EXISTS mediciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id   INTEGER NOT NULL REFERENCES sesiones(id) ON DELETE CASCADE,
    etapa       TEXT NOT NULL CHECK (etapa IN ('entrada','proceso','salida')),
    minuto      INTEGER NOT NULL DEFAULT 0,
    fecha_hora  TEXT NOT NULL,
    pm25        REAL NOT NULL,   -- µg/m³
    pm10        REAL NOT NULL,   -- µg/m³
    co2         REAL NOT NULL,   -- ppm
    co          REAL NOT NULL    -- ppm
);
CREATE INDEX IF NOT EXISTS ix_med_sesion ON mediciones(sesion_id, etapa);

CREATE TABLE IF NOT EXISTS alertas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id   INTEGER REFERENCES sesiones(id) ON DELETE CASCADE,
    fecha_hora  TEXT NOT NULL,
    etapa       TEXT NOT NULL,
    severidad   TEXT NOT NULL,   -- MEDIA | ALTA | CRÍTICA
    mensaje     TEXT NOT NULL,
    atendida    INTEGER NOT NULL DEFAULT 0
);

-- Vista BI: antes vs. después y porcentaje de reducción por sesión
CREATE VIEW IF NOT EXISTS v_resultados AS
SELECT s.id, s.fecha_ingreso, s.fuente, s.filtros, s.minutos,
       s.nivel_inicial, s.nivel_final, s.resultado,
       e.pm25 AS pm25_in, o.pm25 AS pm25_out,
       e.pm10 AS pm10_in, o.pm10 AS pm10_out,
       e.co2  AS co2_in,  o.co2  AS co2_out,
       e.co   AS co_in,   o.co   AS co_out,
       ROUND((e.pm25 - o.pm25) * 100.0 / e.pm25, 1) AS red_pm25,
       ROUND((e.pm10 - o.pm10) * 100.0 / e.pm10, 1) AS red_pm10,
       ROUND((e.co2  - o.co2 ) * 100.0 / e.co2 , 1) AS red_co2,
       ROUND((e.co   - o.co  ) * 100.0 / e.co  , 1) AS red_co
FROM sesiones s
JOIN mediciones e ON e.sesion_id = s.id AND e.etapa = 'entrada'
JOIN mediciones o ON o.sesion_id = s.id AND o.etapa = 'salida'
WHERE s.estado = 'PURIFICADO';
