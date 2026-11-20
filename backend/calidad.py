"""Reglas de negocio: clasificación de calidad del aire, catálogo de filtros,
simulación del proceso de purificación, alertas y modelo predictivo.

Umbrales de PM2.5, PM10 y CO tomados de los puntos de corte del Índice de
Calidad del Aire (ICA) de la Resolución 2254 de 2017 (Colombia). Para CO₂ se
usan umbrales de calidad de aire interior (ASHRAE 62.1 / práctica habitual).
"""
import math
import random

# ---------------------------------------------------------------------------
# 1. Clasificación
# ---------------------------------------------------------------------------
NIVELES = [
    # (orden, nombre, color)
    (0, "Buena", "#2e9d4f"),
    (1, "Aceptable", "#c9b400"),
    (2, "Dañina para grupos sensibles", "#e8820c"),
    (3, "Dañina para la salud", "#d6301f"),
    (4, "Muy dañina", "#8f3f97"),
    (5, "Peligrosa", "#7e0023"),
]

# Límite superior de cada nivel (el último es infinito)
UMBRALES = {
    "pm25": [12, 37, 55, 150, 250],     # µg/m³ (24 h)
    "pm10": [54, 154, 254, 354, 424],   # µg/m³ (24 h)
    "co":   [4.4, 9.4, 12.4, 15.4, 30.4],  # ppm (8 h)
    "co2":  [800, 1000, 1500, 2500, 5000],  # ppm (interior)
}

UNIDADES = {"pm25": "µg/m³", "pm10": "µg/m³", "co2": "ppm", "co": "ppm"}
NOMBRES = {"pm25": "PM2.5", "pm10": "PM10", "co2": "CO₂", "co": "CO"}
CONTAMINANTES = ["pm25", "pm10", "co2", "co"]


def nivel_contaminante(clave, valor):
    for i, lim in enumerate(UMBRALES[clave]):
        if valor <= lim:
            return i
    return 5


def clasificar(m):
    """Devuelve el nivel global (el peor de los cuatro) y el detalle."""
    detalle = {c: nivel_contaminante(c, m[c]) for c in CONTAMINANTES}
    peor = max(detalle.values())
    return peor, detalle


def nombre_nivel(i):
    return NIVELES[i][1]


# ---------------------------------------------------------------------------
# 2. Catálogo de tecnologías de purificación
#    k = constante de remoción por minuto en la cámara (modelo de primer orden)
# ---------------------------------------------------------------------------
FILTROS = {
    "PRE": {
        "nombre": "Prefiltro G4",
        "descripcion": "Retiene partículas gruesas y protege el filtro HEPA.",
        "k": {"pm25": 0.03, "pm10": 0.12, "co2": 0.0, "co": 0.0},
    },
    "HEPA": {
        "nombre": "Filtro HEPA H13",
        "descripcion": "Captura ≥ 99,95 % de partículas finas (PM2.5 y PM10).",
        "k": {"pm25": 0.22, "pm10": 0.20, "co2": 0.0, "co": 0.0},
    },
    "CARBON": {
        "nombre": "Carbón activado",
        "descripcion": "Adsorbe gases orgánicos y olores; remoción baja de CO.",
        "k": {"pm25": 0.02, "pm10": 0.02, "co2": 0.0, "co": 0.015},
    },
    "CATALIZADOR": {
        "nombre": "Catalizador de hopcalita",
        "descripcion": "Oxida el CO a CO₂ a temperatura ambiente.",
        "k": {"pm25": 0.0, "pm10": 0.0, "co2": 0.0, "co": 0.16},
    },
    "CO2": {
        "nombre": "Adsorbente de CO₂ (zeolita) + renovación de aire",
        "descripcion": "Reduce el CO₂ por adsorción e intercambio con aire limpio.",
        "k": {"pm25": 0.0, "pm10": 0.0, "co2": 0.12, "co": 0.0},
    },
}

# Valor de fondo al que tiende cada contaminante (no se llega a cero)
FONDO = {"pm25": 2.0, "pm10": 5.0, "co2": 420.0, "co": 0.2}

FUENTES = {
    "Exterior urbano": {"pm25": (30, 70), "pm10": (60, 130), "co2": (480, 650), "co": (2, 7)},
    "Zona industrial": {"pm25": (60, 180), "pm10": (120, 330), "co2": (600, 1100), "co": (6, 18)},
    "Interior oficina": {"pm25": (12, 35), "pm10": (25, 60), "co2": (1000, 2400), "co": (0.5, 3)},
    "Tráfico vehicular": {"pm25": (45, 110), "pm10": (90, 200), "co2": (550, 900), "co": (8, 25)},
}


def recomendar_filtros(m):
    """Selecciona las tecnologías según los contaminantes identificados."""
    _, det = clasificar(m)
    rec = []
    if det["pm10"] >= 1 or det["pm25"] >= 2:
        rec.append("PRE")
    if det["pm25"] >= 1 or det["pm10"] >= 1:
        rec.append("HEPA")
    if det["co"] >= 1:
        rec += ["CATALIZADOR", "CARBON"]
    if det["co2"] >= 1:
        rec.append("CO2")
    return rec or ["HEPA"]


# ---------------------------------------------------------------------------
# 3. Sensores y simulación
# ---------------------------------------------------------------------------
def leer_sensor(fuente, rng=random):
    r = FUENTES.get(fuente, FUENTES["Exterior urbano"])
    pm25 = rng.uniform(*r["pm25"])
    pm10 = max(pm25 * rng.uniform(1.4, 2.0), rng.uniform(*r["pm10"]))
    return {
        "pm25": round(pm25, 1),
        "pm10": round(pm10, 1),
        "co2": round(rng.uniform(*r["co2"])),
        "co": round(rng.uniform(*r["co"]), 2),
    }


def k_total(filtros):
    return {c: sum(FILTROS[f]["k"][c] for f in filtros if f in FILTROS) for c in CONTAMINANTES}


def simular(inicial, filtros, minutos, rng=random):
    """Curvas de decaimiento exponencial C(t) = F + (C0 − F)·e^(−k·t) con ruido
    de sensor. Devuelve una lectura por minuto (minuto 0 = entrada)."""
    k = k_total(filtros)
    lecturas = []
    for t in range(0, minutos + 1):
        fila = {"minuto": t}
        for c in CONTAMINANTES:
            c0, f = inicial[c], FONDO[c]
            base = c0 if c0 <= f else f + (c0 - f) * math.exp(-k[c] * t)
            sigma = 0.005 if c == "co2" else 0.02  # error típico del sensor
            ruido = 1 + rng.gauss(0, sigma) if t > 0 else 1
            v = max(base * ruido, 0)
            fila[c] = round(v, 2 if c == "co" else (0 if c == "co2" else 1))
        lecturas.append(fila)
    return lecturas


def reduccion(antes, despues):
    return {c: round((antes[c] - despues[c]) / antes[c] * 100, 1) if antes[c] else 0.0
            for c in CONTAMINANTES}


def clasificar_tratamiento(red, nivel_final):
    """Resultado del tratamiento a partir de la reducción de partículas y el nivel final."""
    red_pm = (red["pm25"] + red["pm10"]) / 2
    if nivel_final == 0 and red_pm >= 80:
        return "Excelente"
    if nivel_final <= 1 and red_pm >= 60:
        return "Satisfactorio"
    if nivel_final <= 2 and red_pm >= 40:
        return "Parcial"
    return "Insuficiente"  # algún contaminante sigue en nivel dañino o peor


# ---------------------------------------------------------------------------
# 4. Componente de inteligencia
# ---------------------------------------------------------------------------
def reglas_alerta(etapa, m):
    """Regla de alertas: devuelve lista de (severidad, mensaje)."""
    alertas = []
    _, det = clasificar(m)
    for c in CONTAMINANTES:
        n = det[c]
        txt = f"{NOMBRES[c]} = {m[c]} {UNIDADES[c]} ({nombre_nivel(n)})"
        if etapa == "entrada":
            if n >= 4:
                alertas.append(("CRÍTICA", f"Ingreso: {txt}. Activar purificación de inmediato."))
            elif n >= 2:
                alertas.append(("ALTA", f"Ingreso: {txt}."))
        else:  # salida
            if n >= 2:
                alertas.append(("ALTA", f"Salida sin cumplir: {txt}. Revisar filtro o ampliar tiempo."))
            elif n == 1 and c in ("pm25", "co"):
                alertas.append(("MEDIA", f"Salida en nivel Aceptable: {txt}."))
    return alertas


def ajustar_k(series):
    """Ajusta la constante de decaimiento k por mínimos cuadrados sobre
    ln((C − F)/(C0 − F)) = −k·t, a partir de los registros históricos."""
    num = den = 0.0
    for c0, puntos in series:
        f = FONDO["pm25"]
        if c0 - f <= 1:
            continue
        for t, v in puntos:
            if t == 0 or v - f <= 0.5:
                continue
            y = math.log((v - f) / (c0 - f))
            num += t * y
            den += t * t
    return -num / den if den else None


def predecir_minutos(c0, k, objetivo=12.0):
    """Minutos necesarios para llevar el PM2.5 desde c0 hasta el objetivo."""
    f = FONDO["pm25"]
    if c0 <= objetivo:
        return 0
    if not k or k <= 0:
        return None
    return math.ceil(math.log((c0 - f) / (objetivo - f)) / k)
