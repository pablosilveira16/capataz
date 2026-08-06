# Capataz — Seguimiento

> **Si sos un agente que recién llega a este proyecto, empezá por acá.** Esta es
> la única lista de lo que está abierto. No depende de ninguna sesión ni de
> ningún modelo: lo que no está escrito acá, no existe.
>
> Después leé `CLAUDE.md` (las tres reglas) y `BITACORA.md` (por qué quedó así),
> sólo el capítulo del tema que vas a tocar.

## Qué es capataz

Una app web chica que **mira** el trabajo de los agentes en varios proyectos y
lo muestra en una pantalla que se lee **desde un teléfono**. Ése es el requisito
que la motiva: sin esto, saber qué pasó exige abrir GitHub en la computadora.

**Capataz sólo lee.** El `SEGUIMIENTO.md` de cada proyecto es la verdad y git es
el árbitro; capataz no guarda ningún estado propio. Está escrito como regla en
`CLAUDE.md` y verificado en `pruebas/verificar-lector.py`.

## El contrato de este archivo

**Qué lleva.** Lo que **falta**. La bitácora lleva lo que se hizo y por qué;
cuando un punto se cierra, su historia se va a la bitácora y acá queda la línea
de estado. Las dos cosas se escriben al cerrar cada tanda.

**Cuándo se escribe una línea.** Apenas aparece el punto, no al terminar. Un
pedido que se anota cuando ya está resuelto no sirve de nada: el archivo existe
para el caso en que la sesión se corte en el medio.

**Los estados, y no hay otros** — los verifica `pruebas/verificar-contrato.sh`,
que se pone rojo con cualquier palabra que no sea una de estas cinco:

| | |
|---|---|
| `pendiente` | Falta hacerlo. Si depende de una persona, se aclara: `pendiente (Pablo)` |
| `en curso` | Alguien lo está haciendo ahora. Con quién: `en curso (coder-1)` |
| `hecho` | Terminado **y verificado** — con el arnés y el número de aserciones al lado |
| `diferido` | Se decidió no hacerlo todavía, y se dice hasta cuándo o por qué |
| `descartado` | Se decidió no hacerlo |

**Dónde va el estado.** En la **última celda** de la fila, y la columna se llama
`Estado`. El arnés lo lee de ahí; una tabla de puntos sin columna de estado es
una tabla que nadie verifica — y capataz, que lee los seguimientos ajenos, tiene
que adivinar (ver `lector.py`, y el punto T4).

**Cómo se cierra un punto.** Se marca `hecho` con la prueba pegada al lado —el
arnés que lo vigila **y** su número de aserciones—, se saca de *Abierto ahora* y
se le escribe el capítulo en la bitácora. **`hecho` sin prueba al lado es una
opinión.**

**Y acá hay git.** Todo punto cerrado tiene su commit. Un punto que se cerró en
la máquina de alguien y no está en `main` está abierto.

---

## Abierto ahora

*(vacío — este archivo nace antes que el código, que es el punto del andamio:
`ERP360-Template/documentacion/andamio-proyecto-nuevo.md`, «El orden»)*

### Depende de una decisión (Pablo)

| # | Qué falta | Desde | Estado |
|---|---|---|---|

### Se puede hacer sin preguntar

| # | Qué falta | Desde | Estado |
|---|---|---|---|

### Decidido, esperando el momento

| # | Qué | Desde | Hasta cuándo | Estado |
|---|---|---|---|---|

---

# Historia por tanda

Lo de abajo es el registro de cada tanda, con los puntos ya cerrados. **Para
saber qué falta no hace falta leerlo**: está todo arriba.

---

## Tanda 0 — el andamio y el lector, 2026-08-06

| # | Punto | Estado |
|---|---|---|
| A1 | Este seguimiento, con el contrato y los cinco estados | en curso (coder-1) |
| A2 | `verificar.sh` y el primer arnés, antes del primer commit | pendiente |
| A3 | `git init` y el primer commit, **antes de la primera línea de la app** | pendiente |
| A4 | `CLAUDE.md` con tres reglas — no diez | pendiente |
