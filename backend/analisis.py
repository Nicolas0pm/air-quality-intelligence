"""Análisis de resultados: antes vs. después del tratamiento.
Genera gráficas PNG y un resumen JSON en ../analisis/.
Ejecutar:  python backend/analisis.py"""
import json
import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import calidad as q  # noqa: E402
import db  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analisis")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e5e9ec"})
ANTES, DESPUES = "#c2410c", "#0f766e"


def main():
    con = db.conectar()
    r = [dict(x) for x in con.execute("SELECT * FROM v_resultados ORDER BY fecha_ingreso")]
    n = len(r)
    prom = lambda k: float(np.mean([x[k] for x in r]))  # noqa: E731
    res = {"n": n}
    for c in q.CONTAMINANTES:
        res[c] = {"antes": round(prom(c + "_in"), 2), "despues": round(prom(c + "_out"), 2),
                  "reduccion": round(prom("red_" + c), 1)}
    res["minutos"] = round(prom("minutos"), 1)
    res["cumplimiento"] = round(sum(x["nivel_final"] <= 1 for x in r) / n * 100, 1)
    res["resultados"] = {k: sum(x["resultado"] == k for x in r) for k in
                         ["Excelente", "Satisfactorio", "Parcial", "Insuficiente"]}
    res["niveles_in"] = {q.nombre_nivel(i): sum(x["nivel_inicial"] == i for x in r) for i in range(6)}
    res["niveles_out"] = {q.nombre_nivel(i): sum(x["nivel_final"] == i for x in r) for i in range(6)}

    # Eficiencia por combinación
    combos = {}
    for x in r:
        combos.setdefault(x["filtros"], []).append(x)
    res["combos"] = sorted([{
        "filtros": k, "n": len(v),
        "red_pm25": round(np.mean([i["red_pm25"] for i in v]), 1),
        "red_pm10": round(np.mean([i["red_pm10"] for i in v]), 1),
        "red_co": round(np.mean([i["red_co"] for i in v]), 1),
        "red_co2": round(np.mean([i["red_co2"] for i in v]), 1),
        "minutos": round(np.mean([i["minutos"] for i in v]), 1),
        "cumple": round(np.mean([i["nivel_final"] <= 1 for i in v]) * 100, 1),
    } for k, v in combos.items()], key=lambda d: -d["n"])

    # Por fuente
    fuentes = {}
    for x in r:
        fuentes.setdefault(x["fuente"], []).append(x)
    res["fuentes"] = sorted([{
        "fuente": k, "n": len(v),
        "pm25_in": round(np.mean([i["pm25_in"] for i in v]), 1),
        "pm25_out": round(np.mean([i["pm25_out"] for i in v]), 1),
        "co_in": round(np.mean([i["co_in"] for i in v]), 2),
        "co_out": round(np.mean([i["co_out"] for i in v]), 2),
        "co2_in": round(np.mean([i["co2_in"] for i in v])),
        "co2_out": round(np.mean([i["co2_out"] for i in v])),
        "cumple": round(np.mean([i["nivel_final"] <= 1 for i in v]) * 100, 1),
    } for k, v in fuentes.items()], key=lambda d: -d["n"])

    res["modelos"] = db.modelo_k()
    res["alertas"] = {row[0]: row[1] for row in con.execute(
        "SELECT severidad, COUNT(*) FROM alertas GROUP BY severidad")}
    res["alertas_etapa"] = {f"{a}|{b}": c for a, b, c in con.execute(
        "SELECT etapa, severidad, COUNT(*) FROM alertas GROUP BY etapa, severidad")}
    res["mediciones"] = con.execute("SELECT COUNT(*) FROM mediciones").fetchone()[0]

    # Validación del modelo predictivo: error en sesiones reales (tiempo para PM2.5 ≤ 12)
    errores = []
    for x in r:
        k = res["modelos"].get(x["filtros"], {}).get("k")
        pred = q.predecir_minutos(x["pm25_in"], k) if k else None
        real = con.execute("SELECT MIN(minuto) FROM mediciones WHERE sesion_id=? AND pm25<=12 AND minuto>0",
                           (x["id"],)).fetchone()[0]
        if pred is not None and real is not None and x["pm25_in"] > 12:
            errores.append(abs(pred - real))
    res["modelo_mae"] = round(float(np.mean(errores)), 2) if errores else None
    res["modelo_n"] = len(errores)

    # ---------------- Gráficas
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.4))
    for a, (c, t) in zip(ax, [("pm25", "PM2.5 (µg/m³)"), ("pm10", "PM10 (µg/m³)"), ("co", "CO (ppm)")]):
        v = [res[c]["antes"], res[c]["despues"]]
        b = a.bar(["Entrada", "Salida"], v, color=[ANTES, DESPUES], width=.6)
        a.bar_label(b, labels=[f"{x:.1f}" for x in v], padding=2)
        a.set_title(f"{t}\n−{res[c]['reduccion']} %", fontsize=10)
        a.grid(axis="x", visible=False)
    fig.suptitle("Concentración promedio antes y después del tratamiento", fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_antes_despues.png"), dpi=170)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.6))
    idx = np.arange(n)
    ax.plot(idx, [x["pm25_in"] for x in r], color=ANTES, marker="o", ms=3, label="Entrada")
    ax.plot(idx, [x["pm25_out"] for x in r], color=DESPUES, marker="o", ms=3, label="Salida")
    ax.axhline(12, color="#94a3b8", ls="--", lw=1, label="Límite nivel Bueno (12 µg/m³)")
    ax.set_xlabel("Lote (orden cronológico)")
    ax.set_ylabel("PM2.5 (µg/m³)")
    ax.legend(frameon=False)
    ax.set_title("PM2.5 de entrada y salida por lote", fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_serie_pm25.png"), dpi=170)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    cs = res["combos"]
    y = np.arange(len(cs))
    h = .26
    ax.barh(y - h, [c["red_pm25"] for c in cs], h, color="#0f766e", label="PM2.5")
    ax.barh(y, [c["red_co"] for c in cs], h, color="#6366f1", label="CO")
    ax.barh(y + h, [c["red_co2"] for c in cs], h, color="#d97706", label="CO₂")
    ax.set_yticks(y, [c["filtros"].replace(",", " + ") + f"  (n={c['n']})" for c in cs], fontsize=8)
    ax.set_xlim(-5, 100)
    ax.set_xlabel("% de reducción promedio")
    ax.legend(frameon=False, loc="lower right")
    ax.invert_yaxis()
    ax.set_title("Eficiencia por combinación de filtros", fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_eficiencia.png"), dpi=170)
    plt.close(fig)

    # Curva del modelo predictivo vs. datos reales (combinación más usada con PM)
    combo = next(c["filtros"] for c in cs if "HEPA" in c["filtros"])
    k = res["modelos"][combo]["k"]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ids = [x["id"] for x in r if x["filtros"] == combo]
    for i, sid in enumerate(ids):
        pts = con.execute("SELECT minuto, pm25 FROM mediciones WHERE sesion_id=? ORDER BY minuto", (sid,)).fetchall()
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#94a3b8", lw=.8, alpha=.7,
                label="Lotes reales" if i == 0 else None)
    c0 = 100
    t = np.linspace(0, 30, 200)
    ax.plot(t, q.FONDO["pm25"] + (c0 - q.FONDO["pm25"]) * np.exp(-k * t), color="#0f766e", lw=2.4,
            label=f"Modelo, C₀ = 100 µg/m³ (k = {k} min⁻¹)")
    ax.axhline(12, color=ANTES, ls="--", lw=1, label="Objetivo 12 µg/m³")
    ax.set_xlabel("Minuto de funcionamiento")
    ax.set_ylabel("PM2.5 (µg/m³)")
    ax.set_title(f"Modelo predictivo de decaimiento — filtros {combo.replace(',', ' + ')}", fontweight="bold")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_modelo.png"), dpi=170)
    plt.close(fig)
    res["modelo_combo"] = combo

    json.dump(res, open(os.path.join(OUT, "resumen.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
