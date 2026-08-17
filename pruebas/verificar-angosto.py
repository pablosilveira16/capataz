#!/usr/bin/env python3
"""Que la pantalla entre en un teléfono, y que el puerto sea uno solo.

**El límite de este arnés, dicho antes que nada.** Sin un navegador no hay
layout, y sin layout esto no puede afirmar «entra en 360 px»: afirma las
condiciones que lo hacen entrar, calculadas sobre la hoja de estilo de verdad.
Es menos que mirar, y por eso mirar sigue siendo un punto abierto (V1 del
seguimiento) y hay una instantánea estática —`./run.sh --instantanea`— hecha
justamente para poder mirarla en un navegador que no llega al 5402.

Lo que sí verifica, y son cuentas y no cadenas:

  § 1  el ancho: `padding` del body × 2 + el `max-width` de la hoja ≤ 360, y
       ninguna declaración de ancho mayor a 360 fuera de una media query ancha;
  § 2  que la regla que hace que un texto ajeno no desborde exista **y que
       haga falta** — se mide el token más largo sin espacios de los datos
       reales que llegan a la pantalla;
  § 3  que la página se arme de verdad: se ejecuta `render_estatico()` y se
       mira el HTML producido, no el archivo de plantilla;
  § 4  el puerto 5402, declarado en un solo lugar y repetido en la
       documentación sin separarse.

    python3 pruebas/verificar-angosto.py
"""
import io
import json
import os
import re
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

ASER = 0
ROJAS = 0

ANCHO = 360  # la medida de referencia: un teléfono angosto, sin zoom


def af(descripcion, condicion, detalle=""):
    global ASER, ROJAS
    if condicion:
        ASER += 1
    else:
        ROJAS += 1
        print("ROJA  %s%s" % (descripcion, ("  →  %s" % detalle) if detalle else ""))


def igual(descripcion, obtenido, esperado):
    af(descripcion, obtenido == esperado, "obtuve %r, esperaba %r" % (obtenido, esperado))


HTML = io.open(os.path.join(RAIZ, "capataz.html"), encoding="utf-8").read()
CSS = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", HTML, re.S))

# Sin comentarios. Es la misma trampa que ya se comió una vez el arnés del
# lector: la primera versión de «no hay ni un `<table>`» se puso roja con **el
# comentario de la hoja de estilo que explica por qué no hay ninguno**. Un
# arnés que confunde una frase con marcado no verifica el marcado.
SIN_COMENTARIOS = re.sub(r"/\*.*?\*/", " ",
                         re.sub(r"<!--.*?-->", " ", HTML, flags=re.S), flags=re.S)


def sin_medias_anchas(css):
    """La hoja sin los bloques `@media` que sólo aplican en pantallas anchas.

    Adentro de un `@media (min-width: 700px)` un `max-width: 640px` es
    correcto y no tiene nada que ver con el teléfono. Sacarlos es lo que hace
    que la cuenta de § 1 signifique algo.
    """
    salida = []
    i = 0
    while True:
        m = re.search(r"@media([^{]*)\{", css[i:])
        if not m:
            salida.append(css[i:])
            break
        ini = i + m.start()
        salida.append(css[i:ini])
        # buscar la llave que cierra el bloque
        j = i + m.end()
        nivel = 1
        while j < len(css) and nivel:
            if css[j] == "{":
                nivel += 1
            elif css[j] == "}":
                nivel -= 1
            j += 1
        cond = m.group(1)
        anchos = [int(x) for x in re.findall(r"min-width\s*:\s*(\d+)px", cond)]
        if not anchos or max(anchos) <= ANCHO:
            # una media query que también aplica en angosto: cuenta
            salida.append(css[i + m.end():j - 1])
        i = j
    return "".join(salida)


print("\n§ 1 · El ancho")
angosta = sin_medias_anchas(CSS)

m = re.search(r"\.hoja\s*\{[^}]*?max-width\s*:\s*(\d+)px", angosta)
af("la hoja declara un max-width", bool(m))
hoja = int(m.group(1)) if m else 10 ** 6

def lateral_de(selector):
    """El padding de los costados de una regla, leído **por posición**.

    La versión de antes se quedaba con los valores que terminaban en `px` y
    perdía la posición: con `padding: 0 0 40px` se llevaba el 40 —que es el de
    abajo— y lo sumaba dos veces como si fueran los costados, dando 420 px de
    ancho declarado sobre una hoja que entra perfecta. Se puso roja el
    2026-08-15 al mover el padding lateral del body al contenido, y **la roja
    era del arnés**: la hoja estaba bien. Un cero sin unidad es un cero.
    """
    m = re.search(r"(?m)^%s\s*\{[^}]*?padding\s*:\s*([^;]+);" % re.escape(selector),
                  angosta, re.S)
    if not m:
        return None, []
    partes = m.group(1).split()
    def px(v):
        if v in ("0", "0px"):
            return 0
        return int(v[:-2]) if v.endswith("px") and v[:-2].isdigit() else None
    v = [px(x) for x in partes]
    if None in v or not v:
        return None, partes
    # `padding` abreviado: 1 valor = todos; 2 y 3 = arriba/costados/…; 4 =
    # arriba, derecha, abajo, izquierda.
    if len(v) == 1:
        return v[0], partes
    if len(v) in (2, 3):
        return v[1], partes
    return max(v[1], v[3]), partes


# Los costados los puede poner el body **o** el contenedor de adentro: desde el
# 2026-08-15 la barra llega de borde a borde y el padding lateral vive en `.app`.
# Lo que tiene que entrar en 360 es la suma, mire donde mire.
lat_body, partes_body = lateral_de("body")
lat_app, partes_app = lateral_de(".app")
af("el body declara su padding", lat_body is not None, partes_body)
af("y el contenedor de las vistas también", lat_app is not None, partes_app)
lateral = (lat_body or 0) + (lat_app or 0)

igual("la hoja + los dos padding entran justo en %d px" % ANCHO,
      hoja + 2 * lateral <= ANCHO, True)
print("       %d px de hoja + 2 × %d px de padding = %d px"
      % (hoja, lateral, hoja + 2 * lateral))

anchos = [(int(n), d) for d, n in
          re.findall(r"((?:min-|max-)?width)\s*:\s*(\d+)px", angosta)]
malos = [(n, d) for n, d in anchos if n > ANCHO]
af("ninguna declaración de ancho pasa de %d px fuera de una media query ancha"
   % ANCHO, not malos, malos)
af("y hay declaraciones de ancho que mirar (si no, esto no verifica nada)",
   len(anchos) >= 1, anchos)

af("hay meta viewport width=device-width",
   bool(re.search(r'<meta[^>]+name=["\']viewport["\'][^>]*content=["\'][^"\']*'
                  r'width=device-width', HTML)))
af("y con initial-scale=1, o el teléfono dibuja ancho y después achica",
   "initial-scale=1" in HTML)
af("el html/body corta el desborde horizontal",
   bool(re.search(r"overflow-x\s*:\s*hidden", angosta)))
af("no hay ni un <table>: cinco columnas no entran en %d px de ninguna forma"
   % ANCHO, "<table" not in SIN_COMENTARIOS.lower())

print("§ 2 · Que el texto ajeno no desborde — y que la regla haga falta")
af("la hoja rompe palabras largas (overflow-wrap)",
   bool(re.search(r"overflow-wrap\s*:\s*(anywhere|break-word)", angosta)))
af("y tiene el respaldo de word-break",
   bool(re.search(r"word-break\s*:\s*break-word", angosta)))

import capataz  # noqa: E402
import lector   # noqa: E402

datos = capataz.estado()
af("capataz lee al menos un proyecto de verdad", len(datos["proyectos"]) >= 1,
   len(datos["proyectos"]))

# El token más largo sin espacios que llega a la pantalla. Si no hubiera
# ninguno largo, la regla de arriba sería decorativa y estas dos aserciones
# estarían midiendo el aire.
def tokens(x):
    if isinstance(x, str):
        for t in x.split():
            yield t
    elif isinstance(x, dict):
        for k, v in x.items():
            for t in tokens(v):
                yield t
    elif isinstance(x, (list, tuple)):
        for v in x:
            for t in tokens(v):
                yield t


largo = max([len(t) for t in tokens(datos["proyectos"])] or [0])
af("los datos reales traen tokens largos sin espacios (rutas, `código`): "
   "la regla de arriba es la que evita el desborde", largo >= 30, largo)
print("       el token más largo que llega a la pantalla mide %d caracteres" % largo)

print("§ 3 · La página se arma de verdad")
destino = os.path.join(tempfile.mkdtemp(prefix="capataz-angosto-"), "i.html")
capataz.render_estatico(destino)
salida = io.open(destino, encoding="utf-8").read()
af("la instantánea existe y no está vacía", len(salida) > 4000, len(salida))
af("trae la meta viewport", "width=device-width" in salida)
af("y los datos incrustados, para poder abrirla con file://",
   "window.CAPATAZ_DATOS" in salida)
m = re.search(r"window\.CAPATAZ_DATOS\s*=\s*(\{.*?\});</script>", salida, re.S)
af("los datos incrustados son JSON válido", bool(m))
if m:
    d = json.loads(m.group(1))
    igual("y son los mismos proyectos que sirve la API",
          [p["nombre"] for p in d["proyectos"]],
          [p["nombre"] for p in datos["proyectos"]])
    af("con los cinco estados adentro de cada proyecto",
       all(sorted(p["cuenta_abiertos"]) ==
           sorted(list(lector.ESTADOS) + [lector.SIN_ESTADO])
           for p in d["proyectos"]))
os.remove(destino)

print("§ 4 · El puerto, declarado en un solo lugar")
igual("capataz.py declara el 5402", capataz.PUERTO_POR_DEFECTO, 5402)
for archivo in ("CLAUDE.md", "ops/00-mapa.md"):
    ruta = os.path.join(RAIZ, archivo)
    if not os.path.isfile(ruta):
        af("%s existe (lo nombra CLAUDE.md)" % archivo, False)
        continue
    texto = io.open(ruta, encoding="utf-8").read()
    af("%s dice el mismo puerto que capataz.py" % archivo,
       str(capataz.PUERTO_POR_DEFECTO) in texto)
mapa = os.path.join(RAIZ, "ops", "00-mapa.md")
if os.path.isfile(mapa):
    texto = io.open(mapa, encoding="utf-8").read()
    for ocupado in ("5300", "5301", "5302", "5400", "5401"):
        af("ops/00-mapa.md anota el puerto ocupado %s" % ocupado, ocupado in texto)

print("§ 5 · Los dos temas, y que el claro no se olvide ningún color")
#
# El tema claro se define dando vuelta los tokens. **Un token que el bloque
# claro no redefina se queda con el valor oscuro**, y eso sobre papel blanco es
# un texto invisible o un chip negro: la falla no se ve como error, se ve como
# un renglón que no está. Por eso lo que se compara son los **conjuntos de
# nombres**, no un color puntual.

def bloque_de(selector):
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\}", CSS, re.S)
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", m.group(1))) if m else {}


OSCURO = bloque_de(":root")
CLARO = bloque_de(':root[data-tema="claro"]')
af("la hoja define la paleta en tokens", len(OSCURO) >= 20, len(OSCURO))
af("y el tema claro existe", bool(CLARO), "no encontré :root[data-tema=claro]")
igual("el claro redefine **todos** los tokens del oscuro, sin olvidarse ninguno",
      sorted(set(OSCURO) - set(CLARO)), [])
igual("y no inventa ninguno que el oscuro no tenga",
      sorted(set(CLARO) - set(OSCURO)), [])
# Y que sea otro tema de verdad: si los valores fueran los mismos, las cuatro
# aserciones de arriba pasarían con un «claro» que se ve idéntico al oscuro.
distintos = [k for k in OSCURO if OSCURO[k].strip() != CLARO.get(k, "").strip()]
af("y los valores son otros: no es el mismo tema con otro nombre",
   len(distintos) >= len(OSCURO) - 2, "%d de %d" % (len(distintos), len(OSCURO)))
af("el claro le avisa al navegador con color-scheme, para las barras y los "
   "controles nativos", "color-scheme: light" in CSS)
# Regla 3 en el tema claro: los fondos de estado tienen que seguir siendo
# distinguibles entre sí. Si el claro los aplastara todos a blanco, «no sé» y
# «verde» se verían igual — que es la regla 3 rota por la vía de la paleta.
FONDOS = [v.strip() for k, v in CLARO.items() if k.startswith("--fondo")]
af("en el claro, los fondos no quedaron todos aplastados en el mismo color",
   len(set(FONDOS)) >= max(3, len(FONDOS) // 2),
   "%d distintos de %d" % (len(set(FONDOS)), len(FONDOS)))

# Dos `@keyframes` con el mismo nombre no dan ningún error: gana el último y el
# otro elemento hereda una animación que no es la suya. Pasó el 2026-08-15 —el
# punto que late heredó la animación de fondo de la fila que se despierta y
# salía del color de una tarjeta—, y se encontró mirando el color computado en
# el navegador, no acá. Ahora sí se encuentra acá.
nombres = re.findall(r"@keyframes\s+([\w-]+)", CSS)
repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
igual("ninguna animación comparte nombre con otra", repetidos, [])
af("y hay al menos dos animaciones declaradas, si no esto no mira nada",
   len(nombres) >= 2, nombres)

print("§ 6 · A quién le contesta, que no es lo mismo que el puerto")
#
# **Esto se ejercita levantando el servidor de verdad**, dos veces, y midiendo
# quién contesta desde afuera de loopback. Un arnés que sólo mirara la constante
# `SOLO_ESTA_MAQUINA` pasaría entero con un `ThreadingHTTPServer` que la ignora
# —que es exactamente el bug que importa acá—, y ésa es la forma vacua contra la
# que el proyecto ya se estrelló cuatro veces: leer un archivo y buscar una
# cadena no prueba que el código corra.
#
# Y hay una trampa medida, que es la razón de que se pruebe contra la IP y no
# contra el nombre: `<LocalHostName>.local` contesta 200 **desde esta misma
# Mac** aunque nadie más pueda entrar, porque resuelve también a 127.0.0.1. La
# prueba cómoda es la que miente.
import socket as _socket        # noqa: E402
import subprocess               # noqa: E402
import time as _time            # noqa: E402
import urllib.error             # noqa: E402
import urllib.request           # noqa: E402

igual("el default es sólo esta máquina", capataz.SOLO_ESTA_MAQUINA, "127.0.0.1")
af("y sin la variable, eso es lo que se usa",
   capataz.ESCUCHA == capataz.SOLO_ESTA_MAQUINA, capataz.ESCUCHA)

IP = capataz.ip_en_la_red()
af("esta máquina tiene una IP en la red que no es loopback (si no, esta "
   "sección no puede distinguir nada)",
   bool(IP) and not IP.startswith("127."), IP or "(ninguna)")
print("       la IP de esta máquina en la red es %s" % (IP or "(ninguna)"))


def _puerto_libre():
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _contesta(host, puerto, espera=1.5):
    try:
        with urllib.request.urlopen("http://%s:%d/" % (host, puerto),
                                    timeout=espera) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def _levantar(escucha):
    """Capataz de verdad, en un puerto libre. Devuelve `(proceso, puerto)`."""
    puerto = _puerto_libre()
    entorno = dict(os.environ, CAPATAZ_PUERTO=str(puerto))
    if escucha is not None:
        entorno["CAPATAZ_ESCUCHA"] = escucha
    else:
        entorno.pop("CAPATAZ_ESCUCHA", None)
    proc = subprocess.Popen([sys.executable, "capataz.py"], cwd=RAIZ,
                            env=entorno, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    # Esperar a que conteste, en vez de dormir un número inventado: un sleep
    # corto convierte esta sección en una que falla los días que la máquina está
    # ocupada, y una roja que va y viene sola es la que hace que se deje de
    # mirar el color.
    for _ in range(60):
        if _contesta("127.0.0.1", puerto, 0.3):
            return proc, puerto
        if proc.poll() is not None:
            return proc, puerto
        _time.sleep(0.1)
    return proc, puerto


PROC, PUERTO_A = _levantar(None)
try:
    af("con el default, contesta en esta máquina",
       _contesta("127.0.0.1", PUERTO_A))
    af("y **no** contesta en la IP de la red: el tablero no se expone solo",
       IP and not _contesta(IP, PUERTO_A), "%s:%d contestó" % (IP, PUERTO_A))
finally:
    PROC.terminate()
    PROC.wait(timeout=10)

PROC, PUERTO_B = _levantar("0.0.0.0")
try:
    af("con CAPATAZ_ESCUCHA=0.0.0.0 sigue contestando en esta máquina",
       _contesta("127.0.0.1", PUERTO_B))
    # La anti-vacua de la de arriba: sin ésta, «no se expone solo» pasaría igual
    # con un capataz que no se puede abrir de ninguna forma.
    af("y **sí** contesta en la IP de la red, que es lo que hace que el "
       "teléfono lo pueda leer",
       IP and _contesta(IP, PUERTO_B), "%s:%d no contestó" % (IP, PUERTO_B))
finally:
    PROC.terminate()
    PROC.wait(timeout=10)

# Lo que se imprime al arrancar. Es la única parte de esto que alguien lee.
CERRADO = capataz.donde_mirarlo(capataz.SOLO_ESTA_MAQUINA, capataz.PUERTO)
ABIERTO = capataz.donde_mirarlo("0.0.0.0", capataz.PUERTO)
af("cerrado, dice cómo abrirlo", any("--telefono" in l for l in CERRADO), CERRADO)
af("abierto, avisa que cualquiera en la wifi puede leerlo y que no pide "
   "credencial", any("credencial" in l for l in ABIERTO), ABIERTO)
af("y da la IP, no sólo el nombre: probar el nombre desde esta Mac contesta "
   "igual aunque nadie más entre", any(IP in l for l in ABIERTO) if IP else False,
   ABIERTO)

# La bandera y la variable, declaradas donde alguien las va a buscar.
RUN = io.open(os.path.join(RAIZ, "run.sh"), encoding="utf-8").read()
af("run.sh traduce --telefono a la variable, y no la escribe en el código",
   "--telefono" in RUN and "CAPATAZ_ESCUCHA=0.0.0.0" in RUN)
MAPA = io.open(os.path.join(RAIZ, "ops", "00-mapa.md"), encoding="utf-8").read()
af("ops/00-mapa.md documenta la variable que abre el tablero",
   "CAPATAZ_ESCUCHA" in MAPA)
af("y deja escrito que el nombre .local contesta desde la propia Mac aunque "
   "el teléfono no entre", "resuelve también a loopback" in MAPA)

print("\nASERCIONES: %d\nROJAS: %d" % (ASER, ROJAS))
sys.exit(1 if ROJAS else 0)
