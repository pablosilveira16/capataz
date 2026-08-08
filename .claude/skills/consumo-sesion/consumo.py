#!/usr/bin/env python3
"""
Consumo de la sesión
====================

Lee la transcripción JSONL que Claude Code guarda en
`~/.claude/projects/<carpeta-del-proyecto>/` y dice cuánto contexto ocupó la
sesión, cuánto le queda y a qué ritmo crece, para decidir si conviene seguir
trabajando, cerrar lo abierto, o parar y dejar todo escrito.

**Sólo lee.** No abre ningún archivo para escribir y no corre nada de git.
Es la misma regla 1 de capataz, y acá importa igual: la transcripción es de
Claude Code, no nuestra.

    python3 consumo.py                      la sesión más nueva del proyecto actual
    python3 consumo.py archivo.jsonl        una transcripción puntual
    python3 consumo.py --json               salida para máquinas
    python3 consumo.py --ventana 200000     ventana a mano (modelo desconocido)
    python3 consumo.py --raiz /otra/.claude si la config no está en ~/.claude

Qué mide y qué no
-----------------
Mide la **ventana de contexto** de la sesión: la suma de tokens de entrada
(sin caché y con caché) más los de salida del último turno del hilo
principal. NO mide el cupo de la suscripción —eso no tiene API para cuentas
individuales— y no descuenta la compactación automática de Claude Code, que
puede estirar la sesión más allá de lo que este número sugiere. Por eso las
decisiones son conservadoras: «parar» significa *cerrar por escrito* —
SEGUIMIENTO, BITACORA, commit— no apagar nada.

Lo que no se sabe se dice «no sé», nunca se inventa (CLAUDE.md § 3):
un modelo que no está en la tabla de ventanas y sin `--ventana` da decisión
«no sé»; una transcripción que no está, también.
"""

import argparse
import io
import json
import os
import re
import sys

# La ventana por modelo, de la documentación de Anthropic. Un modelo que no
# matchea acá NO se estima: se dice «no sé» y se pide --ventana. Preferimos
# un «no sé» molesto a un «te quedan 800k» inventado — al que miente se le cree.
VENTANAS = [
    ("claude-fable-5", 1_000_000),
    ("claude-mythos-5", 1_000_000),
    ("claude-opus-5", 1_000_000),
    ("claude-opus-4-8", 1_000_000),
    ("claude-opus-4-7", 1_000_000),
    ("claude-opus-4-6", 1_000_000),
    ("claude-sonnet-5", 1_000_000),
    ("claude-sonnet-4-6", 1_000_000),
    ("claude-haiku-4-5", 200_000),
]

# Umbrales sobre la fracción de ventana ocupada. Conservadores a propósito:
# el número no descuenta la compactación automática, y cortarse a mitad de un
# cierre sale más caro que cerrar un rato antes.
SEGUIR_HASTA = 0.70
CERRAR_HASTA = 0.85


def ventana_de(modelo):
    for prefijo, v in VENTANAS:
        if modelo and modelo.startswith(prefijo):
            return v
    return None


def carpeta_del_proyecto(raiz, cwd):
    """Claude Code guarda cada proyecto bajo la ruta con todo lo raro a «-»."""
    return os.path.join(raiz, "projects", re.sub(r"[^A-Za-z0-9]", "-", cwd))


def transcripcion_mas_nueva(carpeta):
    if not os.path.isdir(carpeta):
        return None
    rutas = [os.path.join(carpeta, a) for a in os.listdir(carpeta)
             if a.endswith(".jsonl")]
    return max(rutas, key=os.path.getmtime) if rutas else None


def leer_turnos(ruta):
    """(modelo, contexto) por turno del hilo principal, en orden de archivo.

    El contexto de un turno es lo que la API cobró por él: entrada sin caché
    + leída de caché + escrita a caché + salida. Los subagentes
    (`isSidechain`) tienen su propia ventana y se saltean; una línea rota no
    tira el reporte — se ignora y se sigue.
    """
    turnos = []
    with io.open(ruta, encoding="utf-8", errors="replace") as f:
        for linea in f:
            try:
                o = json.loads(linea)
            except ValueError:
                continue
            if o.get("type") != "assistant" or o.get("isSidechain"):
                continue
            m = o.get("message") or {}
            uso = m.get("usage") or {}
            modelo = m.get("model") or ""
            if not uso or modelo.startswith("<"):   # "<synthetic>" y parecidos
                continue
            turnos.append((modelo,
                           uso.get("input_tokens", 0)
                           + uso.get("cache_read_input_tokens", 0)
                           + uso.get("cache_creation_input_tokens", 0)
                           + uso.get("output_tokens", 0)))
    return turnos


def crecimiento_por_turno(turnos, ultimos=10):
    """Promedio de los saltos positivos de contexto entre turnos recientes."""
    contextos = [c for _m, c in turnos]
    saltos = [b - a for a, b in zip(contextos, contextos[1:]) if b > a]
    saltos = saltos[-ultimos:]
    return sum(saltos) // len(saltos) if saltos else None


def informe(archivo, ventana_a_mano=None):
    r = {"archivo": archivo, "modelo": None, "ventana": None, "usado": None,
         "pct": None, "restante": None, "crecimiento_por_turno": None,
         "turnos_estimados": None, "decision": "no sé", "motivo": None,
         "pregunta": None}

    if not archivo or not os.path.isfile(archivo):
        r["motivo"] = "no hay transcripción: sin el archivo no hay número"
        return r

    turnos = leer_turnos(archivo)
    if not turnos:
        r["motivo"] = "la transcripción no tiene ningún turno con usage"
        return r

    modelo, usado = turnos[-1]
    r["modelo"] = modelo
    r["usado"] = usado
    r["crecimiento_por_turno"] = crecimiento_por_turno(turnos)

    ventana = ventana_a_mano or ventana_de(modelo)
    if ventana is None:
        r["motivo"] = ("modelo sin ventana conocida: «%s» — pasá --ventana N "
                       "en vez de dejar que esto adivine" % modelo)
        return r

    r["ventana"] = ventana
    r["restante"] = max(0, ventana - usado)
    r["pct"] = round(usado / ventana, 4)
    if r["crecimiento_por_turno"]:
        r["turnos_estimados"] = r["restante"] // r["crecimiento_por_turno"]

    if r["pct"] < SEGUIR_HASTA:
        r["decision"] = "seguir"
    elif r["pct"] < CERRAR_HASTA:
        r["decision"] = "cerrar"
    else:
        r["decision"] = "parar"

    # Al umbral no se decide solo: se arma la pregunta para Pablo, con los
    # números medidos, y él contrasta contra su panel de uso. La medición
    # local no descuenta la compactación automática — el dato real lo tiene
    # él. Su respuesta corrige; sin respuesta posible, vale la tabla.
    if r["decision"] in ("cerrar", "parar"):
        ritmo = (", creciendo ~%s por turno (~%s turnos más)"
                 % (miles(r["crecimiento_por_turno"]),
                    miles(r["turnos_estimados"]))
                 if r["turnos_estimados"] is not None else "")
        r["pregunta"] = (
            "Medí %s de %s tokens de contexto ocupados (%d %%)%s. Mi decisión "
            "por tabla es «%s». ¿Se ajusta a lo que ves en tu panel de uso? "
            "¿Sigo, cierro lo abierto, o paro y dejo todo escrito?"
            % (miles(r["usado"]), miles(r["ventana"]),
               round(r["pct"] * 100), ritmo, r["decision"]))
    return r


def miles(n):
    return format(n, ",").replace(",", ".")


def imprimir(r):
    print()
    print("  transcripción   %s" % (r["archivo"] or "no sé"))
    print("  modelo          %s" % (r["modelo"] or "no sé"))
    if r["usado"] is not None and r["ventana"] is not None:
        print("  contexto usado  %s de %s (%d %%)"
              % (miles(r["usado"]), miles(r["ventana"]), round(r["pct"] * 100)))
        print("  le quedan       %s tokens" % miles(r["restante"]))
    elif r["usado"] is not None:
        print("  contexto usado  %s — ventana: no sé" % miles(r["usado"]))
    if r["crecimiento_por_turno"]:
        cola = ("→ ~%s turnos más" % miles(r["turnos_estimados"])
                if r["turnos_estimados"] is not None else "")
        print("  crecimiento     ~%s por turno %s"
              % (miles(r["crecimiento_por_turno"]), cola))
    print("  decisión        %s%s"
          % (r["decision"], (" — %s" % r["motivo"]) if r["motivo"] else ""))
    if r["pregunta"]:
        print("  pregunta        %s" % r["pregunta"])
    print()


def main(argv):
    p = argparse.ArgumentParser(description="Consumo de contexto de la sesión")
    p.add_argument("archivo", nargs="?", help="transcripción .jsonl puntual")
    p.add_argument("--json", action="store_true", help="salida JSON")
    p.add_argument("--ventana", type=int, help="ventana del modelo, a mano")
    p.add_argument("--raiz", default=os.environ.get(
        "CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")),
        help="carpeta de config de Claude Code (defecto: ~/.claude)")
    a = p.parse_args(argv)

    archivo = a.archivo or transcripcion_mas_nueva(
        carpeta_del_proyecto(a.raiz, os.getcwd()))
    r = informe(archivo, ventana_a_mano=a.ventana)

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        imprimir(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
