# Air Quality Intelligence

Sistema inteligente para el monitoreo, la descontaminación y la purificación del aire, con dashboard de inteligencia de negocios.

**Video demostrativo:** https://youtu.be/3qx19wCI_6U

## Cómo ejecutarlo

Solo necesita Python 3.10 o superior (no hay que instalar paquetes para la aplicación).

```bash
python backend/seed.py      # crea la base de datos con 40 lotes de prueba
python backend/server.py    # abre http://localhost:8000
```

Para regenerar las gráficas del análisis (requiere matplotlib y numpy):

```bash
cd backend && python analisis.py && python diagrama.py
python backend/video.py docs/video.mp4 edge-tts   # video narrado (requiere ffmpeg y pip install edge-tts)
```

## Base de datos

La base de datos de demostración está en `database/air_quality.db` (SQLite) con 41 lotes y 1.031 mediciones. Para verla sin instalar nada, las tablas están exportadas en [`database/csv/`](database/csv): `sesiones`, `mediciones`, `alertas`, `filtros` y la vista `v_resultados` (antes vs. después y % de reducción).

## Módulos

| Pestaña | Qué hace |
|---|---|
| 1 · Monitoreo | Detecta el ingreso de aire, registra fecha y hora, mide PM2.5, PM10, CO₂ y CO, clasifica el nivel y recomienda filtros. |
| 2 · Descontaminación | Selección de filtros, tiempo de funcionamiento, simulación con registro minuto a minuto. |
| 3 · Validación | Medición de salida, comparación antes y después, % de reducción y resultado del tratamiento. |
| Dashboard | 6 indicadores, 4 gráficos, alertas y modelo predictivo de tiempo. |
| Reportes | Resumen por fuente, detalle de lotes, CSV e impresión. |

Enlace directo a un lote: `http://localhost:8000/#validacion/12`.

## Estructura

```
backend/   calidad.py (reglas, simulador, alertas, modelo) · db.py · server.py · seed.py · analisis.py · diagrama.py
frontend/  index.html · app.js (React 18 + htm, sin compilación) · styles.css
database/  schema.sql (SQLite) · schema_postgresql.sql · air_quality.db · csv/ (tablas exportadas)
analisis/  gráficas, capturas y resumen.json
docs/      informe técnico (.docx) y guion del video
```

## API

- `GET /api/dashboard?fuente=&desde=` · `GET /api/sesiones` · `GET /api/sesiones/{id}`
- `POST /api/sesiones` `{fuente, medicion?}` · `POST /api/sesiones/{id}/purificar` `{filtros, minutos}`
- `GET /api/prediccion?pm25=&filtros=` · `GET /api/reporte.csv`
