---
name: consumo-sesion
description: Mide cuánto contexto le queda a la sesión leyendo los JSONL de Claude Code (~/.claude/projects/) y decide si seguir trabajando, cerrar lo abierto, o parar y dejar todo escrito. Usala antes de emprender una tarea larga, cuando la sesión ya viene larga, o cuando dudes de si te alcanza el contexto para terminar lo que estás por empezar.
---

# Consumo de la sesión

Claude Code guarda cada sesión como JSONL en `~/.claude/projects/`, y cada
turno del asistente trae su bloque `usage`. Esta skill lo lee y contesta las
tres preguntas que importan antes de arrancar algo largo: **cuánto contexto
va ocupado, cuánto queda, y a qué ritmo se está yendo.**

## Cómo se corre

    python3 .claude/skills/consumo-sesion/consumo.py

Sin argumentos agarra la transcripción más nueva del proyecto de la carpeta
actual. Para decidir en código, `--json`:

    python3 .claude/skills/consumo-sesion/consumo.py --json

## Cómo se decide

El campo `decision` sale de la fracción de ventana ocupada:

| decisión | cuándo | qué hacer |
|---|---|---|
| `seguir` | menos del 70 % | trabajar normal |
| `cerrar` | 70–85 % | **preguntar primero** (ver abajo); mientras no haya respuesta: nada nuevo y grande, terminar lo abierto y dejar `SEGUIMIENTO.md` al día |
| `parar` | más del 85 % | **preguntar primero**; mientras no haya respuesta: cerrar por escrito **ya** — `SEGUIMIENTO.md`, `BITACORA.md`, commit. Lo que quede, anotado como pendiente |
| `no sé` | falta un dato | ver `motivo`; no tratar «no sé» como verde |

## Al llegar al umbral: preguntar, no decidir solo

Cuando la decisión sale `cerrar` o `parar`, el reporte trae el campo
`pregunta` ya redactado con los números medidos. **Mandásela a Pablo antes
de actuar** —con `AskUserQuestion` si está disponible, o como pregunta
directa— para que contraste contra lo que ve en su panel de uso: esta
medición no descuenta la compactación automática, así que el dato real lo
tiene él.

Su respuesta **corrige, no reemplaza**:

- «hay más lugar del que decís» → seguí, y volvé a medir más seguido; si te
  dice cuánto, ajustá con `--ventana`.
- «sí, se ajusta» → aplicá lo que dice la tabla.
- **Sin respuesta posible** (sesión desatendida) → no te quedes bloqueado
  esperando: vale la tabla, que peca de prudente a propósito.

`crecimiento_por_turno` y `turnos_estimados` son el pronóstico: el promedio
de lo que creció el contexto en los últimos turnos, y cuántos turnos así
entran en lo que queda. Si la tarea que estás por empezar necesita más turnos
que ésos, cerrá primero.

## Qué mide y qué no — leer antes de confiar

- Mide la **ventana de contexto** de esta sesión, no el cupo de la
  suscripción (eso no tiene API para cuentas individuales).
- **No descuenta la compactación automática** de Claude Code, que puede
  estirar la sesión. Por eso los umbrales son conservadores y «parar»
  significa *cerrar por escrito*, no apagar nada: cortarse a mitad de un
  cierre sale más caro que cerrar un rato antes.
- Un modelo que no está en la tabla de ventanas da `no sé` — se arregla con
  `--ventana N`, no adivinando.
- La skill **sólo lee**. Es la regla 1 de capataz aplicada a los archivos de
  Claude Code: mirar y mostrar, nunca escribir.

## Instalarla para toda la máquina

Dentro de este repo la skill anda sola. Para que la vea **cualquier** sesión
—en cualquier carpeta—:

    ./ops/instalar-skill-consumo.sh

La engancha con un enlace simbólico en `~/.claude/skills/` (una sola fuente:
el repo). Correrlo dos veces no rompe nada, y si en el destino hay algo que
no es un enlace, se niega en vez de pisarlo.

Arnés: `pruebas/verificar-consumo.py` — se ejercita contra transcripciones
armadas en `/tmp` con números conocidos, como manda `CLAUDE.md` § 2.
