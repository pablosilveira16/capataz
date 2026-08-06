#!/usr/bin/env python3
"""Capataz — el tablero de la cuadrilla de agentes.

    ./run.sh          →  http://127.0.0.1:5402

Sirve dos cosas y nada más:

    /              capataz.html, la pantalla — pensada para un teléfono
    /api/estado    lo que `lector.py` sabe de cada proyecto vigilado, en JSON

**No hay POST.** No es un olvido: es la regla 1 de `CLAUDE.md` puesta en la
puerta. El panel de ERP 360 tiene un `POST /api/marca` porque *escribe* las
marcas; capataz no escribe ninguna, así que no tiene por dónde. Lo que quiera
marcar algo usa el `panel/agente.py` de su propio proyecto.

Sin dependencias: sólo biblioteca estándar, como `panel/panel.py` de ERP 360.
El motivo está en el andamio —un proyecto que necesita instalar algo para
verificarse es un proyecto donde el agente depende de que vos estés— y acá se
suma otro: capataz mira proyectos ajenos y no debe imponerles nada.

El puerto es el **5402**. Los vecinos ocupados están en `ops/00-mapa.md`: 5300,
5301 y 5302 en la VM de Oracle, 5400 la app de ERP 360, 5401 su panel.
"""
import io
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import lector

AQUI = os.path.dirname(os.path.abspath(__file__))
PROYECTOS = os.environ.get("CAPATAZ_PROYECTOS") or os.path.join(AQUI, "proyectos.json")
PAGINA = os.path.join(AQUI, "capataz.html")

# El puerto vive acá y en `ops/00-mapa.md`. Un puerto declarado en dos lugares
# que se separan es cómo se elige uno ocupado; `pruebas/verificar-angosto.py`
# verifica que los dos digan lo mismo.
PUERTO_POR_DEFECTO = 5402
PUERTO = int(os.environ.get("CAPATAZ_PUERTO", PUERTO_POR_DEFECTO))

# La pantalla se refresca sola cada 15 s y cada refresco corre unos cuantos
# `git` sobre cada proyecto. Esto es una foto de hace un rato, no un estado:
# se descarta entera y se vuelve a leer del disco. Capataz no guarda nada.
CACHE_SEG = 5
_cache = {"ts": 0.0, "datos": None}


def estado():
    ahora = time.time()
    if _cache["datos"] is not None and ahora - _cache["ts"] < CACHE_SEG:
        return _cache["datos"]
    proyectos = lector.leer_proyectos(PROYECTOS)
    datos = {
        "ahora": ahora,
        "cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": PROYECTOS,
        "puerto": PUERTO,
        "proyectos": lector.mirar_todo(proyectos, ahora),
        "sin_proyectos": not proyectos,
    }
    _cache["ts"] = ahora
    _cache["datos"] = datos
    return datos


class Capataz(BaseHTTPRequestHandler):
    server_version = "capataz"

    def _mandar(self, cuerpo, tipo="application/json; charset=utf-8", codigo=200):
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta in ("/", "/index.html"):
            try:
                with io.open(PAGINA, encoding="utf-8") as f:
                    return self._mandar(f.read(), "text/html; charset=utf-8")
            except OSError as e:
                return self._mandar("no encuentro capataz.html: %s" % e,
                                    "text/plain; charset=utf-8", 500)
        if ruta == "/api/estado":
            return self._mandar(json.dumps(estado(), ensure_ascii=False,
                                           default=str))
        self._mandar('{"error":"no existe"}', codigo=404)

    def log_message(self, *_):
        """Sin log de acceso: son cuatro pedidos por minuto de un poll."""


def render_estatico(destino):
    """La misma pantalla con los datos incrustados, en un archivo suelto.

    Existe por una razón concreta: **el ancho angosto hay que mirarlo**, y el
    navegador de la Mac no llega al 5402 del contenedor de un agente. Con esto
    se abre un `file://` de 360 px y se mira de verdad, en vez de suponer.
    `run.sh --instantanea` lo genera; no se versiona (`.gitignore`).
    """
    with io.open(PAGINA, encoding="utf-8") as f:
        html = f.read()
    datos = json.dumps(estado(), ensure_ascii=False, default=str)
    marca = "<!--DATOS-INCRUSTADOS-->"
    inyeccion = '<script>window.CAPATAZ_DATOS = %s;</script>' % datos
    if marca in html:
        html = html.replace(marca, inyeccion)
    else:
        html = html.replace("</head>", inyeccion + "</head>")
    with io.open(destino, "w", encoding="utf-8") as f:
        f.write(html)
    return destino


if __name__ == "__main__":
    import sys
    if "--instantanea" in sys.argv:
        i = sys.argv.index("--instantanea")
        destino = sys.argv[i + 1] if len(sys.argv) > i + 1 else os.path.join(
            AQUI, "_instantanea.html")
        print("instantánea:", render_estatico(destino))
        raise SystemExit(0)
    print("\n  Capataz  ->  http://127.0.0.1:%d\n" % PUERTO)
    print("  Proyectos vigilados: %s" % PROYECTOS)
    for p in lector.leer_proyectos(PROYECTOS):
        print("    · %-12s %s" % (p["nombre"], p["ruta"]))
    print("\n  Capataz sólo lee. No marca puntos, no lanza agentes.\n")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Capataz).serve_forever()
