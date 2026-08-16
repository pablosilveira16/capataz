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
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import consola
import lector
import nube
import taller

AQUI = os.path.dirname(os.path.abspath(__file__))
PROYECTOS = os.environ.get("CAPATAZ_PROYECTOS") or os.path.join(AQUI, "proyectos.json")
PAGINA = os.path.join(AQUI, "capataz.html")

# El puerto vive acá y en `ops/00-mapa.md`. Un puerto declarado en dos lugares
# que se separan es cómo se elige uno ocupado; `pruebas/verificar-angosto.py`
# verifica que los dos digan lo mismo.
PUERTO_POR_DEFECTO = 5402
PUERTO = int(os.environ.get("CAPATAZ_PUERTO", PUERTO_POR_DEFECTO))

# Tres relojes distintos, y confundirlos es cómo se hace un tablero que miente:
#
#   1 s   la pantalla repinta y los contadores avanzan. No sale a ningún lado:
#         el tiempo pasa igual y eso se puede afirmar sin preguntarle a nadie.
#   2 s   la pantalla le pide `/api/estado` a este servidor. Barato: armar la
#         vista salió medido 0,008 s.
#  15 s   este servidor le pregunta a GitHub (`nube.REFRESCO`). Medido el
#         2026-08-06: 1,2 s por repositorio, así que a 15 s son ~16% del
#         tiempo haciendo `git fetch` y no más.
#
# Bajar el tercero es lo único que hace que un agente se vea más rápido, y es
# el único que cuesta. Por eso la pantalla muestra **hace cuánto se leyó
# GitHub** y no sólo la hora: un contador de un segundo sobre datos de hace un
# minuto es exactamente el tablero que miente en el caso que importa.
CACHE_SEG = 1
_cache = {"ts": 0.0, "datos": None}

# Con la pantalla pidiendo cada 2 s y un refresco que tarda ~2,4 s, dos pedidos
# se pisan: los dos ven la caché vencida y los dos salen a hacer `git fetch`
# sobre el mismo espejo. El candado deja que salga uno y que el otro espere su
# resultado — sin él, git compite consigo mismo por el lock del repositorio.
_candado = threading.Lock()


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
    with _candado:
        # Adentro del candado se vuelve a mirar: el que esperó no tiene que
        # repetir el `git fetch` que acaba de hacer el que entró primero.
        ahora = time.time()
        if _cache["datos"] is not None and ahora - _cache["ts"] < CACHE_SEG:
            return _cache["datos"]
        proyectos = lector.leer_proyectos(PROYECTOS)
        vistas = [_mirar(p, ahora) for p in proyectos]
        # El taller es la otra fuente, y contesta otra pregunta: GitHub dice
        # **qué quedó hecho** y esto dice **quién está prendido acá**. Va
        # adentro del mismo candado porque sale de la misma foto del segundo,
        # pero no cuesta red: son unos pocos archivos de cientos de bytes.
        vista_taller = taller.leer(ahora=ahora)
        vista_taller["sueltas"] = taller.empatar(vista_taller, proyectos)
        # La tercera fuente, y contesta lo que ni git ni los archivos pueden:
        # los agentes **background**. Su `state` no está en ningún archivo, y
        # el de uno que ya terminó no está en ninguna parte más —el
        # `<pid>.json` se borra al pararlo, medido el 2026-08-15—.
        #
        # `cotejar` es la regla 1 puesta donde por primera vez hay dos fuentes
        # del mismo hecho: una sesión interactiva viva está en las dos. La regla
        # escrita es que gana el archivo, y lo que **no** coincide se muestra en
        # vez de resolverse en silencio.
        vista_consola = consola.leer(ahora=ahora)
        vista_consola["desacuerdos"] = consola.cotejar(vista_consola, vista_taller)
        # **Un renglón por agente, no uno por fuente.** Las dos secciones que
        # había —una por archivo y otra por CLI— dibujaban el mismo agente dos
        # veces: la pantalla estaba partida por de dónde sale el dato en vez de
        # por qué pregunta contesta.
        vista_taller["agentes_maquina"] = consola.unir(vista_consola, vista_taller)
        # Y el tercer paso: lo publicado en GitHub **también es del mismo
        # agente**. Se asocia por `(proyecto, rama)`, con la rama que sale de
        # `<cwd>/.git/HEAD`. Lo que no empata —otra máquina, un contenedor— queda
        # como su propio renglón y rotulado, en vez de forzarlo.
        agentes_github = lector.agentes(vistas, ahora)
        agentes_todos = lector.asociar(vista_taller["agentes_maquina"],
                                       agentes_github)
        datos = {
            "ahora": ahora,
            "cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": PROYECTOS,
            "puerto": PUERTO,
            "espejos": nube.ESPEJOS,
            # La vista primaria: la cuadrilla de todos los proyectos junta y
            # ordenada por quién se movió recién. Va arriba de `proyectos`
            # porque es lo que se mira, no un resumen de lo de abajo.
            "agentes": agentes_github,
            # La lista única: una pantalla de agentes, y los proyectos aparte.
            "agentes_todos": agentes_todos,
            # Los umbrales viajan **una vez y desde acá**. La pantalla vuelve a
            # decidir el estado a cada segundo, y si los copiara tendría los
            # mismos dos números en dos lugares sin ninguna regla sobre cuál
            # gana — el bug que este proyecto tiene escrito como regla 1.
            "umbrales": {"fresco": lector.FRESCO, "tibio": lector.TIBIO},
            # El taller tiene **sus propios umbrales**, y son otro orden de
            # magnitud: una rama se mira en horas y un subagente en minutos.
            # Viajan igual que los otros —una vez y desde acá— para que la
            # pantalla no los copie.
            "taller": vista_taller,
            "umbrales_taller": {"fresco": taller.FRESCO, "tibio": taller.TIBIO,
                                "latiendo": taller.LATIENDO},
            "consola": vista_consola,
            "refresco_nube": nube.REFRESCO,
            "proyectos": vistas,
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
    print("  Consola: %s (se apaga con CAPATAZ_CONSOLA=0)" % " ".join(consola.ARGV))
    print("\n  Capataz sólo lee. No marca puntos, no lanza agentes.\n")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Capataz).serve_forever()
