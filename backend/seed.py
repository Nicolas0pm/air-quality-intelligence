"""Carga datos de prueba: 40 sesiones de los últimos 14 días.
Ejecutar:  python backend/seed.py   (borra y recrea la base de datos)"""
import os
import random
from datetime import datetime, timedelta

import db

PLANES = [  # (fuente, filtros, minutos) — incluye combinaciones mal elegidas a propósito
    ("Exterior urbano", ["PRE", "HEPA"], 20),
    ("Exterior urbano", ["HEPA"], 15),
    ("Zona industrial", ["PRE", "HEPA", "CARBON", "CATALIZADOR"], 30),
    ("Zona industrial", ["PRE", "HEPA", "CARBON", "CATALIZADOR", "CO2"], 35),
    ("Zona industrial", ["HEPA"], 20),
    ("Interior oficina", ["HEPA", "CO2"], 20),
    ("Interior oficina", ["CARBON"], 15),
    ("Tráfico vehicular", ["PRE", "HEPA", "CATALIZADOR"], 25),
    ("Tráfico vehicular", ["PRE", "HEPA", "CARBON", "CATALIZADOR"], 30),
]


def main(n=40, semilla=2026):
    rng = random.Random(semilla)
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    db.inicializar()
    inicio = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=14)
    for i in range(n):
        fuente, filtros, minutos = rng.choice(PLANES)
        fecha = inicio + timedelta(hours=i * 8 + rng.randint(0, 5), minutes=rng.randint(0, 59))
        s = db.registrar_ingreso(fuente, "Cámara principal", fecha=fecha, rng=rng)
        db.purificar(s["id"], filtros, minutos + rng.choice([-5, 0, 0, 5]), rng=rng)
    print(f"{n} sesiones creadas en {os.path.abspath(db.DB_PATH)}")


if __name__ == "__main__":
    main()
