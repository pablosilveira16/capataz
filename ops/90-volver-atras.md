# La marcha atrás

> Escrita **antes** que cualquier runbook de despliegue, y a propósito: es lo
> único que hay que ensayar antes de necesitarlo. Un proyecto que sabe publicar
> y no sabe deshacer publica una sola vez.

Capataz tiene una ventaja rara y conviene decirla antes que nada: **no guarda
nada**. No hay base, no hay migraciones y no hay datos de usuario. Todo lo que
muestra sale, en cada pedido, de los archivos de otros proyectos. Volver atrás
es volver el código atrás, y nada más.

Eso reduce la marcha atrás a tres casos, y ninguno pierde información.

## 1 · Un commit rompió un arnés

```bash
./verificar.sh                       # anotá el total de ANTES
git log --oneline -10
git revert <sha>                     # revert, no reset: el commit malo queda a la vista
./verificar.sh                       # el total tiene que volver al de antes
```

**Lo que hay que mirar es el total, no el color.** Un revert que deja todo en
verde con menos aserciones que antes se llevó puesto un arnés, y eso es
exactamente lo que el total existe para atrapar. El número queda escrito en
`pruebas/total-aserciones.txt`, así que la comparación es un `git diff` de una
línea.

`git reset --hard` no: reescribe la historia y en una rama compartida deja al
que ya la trajo con dos versiones del mismo pasado. El `revert` cuesta un
commit más y no cuesta ninguna conversación.

## 2 · La pantalla quedó rota y no hay tiempo de arreglarla

```bash
git checkout <sha-bueno> -- capataz.html
./verificar.sh
```

`capataz.html` no tiene estado adentro: se puede volver a cualquier versión
anterior sin tocar nada más, porque todo lo que muestra se lo pasa el servidor.
Es una de las razones por las que la pantalla no guarda nada del lado del
navegador.

## 3 · Un proyecto vigilado se movió, se renombró o desapareció

**No hay nada que revertir en capataz.** Se edita `proyectos.json` —la ruta o el
nombre del archivo de seguimiento— y listo. Si un proyecto desaparece del disco,
capataz lo muestra como «no encuentro el seguimiento» con la ruta que buscó, y
sigue mostrando los demás. Un proyecto que se cayó no puede tirar el tablero.

Se puede comprobar sin romper nada, y conviene hacerlo una vez:

```bash
python3 -c "import lector; print(lector.mirar({'nombre':'x','ruta':'/no/existe'})['seguimiento'])"
```

## Lo que capataz NO puede romper, y por qué

Ningún error de capataz puede dañar un proyecto vigilado: `lector.py` no abre
nada en modo escritura y sus comandos de git pasan por una lista blanca de
subcomandos de lectura —`fetch`, `checkout`, `push` y `worktree` revientan con
`SoloLectura`—. `pruebas/verificar-lector.py` § 1 lo verifica corriendo
`mirar()` entero contra un repositorio de verdad y comparando el árbol byte a
byte, el `HEAD` y el `git status` de antes y después.

Ésa es la marcha atrás más barata que existe: la que no hace falta.

## El ensayo

**Este runbook está escrito y sin ensayar**, que lo deja en hipótesis prolija.
El ensayo del caso 1 se puede hacer hoy, sin servidor y adentro del contenedor
de un agente: romper una aserción a propósito, ver bajar el total, revertir y
ver que vuelve. Cuando se haga, va acá con la fecha y quién lo hizo.

| Caso | Ensayado | Cuándo | Quién |
|---|---|---|---|
| 1 · revertir un commit | no | — | — |
| 2 · volver la pantalla | no | — | — |
| 3 · un proyecto que se movió | sí | 2026-08-06 | coder-1 · `verificar-lector.py` § 6 |
