#!/usr/bin/env python3
"""
Arnés de la skill de consumo
============================

Vigila `.claude/skills/consumo-sesion/consumo.py`: el lector de las
transcripciones JSONL de Claude Code que dice cuánto contexto le queda a la
sesión y si conviene seguir, cerrar o parar.

**Por qué ejecuta en vez de leer** (regla 2 de `CLAUDE.md`): leer el script y
buscar una cadena no prueba que corra. Acá se arman transcripciones falsas en
`/tmp` con números elegidos a mano, se corre el script como lo correría un
agente —subproceso, con `--json`— y se comparan los números contra la cuenta
hecha en papel. Si el script suma otra cosa, esto se pone rojo.

Lo que afirma, en orden:

* **Los números conocidos dan los números conocidos.** Tres turnos con usage
  elegido a mano: usado, restante, pct, crecimiento y turnos estimados salen
  exactos.
* **Lo que no es un turno del hilo principal no cuenta**: subagentes
  (`isSidechain`), líneas rotas, modelos sintéticos, líneas de usuario.
* **Los umbrales deciden lo que dicen que deciden**: seguir / cerrar / parar.
* **Lo que no se sabe dice «no sé», nunca un número inventado** (regla 3):
  modelo desconocido sin `--ventana`, transcripción que no está, transcripción
  sin turnos.
* **Encuentra la transcripción más nueva del proyecto** bajo una raíz de
  mentira, sin que nadie le pase la ruta.
* **Sólo lee**: corre bien con la transcripción en una carpeta de sólo
  lectura, y el fuente no tiene ningún open() de escritura.

    python3 pruebas/verificar-consumo.py
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(AQUI, ".claude", "skills", "consumo-sesion", "consumo.py")
SKILL = os.path.join(AQUI, ".claude", "skills", "consumo-sesion", "SKILL.md")

verdes = 0
rojas = 0


def ok(_etq):
    global verdes
    verdes += 1


def roja(etq, detalle=""):
    global rojas
    rojas += 1
    print("  ROJA  %s%s" % (etq, (" — %s" % detalle) if detalle else ""))


def afirmar(cond, etq, detalle=""):
    ok(etq) if cond else roja(etq, detalle)


def linea_turno(modelo, entrada, cache_leida, cache_escrita, salida,
                sidechain=False):
    return json.dumps({
        "type": "assistant", "isSidechain": sidechain,
        "message": {"model": modelo, "usage": {
            "input_tokens": entrada,
            "cache_read_input_tokens": cache_leida,
            "cache_creation_input_tokens": cache_escrita,
            "output_tokens": salida,
        }}})


def escribir(ruta, lineas):
    with io.open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def correr(*args, cwd=None):
    """Corre el script como subproceso y devuelve (código, json_o_None, texto)."""
    r = subprocess.run([sys.executable, SCRIPT] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=30, cwd=cwd)
    dato = None
    if "--json" in args:
        try:
            dato = json.loads(r.stdout)
        except ValueError:
            pass
    return r.returncode, dato, r.stdout + r.stderr


tmp = tempfile.mkdtemp(prefix="capataz-consumo-")

# ------------------------------------------------------------------
# 1 · Los números conocidos dan los números conocidos
# ------------------------------------------------------------------
#
# La cuenta en papel, para que el que lea la roja no tenga que rehacerla:
#   turno 1: 10 + 0    + 1000 + 100 = 1110
#   turno 2: 5  + 1500 + 200  + 300 = 2005
#   turno 3: 2  + 2500 + 100  + 400 = 3002   ← el usado es el del ÚLTIMO turno
#   saltos: 895 y 997 → promedio entero 946
#   ventana de claude-fable-5: 1.000.000 → restante 996.998 → 996998//946 = 1053
print()
print("1 · Los números conocidos")

sesion = os.path.join(tmp, "sesion.jsonl")
escribir(sesion, [
    json.dumps({"type": "user", "message": {"content": "hola"}}),
    linea_turno("claude-fable-5", 10, 0, 1000, 100),
    "{esto no es json y no tiene que tirar nada",
    linea_turno("claude-fable-5", 999999, 999999, 0, 999999, sidechain=True),
    linea_turno("<synthetic>", 777, 777, 777, 777),
    linea_turno("claude-fable-5", 5, 1500, 200, 300),
    linea_turno("claude-fable-5", 2, 2500, 100, 400),
])

codigo, r, salida = correr(sesion, "--json")
afirmar(codigo == 0 and r is not None, "el script corre y contesta JSON",
        salida[:200])
r = r or {}
afirmar(r.get("usado") == 3002, "usado = 3002, la suma del último turno",
        str(r.get("usado")))
afirmar(r.get("modelo") == "claude-fable-5", "el modelo es el del último turno")
afirmar(r.get("ventana") == 1000000, "la ventana de claude-fable-5 es 1.000.000",
        str(r.get("ventana")))
afirmar(r.get("restante") == 996998, "restante = 996.998", str(r.get("restante")))
afirmar(r.get("pct") == 0.003, "pct = 0.003", str(r.get("pct")))
afirmar(r.get("crecimiento_por_turno") == 946,
        "crecimiento = 946, el promedio de los saltos 895 y 997",
        str(r.get("crecimiento_por_turno")))
afirmar(r.get("turnos_estimados") == 1053, "turnos estimados = 996998 // 946 = 1053",
        str(r.get("turnos_estimados")))
afirmar(r.get("decision") == "seguir", "con 0,3 %% ocupado la decisión es seguir",
        str(r.get("decision")))

# ------------------------------------------------------------------
# 2 · Lo que no es un turno del hilo principal no cuenta
# ------------------------------------------------------------------
#
# El usado==3002 de arriba ya prueba que el subagente de 999999 no sumó. Acá
# el caso límite: un archivo donde SÓLO hay subagentes, basura y usuario tiene
# cero turnos, y cero turnos es «no sé» — no un cero verde.
print("2 · Sólo el hilo principal")

solo_ruido = os.path.join(tmp, "ruido.jsonl")
escribir(solo_ruido, [
    json.dumps({"type": "user", "message": {"content": "hola"}}),
    linea_turno("claude-fable-5", 111, 0, 0, 111, sidechain=True),
    "basura{",
    linea_turno("<synthetic>", 5, 5, 5, 5),
])
codigo, r, _ = correr(solo_ruido, "--json")
r = r or {}
afirmar(codigo == 0 and r.get("decision") == "no sé",
        "una transcripción sin turnos del hilo principal decide «no sé»",
        str(r.get("decision")))
afirmar(r.get("usado") is None, "…y no inventa un usado", str(r.get("usado")))

# ------------------------------------------------------------------
# 3 · Los umbrales deciden lo que dicen que deciden
# ------------------------------------------------------------------
#
# Con --ventana se aprieta la ventana sobre el mismo archivo de 3002:
#   3002 / 4000 = 0,7505 → entre 70 y 85 → cerrar
#   3002 / 3300 = 0,9097 → más de 85     → parar
print("3 · Los umbrales")

codigo, r, _ = correr(sesion, "--json", "--ventana", "4000")
afirmar(codigo == 0 and (r or {}).get("decision") == "cerrar",
        "al 75 %% la decisión es cerrar", str((r or {}).get("decision")))
codigo, r, _ = correr(sesion, "--json", "--ventana", "3300")
afirmar(codigo == 0 and (r or {}).get("decision") == "parar",
        "al 91 %% la decisión es parar", str((r or {}).get("decision")))
afirmar((r or {}).get("restante") == 298,
        "y el restante acompaña a la ventana apretada: 3300 − 3002 = 298",
        str((r or {}).get("restante")))

# ------------------------------------------------------------------
# 4 · «No sé» nunca verde
# ------------------------------------------------------------------
print("4 · «No sé» nunca verde")

# --- modelo que no está en la tabla ---------------------------------
raro = os.path.join(tmp, "raro.jsonl")
escribir(raro, [linea_turno("modelo-inventado-9", 50, 0, 0, 50)])
codigo, r, _ = correr(raro, "--json")
r = r or {}
afirmar(codigo == 0 and r.get("decision") == "no sé",
        "un modelo desconocido decide «no sé», no adivina la ventana",
        str(r.get("decision")))
afirmar(r.get("ventana") is None, "…con ventana en null", str(r.get("ventana")))
afirmar(r.get("usado") == 100,
        "…pero el usado sí se informa: 100 es medido, no adivinado",
        str(r.get("usado")))
afirmar("--ventana" in (r.get("motivo") or ""),
        "…y el motivo dice el arreglo: pasar --ventana",
        str(r.get("motivo")))

# El mismo archivo CON --ventana deja de ser «no sé»: el dato faltante era ése.
codigo, r, _ = correr(raro, "--json", "--ventana", "1000")
afirmar(codigo == 0 and (r or {}).get("decision") == "seguir",
        "el mismo modelo desconocido con --ventana 1000 ya decide: seguir",
        str((r or {}).get("decision")))

# --- y en la salida para humanos, el «no sé» se ve ------------------
codigo, _d, salida = correr(raro)
afirmar(codigo == 0 and "no sé" in salida,
        "la salida para humanos también dice «no sé», no un guión ni un cero",
        salida[:200])

# --- transcripción que no está --------------------------------------
codigo, r, _ = correr(os.path.join(tmp, "no-existe.jsonl"), "--json")
r = r or {}
afirmar(codigo == 0 and r.get("decision") == "no sé",
        "sin transcripción la decisión es «no sé» y el script no revienta",
        str(r.get("decision")))
afirmar("transcripción" in (r.get("motivo") or ""),
        "…y el motivo dice qué falta", str(r.get("motivo")))

# ------------------------------------------------------------------
# 5 · Encuentra la transcripción más nueva del proyecto
# ------------------------------------------------------------------
#
# Se arma una raíz de mentira con la carpeta codificada como la codifica
# Claude Code —la ruta con todo lo no alfanumérico a «-»— y dos sesiones.
# La más nueva por mtime tiene usado 777; si el script agarra la vieja (500),
# rojo.
print("5 · El descubrimiento")

proyecto = os.path.join(tmp, "proyecto de prueba")   # con espacio, a propósito
os.makedirs(proyecto)
raiz = os.path.join(tmp, "raiz-claude")
codificada = re.sub(r"[^A-Za-z0-9]", "-", proyecto)
carpeta = os.path.join(raiz, "projects", codificada)
os.makedirs(carpeta)

vieja = os.path.join(carpeta, "vieja.jsonl")
nueva = os.path.join(carpeta, "nueva.jsonl")
escribir(vieja, [linea_turno("claude-fable-5", 500, 0, 0, 0)])
escribir(nueva, [linea_turno("claude-fable-5", 777, 0, 0, 0)])
os.utime(vieja, (1000000000, 1000000000))
os.utime(nueva, (2000000000, 2000000000))

codigo, r, salida = correr("--json", "--raiz", raiz, cwd=proyecto)
r = r or {}
afirmar(codigo == 0 and (r.get("archivo") or "").endswith("nueva.jsonl"),
        "sin ruta, agarra la transcripción más nueva del proyecto actual",
        str(r.get("archivo")))
afirmar(r.get("usado") == 777, "…y lee ésa: usado = 777", str(r.get("usado")))

# Desde una carpeta que no tiene proyecto, «no sé» — no la sesión de otro.
codigo, r, _ = correr("--json", "--raiz", raiz, cwd=tmp)
afirmar(codigo == 0 and (r or {}).get("decision") == "no sé",
        "una carpeta sin transcripciones decide «no sé», no agarra la de otro",
        str((r or {}).get("decision")))

# ------------------------------------------------------------------
# 6 · Sólo lee
# ------------------------------------------------------------------
#
# Las dos mitades, porque cada una sola es débil: correr con la carpeta en
# sólo lectura prueba que no escribe AHÍ; mirar el fuente prueba que no hay
# ningún open() de escritura hacia ningún otro lado. La segunda sola sería
# leer-y-buscar-una-cadena; la primera sola dejaría pasar un log escrito en
# /tmp.
print("6 · Sólo lee")

os.chmod(carpeta, 0o555)
codigo, r, _ = correr("--json", "--raiz", raiz, cwd=proyecto)
afirmar(codigo == 0 and (r or {}).get("usado") == 777,
        "con la carpeta de las transcripciones en sólo lectura corre igual")
os.chmod(carpeta, 0o755)

with io.open(SCRIPT, encoding="utf-8") as f:
    fuente = f.read()
escrituras = re.findall(r"""open\([^)]*["'][wax]\+?["']""", fuente)
afirmar(not escrituras, "el fuente no tiene ningún open() de escritura",
        " ".join(escrituras))
afirmar("subprocess" not in fuente and "os.system" not in fuente,
        "y no corre ningún comando: lee archivos, nada más")

# ------------------------------------------------------------------
# 7 · La skill existe y apunta a lo que corre
# ------------------------------------------------------------------
print("7 · La skill")

afirmar(os.path.isfile(SKILL), ".claude/skills/consumo-sesion/SKILL.md existe")
with io.open(SKILL, encoding="utf-8") as f:
    skill = f.read()
afirmar("consumo.py" in skill, "la skill dice qué script correr")
afirmar("no sé" in skill, "la skill trae la regla de «no sé» nunca verde")
afirmar("verificar-consumo" in skill,
        "la skill nombra este arnés, para que el que la toque sepa qué corre")

shutil.rmtree(tmp, ignore_errors=True)

print()
print("ASERCIONES: %d" % verdes)
print("ROJAS: %d" % rojas)
sys.exit(1 if rojas else 0)
