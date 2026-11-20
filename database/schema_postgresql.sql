-- AIR QUALITY INTELLIGENCE - Esquema para PostgreSQL (despliegue en servidor)

CREATE TABLE IF NOT EXISTS filtros (
    codigo        VARCHAR(20) PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    descripcion   TEXT
);

CREATE TABLE IF NOT EXISTS sesiones (
    id               SERIAL PRIMARY KEY,
    fecha_ingreso    TIMESTAMP NOT NULL,
    fuente           VARCHAR(60) NOT NULL,
    ubicacion        VARCHAR(100),
    estado           VARCHAR(20) NOT NULL DEFAULT 'INGRESADO',
    filtros          VARCHAR(100),
    minutos          INTEGER,
    nivel_inicial    SMALLINT,
    nivel_final      SMALLINT,
    resultado        VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS mediciones (
    id          SERIAL PRIMARY KEY,
    sesion_id   INTEGER NOT NULL REFERENCES sesiones(id) ON DELETE CASCADE,
    etapa       VARCHAR(10) NOT NULL CHECK (etapa IN ('entrada','proceso','salida')),
    minuto      INTEGER NOT NULL DEFAULT 0,
    fecha_hora  TIMESTAMP NOT NULL,
    pm25        NUMERIC(7,1) NOT NULL,
    pm10        NUMERIC(7,1) NOT NULL,
    co2         NUMERIC(7,0) NOT NULL,
    co          NUMERIC(6,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_med_sesion ON mediciones(sesion_id, etapa);

CREATE TABLE IF NOT EXISTS alertas (
    id          SERIAL PRIMARY KEY,
    sesion_id   INTEGER REFERENCES sesiones(id) ON DELETE CASCADE,
    fecha_hora  TIMESTAMP NOT NULL,
    etapa       VARCHAR(10) NOT NULL,
    severidad   VARCHAR(10) NOT NULL,
    mensaje     TEXT NOT NULL,
    atendida    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE OR REPLACE VIEW v_resultados AS
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
