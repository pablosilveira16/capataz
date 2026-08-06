#!/usr/bin/env python3
"""Capataz — el tablero de la cuadrilla de agentes.

    ./run.sh          →  http://127.0.0.1:5402

Sirve dos cosas y nada más:

    /              capataz.html, la pantalla — pensada para un teléfono
    /api/estado    lo que capataz sabe de cada proyecto vigilado, en JSON

**Capataz mira la nube.** Desde el 2026-08-06 los datos salen de GitHub y no de
ninguna carpeta local: `nube.py` los trae por git y `lector.py` los entiende.
Las dos mitades están separadas porque una se prueba contra los repositorios de
verdad y la otra sin red — el porqué está escrito arriba de cada archivo.

**No hay POST.** No es un olvido: es la regla 1 de `CLAUDE.md` puesta en la
puerta. El panel de ERP 360 tiene un `POST /api/marca` porque *escribe* las
marcas; capataz no escribe ninguna, así que no tiene por dónde.

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
import nube

AQUI = os.path.dirname(os.path.abspath(__file__))
PROYECTOS = os.environ.get("CAPATAZ_PROYECTOS") or os.path.join(AQUI, "proyectos.json")
PAGINA = os.path.join(AQUI, "capataz.html")

# El puerto vive acá y en `ops/00-mapa.md`. Un puerto declarado en dos lugares
# que se separan es cómo se elige uno ocupado; `pruebas/verificar-angosto.py`
# verifica que los dos digan lo mismo.
PUERTO_POR_DEFECTO = 5402
PUERTO = int(os.environ.get("CAPATAZ_PUERTO", PUERTO_POR_DEFECTO))

# La pantalla se refresca sola cada 15 s. Esta caché es de la vista armada; la
# que decide cada cuánto se le vuelve a preguntar a GitHub es `nube.REFRESCO`,
# y son dos cosas distintas: armar la vista es gratis, salir a la red no.
#
# Las dos son fotos de hace un rato y ninguna es un estado: se descartan
# enteras y se vuelven a leer. Capataz no guarda nada que no esté en GitHub.
CACHE_SEG = 5
_cache = {"ts": 0.0, "datos": None}


def _mirar(proy, ahora):
    """Un proyecto: traerlo de la nube y entenderlo. Y el CI, si está prendido.

    El CI es el único dato que git no puede contestar y por el que hay que ir a
    `api.github.com` —que desde el contenedor de un agente no se alcanza—. Por
    eso va detrás de `CAPATAZ_CI=1` y **sin ella el resultado se queda en «no
    sé», nunca en verde**.
    """
    datos = nube.leer(proy, ahora=ahora)
    respuesta, motivo = nube.pedir_ci(
        proy.get("repo") or "", proy.get("rama_principal") or "main",
        nube._archivo_token(proy))
    datos["ci"] = respuesta
    datos["motivo_ci"] = motivo
    return lector.mirar(proy, datos, ahora)


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
        "espejos": nube.ESPEJOS,
        "proyectos": [_mirar(p, ahora) for p in proyectos],
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
        print("    · %-12s %s" % (p["nombre"], p["repo"] or "(sin repo)"))
    print("  Espejos de sólo lectura en: %s" % nube.ESPEJOS)
    print("\n  Capataz sólo lee. No marca puntos, no lanza agentes.\n")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Capataz).serve_forever()
