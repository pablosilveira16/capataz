"""La consola: los agentes **background**, que es lo que nadie más tiene.

Capataz tiene ya dos fuentes y cada una contesta una pregunta que la otra no
puede contestar:

    nube.py     qué quedó **publicado**            → lo dice git, que es el árbitro
    taller.py   qué proceso está **vivo acá**      → lo dicen los archivos de ~/.claude

Esta es la tercera, y entra por la misma puerta que entró la segunda: **trae un
dato que las otras dos no pueden tener**. No por comodidad, por medición.

## Lo que se midió el 2026-08-15, y que dio vuelta el T22

El T22 rechazaba usar `claude agents --json` con una medición del 2026-08-06 que
era correcta: para una sesión **interactiva** el CLI devuelve seis campos y
`~/.claude/sessions/<pid>.json` devuelve doce. Pagar un subproceso para obtener
menos que un `open()` no se paga, y eso **sigue siendo cierto hoy**.

Lo que cambió es que se lanzó un background de verdad (`claude --bg`) en vez de
suponer qué haría:

  · Vivo, el CLI trae `id`, `status` y **`state`** — y `state` **no está en el
    archivo**. Es el campo que dice si el agente trabaja o está trabado.
  · **Parado, el archivo `<pid>.json` desaparece** y sólo `claude agents --json
    --all` lo conserva, con `state: "stopped"`. O sea que un background
    terminado es, literalmente, un dato que `taller.py` no puede leer: ya no
    hay archivo que abrir.

Por eso este módulo contesta **una sola cosa**: los background. Para las
sesiones interactivas **no vuelve a contestar nada** —ahí gana el archivo, que
trae el doble de campos— y lo único que hace con ellas es cotejar, que es lo de
abajo.

## Dos fuentes del mismo hecho, y la regla de cuál gana escrita

«Dos lugares con el mismo dato y ninguna regla sobre cuál gana» es el bug más
caro de Finca 360 y es la regla 1 de `CLAUDE.md`. Acá, por primera vez, hay
solapamiento de verdad: una sesión interactiva viva aparece en el archivo **y**
en el CLI. La regla, entonces, se escribe:

    1. Sesión interactiva  → **gana el archivo** (`taller.py`). El CLI no la
       vuelve a mostrar: es un subconjunto medido de lo que ya está.
    2. `state` y background terminado → **sólo la consola**. El archivo no los
       tiene, así que no hay nada que comparar.
    3. Donde las dos hablan del mismo hecho y **no coinciden**, el desacuerdo
       **se muestra** (`cotejar`). Resolverlo en silencio sería elegir un ganador
       sin decirlo, que es exactamente el bug.

## Y el desacuerdo que no es un desacuerdo

El archivo dice `kind: "bg"` y el CLI dice `kind: "background"` **para la misma
sesión**. Si eso cuenta como diferencia, la pantalla avisa en todas las corridas
—y el corolario de la regla 3 dice que un aviso que sale siempre enseña a
ignorarse, y el día que diga algo tampoco se lee—. Son la misma palabra y está
declarado en `ALIAS_KIND`. Lo mismo con un background terminado que ya no tiene
archivo: es lo **esperado**, está medido, y no se reporta.

## Capataz no lanza agentes, y acá eso es una compuerta y no una promesa

`claude agents` **sin** `--json` abre la vista interactiva, desde donde se
despachan sesiones nuevas. Este módulo corre un argv que pasa por `_compuerta`:
tiene que ser `claude agents … --json`, y no puede llevar ninguna bandera de las
que despachan. El arnés cuenta por AST que hay **un solo `subprocess`** en todo
el archivo y que está adentro de `_correr`, igual que `verificar-nube.py` exige
uno solo adentro de `_git`.

Y `stdin` va a `/dev/null`: un proceso ajeno que se quede esperando una tecla no
puede colgar la pantalla. El tope de tiempo es la otra mitad de lo mismo.

Sin dependencias: sólo biblioteca estándar. → `pruebas/verificar-consola.py`
"""

import json
import os
import subprocess
import time

from nube import limpiar_secreto

# El argv por defecto. Es una constante y **no se arma con nada de afuera**: lo
# único que un entorno puede hacer es apagar el módulo entero, no cambiarle los
# argumentos. `--all` es lo que trae los background ya terminados, que es medio
# módulo: sin él, un agente que falló hace un minuto no existe para nadie.
ARGV = ("claude", "agents", "--json", "--all")

# Las banderas que despachan una sesión o se cuelgan de una. Ninguna puede
# aparecer en el argv, y la lista es explícita para que se lea qué se prohíbe.
# `--json` está documentado como «no requiere TTY», que es lo que hace que esto
# sea leer y no abrir una vista.
PROHIBIDAS = (
    "--agent", "--model", "--effort", "--permission-mode", "--settings",
    "--dangerously-skip-permissions", "--allow-dangerously-skip-permissions",
    "--mcp-config", "--plugin-dir", "--add-dir", "--setting-sources",
    "attach", "stop", "logs", "resume", "-p", "--print",
)

# Medido el 2026-08-15 sobre tres corridas: 0,17 s. El tope está dos órdenes
# arriba a propósito — no es para apurar al CLI, es para que una máquina cargada
# no deje la pantalla colgada de un proceso que no es de capataz.
ESPERA = 5

# Cada cuánto se le vuelve a preguntar. La pantalla pide cada 2 s y el servidor
# cachea 1 s; sin esto serían ~0,17 s de CPU por segundo lanzando un proceso.
# Con 3 s el `state` de un background llega igual de rápido que cualquier otra
# cosa de la pantalla, y **la frescura viaja** en `preguntado_en`: la lección de
# T21 es que un contador de un segundo sobre datos viejos es el tablero que
# miente.
REFRESCO = int(os.environ.get("CAPATAZ_CONSOLA_REFRESCO", 3))

# Se apaga con `CAPATAZ_CONSOLA=0`. Apagada, el resultado es «no sé» con el
# motivo — nunca «cero agentes», que es la regla 3.
APAGADA = os.environ.get("CAPATAZ_CONSOLA", "1") == "0"

# Estos cuatro textos **se leen en la pantalla**, así que van sin markdown: los
# backticks salieron literales la primera vez que se miró el navegador, igual
# que los asteriscos de `taller.py`. El arnés no los ve —para él son cadenas— y
# por eso está escrito acá: lo encontró un par de ojos a 375 px.
ALCANCE = ("esta máquina · ahora. Son los agentes background de claude agents; "
           "los de otra máquina no aparecen acá.")

# Los seis valores de `state`, medidos y no elegidos: dos vistos en vivo
# —`blocked` y `stopped`— y el resto leídos del propio binario del CLI, que los
# lleva como lista literal (`"working","blocked","done","stopped","failed"`, más
# `queued`). Lo que no esté acá se muestra **«no sé» con la palabra cruda**:
# inventarle un color a un valor que nadie vio es cómo se pinta de verde algo
# que no se entiende.
#
# Y hay un hallazgo que conviene tener escrito, porque contradice al T19 sin
# contradecirlo: un **background sí deja marca de cierre** —`done`, `failed` y
# `stopped` son tres desenlaces distintos—, mientras que de un **subagente** no
# se puede saber si terminó o se colgó. Son dos cosas distintas con nombres
# parecidos, y por eso el taller sigue diciendo `sin señal`.
ESTADOS = {
    "working": ("trabajando", ""),
    "queued":  ("en cola", "despachado y todavía no arrancó"),
    "blocked": ("esperando", "trabado: necesita a una persona. El comando de "
                             "abajo lo abre en una terminal"),
    "done":    ("terminado", "terminó solo"),
    "failed":  ("falló", "terminó con error"),
    "stopped": ("parado", "lo pararon a mano"),
}

# `bg` y `background` son **la misma palabra**, dichas por las dos fuentes. Está
# declarado acá y no resuelto adentro de `cotejar` para que se pueda leer, y
# para que agregar un alias sea una decisión visible: cada alias que se agrega es
# un desacuerdo que se deja de mostrar.
ALIAS_KIND = {"bg": "background", "background": "background",
              "interactive": "interactive"}

MOTIVO_APAGADA = (
    "la consola está apagada con CAPATAZ_CONSOLA=0, así que de los agentes "
    "background no se sabe nada. Lo de GitHub y el taller se leen igual")

MOTIVO_SIN_CLAUDE = (
    "no pude correr «%s»: %s. Sin el CLI de Claude Code no hay forma de saber "
    "de los agentes background —el archivo de una sesión background desaparece "
    "cuando termina—, así que acá dice «no sé» y no cero. Lo de GitHub y el "
    "taller se leen igual: esto no apaga el resto del tablero")

MOTIVO_TARDO = (
    "«%s» tardó más de %d s y se cortó. Medido el 2026-08-15, contesta en "
    "0,17 s: si tarda esto, algo le pasa al CLI y no a capataz")

# El nombre de una sesión background **es el pedido que escribió una persona**,
# así que se lo trata como texto de afuera: se le pasa el limpiador de secretos
# y se lo corta. Un tablero que se lee desde un teléfono no es lugar para volcar
# un prompt de tres renglones.
TOPE_NOMBRE = 90


class FueraDeLaConsola(RuntimeError):
    """Se intentó correr algo que no es `claude agents --json`.

    Es la hermana de `FueraDelEspejo` de `nube.py` y de `FueraDelTaller` de
    `taller.py`. Acá lo que se protege es la regla 1 entera: `claude agents`
    **sin** `--json` es la vista desde la que se despachan agentes, y capataz no
    lanza ninguno.
    """


# ----------------------------------------------------------------------------
# 1 · La compuerta y el único subprocess del módulo
# ----------------------------------------------------------------------------

def _compuerta(argv):
    """Que el argv sea una lectura y no un despacho. Revienta si no.

    Tres condiciones, y la tercera es la que vale: las dos primeras dicen qué
    tiene que estar, y la tercera dice qué **no puede** estar. Un subcomando
    nuevo que parezca inocente pasa las dos primeras; la lista de prohibidas es
    lo que hace que agregar uno sea una decisión y no un descuido.
    """
    argv = tuple(argv or ())
    if not argv:
        raise FueraDeLaConsola("argv vacío: capataz no corre nada sin decir qué.")
    if os.path.basename(argv[0]) != "claude":
        raise FueraDeLaConsola(
            "«%s» no es el CLI de Claude Code. Capataz corre un solo programa "
            "acá, y es `claude`." % argv[0])
    if "agents" not in argv or "--json" not in argv:
        raise FueraDeLaConsola(
            "«%s» no es `claude agents … --json`. Sin --json eso abre la vista "
            "interactiva, que es desde donde se despachan agentes: capataz "
            "sólo lee (CLAUDE.md § 1)." % " ".join(argv))
    malas = [a for a in argv[1:] if a in PROHIBIDAS]
    if malas:
        raise FueraDeLaConsola(
            "«%s» lleva %s, que despacha o se cuelga de una sesión. Capataz no "
            "lanza agentes (CLAUDE.md § 1)." % (" ".join(argv), ", ".join(malas)))
    return argv


def _correr(argv=None):
    """Correr el CLI y devolver `(texto, error)`. **El único `subprocess`.**

    Que sea uno solo, y adentro de la compuerta, es lo que hace verificable la
    frase «capataz no lanza agentes»: se cuenta por AST y no hay que creerle a
    ningún comentario. `stdin` va a `/dev/null` porque un proceso ajeno que se
    quede esperando una tecla es una pantalla colgada, y el tope de tiempo es la
    otra mitad de lo mismo.
    """
    argv = _compuerta(argv or ARGV)
    try:
        p = subprocess.run(list(argv), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                           timeout=ESPERA)
    except subprocess.TimeoutExpired:
        return None, MOTIVO_TARDO % (" ".join(argv), ESPERA)
    except OSError as e:
        return None, MOTIVO_SIN_CLAUDE % (" ".join(argv), e)
    if p.returncode != 0:
        error = limpiar_secreto(p.stderr.decode("utf-8", "replace").strip())
        return None, limpiar_secreto(
            "«%s» falló con código %d%s" % (" ".join(argv), p.returncode,
                                            (": " + error) if error else ""))
    return p.stdout.decode("utf-8", "replace"), ""


# ----------------------------------------------------------------------------
# 2 · Qué se puede afirmar de un agente background
# ----------------------------------------------------------------------------

def estado_background(sesion):
    """`(estado, motivo)` de un background. Lo que no se midió se dice «no sé».

    El `state` viene del CLI y es el único lugar donde existe. Si trae una
    palabra que no está en `ESTADOS` —una versión nueva del CLI, un valor que
    nadie vio— el resultado es `no sé` **con la palabra cruda adentro del
    motivo**, que es lo accionable: el que la lee sabe qué buscar. Pintarla del
    color de al lado sería afirmar algo que no se sabe.
    """
    crudo = sesion.get("state") or ""
    if not crudo:
        return "no sé", ("el CLI no mandó el campo «state» para esta sesión. Es "
                         "background only: si aparece vacío acá, cambió el CLI")
    if crudo not in ESTADOS:
        return "no sé", ("el CLI dice state: %r, que no es ninguno de los seis "
                         "valores medidos (%s)" % (crudo, ", ".join(sorted(ESTADOS))))
    nombre, motivo = ESTADOS[crudo]
    if "%s" in motivo:
        motivo = motivo % (sesion.get("id") or sesion.get("sesion") or "")
    return nombre, motivo


def _texto(valor, tope=TOPE_NOMBRE):
    """Texto de afuera: sin secretos y cortado. El nombre de un background **es
    el pedido que escribió una persona**, así que no se lo trata como un campo."""
    t = limpiar_secreto(str(valor or "")).strip().replace("\n", " ")
    return t if len(t) <= tope else t[:tope - 1] + "…"


def _sesion(cruda, ahora):
    """Un renglón del JSON del CLI, traducido y sin nada de más."""
    arrancada = cruda.get("startedAt")
    arrancada = arrancada / 1000.0 if isinstance(arrancada, (int, float)) else None
    return {
        "id": cruda.get("id") or "",
        "sesion": cruda.get("sessionId") or "",
        "pid": cruda.get("pid"),
        "nombre": _texto(cruda.get("name")),
        "cwd": cruda.get("cwd") or "",
        "clase": ALIAS_KIND.get(cruda.get("kind") or "", cruda.get("kind") or ""),
        "state": cruda.get("state") or "",
        "status": cruda.get("status") or "",
        "arrancada": arrancada,
        "hace": None if arrancada is None else max(0, int(ahora - arrancada)),
    }


# ----------------------------------------------------------------------------
# 3 · La vista entera
# ----------------------------------------------------------------------------

_ultima = {"ts": 0.0, "vista": None}


def olvidar():
    """Tirar lo cacheado. Existe para el arnés, y es la aserción que prueba que
    esto no es estado propio: se borra, se vuelve a leer y sale lo mismo."""
    _ultima["ts"] = 0.0
    _ultima["vista"] = None


def leer(argv=None, ahora=None, refresco=None):
    """Los agentes background de esta máquina. Devuelve **siempre** la misma forma.

    Nunca revienta y nunca devuelve vacío por error: si el CLI no está, `ok` es
    `False` y `error` dice **qué comando corrió y qué pasó**, que es lo
    accionable. Cero background y «no pude preguntar» son cosas distintas y
    tienen que verse distintas — regla 3.

    Las sesiones **interactivas** viajan aparte, en `interactivas`, y no se
    muestran: están para `cotejar` y nada más. Quien las muestra es `taller.py`,
    que de cada una sabe el doble.
    """
    ahora = time.time() if ahora is None else ahora
    refresco = REFRESCO if refresco is None else refresco
    if (_ultima["vista"] is not None and refresco
            and ahora - _ultima["ts"] < refresco):
        return _ultima["vista"]
    argv = tuple(argv or ARGV)
    vista = {
        "ok": False,
        "error": "",
        "alcance": ALCANCE,
        "comando": " ".join(argv),
        "preguntado_en": ahora,
        "background": [],
        "interactivas": [],
        "cuenta": {"background": 0, "trabajando": 0, "esperando": 0,
                   "terminados": 0, "interactivas": 0},
    }
    if APAGADA:
        vista["error"] = MOTIVO_APAGADA
        return vista
    texto, error = _correr(argv)
    if error:
        vista["error"] = error
        return vista
    try:
        crudas = json.loads(texto)
    except ValueError as e:
        # Que el CLI conteste algo que no es JSON es exactamente el caso en que
        # un lector descuidado devuelve una lista vacía y la pantalla dice
        # «ningún agente», que es mentira. Acá dice qué contestó.
        vista["error"] = limpiar_secreto(
            "«%s» no contestó JSON: %s. Los primeros 200 caracteres fueron: %r"
            % (vista["comando"], e, (texto or "")[:200]))
        return vista
    if not isinstance(crudas, list):
        vista["error"] = ("«%s» contestó un %s y no una lista de sesiones"
                          % (vista["comando"], type(crudas).__name__))
        return vista
    cuenta = vista["cuenta"]
    for cruda in crudas:
        if not isinstance(cruda, dict):
            continue
        s = _sesion(cruda, ahora)
        if s["clase"] == "interactive":
            vista["interactivas"].append(s)
            cuenta["interactivas"] += 1
            continue
        s["estado"], s["motivo_estado"] = estado_background(s)
        vista["background"].append(s)
        cuenta["background"] += 1
        if s["estado"] == "trabajando":
            cuenta["trabajando"] += 1
        elif s["estado"] == "esperando":
            cuenta["esperando"] += 1
        elif s["estado"] in ("terminado", "falló", "parado"):
            cuenta["terminados"] += 1
    # Primero el que necesita a alguien, después el que trabaja, y los
    # terminados al final: un tablero se ordena por lo que hay que hacer.
    orden = {"esperando": 0, "no sé": 1, "trabajando": 2, "en cola": 3}
    vista["background"].sort(
        key=lambda s: (orden.get(s["estado"], 4), -(s["arrancada"] or 0)))
    vista["ok"] = True
    _ultima["ts"] = ahora
    _ultima["vista"] = vista
    return vista


# ----------------------------------------------------------------------------
# 4 · Cotejar — el desacuerdo se muestra, no se resuelve en silencio
# ----------------------------------------------------------------------------

def unir(vista_consola, vista_taller):
    """Los agentes de esta máquina, **un renglón por agente**.

    Hasta el 2026-08-15 la pantalla tenía dos secciones, una por fuente: «el
    taller» con lo que sale de los archivos y «la consola» con lo que sale del
    CLI. Medido con un background vivo, el **mismo** agente salía dibujado en
    las dos —sesión por archivo y background por CLI— y sus subagentes colgaban
    sólo de la primera. Eso es la regla 1 puesta en la pantalla: el mismo hecho
    en dos lugares, y el que mira adivinando que son el mismo.

    Las secciones estaban partidas **por fuente**, y una pantalla se parte por
    **pregunta**. La pregunta acá es una sola: quién está trabajando en esta
    máquina. Así que se juntan por `sessionId`, y la regla de cuál gana es la
    que ya estaba escrita arriba:

      · lo que comparten —nombre, carpeta, si vive— lo pone **el archivo**, que
        trae el doble de campos;
      · el `state` y el `id` para `claude attach` los pone **el CLI**, porque no
        están en ningún archivo;
      · un background que ya terminó **sólo** está en el CLI: su archivo se
        borró, y entra igual, marcado.

    Cada renglón dice de qué fuente salió (`fuente`), que es lo que evita que
    unir se convierta en tapar: si mañana las dos discrepan, `cotejar` lo sigue
    diciendo aparte.
    """
    if not vista_taller.get("ok"):
        return list(vista_taller.get("sesiones", []))
    por_cli = {}
    if vista_consola.get("ok"):
        for b in vista_consola.get("background", []):
            if b.get("sesion"):
                por_cli[b["sesion"]] = b
    salida = []
    vistos = set()
    for s in vista_taller.get("sesiones", []):
        fila = dict(s)
        fila["fuente"] = "archivo"
        b = por_cli.get(s.get("sesion"))
        if b:
            vistos.add(s["sesion"])
            # Del CLI entra **sólo lo que el archivo no tiene**. Copiar encima
            # lo compartido sería elegir un ganador distinto del escrito.
            fila["id"] = b.get("id") or ""
            fila["estado_consola"] = b.get("estado") or ""
            fila["motivo_consola"] = b.get("motivo_estado") or ""
            fila["state"] = b.get("state") or ""
            fila["fuente"] = "archivo+cli"
        salida.append(fila)
    # Y los que el archivo ya no puede tener.
    for sesion, b in por_cli.items():
        if sesion in vistos:
            continue
        salida.append({
            "sesion": sesion, "pid": b.get("pid"), "nombre": b.get("nombre") or "",
            "cwd": b.get("cwd") or "", "clase": "background", "viva": None,
            "arrancada": b.get("arrancada"), "quieto_hace": None,
            "que": "", "sobre": "", "motivo_que": "",
            "agentes": [], "motivo_sin_agentes": SIN_ARCHIVO,
            "proyecto": "", "error": "",
            "id": b.get("id") or "", "estado_consola": b.get("estado") or "",
            # **El caso del T37, dicho en el renglón y no en un aviso aparte.**
            # Si el CLI lo da por vivo —trabado, trabajando, en cola— y de él no
            # queda ningún archivo, las dos cosas no pueden ser ciertas a la
            # vez. Antes eso salía como un banner que, por venir de un registro
            # que el CLI no limpia nunca, aparecía en todas las corridas.
            "motivo_consola": (MOTIVO_VIVO_SIN_ARCHIVO % b.get("estado")
                               if b.get("estado") in ("esperando", "trabajando",
                                                      "en cola")
                               else b.get("motivo_estado") or ""),
            "state": b.get("state") or "", "fuente": "cli",
        })
    # Primero el que necesita a una persona, después el que se movió recién.
    def orden(f):
        pide = 0 if f.get("estado_consola") in ("esperando", "falló") else 1
        quieto = f.get("quieto_hace")
        return (pide, 10 ** 9 if quieto is None else quieto, f.get("nombre") or "")
    salida.sort(key=orden)
    return salida


MOTIVO_VIVO_SIN_ARCHIVO = (
    "el CLI lo da por «%s» pero de este agente ya no queda ningún archivo en la "
    "máquina: las dos cosas no pueden ser ciertas. Lo más probable es que el "
    "proceso haya muerto y el registro del CLI haya quedado viejo — no está "
    "esperando a nadie")

SIN_ARCHIVO = (
    "de este agente ya no queda archivo en la máquina: cuando un background "
    "termina, su registro se borra y lo único que lo recuerda es el CLI. Por eso "
    "no tiene subagentes acá, ni se puede decir si su proceso vive")


def cotejar(vista_consola, vista_taller):
    """Dónde las dos fuentes dicen cosas distintas del **mismo** hecho.

    Devuelve una lista, y **la lista vacía es el caso normal**: si esto avisara
    siempre sería el aviso que enseña a ignorarse (corolario de la regla 3), y
    por eso las dos diferencias que están **medidas y explicadas** no se
    reportan:

      · `kind: "bg"` en el archivo contra `kind: "background"` en el CLI. Es la
        misma palabra, declarada en `ALIAS_KIND`.
      · Un background terminado que ya no tiene archivo. Medido el 2026-08-15:
        al pararlo, `<pid>.json` desaparece y el CLI lo conserva con `--all`.
        Es lo esperado, y es la razón de ser de este módulo.

    Lo que sí se reporta es lo que **nadie explicó**: una sesión que una fuente
    ve viva y la otra no, o el mismo `sessionId` con distinto `cwd`. Eso no se
    resuelve acá —elegir un ganador sin decirlo es el bug de la regla 1—: se
    muestra, con las dos versiones al lado.
    """
    if not vista_consola.get("ok") or not vista_taller.get("ok"):
        return []
    por_sesion = {}
    for s in vista_taller.get("sesiones", []):
        if s.get("sesion"):
            por_sesion[s["sesion"]] = s
    desacuerdos = []
    vistas_por_cli = set()
    for c in (vista_consola.get("interactivas", [])
              + vista_consola.get("background", [])):
        if not c["sesion"]:
            continue
        vistas_por_cli.add(c["sesion"])
        t = por_sesion.get(c["sesion"])
        if t is None:
            # **Que una fuente lo tenga y la otra no ya no se reporta acá**, y
            # es consecuencia de unir las dos secciones en una: ese agente ahora
            # se dibuja igual, en su propio renglón, marcado `fuente: cli` y con
            # «no sé si vive». Repetirlo como aviso sería decir dos veces lo
            # mismo — y como un background muerto se queda en el CLI para
            # siempre (T37), ese aviso saldría en **todas** las corridas: el que
            # enseña a ignorarse, corolario de la regla 3.
            #
            # Lo que sí queda acá es lo que la pantalla no puede mostrar sola:
            # que las dos digan cosas **distintas** del mismo campo.
            continue
        if c["cwd"] and t.get("cwd") and c["cwd"] != t["cwd"]:
            desacuerdos.append({
                "sesion": c["sesion"], "que": "la carpeta no coincide",
                "consola": c["cwd"], "taller": t["cwd"]})
        clase_taller = ALIAS_KIND.get(t.get("clase") or t.get("kind") or "", "")
        if clase_taller and c["clase"] and clase_taller != c["clase"]:
            desacuerdos.append({
                "sesion": c["sesion"], "que": "la clase de sesión no coincide",
                "consola": c["clase"], "taller": clase_taller})
    return desacuerdos
