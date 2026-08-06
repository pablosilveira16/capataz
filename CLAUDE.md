# Reglas de esta carpeta

Una página, **tope duro de 72 líneas**: el valor de este archivo es que se lee
entero antes de empezar, y un archivo que crece deja de leerse. Si algo entra,
algo sale. Lo que **falta** va en `SEGUIMIENTO.md`, el *por qué* en `BITACORA.md`;
`pruebas/verificar-contrato.sh` verifica el tope y que exista lo que se nombra acá.

**Son tres reglas y no diez.** Van a ser diez; se ganan una por una, cada una con
el día que costó. Una regla sin cicatriz es una regla que nadie respeta.

## Empezar y terminar

1. **Leer `SEGUIMIENTO.md`.** Es la única lista de lo que está abierto: lo que no
   está escrito ahí, no existe. Y la bitácora, sólo el capítulo del tema.
2. `./run.sh` → **http://127.0.0.1:5402**. El puerto está fijo en `capataz.py` y
   escrito en `ops/00-mapa.md`; los vecinos ocupados son el 5300, 5301 y 5302 (VM
   de Oracle), el 5400 (app de ERP 360) y el 5401 (panel de ERP 360).
3. **Acá hay git: el respaldo es el commit.** Nada de copias `.antes-de-*`.
4. Al terminar: `./verificar.sh` en verde **con el total**, y cerrar por escrito
   —`SEGUIMIENTO.md` y `BITACORA.md` siempre—. Un punto nuevo se anota **apenas
   aparece**: el seguimiento existe para la sesión que se corta.

## 1 · Capataz sólo lee. No es fuente de verdad de nada

El `SEGUIMIENTO.md` de cada proyecto es la verdad y **git es el árbitro**. Capataz
mira y muestra: no decide, no lanza agentes, no marca puntos y **no guarda ningún
estado propio**.

Si guardara el estado de un punto habría dos lugares con el mismo dato y ninguna
regla sobre cuál gana — **el bug más caro de Finca 360**, según el andamio
(`ERP360-Template/documentacion/andamio-proyecto-nuevo.md`). Lo que se verifica
es esto: **`lector.py` no abre ningún archivo
para escribir, no crea ninguna base y no corre ningún comando de git que
escriba.** Un `fetch`, un `checkout` o un `worktree` desde acá ya es capataz
teniendo opinión sobre el repo de otro. → `pruebas/verificar-lector.py` § 1

Corolario que se pierde si no se escribe: las marcas de agentes las escribe el
`panel/agente.py` **de cada proyecto**, en su propio `panel/agentes.jsonl`.
Capataz lo lee y no lo escribe nunca. Por eso no absorbió `agente.py`.

## 2 · Un arnés no vale hasta verlo rojo, y menos si es vacuo

**Nuevo o cambiado, se pone el bug de vuelta y se mira el rojo** — después se
revierte y se confirma con `diff -q`. Si no está escrito que se lo vio, no se lo
vio. Y **cuando un arnés falla, la primera hipótesis es el arnés.**

**El caso vacuo es el que más caro sale**, porque se cuenta en el total y da
sensación de cobertura: una aserción que pasa igual con el bug puesto no verifica
nada. La forma que ya salió mal cuatro veces en el proyecto hermano: **leer un
archivo y buscar una cadena no prueba que el código corra.** Acá el lector se
ejercita contra proyectos de prueba armados en `/tmp`, con números conocidos.
→ `pruebas/verificar-lector.py`

**El total de aserciones es parte del resultado**, y cero aserciones es falla: un
arnés que deja de encontrar lo que mira no se pone rojo, saltea en silencio y lo
único que cambia es la cuenta. → `verificar.sh`

## 3 · Lo que no se sabe se muestra «no sé», nunca verde

Un tablero que miente en el caso que importa es peor que no tenerlo: **al que
miente se le cree**. Tres datos pueden faltar y tienen que verse faltando:

- **El CI.** `api.github.com` está fuera de la lista blanca del contenedor de un
  agente —medido, no supuesto—, así que desde acá no se lee. Sin respuesta, `no
  sé`; jamás `verde`.
- **El total de aserciones de una rama.** Sólo si el proyecto lo dejó medido en
  `pruebas/total-aserciones.txt`. Declarado en prosa no es medido.
- **Los roles de un proyecto sin `ops/60-roles.md`** —Finca 360 es uno—: no se
  inventa la lista de seis, se dice que no se sabe.

Corolario: **no se agrega un aviso que sale siempre.** Enseña a ignorarlo, y el
día que dice algo tampoco se lee. → `pruebas/verificar-lector.py` § 5
