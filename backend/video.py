"""Genera el video demostrativo (MP4, 1920x1080) a partir de las capturas y gráficas.
Requiere matplotlib y ffmpeg.  Ejecutar:  python backend/video.py [salida.mp4]"""
import os
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
A = os.path.join(BASE, "analisis")
CAP = os.path.join(A, "capturas")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "docs", "video_demo.mp4")

OSCURO, ACENTO, TEXTO = "#0b2b33", "#5eead4", "#15232d"

# (título, imagen, recorte (y0, y1) en px o None, texto, segundos)
ESCENAS = [
    ("AIR QUALITY INTELLIGENCE", None, None,
     "Sistema inteligente para el monitoreo, descontaminación y purificación del aire\n"
     "Inteligencia de Negocios · Manuela Beltrán University", 10),
    ("El reto", None, None,
     "¿Cómo identificar el ingreso de aire contaminado, analizar sus componentes,\n"
     "controlar la descontaminación y verificar el aire purificado con indicadores de BI?", 14),
    ("Arquitectura", os.path.join(A, "fig_arquitectura.png"), None,
     "Sensores de entrada → purificación → validación. Un backend en Python clasifica, controla los filtros\n"
     "y guarda todo en SQLite/PostgreSQL; la interfaz en React muestra el dashboard.", 22),
    ("Módulo 1 · Monitoreo del aire contaminado", os.path.join(CAP, "monitoreo.png"), None,
     "Se registra fecha y hora de ingreso y se miden PM2.5, PM10, CO₂ y CO. Cada contaminante se clasifica\n"
     "con la Resolución 2254 de 2017, se generan alertas y se recomiendan los filtros adecuados.", 24),
    ("Módulo 2 · Selección de filtros y tiempo", os.path.join(CAP, "proceso_sel.png"), None,
     "HEPA para partículas, catalizador de hopcalita para CO, adsorbente para CO₂.\n"
     "El modelo predictivo estima cuántos minutos se necesitan antes de activar el proceso.", 22),
    ("Módulo 2 · Registro durante el proceso", os.path.join(CAP, "proceso_run.png"), None,
     "Se guarda una medición por minuto. Las curvas siguen C(t) = F + (C₀ − F)·e^(−kt):\n"
     "en 30 minutos el PM2.5 pasa de 142,6 a 2 µg/m³.", 20),
    ("Módulo 3 · Validación del aire purificado", os.path.join(CAP, "validacion.png"), None,
     "Nueva medición, comparación de valores iniciales y finales y % de reducción.\n"
     "Resultado del tratamiento: Excelente · Satisfactorio · Parcial · Insuficiente.", 20),
    ("Módulo 4 · Dashboard de inteligencia de negocios", os.path.join(CAP, "dashboard.png"), (0, 760),
     "Indicadores: PM2.5 antes/después, CO₂ en ppm, % de reducción, tiempo de purificación,\n"
     "cumplimiento y alertas. Gráficos comparativos de entrada y salida.", 24),
    ("Dashboard · Eficiencia, niveles, alertas y predicción", os.path.join(CAP, "dashboard.png"), (760, 1520),
     "Eficiencia por combinación de filtros, distribución de niveles al ingreso,\n"
     "alertas recientes y modelo predictivo del tiempo de purificación.", 22),
    ("Reportes para la toma de decisiones", os.path.join(CAP, "reportes.png"), (0, 760),
     "Resumen por fuente de aire y detalle de cada lote. Exportación a CSV e impresión.", 16),
    ("Resultados · Antes vs. después", os.path.join(A, "fig_antes_despues.png"), None,
     "41 lotes analizados: el PM2.5 baja 92,2 % (de 84,8 a 3,8 µg/m³) y el PM10 91,6 %.\n"
     "82,9 % de los lotes sale en nivel Bueno o Aceptable.", 20),
    ("Resultados · Eficiencia por filtros", os.path.join(A, "fig_eficiencia.png"), None,
     "El HEPA no actúa sobre gases y el carbón activado solo es la peor opción.\n"
     "Con catalizador el CO baja más de 96 %; con adsorbente el CO₂ baja entre 50 y 71 %.", 20),
    ("Componente de inteligencia · Modelo predictivo", os.path.join(A, "fig_modelo.png"), None,
     "La constante k se ajusta por mínimos cuadrados con el histórico de cada combinación de filtros.\n"
     "Con HEPA, un aire de 100 µg/m³ llega a 12 µg/m³ en unos 10 minutos.", 20),
    ("Conclusiones", None, None,
     "• La aplicación cumple el ciclo completo: detecta, clasifica, purifica, valida y reporta.\n"
     "• Los 7 lotes que no cumplieron tenían un gas sin tratar: la selección de filtros es clave.\n"
     "• En interiores el problema es el CO₂ y requiere adsorbente o renovación de aire.\n"
     "• Siguiente paso: conectar sensores físicos a la misma API.\n\n"
     "github.com/Nicolas0pm/air-quality-intelligence", 22),
]


def escena(path, titulo, img, recorte, texto):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor("#f3f6f8")
    if img is None:  # diapositiva de texto
        fig.patch.set_facecolor(OSCURO)
        largo = texto.count("\n") > 2
        fig.text(0.5, 0.80 if largo else 0.62, titulo, ha="center", va="center", fontsize=54, fontweight="bold", color=ACENTO)
        fig.text(0.5, 0.42 if largo else 0.40, texto, ha="center", va="center", fontsize=26, color="white", linespacing=1.7)
    else:
        bar = fig.add_axes([0, 0.91, 1, 0.09]); bar.axis("off")
        bar.add_patch(plt.Rectangle((0, 0), 1, 1, color=OSCURO, transform=bar.transAxes))
        bar.text(0.025, 0.5, titulo, va="center", fontsize=30, fontweight="bold", color="white", transform=bar.transAxes)
        im = mpimg.imread(img)
        if recorte:
            im = im[recorte[0]:recorte[1]]
        ax = fig.add_axes([0.03, 0.17, 0.94, 0.72]); ax.axis("off")
        ax.imshow(im, interpolation="lanczos")
        cap = fig.add_axes([0, 0, 1, 0.15]); cap.axis("off")
        cap.add_patch(plt.Rectangle((0, 0), 1, 1, color="white", transform=cap.transAxes))
        cap.text(0.5, 0.5, texto, ha="center", va="center", fontsize=23, color=TEXTO, linespacing=1.55, transform=cap.transAxes)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    tmp = tempfile.mkdtemp(prefix="aqi_video_")
    lista = []
    for i, (t, img, rec, txt, seg) in enumerate(ESCENAS):
        p = os.path.join(tmp, f"s{i:02d}.png")
        escena(p, t, img, rec, txt)
        lista.append((p, seg))
    concat = os.path.join(tmp, "lista.txt")
    with open(concat, "w") as f:
        for p, seg in lista:
            f.write(f"file '{p}'\nduration {seg}\n")
        f.write(f"file '{lista[-1][0]}'\n")
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat,
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-movflags", "+faststart", OUT], check=True)
    print(OUT, sum(s for _, s in lista), "s")


if __name__ == "__main__":
    main()
