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

print("\nASERCIONES: %d\nROJAS: %d" % (ASER, ROJAS))
sys.exit(1 if ROJAS else 0)
