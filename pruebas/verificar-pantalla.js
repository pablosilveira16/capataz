#!/usr/bin/env node
/* La pantalla, ejecutándola — y sobre todo: que «no sé» NUNCA se pinte verde.
 *
 * **Por qué existe, y por qué en node.** `pruebas/verificar-angosto.py` mira la
 * hoja de estilo y el HTML que produce `render_estatico()`, pero la tarjeta de
 * cada proyecto la dibuja el JavaScript de `capataz.html` en el navegador: el
 * archivo estático trae los datos y un `<div id="cuerpo">` vacío. O sea que la
 * regla 3 de `CLAUDE.md` —«lo que no se sabe se muestra no sé, nunca verde»—
 * estaría verificada en el lector y **no en la pantalla**, que es donde alguien
 * la lee. Entre las dos cosas hay una función y una línea que decide la clase
 * CSS. Un tablero que miente justo cuando no sabe es peor que no tenerlo, así
 * que esa línea merece que alguien la ejecute.
 *
 * Cómo: se saca el `<script>` de `capataz.html`, se lo corre en un `vm` con un
 * DOM mínimo, y se le pasan **los datos de verdad** —los que produce
 * `capataz.estado()` leyendo GitHub— capturando el HTML que escribe. No se lee
 * ni una cadena del archivo: se mira lo que dibujó.
 *
 * Las secciones que sostienen a las demás:
 *
 *   § 2  con los datos reales, el CI de cada proyecto dice «no sé» y su chip
 *        NO lleva la clase verde;
 *   § 3  **y con un CI verde de verdad, sí la lleva** — sin esto, § 2 pasaría
 *        igual con una pantalla que no pinta verde nunca, que es la definición
 *        de aserción vacua;
 *   § 4  un total de aserciones que no se sabe se dibuja «no sé» y no «0»: un
 *        cero se lee como «no hay» y esto es «no sé», que es otra cosa;
 *   § 6  prendido o caído: los tres colores de un agente, y que «dudoso» no
 *        sea ninguno de los dos.
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

// --- los datos de verdad, producidos por el mismo código que sirve la API ----
//
// No es un JSON escrito a mano: es `capataz.estado()`, leyendo los repositorios
// vigilados de GitHub. Si mañana el lector devuelve otra forma, esto se entera.
const datos = JSON.parse(execFileSync(
  "python3",
  ["-c", "import json,capataz; print(json.dumps(capataz.estado(), default=str))"],
  { cwd: RAIZ, encoding: "utf-8", maxBuffer: 64 * 1024 * 1024 }
));

// --- el DOM más chico que hace falta ---------------------------------------
// Los atributos son de verdad —`hidden` y `aria-current` son TODO el mecanismo
// de las pestañas—, así que el nodo de mentira los guarda. Con un `setAttribute`
// que no hace nada, `irA()` corre entero, no rompe, y no cambia nada: la § 10
// pasaría en verde sin que la navegación funcionara.
function nodo(attrs) {
  const a = Object.assign({}, attrs || {});
  return {
    textContent: "", innerHTML: "", className: "",
    classList: { add() {}, remove() {} },
    getAttribute: (k) => (k in a ? a[k] : null),
    setAttribute: (k, v) => { a[k] = v; },
    removeAttribute: (k) => { delete a[k]; },
    hasAttribute: (k) => k in a,
    atributos: a,
    querySelector: () => null, querySelectorAll: () => []
  };
}

function armarPantalla() {
  const nodos = {
    cabecera: nodo(), cuerpo: nodo(),
    // Los tres de la vista primaria. Sin ellos `pintarAgentes()` escribiría
    // sobre `undefined` y este arnés se caería antes de afirmar nada.
    agentes: nodo(), frescura: nodo(), pulso: nodo(),
    // Y los dos del taller, por lo mismo.
    taller: nodo(), alcance: nodo(),
    // Y los dos de la consola. Faltando, `pintarConsola()` escribe sobre
    // `undefined` y este arnés se cae con 0 aserciones — que es exactamente
    // como se descubrió que faltaban.
    consola: nodo(), "alcance-consola": nodo(),
    // El shell: los dos lugares donde se dibuja el menú.
    "nav-principal": nodo(), tabbar: nodo()
  };
  // Las cuatro vistas, con el `hidden` inicial que tiene el marcado: la primera
  // abierta y las otras tres cerradas. Si acá arrancaran todas visibles, la
  // aserción de «sólo una a la vez» no verificaría el estado inicial.
  const vistas = ["consola", "taller", "agentes", "proyectos"].map((v, i) =>
    nodo(i === 0 ? { "data-vista": v } : { "data-vista": v, hidden: "" }));
  const relojes = [];
  const contexto = {
    window: {},
    document: {
      getElementById: (id) => nodos[id],
      querySelectorAll: (sel) => (sel === ".vista" ? vistas : []),
      body: nodo()
    },
    console: console,
    // Si el script intentara pedir datos por la red, esto lo delata: acá los
    // datos vienen incrustados y `traer()` no se tiene que llamar nunca.
    fetch: () => { throw new Error("la pantalla estática no debe hacer fetch"); },
    // **Un `setInterval` local ya no es un pecado, y un `fetch` sí.** La
    // pantalla estática late para que los contadores sigan siendo ciertos
    // mientras alguien la mira —el tiempo pasa igual—, pero no tiene a quién
    // preguntarle. Lo que se afirma abajo es que late y que NO pollea.
    setInterval: (fn, ms) => { relojes.push(ms); return relojes.length; }
  };
  contexto.window.CAPATAZ_DATOS = null;
  return { nodos, contexto, relojes, vistas };
}

const HTML = fs.readFileSync(path.join(RAIZ, "capataz.html"), "utf-8");
const guiones = HTML.match(/<script>([\s\S]*?)<\/script>/g) || [];
af("capataz.html trae exactamente un <script> con la pantalla",
   guiones.length === 1, String(guiones.length));
const CODIGO = guiones.join("\n").replace(/<\/?script>/g, "");
af("y el guión no está vacío", CODIGO.length > 2000, String(CODIGO.length));

function pintarCon(d) {
  const { nodos, contexto, relojes, vistas } = armarPantalla();
  contexto.window.CAPATAZ_DATOS = d;
  vm.createContext(contexto);
  vm.runInContext(CODIGO, contexto, { filename: "capataz.html" });
  nodos.relojes = relojes;
  nodos.contexto = contexto;
  nodos.vistas = vistas;
  return nodos;
}

function copia(x) { return JSON.parse(JSON.stringify(x)); }

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
/* **Una aserción por comprobación, no una por proyecto.** El total de
 * aserciones es parte del resultado, y con un `forEach` que suma una por
 * proyecto el total dependería de cuántos repositorios haya configurados — se
 * midió: 274 en la carpeta de trabajo y 260 en un clon sin vecinos, como el del
 * CI, sin que nada hubiera cambiado. Un número que se mueve solo deja de servir
 * para comparar una rama con main. Agrupado da el mismo número de los dos
 * lados, y **el detalle dice cuáles fallaron**. */
function todos(descripcion, lista, prueba) {
  const malos = lista.filter(function (p) { return !prueba(p); })
                     .map(function (p) { return p.nombre; });
  af(descripcion + " (" + lista.length + " proyectos)", malos.length === 0,
     malos.join(", "));
}

todos("cada proyecto vigilado tiene su tarjeta dibujada", datos.proyectos,
      function (p) { return pintado.cuerpo.innerHTML.indexOf(">" + p.nombre + "<") >= 0; });

/* Los proyectos cuyo seguimiento SÍ se pudo leer. En el runner del CI no hay
 * credencial para los repositorios privados y Finca 360 no está publicado, así
 * que la lista de acá cambia según dónde se corra — y por eso todo lo de abajo
 * va agrupado. Sin este corte, este arnés se pondría rojo en el CI por algo que
 * no es un bug; con él, sigue habiendo una aserción de que quedó al menos uno
 * que mirar. */
const legibles = datos.proyectos.filter(function (p) { return p.seguimiento.existe; });
af("hay al menos un proyecto con el seguimiento legible (si no, § 2 no mira nada)",
   legibles.length >= 1, String(legibles.length));

/* Y el caso contrario, armado a mano para que se ejercite siempre: un
 * repositorio que capataz no pudo leer tiene que DECIRLO, no dibujar una
 * tarjeta vacía que se lee como «no hay nada pendiente». */
const perdido = copia(datos);
perdido.proyectos = [copia(datos.proyectos[0])];
perdido.proyectos[0].nombre = "No llegué";
perdido.proyectos[0].nube = { ok: false, error: "x", rancio: false, sin_repo: false };
perdido.proyectos[0].seguimiento.existe = false;
perdido.proyectos[0].seguimiento.error =
  "no existe github.com/pablosilveira16/fantasma, o el token no lo alcanza";
const htmlPerdido = pintarCon(perdido).cuerpo.innerHTML;
af("un repositorio que no se pudo leer lo dice, en rojo",
   /class="chip rojo"/.test(htmlPerdido) &&
   htmlPerdido.indexOf("no pude leer el repositorio") >= 0, htmlPerdido.slice(0, 300));
af("y muestra lo que buscó, que es lo único accionable",
   htmlPerdido.indexOf("github.com/pablosilveira16/fantasma") >= 0);
af("y NO dibuja chips de estados, que se leerían como «no falta nada»",
   htmlPerdido.indexOf("Puntos abiertos") < 0);

/* Un proyecto declarado SIN repositorio —Finca 360, que todavía no está
 * publicado— no es lo mismo que uno que falló. No se pinta rojo: pintar de rojo
 * algo que está así a propósito es el aviso que sale siempre, y el corolario de
 * la regla 3 dice que eso enseña a ignorar los avisos. */
const sinRepo = copia(datos);
sinRepo.proyectos = [copia(datos.proyectos[0])];
sinRepo.proyectos[0].nombre = "Sin publicar";
sinRepo.proyectos[0].repo = "";
sinRepo.proyectos[0].nube = { ok: false, error: "todavía no está en GitHub",
                              rancio: false, sin_repo: true };
const htmlSinRepo = pintarCon(sinRepo).cuerpo.innerHTML;
af("un proyecto sin repositorio dice «no sé», no un error",
   htmlSinRepo.indexOf("sin publicar") >= 0 &&
   htmlSinRepo.indexOf("no sé") >= 0, htmlSinRepo.slice(0, 300));
af("y NO se pinta rojo: está así a propósito",
   !/class="chip rojo"/.test(htmlSinRepo));
af("ni verde, que sería decir que está todo bien",
   !/class="chip[^"]*\bverde\b/.test(htmlSinRepo));
af("con el motivo declarado en proyectos.json a la vista",
   htmlSinRepo.indexOf("todavía no está en GitHub") >= 0);

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
const ci = function (p) { return bloqueCiDe(pintado.cuerpo.innerHTML, p.nombre); };
todos("cada proyecto legible dibuja su bloque de CI", legibles,
      function (p) { return ci(p).length > 0; });
todos("el lector dice «no sé» para todos —la lectura del CI está apagada—", legibles,
      function (p) { return p.ci.estado === "no sé"; });
todos("y la pantalla lo muestra como «no sé»", legibles,
      function (p) { return ci(p).indexOf("no sé") >= 0; });
todos("y NINGÚN chip de CI lleva la clase verde", legibles,
      function (p) { return !/class="chip[^"]*\bverde\b/.test(ci(p)); });
todos("ni la clase roja: no saber no es haber fallado", legibles,
      function (p) { return !/class="chip[^"]*\brojo\b/.test(ci(p)); });
todos("lleva la clase «nose», que es la de borde punteado", legibles,
      function (p) { return /class="chip[^"]*\bnose\b/.test(ci(p)); });
todos("y trae el porqué a mano, plegado", legibles,
      function (p) { return ci(p).indexOf("por qué no se sabe") >= 0; });

console.log("§ 3 · …y con un CI verde de verdad, sí se pinta verde");
/* Sin esta sección, la § 2 pasaría igual con una pantalla que no pinta verde
 * nunca —o que no dibuja el CI—, y sería la aserción vacua de la regla 2. */
const conCi = copia(datos);
conCi.proyectos = [copia(legibles[0])];
const nombre0 = conCi.proyectos[0].nombre;

conCi.proyectos[0].ci = { estado: "verde", motivo: "", detalle: "success" };
let b = bloqueCiDe(pintarCon(conCi).cuerpo.innerHTML, nombre0);
af("un CI verde se dibuja verde", /class="chip[^"]*\bverde\b/.test(b), b);
af("y sin el «por qué no se sabe», que ahí sería el aviso que sale siempre",
   b.indexOf("por qué no se sabe") < 0, b);

conCi.proyectos[0].ci = { estado: "rojo", motivo: "", detalle: "failure" };
b = bloqueCiDe(pintarCon(conCi).cuerpo.innerHTML, nombre0);
af("un CI rojo se dibuja rojo", /class="chip[^"]*\brojo\b/.test(b), b);

/* «corriendo» no es ninguna de las dos. Es el caso que se cuela si alguien
 * escribe `clase = e === "rojo" ? "rojo" : "verde"`. */
conCi.proyectos[0].ci = { estado: "corriendo", motivo: "", detalle: "in_progress" };
b = bloqueCiDe(pintarCon(conCi).cuerpo.innerHTML, nombre0);
af("«corriendo» no se pinta verde", !/class="chip[^"]*\bverde\b/.test(b), b);
af("ni rojo", !/class="chip[^"]*\brojo\b/.test(b), b);

console.log("§ 4 · Un total que no se sabe se dibuja «no sé», no «0»");
function ramaFalsa(extra) {
  return Object.assign({
    nombre: "x", es_principal: false, punto: "", sha: "abc1234",
    ts: 1785989327, hace_seg: 600, autor: "coder-1", asunto: "algo",
    commits_adelante: 1, commits_atras: 0, total: 100, total_main: 100,
    delta: 0, motivo_sin_total: "", estado: "trabajando"
  }, extra);
}
const conRamas = copia(datos);
conRamas.proyectos = [copia(legibles[0])];
conRamas.proyectos[0].ramas = [
  ramaFalsa({ nombre: "main", es_principal: true, estado: "principal",
              commits_adelante: 0 }),
  ramaFalsa({ nombre: "t9-baja", punto: "T9", total: 97, delta: -3 }),
  ramaFalsa({ nombre: "t8-sin-total", punto: "T8", total: null, delta: null,
              motivo_sin_total: "no dejó el total medido" })
];
const htmlRamas = pintarCon(conRamas).cuerpo.innerHTML;
const iSin = htmlRamas.indexOf("t8-sin-total");
const filaSin = htmlRamas.slice(iSin, iSin + 400);
af("la rama sin total medido dice «no sé»", filaSin.indexOf("no sé") >= 0, filaSin);
af("y no dibuja un 0, que se leería como «no hay aserciones»",
   !/<b>0<\/b>\s*aserciones/.test(filaSin), filaSin);
const iBaja = htmlRamas.indexOf("t9-baja");
const filaBaja = htmlRamas.slice(iBaja, iBaja + 500);
af("una rama que BAJA el total se marca en rojo aunque esté verde",
   /class="chip[^"]*\brojo\b/.test(filaBaja), filaBaja);
af("y dice cuánto bajó contra main", filaBaja.indexOf("-3 vs main") >= 0, filaBaja);

/* Un repositorio que no se pudo leer: «no sé», no «ninguna rama». */
conRamas.proyectos[0].ramas = null;
const sinRamas = pintarCon(conRamas).cuerpo.innerHTML;
af("un repositorio que no se leyó dice «no sé» en ramas",
   /ramas · no sé/.test(sinRamas));
af("y no dice «ninguna», que sería afirmar que no tiene",
   sinRamas.indexOf(">ninguna<") < 0);
/* Y lo mismo con la cuadrilla, que es el dato nuevo de esta tanda: sin poder
 * leer el repositorio, «nadie trabajando» se lee igual que «todo tranquilo» y
 * es exactamente lo contrario de lo que puede estar pasando. */
af("y en la cuadrilla dice «quién trabaja · no sé», no «nadie trabajando»",
   sinRamas.indexOf("quién trabaja · no sé") >= 0 &&
   sinRamas.indexOf("nadie trabajando") < 0, sinRamas.slice(0, 200));

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
const conHtml = copia(datos);
conHtml.proyectos = [copia(legibles[0])];
conHtml.proyectos[0].pendientes_de_pablo = [{
  id: "Z1", titulo: '<img src=x onerror="alert(1)">& "comillas"',
  dias: 3, quien: "", estado: "pendiente"
}];
const escapado = pintarCon(conHtml).cuerpo.innerHTML;
af("un título con marcado ajeno sale escapado",
   escapado.indexOf("<img src=x") < 0 && escapado.indexOf("&lt;img src=x") >= 0);
af("y los & y las comillas también",
   escapado.indexOf("&amp;") >= 0 && escapado.indexOf("&quot;") >= 0);

console.log("§ 6 · Prendido o caído — los tres colores de un agente");
/* Es el punto entero de la tanda: «al observar variaciones en vivo va a poder
 * ver los agentes que se prenden y apagan». Los tres estados tienen que
 * distinguirse **en la pantalla** y no sólo en el JSON, y el del medio —el que
 * capataz no sabe— no puede caer en ninguno de los otros dos. */
const conAgentes = copia(datos);
conAgentes.proyectos = [copia(legibles[0])];
conAgentes.proyectos[0].ramas = [
  ramaFalsa({ nombre: "main", es_principal: true, estado: "principal",
              commits_adelante: 0 }),
  ramaFalsa({ nombre: "t1-viva", estado: "trabajando", hace_seg: 600,
              autor: "coder-1" }),
  ramaFalsa({ nombre: "t2-dudosa", estado: "dudoso", hace_seg: 7200,
              autor: "coder-2" }),
  ramaFalsa({ nombre: "t3-caida", estado: "caído", hace_seg: 108000,
              autor: "coder-3" }),
  ramaFalsa({ nombre: "t4-lista", estado: "integrada", commits_adelante: 0,
              autor: "escriba-1" })
];
conAgentes.proyectos[0].cuadrilla = [
  { quien: "coder-3", rol: "coder", que: "t3-caida", punto: "T3",
    asunto: "algo", estado: "caído", desde: 1, hace_seg: 108000 },
  { quien: "coder-2", rol: "coder", que: "t2-dudosa", punto: "T2",
    asunto: "algo", estado: "dudoso", desde: 1, hace_seg: 7200 },
  { quien: "coder-1", rol: "coder", que: "t1-viva", punto: "T1",
    asunto: "algo", estado: "trabajando", desde: 1, hace_seg: 600 },
  { quien: "reviewer-1", rol: "reviewer", que: "T7", punto: "T7",
    asunto: "un punto tomado", estado: "sin rama", desde: null, hace_seg: null }
];
const htmlAg = pintarCon(conAgentes).cuerpo.innerHTML;
/* La fila de esa clave, **cortada en su propio `</li>`**. Con una ventana de
 * N caracteres se colaba el chip del agente siguiente: la aserción de que
 * «dudoso» no lleva la clase de «trabajando» se ponía roja porque la clase
 * estaba en la fila de al lado. Primera hipótesis, el arnés — y era. */
function filaDe(html, clave) {
  const i = html.indexOf(clave);
  if (i < 0) return "";
  const fin = html.indexOf("</li>", i);
  return html.slice(i, fin < 0 ? i + 420 : fin);
}
af("un agente que se movió recién se dibuja como «trabajando», en verde",
   /class="chip r-trabajando"/.test(filaDe(htmlAg, "t1-viva")) &&
   filaDe(htmlAg, "t1-viva").indexOf("trabajando") >= 0,
   filaDe(htmlAg, "t1-viva"));
af("uno que no se mueve hace 30 horas se dibuja «caído», en rojo",
   /class="chip r-caido"/.test(filaDe(htmlAg, "t3-caida")),
   filaDe(htmlAg, "t3-caida"));
af("y el del medio se dibuja «dudoso», que NO es ni el verde ni el rojo",
   /class="chip r-dudoso"/.test(filaDe(htmlAg, "t2-dudosa")) &&
   !/class="chip r-trabajando"/.test(filaDe(htmlAg, "t2-dudosa")) &&
   !/class="chip r-caido"/.test(filaDe(htmlAg, "t2-dudosa")),
   filaDe(htmlAg, "t2-dudosa"));
af("una rama integrada no se dibuja como un agente caído",
   /class="chip r-integrada"/.test(filaDe(htmlAg, "t4-lista")),
   filaDe(htmlAg, "t4-lista"));
af("un punto en curso sin rama se ve como «sin rama», no como caído",
   htmlAg.indexOf("sin rama") >= 0 &&
   /class="chip r-sinrama"/.test(filaDe(htmlAg, "reviewer-1")),
   filaDe(htmlAg, "reviewer-1"));
af("la cuadrilla dice hace cuánto se movió cada uno, en la unidad que se lee",
   htmlAg.indexOf("hace 10 min") >= 0 && htmlAg.indexOf("hace 30 h") >= 0,
   htmlAg.slice(htmlAg.indexOf("La cuadrilla"), htmlAg.indexOf("La cuadrilla") + 600));
af("y el reparto por rol sigue con los ceros",
   /class="chip [^"]*cero"/.test(htmlAg));

/* Sin ninguna rama viva, se dice que no hay nadie **y sobre qué se miró**: no
 * es lo mismo que no haber podido mirar, y las dos frases tienen que ser
 * distintas. */
conAgentes.proyectos[0].cuadrilla = [];
conAgentes.proyectos[0].ramas = [
  ramaFalsa({ nombre: "main", es_principal: true, estado: "principal",
              commits_adelante: 0 })
];
const htmlVacio = pintarCon(conAgentes).cuerpo.innerHTML;
af("sin nadie trabajando se dice, y se dice sobre qué se miró",
   htmlVacio.indexOf("nadie trabajando") >= 0 &&
   htmlVacio.indexOf("sin integrar") >= 0, htmlVacio.slice(0, 200));
af("y eso NO es «no sé»", htmlVacio.indexOf("quién trabaja · no sé") < 0);

console.log("§ 7 · El visor por agente, y el demonio de un segundo");
/* La vista primaria: quién trabaja ahora, de todos los proyectos juntos. Y el
 * demonio que la mantiene viva sin mentir sobre la frescura de lo que muestra. */
const conAg = copia(datos);
conAg.agentes = [
  { quien: "coder-1", rol: "coder", proyecto: "Uno", que: "t1-una",
    punto: "T1", asunto: "empujó algo", estado: "trabajando", desde: 1,
    hace_seg: 60, sha: "aaa1111" },
  { quien: "coder-2", rol: "coder", proyecto: "Dos", que: "t2-otra",
    punto: "T2", asunto: "hace rato", estado: "caído", desde: 1,
    hace_seg: 90000, sha: "bbb2222" }
];
const p7 = pintarCon(conAg);
const hAg = p7.agentes.innerHTML;
af("la vista primaria dibuja a cada agente con su nombre",
   hAg.indexOf("coder-1") >= 0 && hAg.indexOf("coder-2") >= 0, hAg.slice(0, 200));
af("y de qué proyecto es cada uno: sin eso no se sabe a quién ir a buscar",
   hAg.indexOf("Uno") >= 0 && hAg.indexOf("Dos") >= 0);
af("junta agentes de proyectos distintos, que es lo que la hace primaria",
   hAg.indexOf("t1-una") >= 0 && hAg.indexOf("t2-otra") >= 0);
af("el que se cayó se pinta con su color y NO de verde",
   /a-caido/.test(hAg) && !/chip-estado verde/.test(hAg), hAg.slice(0, 300));
af("y el que trabaja, con el suyo", /a-trabajando/.test(hAg));

/* El demonio. Lo que se afirma no es que exista un `setInterval` —eso es una
 * cadena— sino con qué ritmos quedó armado y que la instantánea no pollee. */
af("la pantalla late una vez por segundo: los contadores siguen siendo ciertos " +
   "mientras alguien la mira", p7.relojes.indexOf(1000) >= 0,
   JSON.stringify(p7.relojes));
af("y la instantánea NO pollea: no hay a quién preguntarle",
   p7.relojes.filter(function (m) { return m !== 1000; }).length === 0,
   JSON.stringify(p7.relojes));

/* Los umbrales los manda el servidor y la pantalla los vuelve a aplicar a cada
 * segundo. Los dos lados de cada uno, que es donde se esconde un `<` de más. */
const ctx = p7.contexto;
af("un segundo antes de FRESCO la pantalla dice «trabajando»",
   ctx.estadoVivo(conAg.umbrales.fresco - 1, "caído") === "trabajando");
af("un segundo después, «dudoso» — sin esperar ninguna lectura nueva",
   ctx.estadoVivo(conAg.umbrales.fresco + 1, "trabajando") === "dudoso");
af("un segundo antes de TIBIO todavía es «dudoso»",
   ctx.estadoVivo(conAg.umbrales.tibio - 1, "trabajando") === "dudoso");
af("un segundo después ya es «caído»",
   ctx.estadoVivo(conAg.umbrales.tibio + 1, "trabajando") === "caído");
af("y el que no tiene rama sigue sin tenerla: el reloj no lo convierte en nada",
   ctx.estadoVivo(null, "sin rama") === "sin rama");
/* Una instantánea vieja no trae umbrales. No se inventan: queda lo que dijo el
 * servidor, que es la regla 3 aplicada a la pantalla misma. */
const sinUmbrales = copia(conAg);
delete sinUmbrales.umbrales;
af("sin umbrales en el JSON no se inventa ninguno",
   pintarCon(sinUmbrales).contexto.estadoVivo(10, "dudoso") === "dudoso");

/* «Se despertó» tiene que ser un empujón y no un reloj: si se marcara por
 * tiempo, avisaría solo y el aviso dejaría de querer decir nada. */
function relectura(ctxt, agentes) {
  const d = copia(conAg);
  d.agentes = agentes;
  ctxt.FIRMA = "";
  ctxt.pintar(d);
  return ctxt.document.getElementById("agentes").innerHTML;
}
ctx.VISTOS = null;
ctx.DESPIERTOS = {};
af("la primera lectura no marca a nadie como recién despierto: si no, cada vez " +
   "que se abre la pantalla parecería que empujaron todos",
   !/desperto/.test(relectura(ctx, conAg.agentes)));
af("dos lecturas con el mismo sha tampoco: no pasó nada",
   !/desperto/.test(relectura(ctx, conAg.agentes)));
const movido = copia(conAg.agentes);
movido[0].sha = "ccc3333";
movido[0].hace_seg = 2;
af("y un sha nuevo sí: eso es un empujón",
   /desperto/.test(relectura(ctx, movido)));

/* La frescura. Es el dato que dice si creerle al resto de la pantalla. */
ctx.ESTATICA = false;
ctx.ULTIMO_OK = Date.now();
const sinMarca = copia(conAg);
sinMarca.proyectos.forEach(function (p) {
  if (p.nube) { p.nube.traido_en = null; p.nube.sin_repo = false; }
});
ctx.pintar(sinMarca);
ctx.pintarFrescura();
af("sin la marca de cuándo se trajo, la frescura dice «no sé» y no «hace 0 s»",
   p7.frescura.textContent.indexOf("no sé") >= 0, p7.frescura.textContent);
ctx.ULTIMO_OK = Date.now() - 30000;
ctx.pintarFrescura();
af("y si el servidor deja de contestar, la pantalla lo dice en vez de seguir " +
   "mostrando lo viejo como si fuera de ahora",
   p7.frescura.textContent.indexOf("sin contacto") >= 0, p7.frescura.textContent);
af("con hace cuánto que no sabe nada, que es lo accionable",
   /\d+ s/.test(p7.frescura.textContent), p7.frescura.textContent);

/* -------------------------------------------------------------------------
   § 8 · El taller — y que su alcance se vea

   La sección nueva muestra los agentes de ESTA máquina. Dos cosas tienen que
   ser ciertas en la pantalla y no sólo en el lector: que `sin señal` no se
   pinte como un desenlace —terminado y colgado no se distinguen— y que el
   alcance esté a la vista, porque tres agentes locales mostrados como si
   fueran la flota son el tablero que miente.
------------------------------------------------------------------------- */
console.log("\n§ 8 · El taller");

const p8 = pintarCon(datos);
af("el alcance está escrito, no es una nota al pie",
   p8.alcance.textContent.indexOf("esta máquina") >= 0, p8.alcance.textContent);
af("con los datos de verdad, el taller dibuja algo",
   p8.taller.innerHTML.length > 50, String(p8.taller.innerHTML.length));

/* Un taller a mano con los cinco desenlaces, para que ninguno quede sin pintar
   por lo que haya corriendo en la máquina en este momento. */
function conTaller(sesiones, ok, error) {
  const d = copia(datos);
  d.taller = { ok: ok === undefined ? true : ok, error: error || "",
               raiz: "/x/.claude", alcance: "esta máquina · ahora",
               leido_en: d.ahora, sesiones: sesiones,
               cuenta: { sesiones: sesiones.length, vivas: 1, agentes: 0,
                         trabajando: 0 }, sueltas: 0 };
  return d;
}

function agente(id, estado, quieto, hijos) {
  return { id: id, tipo: "general-purpose", descripcion: "el " + id,
           profundidad: hijos ? 1 : 2, padre: null, modelo: null,
           worktree: null, arrancado: 1, ultimo: 1, quieto_hace: quieto,
           estado: estado, motivo_estado: estado === "sin señal"
             ? "terminado y colgado no se distinguen desde acá" : "",
           hijos: hijos || [] };
}

const sesion = {
  pid: 1, viva: true, sesion: "s-1", nombre: "una-sesion", cwd: "/x/proy",
  arrancada: 1, version: "2.1.221", entrada: "claude-desktop", error: "",
  proyecto: "Capataz", motivo_sin_agentes: "",
  agentes: [agente("padre", "trabajando", 3, [agente("hijo", "dudoso", 600)]),
            agente("mudo", "sin señal", 9000),
            agente("ido", "cerrado", 50)]
};
const p8b = pintarCon(conTaller([sesion]));
const htmlT = p8b.taller.innerHTML;

af("«sin señal» se pinta con la pinta de «no sé» y NUNCA verde",
   /r-sinsenal/.test(htmlT) && !/r-sinsenal[^"]*verde/.test(htmlT), htmlT.slice(0, 120));
af("y dice por qué: que terminado y colgado no se distinguen",
   htmlT.indexOf("no se distinguen") >= 0);
af("«cerrado» tampoco es verde: el proceso no está, no es un logro",
   /r-cerrado/.test(htmlT));
/* La anti-vacua de las tres de arriba: sin esto pasarían igual con una
   pantalla que no pinta de color nunca. */
af("y un agente trabajando SÍ lleva la clase de trabajando",
   /r-trabajando/.test(htmlT));
af("el subagente anidado se dibuja adentro del padre",
   htmlT.indexOf("el hijo") > htmlT.indexOf("el padre"));
af("la sesión dice de qué proyecto es la carpeta", htmlT.indexOf("Capataz") >= 0);

/* Los umbrales llegan del servidor. Sin ellos no se inventa ninguno. */
const ctxT = p8b.contexto;
af("con los umbrales del servidor, el estado se recalcula con el reloj",
   ctxT.estadoTaller(1, "sin señal") === "trabajando" &&
   ctxT.estadoTaller(999999, "trabajando") === "sin señal");
af("pero «cerrado» no se recalcula: es un hecho medido, no un rato",
   ctxT.estadoTaller(1, "cerrado") === "cerrado");
af("ni «no sé»: es la ausencia de transcripción",
   ctxT.estadoTaller(1, "no sé") === "no sé");

/* No pude mirar ≠ no hay nadie. Es la distinción que un tablero suele borrar. */
const p8c = pintarCon(conTaller([], false, "no encontré /x/.claude · CAPATAZ_TALLER"));
af("si el taller no se pudo leer, se dice y se nombra lo que buscó",
   p8c.taller.innerHTML.indexOf("/x/.claude") >= 0, p8c.taller.innerHTML.slice(0, 120));
const p8d = pintarCon(conTaller([]));
af("y cero sesiones es otra cosa: se dice que no hay ninguna abierta",
   p8d.taller.innerHTML.indexOf("ninguna sesión") >= 0,
   p8d.taller.innerHTML.slice(0, 120));
af("y avisa que los de otra máquina no se ven acá",
   p8d.taller.innerHTML.indexOf("otra máquina") >= 0);

/* -------------------------------------------------------------------------
   § 9 · La consola — los agentes background, dibujados

   Es la tercera fuente y la única que sale de correr un programa. Tres cosas
   tienen que ser ciertas **en la pantalla** y no sólo en el lector:

     · `esperando` salta —es lo único que pide que alguien haga algo— y `no sé`
       no se pinta de ningún color, que es la regla 3;
     · no haber podido preguntar no se dibuja como «ningún agente»;
     · **el desacuerdo entre las dos fuentes sólo aparece cuando lo hay.** Un
       aviso que sale siempre enseña a ignorarse (corolario de la regla 3), así
       que hay una aserción de cada lado: que sale, y que no sale.
------------------------------------------------------------------------- */
console.log("\n§ 9 · La consola");

function conConsola(background, extra) {
  const d = copia(datos);
  d.consola = Object.assign({
    ok: true, error: "", alcance: "esta máquina · ahora. Son los agentes background",
    comando: "claude agents --json --all", preguntado_en: d.ahora,
    background: background, interactivas: [], desacuerdos: [],
    cuenta: { background: background.length, trabajando: 0, esperando: 0,
              terminados: 0, interactivas: 0 }
  }, extra || {});
  return d;
}

function bg(id, estado, motivo) {
  return { id: id, sesion: "s-" + id, pid: 10, nombre: "el " + id,
           cwd: "/x/proy", clase: "background", state: "x", status: "y",
           arrancada: 1, hace: 120, estado: estado, motivo_estado: motivo || "" };
}

const p9 = pintarCon(conConsola([
  bg("b1", "esperando", "trabado: necesita a una persona"),
  bg("b2", "trabajando"), bg("b3", "falló"), bg("b4", "terminado"),
  bg("b5", "no sé", "el CLI dice `state: 'hibernating'`")]));
const htmlC = p9.consola.innerHTML;

af("el alcance de la consola está escrito y dice que es esta máquina",
   p9["alcance-consola"].textContent.indexOf("esta máquina") >= 0,
   p9["alcance-consola"].textContent);
af("«esperando» se pinta ámbar: no está roto, está trabado esperando a alguien",
   /c-esperando/.test(htmlC));
af("y dice cómo se destraba", htmlC.indexOf("necesita a una persona") >= 0);
af("«no sé» no se pinta de ningún color, y lleva la palabra cruda del CLI",
   /nose/.test(htmlC) && htmlC.indexOf("hibernating") >= 0);
af("«falló» sí es rojo: eso sí es un incendio", /c-fallo/.test(htmlC));
af("«terminado» va apagado: es un hecho sabido, no un logro", /c-quieto/.test(htmlC));
/* La anti-vacua de las cuatro de arriba: sin esto pasarían con una pantalla
   que no pinta de verde nunca. */
af("y «trabajando» SÍ lleva la clase de trabajando", /c-trabajando/.test(htmlC));
af("el asa para abrirlo se muestra, y es un texto: capataz no lo corre",
   htmlC.indexOf("claude attach b1") >= 0);
af("el que espera a una persona va primero, antes que el que trabaja",
   htmlC.indexOf("el b1") < htmlC.indexOf("el b2"));

/* El estado de un background NO se recalcula con el reloj, al revés que el de
   una rama y el de un subagente. Aquéllos son «hace cuánto que no se mueve»;
   éste es un hecho que el CLI afirma. Recalcularlo sería inventarlo. */
const viejo = bg("b9", "trabajando");
viejo.hace = 999999;
af("un background que arrancó hace un siglo sigue diciendo lo que dice el CLI",
   /c-trabajando/.test(pintarCon(conConsola([viejo])).consola.innerHTML));

/* No pude preguntar ≠ no hay ninguno. */
const p9b = pintarCon(conConsola([], {
  ok: false, error: "no pude correr «claude agents --json --all»: no such file" }));
af("si la consola no se pudo leer, se dice y se nombra el comando que corrió",
   p9b.consola.innerHTML.indexOf("claude agents --json --all") >= 0,
   p9b.consola.innerHTML.slice(0, 140));
af("y se aclara que el resto del tablero no depende de esto",
   p9b.consola.innerHTML.indexOf("no depende") >= 0);
const p9c = pintarCon(conConsola([]));
af("y cero background es otra cosa: se dice que no hay ninguno",
   p9c.consola.innerHTML.indexOf("ningún agente background") >= 0,
   p9c.consola.innerHTML.slice(0, 140));

/* Los dos lados del aviso que no puede salir siempre. */
af("sin desacuerdos, la pantalla no dibuja ninguno",
   p9c.consola.innerHTML.indexOf("no dicen lo mismo") < 0);
const p9d = pintarCon(conConsola([], { desacuerdos: [{
  sesion: "s-7", que: "la carpeta no coincide",
  consola: "/uno", taller: "/otro" }] }));
af("con uno, se muestra y se ven **las dos** versiones",
   p9d.consola.innerHTML.indexOf("/uno") >= 0 &&
   p9d.consola.innerHTML.indexOf("/otro") >= 0);
af("y se dice que capataz no eligió ganador",
   p9d.consola.innerHTML.indexOf("no elige un ganador") >= 0 ||
   p9d.consola.innerHTML.indexOf("no elige") >= 0);

/* -------------------------------------------------------------------------
   § 10 · El menú — y que una pestaña no esconda nada

   El pedido fue «una app con menús, y el primer dashboard el de los agentes de
   la consola». Lo que hay que verificar no es que el menú se dibuje: es que
   **navegar no haga a capataz menos honesto**. Apiladas, las cuatro secciones
   se veían al pasar; detrás de un menú, un «no pude leer» que nadie abre es un
   error que no existe.

   Por eso las dos mitades: la marca **sale** cuando hay algo, y **no sale**
   cuando no lo hay. Sin la segunda, prender las cuatro pestañas siempre pasaría
   este arnés y sería el aviso que enseña a ignorarse.
------------------------------------------------------------------------- */
console.log("\n§ 10 · El menú");

function igualdad(descripcion, obtenido, esperado) {
  af(descripcion, JSON.stringify(obtenido) === JSON.stringify(esperado),
     "obtuve " + JSON.stringify(obtenido) + ", esperaba " + JSON.stringify(esperado));
}

const p10 = pintarCon(datos);
const ctx10 = p10.contexto;

af("arranca en la consola, que es lo que se pidió", ctx10.VISTA === "consola");
igualdad("y esa es la única vista abierta",
  p10.vistas.filter((v) => !v.hasAttribute("hidden")).map(
    (v) => v.getAttribute("data-vista")), ["consola"]);
af("el menú se dibuja en los dos lugares: lateral y tabbar",
   p10["nav-principal"].innerHTML.indexOf("Consola") >= 0 &&
   p10.tabbar.innerHTML.indexOf("Proyectos") >= 0);
af("y las cuatro vistas están en el menú",
   ["Consola", "Taller", "Agentes", "Proyectos"].every(
     (r) => p10.tabbar.innerHTML.indexOf(r) >= 0));
af("la pestaña abierta se marca como tal, para que se sepa dónde uno está",
   /aria-current="page"/.test(p10.tabbar.innerHTML));

ctx10.irA("proyectos");
igualdad("al navegar, la abierta es la nueva y ninguna otra",
  p10.vistas.filter((v) => !v.hasAttribute("hidden")).map(
    (v) => v.getAttribute("data-vista")), ["proyectos"]);
af("y el contenido de la vista de antes NO se borra: no se vuelve a pedir nada",
   p10.consola.innerHTML.length > 50,
   String(p10.consola.innerHTML.length));
ctx10.irA("consola");
igualdad("y se puede volver", p10.vistas.filter(
  (v) => !v.hasAttribute("hidden")).map((v) => v.getAttribute("data-vista")),
  ["consola"]);

/* La frescura y el pulso viven en la barra, no adentro de una vista: si
   estuvieran en una, las otras tres mostrarían datos sin decir de cuándo son. */
af("la frescura se escribe en el shell y no en una pestaña",
   p10.frescura.textContent.length > 5, p10.frescura.textContent);
af("y sigue escrita después de navegar a otra vista",
   (ctx10.irA("taller"), ctx10.pintarFrescura(),
    p10.frescura.textContent.length > 5), p10.frescura.textContent);

/* --- La marca: los dos lados ------------------------------------------ */
function conTodoSano() {
  const d = conConsola([bg("ok1", "trabajando")]);
  d.taller = { ok: true, error: "", raiz: "/x", alcance: "esta máquina · ahora",
               leido_en: d.ahora, sesiones: [], cuenta: {}, sueltas: 0 };
  d.agentes = (d.agentes || []).map((a) => Object.assign({}, a,
    { estado: "trabajando" }));
  d.proyectos = d.proyectos.map((p) => Object.assign({}, p,
    { seguimiento: Object.assign({}, p.seguimiento, { existe: true, error: "" }) }));
  return d;
}
const sano = pintarCon(conTodoSano());
af("con todo sano, NINGUNA pestaña se marca — si no, el aviso sale siempre",
   sano.tabbar.innerHTML.indexOf("marca-vista") < 0,
   sano.tabbar.innerHTML.slice(0, 200));
/* La anti-vacua de la de arriba, y la razón de ser de toda la sección. */
const rota = pintarCon(conConsola([], {
  ok: false, error: "no pude correr «claude agents --json --all»" }));
af("una consola que no se pudo leer marca su pestaña **estando escondida**",
   (rota.contexto.irA("proyectos"),
    rota.tabbar.innerHTML.indexOf("marca-vista") >= 0),
   rota.tabbar.innerHTML.slice(0, 240));
af("un background esperando a una persona también marca",
   pintarCon(conConsola([bg("b1", "esperando")])).tabbar
     .innerHTML.indexOf("marca-vista") >= 0);
af("pero uno terminado no: es un hecho, no un pendiente",
   pintarCon(conConsola([bg("b1", "terminado")])).tabbar
     .innerHTML.indexOf("marca-vista") < 0);

/* Y los tres estados que NO pueden marcar, porque salen en todas las corridas.
   Medido el 2026-08-15 contra los datos de verdad: los cuatro agentes del
   tablero están «caído» y los tres proyectos tienen filas «sin estado». */
const conCaidos = conTodoSano();
conCaidos.agentes = [{ quien: "x", proyecto: "P", que: "r", estado: "caído",
                       punto: "", asunto: "", sha: "a" }];
af("«caído» NO marca la pestaña de agentes: es el estado más común del tablero",
   pintarCon(conCaidos).tabbar.innerHTML.indexOf("marca-vista") < 0);
const conSinRama = conTodoSano();
conSinRama.agentes = [{ quien: "x", proyecto: "P", que: "r", estado: "sin rama",
                        punto: "T1", asunto: "", sha: "" }];
af("«sin rama» sí marca: es un `en curso` del que no llegó ni un commit",
   pintarCon(conSinRama).tabbar.innerHTML.indexOf("marca-vista") >= 0);

console.log("\nASERCIONES: " + ASER + "\nROJAS: " + ROJAS);
process.exit(ROJAS ? 1 : 0);
