"""Dibuja el diagrama de arquitectura (analisis/fig_arquitectura.png)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analisis", "fig_arquitectura.png")
fig, ax = plt.subplots(figsize=(11, 4.6))
ax.set_xlim(0, 110); ax.set_ylim(0, 46); ax.axis("off")

def caja(x, y, w, h, titulo, lineas, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5",
                                fc=color + "22", ec=color, lw=1.6))
    ax.text(x + w / 2, y + h - 3, titulo, ha="center", va="top", fontsize=10.5, fontweight="bold", color="#15232d")
    ax.text(x + w / 2, y + h - 8.5, "\n".join(lineas), ha="center", va="top", fontsize=8.6, color="#334155", linespacing=1.45)

def flecha(x1, y1, x2, y2, txt=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, lw=1.4, color="#475569"))
    if txt:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.4, txt, ha="center", fontsize=7.8, color="#475569")

caja(1, 24, 22, 20, "1. Entrada de aire", ["Sensores PM2.5 / PM10", "(láser), NDIR CO₂,", "electroquímico CO", "Fecha y hora de ingreso"], "#c2410c")
caja(30, 24, 24, 20, "2. Purificación", ["Prefiltro G4 · HEPA H13", "Carbón activado", "Catalizador de hopcalita", "Adsorbente de CO₂", "Tiempo controlado"], "#6366f1")
caja(61, 24, 22, 20, "3. Validación", ["Sensores de salida", "Antes vs. después", "% de reducción", "Resultado del", "tratamiento"], "#0f766e")
caja(30, 1, 24, 18, "Backend Python", ["API REST (http.server)", "Reglas de clasificación", "Alertas · modelo predictivo", "Simulador de proceso"], "#0b2b33")
caja(61, 1, 22, 18, "Base de datos", ["SQLite / PostgreSQL", "sesiones · mediciones", "alertas · filtros", "vista v_resultados"], "#b45309")
caja(88, 12, 21, 26, "4. Software BI", ["Interfaz React", "Dashboard con KPI", "Gráficos comparativos", "Alertas", "Modelo predictivo", "Reportes CSV"], "#0f766e")

flecha(23.5, 34, 29.5, 34, "aire")
flecha(54.5, 34, 60.5, 34, "tratado")
flecha(12, 23.5, 29.5, 12, "lecturas")
flecha(42, 19.5, 42, 23.5)
ax.text(43, 21.5, "control de filtros y tiempo", ha="left", va="center", fontsize=7.8, color="#475569")
flecha(72, 23.5, 54.5, 14, "")
ax.text(66, 21, "lecturas", ha="center", fontsize=7.8, color="#475569")
flecha(54.5, 10, 60.5, 10, "SQL")
flecha(83.5, 10, 87.5, 18, "")
ax.text(87, 7.5, "API REST\n(JSON)", ha="center", fontsize=7.8, color="#475569")
fig.tight_layout()
fig.savefig(OUT, dpi=170)
