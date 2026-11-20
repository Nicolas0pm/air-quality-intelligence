"""Capa de datos (SQLite). Toda la lógica de los cuatro módulos pasa por aquí."""
import os
import random
import sqlite3
from datetime import datetime, timedelta

import calidad as q

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("AQI_DB", os.path.join(BASE, "..", "database", "air_quality.db"))
SCHEMA = os.path.join(BASE, "..", "database", "schema.sql")


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar():
    with conectar() as con:
        con.executescript(open(SCHEMA, encoding="utf-8").read())
        for cod, f in q.FILTROS.items():
            con.execute("INSERT OR REPLACE INTO filtros VALUES (?,?,?)",
                        (cod, f["nombre"], f["descripcion"]))


def _iso(dt):
    return dt.replace(microsecond=0).isoformat(sep=" ")


def _registrar_alertas(con, sesion_id, etapa, m, fecha):
    for sev, msg in q.reglas_alerta(etapa, m):
        con.execute("INSERT INTO alertas (sesion_id, fecha_hora, etapa, severidad, mensaje) "
                    "VALUES (?,?,?,?,?)", (sesion_id, fecha, etapa, sev, msg))


# ---------------------------------------------------------------- Módulo 1
def registrar_ingreso(fuente, ubicacion="Cámara principal", medicion=None, fecha=None, rng=random):
    """Detecta el ingreso de aire, toma la medición y clasifica el nivel."""
    fecha = fecha or datetime.now()
    m = medicion or q.leer_sensor(fuente, rng)
    m = {c: float(m[c]) for c in q.CONTAMINANTES}
    nivel, detalle = q.clasificar(m)
    with conectar() as con:
        cur = con.execute("INSERT INTO sesiones (fecha_ingreso, fuente, ubicacion, nivel_inicial) "
                          "VALUES (?,?,?,?)", (_iso(fecha), fuente, ubicacion, nivel))
        sid = cur.lastrowid
        con.execute("INSERT INTO mediciones (sesion_id, etapa, minuto, fecha_hora, pm25, pm10, co2, co) "
                    "VALUES (?,?,?,?,?,?,?,?)", (sid, "entrada", 0, _iso(fecha),
                                                 m["pm25"], m["pm10"], m["co2"], m["co"]))
        _registrar_alertas(con, sid, "entrada", m, _iso(fecha))
    return obtener_sesion(sid)


# ---------------------------------------------------------- Módulos 2 y 3
def purificar(sid, filtros, minutos, rng=random):
    """Simula la filtración, registra cada minuto y valida el aire de salida."""
    filtros = [f for f in filtros if f in q.FILTROS]
    if not filtros:
        raise ValueError("Seleccione al menos un filtro")
    minutos = max(1, min(int(minutos), 120))
    with conectar() as con:
        s = con.execute("SELECT * FROM sesiones WHERE id=?", (sid,)).fetchone()
        if not s:
            raise KeyError(sid)
        if s["estado"] == "PURIFICADO":
            raise ValueError("La sesión ya fue purificada")
        e = con.execute("SELECT * FROM mediciones WHERE sesion_id=? AND etapa='entrada'", (sid,)).fetchone()
        inicial = {c: e[c] for c in q.CONTAMINANTES}
        inicio = datetime.fromisoformat(s["fecha_ingreso"]) + timedelta(minutes=1)
        lecturas = q.simular(inicial, filtros, minutos, rng)
        for l in lecturas[1:]:
            etapa = "salida" if l["minuto"] == minutos else "proceso"
            con.execute("INSERT INTO mediciones (sesion_id, etapa, minuto, fecha_hora, pm25, pm10, co2, co) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (sid, etapa, l["minuto"], _iso(inicio + timedelta(minutes=l["minuto"])),
                         l["pm25"], l["pm10"], l["co2"], l["co"]))
        final = {c: lecturas[-1][c] for c in q.CONTAMINANTES}
        nivel_final, _ = q.clasificar(final)
        red = q.reduccion(inicial, final)
        resultado = q.clasificar_tratamiento(red, nivel_final)
        con.execute("UPDATE sesiones SET estado='PURIFICADO', filtros=?, minutos=?, nivel_final=?, "
                    "resultado=? WHERE id=?", (",".join(filtros), minutos, nivel_final, resultado, sid))
        _registrar_alertas(con, sid, "salida", final, _iso(inicio + timedelta(minutes=minutos)))
    return obtener_sesion(sid)


def obtener_sesion(sid):
    with conectar() as con:
        s = con.execute("SELECT * FROM sesiones WHERE id=?", (sid,)).fetchone()
        if not s:
            return None
        meds = [dict(r) for r in con.execute(
            "SELECT etapa, minuto, fecha_hora, pm25, pm10, co2, co FROM mediciones "
            "WHERE sesion_id=? ORDER BY minuto", (sid,))]
        alertas = [dict(r) for r in con.execute(
            "SELECT * FROM alertas WHERE sesion_id=? ORDER BY id", (sid,))]
    out = dict(s)
    entrada = next(m for m in meds if m["etapa"] == "entrada")
    salida = next((m for m in meds if m["etapa"] == "salida"), None)
    out["mediciones"] = meds
    out["entrada"] = entrada
    out["salida"] = salida
    out["alertas"] = alertas
    out["detalle_inicial"] = q.clasificar(entrada)[1]
    out["recomendados"] = q.recomendar_filtros(entrada)
    if salida:
        out["reduccion"] = q.reduccion(entrada, salida)
        out["detalle_final"] = q.clasificar(salida)[1]
    return out


def listar_sesiones(limite=200):
    with conectar() as con:
        rows = con.execute(
            "SELECT s.*, e.pm25 pm25_in, e.pm10 pm10_in, e.co2 co2_in, e.co co_in, "
            "o.pm25 pm25_out, o.pm10 pm10_out, o.co2 co2_out, o.co co_out "
            "FROM sesiones s JOIN mediciones e ON e.sesion_id=s.id AND e.etapa='entrada' "
            "LEFT JOIN mediciones o ON o.sesion_id=s.id AND o.etapa='salida' "
            "ORDER BY s.fecha_ingreso DESC LIMIT ?", (limite,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- Módulo 4
def modelo_k():
    """k de PM2.5 ajustado por combinación de filtros con los datos históricos."""
    with conectar() as con:
        rows = con.execute(
            "SELECT s.id, s.filtros, m.minuto, m.pm25 FROM sesiones s "
            "JOIN mediciones m ON m.sesion_id=s.id WHERE s.estado='PURIFICADO' "
            "ORDER BY s.id, m.minuto").fetchall()
    grupos = {}
    for r in rows:
        g = grupos.setdefault(r["filtros"], {})
        g.setdefault(r["id"], []).append((r["minuto"], r["pm25"]))
    modelos = {}
    for combo, sesiones in grupos.items():
        series = [(pts[0][1], pts) for pts in sesiones.values()]
        k = q.ajustar_k(series)
        if k:
            modelos[combo] = {"k": round(k, 4), "n": len(sesiones)}
    return modelos


def predecir(pm25, filtros):
    combo = ",".join(f for f in q.FILTROS if f in filtros)
    modelos = modelo_k()
    m = modelos.get(combo)
    origen = "histórico"
    if not m:  # sin historial: usa el k teórico del catálogo
        m = {"k": q.k_total(filtros)["pm25"], "n": 0}
        origen = "teórico"
    return {"combo": combo, "k": m["k"], "sesiones": m["n"], "origen": origen,
            "minutos": q.predecir_minutos(float(pm25), m["k"]), "objetivo": 12}


def dashboard(desde=None, fuente=None):
    filtro, params = "WHERE 1=1", []
    if desde:
        filtro += " AND fecha_ingreso >= ?"
        params.append(desde)
    if fuente:
        filtro += " AND fuente = ?"
        params.append(fuente)
    with conectar() as con:
        r = [dict(x) for x in con.execute(f"SELECT * FROM v_resultados {filtro} ORDER BY fecha_ingreso", params)]
        total = con.execute(f"SELECT COUNT(*) FROM sesiones {filtro}", params).fetchone()[0]
        alertas = [dict(x) for x in con.execute(
            "SELECT a.*, s.fuente FROM alertas a JOIN sesiones s ON s.id=a.sesion_id "
            "ORDER BY a.fecha_hora DESC LIMIT 15")]
        al_cnt = {row[0]: row[1] for row in con.execute(
            "SELECT severidad, COUNT(*) FROM alertas WHERE atendida=0 GROUP BY severidad")}
        niveles = {row[0]: row[1] for row in con.execute(
            f"SELECT nivel_inicial, COUNT(*) FROM sesiones {filtro} GROUP BY nivel_inicial", params)}
        fuentes = [row[0] for row in con.execute("SELECT DISTINCT fuente FROM sesiones ORDER BY 1")]

    def prom(campo):
        vals = [x[campo] for x in r if x[campo] is not None]
        return round(sum(vals) / len(vals), 1) if vals else 0

    por_combo = {}
    for x in r:
        g = por_combo.setdefault(x["filtros"], [])
        g.append(x)
    eficiencia = [{
        "filtros": k, "n": len(v),
        "red_pm25": round(sum(i["red_pm25"] for i in v) / len(v), 1),
        "red_co": round(sum(i["red_co"] for i in v) / len(v), 1),
        "red_co2": round(sum(i["red_co2"] for i in v) / len(v), 1),
        "minutos": round(sum(i["minutos"] for i in v) / len(v), 1),
    } for k, v in sorted(por_combo.items(), key=lambda kv: -len(kv[1]))]

    resultados = {}
    for x in r:
        resultados[x["resultado"]] = resultados.get(x["resultado"], 0) + 1

    return {
        "kpi": {
            "sesiones": total, "purificadas": len(r),
            "pm25_antes": prom("pm25_in"), "pm25_despues": prom("pm25_out"),
            "pm10_antes": prom("pm10_in"), "pm10_despues": prom("pm10_out"),
            "co2_antes": prom("co2_in"), "co2_despues": prom("co2_out"),
            "co_antes": prom("co_in"), "co_despues": prom("co_out"),
            "red_pm25": prom("red_pm25"), "red_pm10": prom("red_pm10"),
            "red_co2": prom("red_co2"), "red_co": prom("red_co"),
            "minutos": prom("minutos"),
            "cumplimiento": round(sum(1 for x in r if x["nivel_final"] <= 1) / len(r) * 100, 1) if r else 0,
        },
        "serie": r[-40:],
        "niveles": [{"nivel": q.nombre_nivel(i), "color": q.NIVELES[i][2], "n": niveles.get(i, 0)} for i in range(6)],
        "eficiencia": eficiencia,
        "resultados": resultados,
        "alertas": alertas,
        "alertas_cnt": al_cnt,
        "fuentes": fuentes,
        "modelos": modelo_k(),
    }


def catalogo():
    return {
        "filtros": {k: {"nombre": v["nombre"], "descripcion": v["descripcion"]} for k, v in q.FILTROS.items()},
        "fuentes": list(q.FUENTES),
        "niveles": [{"nombre": n, "color": c} for _, n, c in q.NIVELES],
        "umbrales": q.UMBRALES,
        "unidades": q.UNIDADES,
        "nombres": q.NOMBRES,
    }
