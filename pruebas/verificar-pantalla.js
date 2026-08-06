#!/usr/bin/env node
/* La pantalla, ejecutándola — y sobre todo: que «no sé» NUNCA se pinte verde.
 *
 * **Por qué existe, y por qué en node.** `pruebas/verificar-angosto.py` mira la
 * hoja de estilo y el HTML que produce `render_estatico()`, pero la tarjeta de
 * cada proyecto la dibuja el JavaScript de `capataz.html` en el navegador: el
 * archivo estático trae los datos y un `<div id="cuerpo">` vacío. O sea que la
 * regla 3 de `CLAUDE.md` —«lo que no se sabe se muestra no sé, nunca verde»—
 * estaba verificada en el lector (`interpretar_ci` devuelve «no sé») y **no en
 * la pantalla**, que es donde alguien la lee. Entre las dos cosas hay una
 * función, `bloqueCI`, y una línea que decide la clase CSS.
 *
 * Un tablero que miente justo cuando no sabe es peor que no tenerlo, así que esa
 * línea merece que alguien la ejecute.
 *
 * Cómo: se saca el `<script>` de `capataz.html`, se lo corre en un `vm` con un
 * DOM mínimo, y se le pasan **los datos de verdad** —los que produce
 * `capataz.estado()` sobre los proyectos vigilados— capturando el HTML que
 * escribe. No se lee ni una cadena del archivo: se mira lo que dibujó.
 *
 * Las tres aserciones que sostienen a las demás:
 *
 *   § 2  con los datos reales, el CI de cada proyecto dice «no sé» y su chip
 *        NO lleva la clase verde;
 *   § 3  **y con un CI verde de verdad, sí la lleva** — sin esto, § 2 pasaría
 *        igual con una pantalla que no pinta verde nunca, que es la definición
 *        de aserción vacua;
 *   § 4  un total de aserciones que no se sabe se dibuja «no sé» y no «0»: un
 *        cero se lee como «no hay» y esto es «no sé», que es otra cosa.
 *
 *     node pruebas/verificar-pantalla.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { execFileSync } = require("child_process");

const RAIZ = path.dirname(__dirname);
let ASER = 0;
let ROJAS = 0;

function af(descripcion, condicion, detalle) {
  if (condicion) {
    ASER += 1;
  } else {
    ROJAS += 1;
    console.log("ROJA  " + descripcion + (detalle ? "  →  " + detalle : ""));
  }
}

function igual(descripcion, obtenido, esperado) {
  af(descripcion, obtenido === esperado,
     "obtuve " + JSON.stringify(obtenido) + ", esperaba " + JSON.stringify(esperado));
}

// --- los datos de verdad, producidos por el mismo código que sirve la API ----
//
// No es un JSON escrito a mano: es `capataz.estado()`, leyendo los proyectos
// vigilados del disco. Si mañana el lector devuelve otra forma, esto se entera.
const datos = JSON.parse(execFileSync(
  "python3",
  ["-c", "import json,capataz; print(json.dumps(capataz.estado(), default=str))"],
  { cwd: RAIZ, encoding: "utf-8", maxBuffer: 64 * 1024 * 1024 }
));

// --- el DOM más chico que hace falta ---------------------------------------
function armarPantalla() {
  const nodos = {
    cabecera: { textContent: "", innerHTML: "" },
    cuerpo: { textContent: "", innerHTML: "" }
  };
  const contexto = {
    window: {},
    document: { getElementById: (id) => nodos[id] },
    console: console,
    // Si el script intentara pedir datos por la red, esto lo delata: acá los
    // datos vienen incrustados y `traer()` no se tiene que llamar nunca.
    fetch: () => { throw new Error("la pantalla estática no debe hacer fetch"); },
    setInterval: () => { throw new Error("la pantalla estática no debe pollear"); }
  };
  contexto.window.CAPATAZ_DATOS = null;
  return { nodos, contexto };
}

const HTML = fs.readFileSync(path.join(RAIZ, "capataz.html"), "utf-8");
const guiones = HTML.match(/<script>([\s\S]*?)<\/script>/g) || [];
af("capataz.html trae exactamente un <script> con la pantalla",
   guiones.length === 1, String(guiones.length));
const CODIGO = guiones.join("\n").replace(/<\/?script>/g, "");
af("y el guión no está vacío", CODIGO.length > 2000, String(CODIGO.length));

function pintarCon(d) {
  const { nodos, contexto } = armarPantalla();
  contexto.window.CAPATAZ_DATOS = d;
  vm.createContext(contexto);
  vm.runInContext(CODIGO, contexto, { filename: "capataz.html" });
  return nodos;
}

console.log("\n§ 1 · La pantalla dibuja algo con los datos de verdad");
const pintado = pintarCon(datos);
af("hay al menos un proyecto vigilado que mirar",
   datos.proyectos.length >= 1, String(datos.proyectos.length));
af("el cuerpo no quedó vacío — «sin errores» no es lo mismo que «dibujó algo»",
   pintado.cuerpo.innerHTML.length > 500, String(pintado.cuerpo.innerHTML.length));
af("la cabecera dice cuántos proyectos y cuándo",
   /\d{4}-\d{2}-\d{2}/.test(pintado.cabecera.textContent) &&
   pintado.cabecera.textContent.indexOf("proyecto") >= 0,
   pintado.cabecera.textContent);
datos.proyectos.forEach(function (p) {
  af("la tarjeta de «" + p.nombre + "» está dibujada",
     pintado.cuerpo.innerHTML.indexOf(">" + p.nombre + "<") >= 0);
});

/* Los proyectos cuyo seguimiento SÍ se pudo leer. En el CI no hay ninguno de
 * los vecinos —el checkout trae capataz solo—, y una tarjeta que no encontró su
 * archivo dibuja el aviso rojo en vez de los chips. Sin este corte, este arnés
 * se pondría rojo en el CI por algo que no es un bug; con él, sigue habiendo
 * una aserción de que quedó al menos uno que mirar. */
const legibles = datos.proyectos.filter(function (p) { return p.seguimiento.existe; });
af("hay al menos un proyecto con el seguimiento legible (si no, § 2 no mira nada)",
   legibles.length >= 1, String(legibles.length));

/* Y el caso contrario, armado a mano para que se ejercite siempre: un proyecto
 * que capataz no encuentra tiene que DECIRLO, no dibujar una tarjeta vacía que
 * se lee como «no hay nada pendiente». */
const perdido = JSON.parse(JSON.stringify(datos));
perdido.proyectos = [JSON.parse(JSON.stringify(datos.proyectos[0]))];
perdido.proyectos[0].nombre = "Se mudó";
perdido.proyectos[0].seguimiento.existe = false;
perdido.proyectos[0].seguimiento.error = "no encuentro /ruta/vieja/SEGUIMIENTO.md";
const htmlPerdido = pintarCon(perdido).cuerpo.innerHTML;
af("un proyecto sin seguimiento lo dice, en rojo",
   /class="chip rojo"/.test(htmlPerdido) &&
   htmlPerdido.indexOf("no encuentro el seguimiento") >= 0, htmlPerdido.slice(0, 300));
af("y muestra la ruta que buscó, que es lo único accionable",
   htmlPerdido.indexOf("/ruta/vieja/SEGUIMIENTO.md") >= 0);
af("y NO dibuja chips de estados, que se leerían como «no falta nada»",
   htmlPerdido.indexOf("Puntos abiertos") < 0);

/* El bloque de CI de un proyecto, tal como quedó dibujado. Se corta desde el
 * <h3>CI</h3> hasta el final de sus chips: mirar el HTML entero mezclaría el
 * verde de un chip de aserciones con el del CI, que es justo lo que hay que
 * distinguir. */
function bloqueCiDe(html, nombre) {
  const i = html.indexOf(">" + nombre + "<");
  const desde = html.indexOf("<h3>CI</h3>", i);
  if (desde < 0) return "";
  const hasta = html.indexOf("</details>", desde);
  return html.slice(desde, hasta > 0 ? hasta : desde + 400);
}

console.log("§ 2 · El CI que no se pudo leer no se pinta verde");
legibles.forEach(function (p) {
  const bloque = bloqueCiDe(pintado.cuerpo.innerHTML, p.nombre);
  af("«" + p.nombre + "» dibuja un bloque de CI", bloque.length > 0);
  igual("el lector dice «no sé» para " + p.nombre, p.ci.estado, "no sé");
  af("la pantalla lo muestra como «no sé»", bloque.indexOf("no sé") >= 0, bloque);
  af("y su chip NO lleva la clase verde",
     !/class="chip[^"]*\bverde\b/.test(bloque), bloque);
  af("ni la clase roja: no saber no es haber fallado",
     !/class="chip[^"]*\brojo\b/.test(bloque), bloque);
  af("lleva la clase «nose», que es la de borde punteado",
     /class="chip[^"]*\bnose\b/.test(bloque), bloque);
  af("y trae el porqué a mano, plegado", bloque.indexOf("por qué no se sabe") >= 0);
});

console.log("§ 3 · …y con un CI verde de verdad, sí se pinta verde");
/* Sin esta sección, la § 2 pasaría igual con una pantalla que no pinta verde
 * nunca —o que no dibuja el CI—, y sería la aserción vacua de la regla 2. */
const copia = JSON.parse(JSON.stringify(datos));
copia.proyectos = [JSON.parse(JSON.stringify(legibles[0]))];
const nombre0 = copia.proyectos[0].nombre;

copia.proyectos[0].ci = { estado: "verde", motivo: "", detalle: "success" };
let b = bloqueCiDe(pintarCon(copia).cuerpo.innerHTML, nombre0);
af("un CI verde se dibuja verde", /class="chip[^"]*\bverde\b/.test(b), b);
af("y sin el «por qué no se sabe», que ahí sería el aviso que sale siempre",
   b.indexOf("por qué no se sabe") < 0, b);

copia.proyectos[0].ci = { estado: "rojo", motivo: "", detalle: "failure" };
b = bloqueCiDe(pintarCon(copia).cuerpo.innerHTML, nombre0);
af("un CI rojo se dibuja rojo", /class="chip[^"]*\brojo\b/.test(b), b);

/* «corriendo» no es ninguna de las dos. Es el caso que se cuela si alguien
 * escribe `clase = e === "rojo" ? "rojo" : "verde"`. */
copia.proyectos[0].ci = { estado: "corriendo", motivo: "", detalle: "in_progress" };
b = bloqueCiDe(pintarCon(copia).cuerpo.innerHTML, nombre0);
af("«corriendo» no se pinta verde", !/class="chip[^"]*\bverde\b/.test(b), b);
af("ni rojo", !/class="chip[^"]*\brojo\b/.test(b), b);

console.log("§ 4 · Un total que no se sabe se dibuja «no sé», no «0»");
const conRamas = JSON.parse(JSON.stringify(datos));
conRamas.proyectos = [JSON.parse(JSON.stringify(legibles[0]))];
conRamas.proyectos[0].ramas = [
  { nombre: "main", es_principal: true, punto: "", fecha: "2026-08-06",
    autor: "a", asunto: "x", commits_adelante: 0, commits_atras: 0,
    total: 100, total_main: 100, delta: 0, motivo_sin_total: "" },
  { nombre: "t9-baja", es_principal: false, punto: "T9", fecha: "2026-08-06",
    autor: "a", asunto: "x", commits_adelante: 1, commits_atras: 0,
    total: 97, total_main: 100, delta: -3, motivo_sin_total: "" },
  { nombre: "t8-sin-total", es_principal: false, punto: "T8", fecha: "2026-08-06",
    autor: "a", asunto: "x", commits_adelante: 1, commits_atras: 0,
    total: null, total_main: 100, delta: null,
    motivo_sin_total: "no dejó el total medido" }
];
const htmlRamas = pintarCon(conRamas).cuerpo.innerHTML;
const iSin = htmlRamas.indexOf("t8-sin-total");
const filaSin = htmlRamas.slice(iSin, iSin + 400);
af("la rama sin total medido dice «no sé»", filaSin.indexOf("no sé") >= 0, filaSin);
af("y no dibuja un 0, que se leería como «no hay aserciones»",
   !/<b>0<\/b>\s*aserciones/.test(filaSin), filaSin);
const iBaja = htmlRamas.indexOf("t9-baja");
const filaBaja = htmlRamas.slice(iBaja, iBaja + 400);
af("una rama que BAJA el total se marca en rojo aunque esté verde",
   /class="chip[^"]*\brojo\b/.test(filaBaja), filaBaja);
af("y dice cuánto bajó contra main", filaBaja.indexOf("-3 vs main") >= 0, filaBaja);

/* Un proyecto que no es repo git: «no sé», no «ninguna rama». Finca 360 es uno
 * de verdad, así que esto no es un caso inventado. */
conRamas.proyectos[0].ramas = null;
const sinRepo = pintarCon(conRamas).cuerpo.innerHTML;
af("un proyecto que no es repo git dice «no sé» en ramas",
   /ramas · no sé/.test(sinRepo));
af("y no dice «ninguna», que sería afirmar que no tiene",
   sinRepo.indexOf(">ninguna<") < 0);

console.log("§ 5 · Los ceros se dibujan, y el texto ajeno se escapa");
const primero = legibles[0];
const trozo = pintado.cuerpo.innerHTML;
["pendiente", "en curso", "hecho", "diferido", "descartado"].forEach(function (e) {
  af("el chip de «" + e + "» está dibujado aunque valga " +
     primero.cuenta_abiertos[e], trozo.indexOf(">" + e + "</span>") >= 0);
});
af("y los ceros se marcan con la clase «cero» en vez de esconderse",
   trozo.indexOf("chip e-") >= 0 && /class="chip [^"]*cero"/.test(trozo));

/* El seguimiento de otro proyecto es texto que capataz no controla. Si alguien
 * escribe `<img onerror=…>` en una celda, tiene que salir escapado. */
const conHtml = JSON.parse(JSON.stringify(datos));
conHtml.proyectos = [JSON.parse(JSON.stringify(legibles[0]))];
conHtml.proyectos[0].pendientes_de_pablo = [{
  id: "Z1", titulo: '<img src=x onerror="alert(1)">& "comillas"',
  dias: 3, quien: "", estado: "pendiente"
}];
const escapado = pintarCon(conHtml).cuerpo.innerHTML;
af("un título con marcado ajeno sale escapado",
   escapado.indexOf("<img src=x") < 0 && escapado.indexOf("&lt;img src=x") >= 0);
af("y los & y las comillas también",
   escapado.indexOf("&amp;") >= 0 && escapado.indexOf("&quot;") >= 0);

console.log("\nASERCIONES: " + ASER + "\nROJAS: " + ROJAS);
process.exit(ROJAS ? 1 : 0);
