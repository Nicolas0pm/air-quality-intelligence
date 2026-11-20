"""Servidor de AIR QUALITY INTELLIGENCE.

Sólo usa la biblioteca estándar de Python (http.server + sqlite3).
Ejecutar:  python backend/server.py   →  http://localhost:8000
"""
import csv
import io
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FRONTEND, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    # ------------------------------------------------------------ utilidades
    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    # ---------------------------------------------------------------- GET
    def do_GET(self):
        url = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(url.query).items()}
        p = url.path.rstrip("/")
        try:
            if p == "/api/catalogo":
                return self._json(db.catalogo())
            if p == "/api/dashboard":
                return self._json(db.dashboard(qs.get("desde"), qs.get("fuente")))
            if p == "/api/sesiones":
                return self._json(db.listar_sesiones())
            if p.startswith("/api/sesiones/"):
                s = db.obtener_sesion(int(p.split("/")[-1]))
                return self._json(s) if s else self._json({"error": "No existe"}, 404)
            if p == "/api/prediccion":
                filtros = qs.get("filtros", "HEPA").split(",")
                return self._json(db.predecir(float(qs.get("pm25", 50)), filtros))
            if p == "/api/reporte.csv":
                return self._csv()
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 400)
        return super().do_GET()

    def _csv(self):
        rows = db.listar_sesiones(10000)
        buf = io.StringIO()
        campos = ["id", "fecha_ingreso", "fuente", "filtros", "minutos", "pm25_in", "pm25_out",
                  "pm10_in", "pm10_out", "co2_in", "co2_out", "co_in", "co_out",
                  "nivel_inicial", "nivel_final", "resultado"]
        w = csv.DictWriter(buf, fieldnames=campos, extrasaction="ignore", delimiter=";")
        w.writeheader()
        w.writerows(rows)
        body = ("﻿" + buf.getvalue()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=reporte_calidad_aire.csv")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------------------------------------------------------------- POST
    def do_POST(self):
        p = urlparse(self.path).path.rstrip("/")
        try:
            b = self._body()
            if p == "/api/sesiones":
                med = b.get("medicion")
                return self._json(db.registrar_ingreso(b.get("fuente", "Exterior urbano"),
                                                       b.get("ubicacion") or "Cámara principal", med), 201)
            if p.startswith("/api/sesiones/") and p.endswith("/purificar"):
                sid = int(p.split("/")[-2])
                return self._json(db.purificar(sid, b.get("filtros", []), b.get("minutos", 20)))
            if p.startswith("/api/alertas/") and p.endswith("/atender"):
                with db.conectar() as con:
                    con.execute("UPDATE alertas SET atendida=1 WHERE id=?", (int(p.split("/")[-2]),))
                return self._json({"ok": True})
        except KeyError:
            return self._json({"error": "Sesión no encontrada"}, 404)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 400)
        return self._json({"error": "Ruta no encontrada"}, 404)


def main():
    db.inicializar()
    port = int(os.environ.get("PORT", 8000))
    print(f"AIR QUALITY INTELLIGENCE en http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
