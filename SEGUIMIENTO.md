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

Lo único que hay que mirar para saber qué falta. El detalle de cada punto está
más abajo, en la tanda donde nació.

### Depende de una decisión (Pablo)

| # | Qué falta | Desde | Estado |
|---|---|---|---|
| D1 | **Mirar la pantalla en un teléfono de verdad.** Está verificado que las condiciones para 360 px se cumplen —`verificar-angosto.py` § 1 calcula 340 + 2×10 = 360— pero *mirar* no se pudo: en el contenedor de un agente no hay Chromium ni Playwright. `./run.sh --instantanea` deja un `_instantanea.html` que se abre con `file://` desde la Mac. Es de Pablo porque el navegador está de ese lado | 2026-08-06 | pendiente (Pablo) |
| D2 | **El repositorio `github.com/pablosilveira16/capataz`.** La plomería está hecha y verificada (T1); falta el repo vacío y el token *fine-grained* con `Contents: Read and write` + `Metadata: Read-only` + **`Workflows: Read and write`** —el que a ERP 360 le faltó y rechazó el push entero— en `../.credenciales/github-capataz.token`, `chmod 600`. Los pasos exactos están en `ops/70-credenciales.md` | 2026-08-06 | pendiente (Pablo) |
| D3 | **Hasta dónde llega capataz.** Hoy es un visor y `CLAUDE.md` § 1 dice que no decide ni lanza nada. La orquestación —convocar un agente, asignarle un punto— es el paso siguiente y **cambia la regla que manda**: en el momento en que capataz marque un punto `en curso`, deja de ser sólo lector. Se decide cuando la lectura esté rodada, no antes | 2026-08-06 | pendiente (Pablo) |

### Se puede hacer sin preguntar

| # | Qué falta | Desde | Estado |
|---|---|---|---|
| T2 | **Ni ERP 360 ni Finca 360 dejan el total de aserciones medido**, así que capataz muestra «no sé» en todas sus ramas — que es lo correcto y también es inútil. El arreglo son tres líneas en el `verificar.sh` de cada uno, las mismas que ya tiene el de capataz: escribir el total en `pruebas/total-aserciones.txt` sólo cuando está todo verde. Es trabajo **en el repo de ellos**, no acá | 2026-08-06 | pendiente |
| T3 | **Un `en curso` sin fecha no dice hace cuánto.** El lector saca la antigüedad de la columna `Desde`, que es la fecha en que nació el punto y no la de la toma. Un punto tomado hoy que nació hace un mes se ve como un `en curso` de treinta días. La fecha de la toma está en dos lugares que capataz ya alcanza: la marca de `panel/agentes.jsonl` y el commit del `--tomar`. Falta cruzarlas | 2026-08-06 | pendiente |
| T4 | **Un proyecto cuyas tablas de puntos no tengan columna `#` se lee como vacío**, en silencio. Hoy se cuenta en `tablas_ignoradas` y no se muestra: mostrarlo siempre sería el aviso que sale siempre. Falta la forma que avise **sólo cuando importa** —cero puntos leídos y una tabla ignorada— y un arnés que lo vea rojo | 2026-08-06 | pendiente |
| T5 | **El CI se puede leer desde la Mac y no desde el contenedor.** `interpretar_ci()` ya existe y está verificada con las cinco respuestas; lo que falta es quién le pasa la respuesta. Va detrás de una variable de entorno, y **sin ella el resultado se queda en «no sé»**, nunca en verde | 2026-08-06 | pendiente |
| T6 | **Capataz no tiene CI.** ERP 360 corre `./verificar.sh` en un workflow; acá no hay ninguno. Es barato y es la única forma de que el total se mire solo | 2026-08-06 | pendiente |

### Decidido, esperando el momento

| # | Qué | Desde | Hasta cuándo | Estado |
|---|---|---|---|---|
| X1 | **Que capataz muestre el CI de verdad en el tablero.** El mecanismo está (T5); lo que falta es dónde corre capataz | 2026-08-06 | que se decida D3 | diferido |
| X2 | **Despliegue.** Hoy corre en `127.0.0.1:5402` con el servidor de la biblioteca estándar, que no va a producción. Y para leerlo desde el teléfono hace falta que llegue desde afuera de la Mac, que es una decisión de red antes que de código | 2026-08-06 | que se decida D3 | diferido |

---

# Historia por tanda

Lo de abajo es el registro de cada tanda, con los puntos ya cerrados. **Para
saber qué falta no hace falta leerlo**: está todo arriba.

---

## Tanda 0 — el andamio y el lector, 2026-08-06

El proyecto arranca siguiendo al pie el orden de
`ERP360-Template/documentacion/andamio-proyecto-nuevo.md`, § «El orden». Los
cuatro primeros puntos son el andamio y **ninguno toca la aplicación**; el
código empieza en el A5.

| # | Punto | Estado |
|---|---|---|
| A1 | Este seguimiento, con el contrato y los cinco estados, **vacío** | **hecho** · `verificar-contrato.sh` 10 aserciones — commit `eb6a341` |
| A2 | `verificar.sh` y un arnés que verifique lo más tonto que se me ocurra | **hecho** · `verificar-contrato.sh` 10 aserciones — visto en rojo con un estado inventado |
| A3 | `git init` y el primer commit, **antes de la primera línea de la app** | **hecho** · `verificar-contrato.sh` 10 aserciones — commit `eb6a341`, y `core.filemode true` puesto desde el día cero |
| A4 | `CLAUDE.md` con tres reglas — no diez | **hecho** · `verificar-angosto.py` 25 aserciones — 72 de 72 líneas, commit `f968fa6` |
| A5 | `lector.py`: los dos formatos de seguimiento, los roles, la cuadrilla, las ramas y el CI | **hecho** · `verificar-lector.py` 81 aserciones — proyectos de verdad armados en `/tmp` |
| A6 | `capataz.py` y `capataz.html` en el 5402, sin dependencias | **hecho** · `verificar-angosto.py` 25 aserciones — se ejecuta `render_estatico()` y se mira el HTML producido |
| A7 | `ops/`, con la marcha atrás **antes** que el despliegue | **hecho** · `verificar-angosto.py` 25 aserciones — el puerto del mapa y el de `capataz.py` son el mismo |
| T1 | La plomería para empujar a GitHub, traída de ERP 360 y adaptada | **hecho** · `verificar-credenciales.py` 26 aserciones — el helper se ejecuta de verdad |
