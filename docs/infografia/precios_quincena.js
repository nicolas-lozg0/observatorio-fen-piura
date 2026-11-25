/* Infografía: precios de alimentos en los mercados de Piura, la última quincena frente a lo habitual.
   Es el gráfico que estaba en la pestaña Precios hasta el 25/11/2026, con sus mismas reglas, separado para la infografía de
   Germán Vega. Lee los mismos datos que la página (../data/sisap_historial.json y ../data/precios_sisap.json) y calcula aquí
   la comparación, así que sigue sirviendo con datos nuevos. Cálculo: el mismo de scripts/precios_sisap.py (función calcular);
   scripts/test_pagina.py comprueba que con los valores por defecto dé exactamente las cifras de precios_sisap.json.
   Parámetros en la URL (todos opcionales): corte=aaaa-mm-dd, desde=aaaa, hasta=aaaa (años de referencia), mercado,
   comparar (habitual, un año o vacío), orden (var o dif). */
"use strict";
const $ = id => document.getElementById(id);
const COLOR = { sube: "#c2410c", baja: "#2563a8", texto: "#14202e", texto2: "#3e4751", texto3: "#56616e", linea: "#dbe2eb" };
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre"];
const MES_CORTO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];
const MINIMO_FECHAS = 2, MINIMO_HIST = 3, UMBRAL_HABITUAL = 5;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const num = (x, d = 0) => Number(x).toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" });
const signo = v => v == null ? "sin dato" : `${v >= 0.05 ? "+" : v <= -0.05 ? "−" : ""}${num(Math.abs(v), 1)} %`;
const yLista = xs => xs.join(", ").replace(/, ([^,]*)$/, " y $1");
// como round() de Python: el valor decimal exacto y, en un empate exacto (−6,25), al par (−6,2); toFixed lo alejaría del cero
// (el empate se mira en la expansión decimal exacta del número binario: 8,215 se guarda como 8,2149999… y no es empate)
function redondear(v, d) {
  const s = Math.abs(v).toFixed(60), i = s.indexOf(".") + 1 + d;
  if (s[i] !== "5" || !/^0*$/.test(s.slice(i + 1))) return +v.toFixed(d);
  const k = 10 ** d, f = Math.floor(Math.abs(v) * k), r = (f % 2 === 0 ? f : f + 1) / k;
  return v < 0 ? -r : r;
}
const r1 = v => redondear(v, 1), r2 = v => redondear(v, 2);
const fechaTxt = f => `${+f.slice(8)} de ${MESES[+f.slice(5, 7) - 1]} de ${f.slice(0, 4)}`;

// ---------- Cálculo (copia de scripts/precios_sisap.py) ----------
const iso = (a, m, d) => `${a}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
const mesAnterior = (a, m) => m === 1 ? [a - 1, 12] : [a, m - 1];
const ultimoDia = (a, m) => new Date(a, m, 0).getDate();
function ventanas(corte, fechas) {
  let [a, m, fin] = [+corte.slice(0, 4), +corte.slice(5, 7), +corte.slice(8)];
  if (fechas.filter(f => +f.slice(0, 4) === a && +f.slice(5, 7) === m && +f.slice(8) <= fin).length < 2) { [a, m] = mesAnterior(a, m); fin = 31; }
  return [[a, m, fin], mesAnterior(a, m)];
}
const tramo = (a, m, d0, d1) => [iso(a, m, d0), iso(a, m, Math.min(d1, ultimoDia(a, m)))];
function promedio(serie, desde, hasta) {
  const v = Object.entries(serie).filter(([f]) => desde <= f && f <= hasta).map(([, p]) => p);
  return v.length ? [v.reduce((s, x) => s + x, 0) / v.length, v.length] : [null, 0];
}
const mediana = xs => { const o = [...xs].sort((a, b) => a - b), k = o.length >> 1; return o.length % 2 ? o[k] : (o[k - 1] + o[k]) / 2; };
function calcular(hist, meta, corte, anios) {
  const todas = [...new Set(Object.values(hist).flatMap(Object.keys))].sort();
  corte = corte || todas.at(-1);
  const [[ar, mr, fin], [ab, mb]] = ventanas(corte, todas);
  const periodos = d => [tramo(ab - d, mb, 16, 31), tramo(ar - d, mr, 1, fin)];
  const [b0, r0] = periodos(0);
  anios = anios || [1, 2, 3, 4].map(k => ar - k).reverse();
  const salida = { fecha_corte: corte, base: b0, reciente: r0, fechas_base: todas.filter(f => b0[0] <= f && f <= b0[1]),
    fechas_reciente: todas.filter(f => r0[0] <= f && f <= r0[1]), anios, productos: [] };
  for (const p of meta) {
    const fila = { ...p };
    for (const tipo of ["mayorista", "minorista"]) {
      const serie = { ...(hist[`${p.sisap_antes}|${tipo}`] || {}), ...(hist[`${p.sisap}|${tipo}`] || {}) };
      const porAnio = {}, precio = {}, baseAnio = {}, fechas = {};
      for (const a of [ar, ...anios]) {
        const [b, r] = periodos(ar - a), [pb, nb] = promedio(serie, ...b), [pr, nr] = promedio(serie, ...r);
        precio[a] = pr; baseAnio[a] = pb; fechas[a] = [nb, nr];
        porAnio[a] = pb && pr ? (pr / pb - 1) * 100 : null;
      }
      const actual = porAnio[ar] != null ? r1(porAnio[ar]) : null;
      const ref = anios.filter(a => porAnio[a] != null), hist_ = ref.map(a => porAnio[a]);
      const habitual = hist_.length >= Math.min(MINIMO_HIST, anios.length) ? r1(mediana(hist_)) : null;
      const anterior = precio[ar - 1];
      fila[tipo] = { base: baseAnio[ar] ? r2(baseAnio[ar]) : null, reciente: precio[ar] ? r2(precio[ar]) : null, var: actual,
        anios: Object.fromEntries(anios.map(a => [a, porAnio[a] == null ? null : r1(porAnio[a])])), habitual,
        habitual_base: habitual != null ? r2(mediana(ref.map(a => baseAnio[a]))) : null,
        habitual_reciente: habitual != null ? r2(mediana(ref.map(a => precio[a]))) : null,
        fechas, suficiente: Math.min(...fechas[ar]) >= MINIMO_FECHAS,
        vs_anio_anterior: precio[ar] && anterior ? r1((precio[ar] / anterior - 1) * 100) : null };
    }
    salida.productos.push(fila);
  }
  salida.promedio = Object.fromEntries(["mayorista", "minorista"].map(t => [t, promedioPonderado(salida.productos, t)]));
  return salida;
}
function promedioPonderado(productos, tipo) {
  const filas = productos.filter(x => x[tipo].suficiente && x[tipo].var != null && x[tipo].habitual != null).map(x => [x.peso, x[tipo]]);
  if (!filas.length) return null;
  const w = filas.reduce((s, [p]) => s + p, 0);
  return { var: r1(filas.reduce((s, [p, f]) => s + p * f.var, 0) / w), habitual: r1(filas.reduce((s, [p, f]) => s + p * f.habitual, 0) / w), n: filas.length };
}

// ---------- Textos (los mismos de la pestaña) ----------
function periodoAlim(s) {
  const r = s.reciente[1], dia = +r.slice(8), fin = ultimoDia(+r.slice(0, 4), +r.slice(5, 7));
  const mb = MESES[+s.base[0].slice(5, 7) - 1], mr = MESES[+r.slice(5, 7) - 1];
  return { base: `la 2.ª quincena de ${mb}`, corto: `2.ª quincena de ${mb}`, reciente: dia < fin ? `${mr} (hasta el ${dia})` : mr, anio: +s.reciente[0].slice(0, 4) };
}
const sueleTxt = h => h >= 0.5 ? `suele subir ${num(h, 1)} %` : h <= -0.5 ? `suele bajar ${num(-h, 1)} %` : "suele mantenerse";
const fueraHabitual = x => x.var != null && x.habitual != null && Math.abs(x.var - x.habitual) >= UMBRAL_HABITUAL;
const visibles = (s, tipo) => s.productos.filter(p => p[tipo].suficiente !== false && p[tipo].var != null);
function frases(s, tipo) {
  const P = periodoAlim(s), xs = visibles(s, tipo).map(p => ({ n: p.nombre, ...p[tipo] }));
  const l1 = `Entre ${P.base} y ${P.reciente}, subieron ${xs.filter(x => x.var >= 1).length} de ${xs.length} alimentos en los mercados ${tipo}s de Piura`;
  const raros = xs.filter(fueraHabitual).sort((a, b) => Math.abs(b.var - b.habitual) - Math.abs(a.var - a.habitual));
  const nombra = raros.slice(0, 3).map(x => `${x.n.toLowerCase()} (${signo(x.var)}; ${sueleTxt(x.habitual)})`);
  if (raros.length > 3) nombra.push(`${raros.length - 3} más`);
  return [l1, raros.length ? `Fuera de lo habitual: ${yLista(nombra)}` : `Ningún alimento se aleja ${UMBRAL_HABITUAL} puntos o más de lo habitual en estas fechas`];
}
const rangoAnios = s => `${s.anios[0]}-${s.anios.at(-1)}`;

// ---------- Gráfico (el mismo de la pestaña, con colores fijos para poder exportarlo) ----------
function dibujar(s, op, W) {
  const tipo = op.tipo, comp = op.comp;
  const ref = x => comp === "habitual" ? x.habitual : comp ? x.anios[comp] : null;
  const clave = x => op.orden === "dif" ? (x.var != null && x.habitual != null ? x.var - x.habitual : null) : x.var;
  const filas = visibles(s, tipo).map(p => ({ p, ...p[tipo], ref: ref(p[tipo]) })).sort((a, b) => (clave(b) ?? -1e9) - (clave(a) ?? -1e9));
  const estrecho = W < 500, fila = estrecho ? 44 : 32, sobre = estrecho ? 15 : 0;
  const m = { l: estrecho ? 0 : 170, r: 4, t: 4, b: 24 }, H = m.t + m.b + fila * filas.length;
  const vals = filas.flatMap(x => [x.var, x.ref]).filter(v => v != null), lo = Math.min(0, ...vals), hi = Math.max(0, ...vals);
  const paso = [1, 2, 5, 10, 20, 50, 100].find(p => (hi - lo) / p <= (estrecho ? 4 : 7)) || 200;
  const lo2 = Math.floor(lo / paso) * paso, hi2 = Math.ceil(hi / paso) * paso || paso;
  const izq = m.l + (lo < 0 ? 54 : 6), der = W - m.r - (hi > 0 ? 54 : 6);
  const x = v => izq + (v - lo2) * (der - izq) / (hi2 - lo2 || 1);
  let svg = "";
  for (let v = lo2; v <= hi2 + 1e-9; v += paso) svg += `<line x1="${x(v)}" x2="${x(v)}" y1="${m.t}" y2="${H - m.b}" stroke="${
    Math.abs(v) < 1e-9 ? COLOR.texto3 : COLOR.linea}"/><text x="${x(v)}" y="${H - 6}" text-anchor="middle" fill="${COLOR.texto2}">${signo(v).replace(",0", "")}</text>`;
  filas.forEach((f, i) => {
    const y0 = m.t + i * fila, yc = y0 + sobre + (fila - sobre) / 2, v = f.var, r = f.ref, alto = (fila - sobre) * (estrecho ? .62 : .58);
    const fuera = comp === "habitual" && fueraHabitual(f);
    svg += `<g class="alim-fila${fuera ? " fuera" : ""}" data-i="${i}"><rect x="0" y="${y0}" width="${W}" height="${fila}" fill="transparent"/>
      <text class="nombre" x="${estrecho ? 2 : m.l - 8}" y="${estrecho ? y0 + 13 : yc + 4}" text-anchor="${estrecho ? "start" : "end"}" fill="${COLOR.texto}"
        font-size="13"${fuera ? ' font-weight="700"' : ""}>${esc(f.p.nombre)}</text>`;
    if (v == null) svg += `<text x="${x(0) + 6}" y="${yc + 4}">sin dato</text>`;
    else {
      const a = Math.min(x(0), x(v)), w = Math.max(Math.abs(x(v) - x(0)), 1.5);
      svg += `<rect x="${a.toFixed(1)}" y="${(yc - alto / 2).toFixed(1)}" width="${w.toFixed(1)}" height="${alto.toFixed(1)}" rx="2"
        fill="${v >= 0.05 ? COLOR.sube : v <= -0.05 ? COLOR.baja : COLOR.texto3}"/>`;
      const xs = [x(0), x(v), ...(r != null ? [x(r)] : [])], pos = v >= 0 ? Math.max(...xs) + 6 : Math.min(...xs) - 6;
      svg += `<text class="rotulo" x="${pos.toFixed(1)}" y="${yc + 4}" text-anchor="${v >= 0 ? "start" : "end"}" fill="${COLOR.texto}" font-weight="700">${signo(v)}</text>`;
    }
    if (fuera) svg += `<line x1="${x(r).toFixed(1)}" x2="${x(v).toFixed(1)}" y1="${yc.toFixed(1)}" y2="${yc.toFixed(1)}" stroke="${COLOR.texto}" stroke-width="1.2" stroke-dasharray="3 2"/>`;
    if (r != null) svg += `<line x1="${x(r).toFixed(1)}" x2="${x(r).toFixed(1)}" y1="${(yc - alto / 2 - 4).toFixed(1)}" y2="${(yc + alto / 2 + 4).toFixed(1)}" stroke="${COLOR.texto}" stroke-width="${fuera ? 4 : 2.5}"/>`;
    svg += "</g>";
  });
  return { svg, W, H, filas };
}

// ---------- Página ----------
let HIST, META, S, OP, compElegida = "habitual";
const params = new URLSearchParams(location.search);
function textos(s, op) {
  const P = periodoAlim(s), [l1, l2] = frases(s, op.tipo), pr = s.promedio[op.tipo];
  const prom = pr ? `En promedio, los alimentos ${pr.var >= 0.05 ? `subieron ${num(pr.var, 1)} %` : pr.var <= -0.05 ? `bajaron ${num(-pr.var, 1)} %` : "no variaron"} (lo habitual en estas fechas: ${signo(pr.habitual)})` : "";
  const raya = op.comp === "habitual" ? `Lo habitual en estas fechas (mediana de ${rangoAnios(s)})` : op.comp ? `Lo que pasó en las mismas fechas de ${op.comp}` : "";
  const sinRef = op.comp ? visibles(s, op.tipo).filter(p => p[op.tipo].var != null && (op.comp === "habitual" ? p[op.tipo].habitual : p[op.tipo].anios[op.comp]) == null).map(p => p.nombre.toLowerCase()) : [];
  const nota = [op.comp === "habitual" ? `La raya marca cuánto suele cambiar el precio en estas mismas fechas; en negrita y con línea punteada, los que se alejan ${UMBRAL_HABITUAL} puntos o más.`
    : op.comp ? `La raya marca cuánto cambió en las mismas fechas de ${op.comp}.` : "",
    sinRef.length ? `Sin raya: ${yLista(sinRef)} (${op.comp === "habitual" ? "pocos años con dato" : `sin dato en ${op.comp}`}).` : "",
    `Solo alimentos con al menos ${MINIMO_FECHAS} fechas con precio en cada periodo de ${P.anio}.`].filter(Boolean).join(" ");
  return { l1, l2, ud: `Variación del precio promedio por kg: ${P.base} frente a ${P.reciente}`, prom,
    promN: pr ? `Promedio ponderado por el peso de cada alimento en la canasta del IPC, con los ${pr.n} alimentos que tienen raya de lo habitual.` : "",
    raya, nota, fuente: `Fuente: Midagri, SISAP «Precios en ciudades», mercados ${op.tipo}s de Piura. Datos al ${fechaTxt(s.fecha_corte)}. Elaboración: Observatorio FEN Piura (UDEP).` };
}
function pintar() {
  const anios = []; for (let a = +$("f-desde").value; a <= +$("f-hasta").value; a++) anios.push(a);
  OP = { corte: $("f-corte").value || null, tipo: $("f-tipo").value, comp: $("f-comp").value, orden: $("f-orden").value, anios };
  S = calcular(HIST, META, OP.corte, anios.length ? anios : null);
  window.INFOGRAFIA = S;  // para la prueba (scripts/test_pagina.py)
  const cs = $("f-comp"), prev = compElegida;
  cs.innerHTML = `<option value="habitual">Lo habitual (${rangoAnios(S)})</option>${[...S.anios].reverse().map(a => `<option value="${a}">Lo que pasó en ${a}</option>`).join("")}<option value="">Sin comparación</option>`;
  cs.value = [...cs.options].some(o => o.value === prev) ? prev : "habitual";
  OP.comp = compElegida = cs.value;
  const t2 = textos(S, OP);
  $("titulo").textContent = t2.l1; $("frase").textContent = t2.l2 + "."; $("ud").textContent = t2.ud;
  $("prom").textContent = t2.prom ? t2.prom + "." : ""; $("prom-n").textContent = t2.promN;
  $("raya").textContent = t2.raya; $("raya").hidden = !OP.comp; $("nota").textContent = t2.nota; $("fuente").textContent = t2.fuente;
  const g = dibujar(S, OP, Math.max(280, Math.min(900, $("grafico").clientWidth || 720)));
  $("grafico").innerHTML = `<svg viewBox="0 0 ${g.W} ${g.H}" role="img" aria-label="${esc(t2.l1)}">${g.svg}</svg>`;
  const q = new URLSearchParams({ corte: S.fecha_corte, desde: S.anios[0], hasta: S.anios.at(-1), mercado: OP.tipo, comparar: OP.comp, orden: OP.orden });
  $("enlace").href = `?${q}`;
}
// PNG en alta resolución (2x), fondo blanco, con título, frase, cifra, leyenda, gráfico, nota y fuente
const lienzo = document.createElement("canvas").getContext("2d");
function partir(txt, ancho, font) {
  lienzo.font = font; const out = [""];
  for (const w of txt.split(" ")) { const p = (out.at(-1) + " " + w).trim(); if (lienzo.measureText(p).width > ancho && out.at(-1)) out.push(w); else out[out.length - 1] = p; }
  return out;
}
function descargar() {
  const W = 960, pad = 32, g = dibujar(S, OP, W - 2 * pad), t = textos(S, OP), F = "Helvetica, Arial, sans-serif";
  let y = pad, svg = "";
  const parrafo = (txt, size, peso, color, alto) => { for (const l of partir(txt, W - 2 * pad, `${peso} ${size}px ${F}`)) { y += alto;
    svg += `<text x="${pad}" y="${y}" font-family="${F}" font-size="${size}" font-weight="${peso}" fill="${color}">${esc(l)}</text>`; } };
  parrafo(t.l1, 24, 700, COLOR.texto, 30); y += 6;
  parrafo(t.l2 + ".", 17, 400, COLOR.texto, 23);
  parrafo(t.ud, 15, 400, COLOR.texto2, 21); y += 6;
  if (t.prom) parrafo(t.prom + ".", 17, 700, COLOR.texto, 23);
  y += 14;
  let lx = pad;
  for (const [txt, color, raya] of [["Subió", COLOR.sube], ["Bajó", COLOR.baja], ...(OP.comp ? [[t.raya, COLOR.texto, true]] : [])]) {
    svg += raya ? `<rect x="${lx}" y="${y + 4}" width="3" height="14" fill="${color}"/>` : `<rect x="${lx}" y="${y + 5}" width="12" height="12" rx="2" fill="${color}"/>`;
    lienzo.font = `400 15px ${F}`;
    svg += `<text x="${lx + 18}" y="${y + 16}" font-family="${F}" font-size="15" fill="${COLOR.texto2}">${esc(txt)}</text>`;
    lx += 18 + lienzo.measureText(txt).width + 22;
  }
  y += 30;
  svg += `<g transform="translate(${pad} ${y})" font-family="${F}" font-size="12" fill="${COLOR.texto2}">${g.svg}</g>`;
  y += g.H + 8;
  parrafo(t.nota, 13, 400, COLOR.texto3, 18);
  if (t.promN) parrafo(t.promN, 13, 400, COLOR.texto3, 18);
  y += 6; parrafo(t.fuente, 13, 400, COLOR.texto3, 18);
  const H = y + pad;
  const doc = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" fill="#fff"/>${svg}</svg>`;
  const img = new Image();
  img.onload = () => {
    const c = document.createElement("canvas"); c.width = W * 2; c.height = H * 2;
    const ctx = c.getContext("2d"); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, c.width, c.height); ctx.scale(2, 2); ctx.drawImage(img, 0, 0);
    c.toBlob(b => { const a = document.createElement("a"); a.href = URL.createObjectURL(b);
      a.download = `precios_quincena_piura_${S.fecha_corte}.png`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); }, "image/png");
  };
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(doc);
  return doc;
}
(async () => {
  try {
    const [h, s] = await Promise.all(["../data/sisap_historial.json", "../data/precios_sisap.json"].map(u => fetch(u).then(r => { if (!r.ok) throw new Error(u); return r.json(); })));
    HIST = h.precios;
    META = s.productos.map(p => ({ nombre: p.nombre, sisap: p.sisap, sisap_antes: p.sisap_antes, peso: p.peso, descripcion: p.descripcion, reemplaza: p.reemplaza }));
    const todas = [...new Set(Object.values(HIST).flatMap(Object.keys))].sort(), primer = +todas[0].slice(0, 4), ultimo = +todas.at(-1).slice(0, 4);
    const anios = []; for (let a = primer; a < ultimo; a++) anios.push(a);
    $("f-desde").innerHTML = $("f-hasta").innerHTML = anios.map(a => `<option>${a}</option>`).join("");
    const def = calcular(HIST, META, params.get("corte"), null);
    $("f-corte").value = params.get("corte") || todas.at(-1); $("f-corte").min = todas[0]; $("f-corte").max = todas.at(-1);
    $("f-desde").value = params.get("desde") || def.anios[0]; $("f-hasta").value = params.get("hasta") || def.anios.at(-1);
    $("f-tipo").value = params.get("mercado") || "mayorista"; $("f-orden").value = params.get("orden") || "var";
    if (params.has("comparar")) compElegida = params.get("comparar");
    pintar();
    for (const id of ["f-corte", "f-desde", "f-hasta", "f-tipo", "f-orden"]) $(id).onchange = pintar;
    $("f-comp").onchange = () => { compElegida = $("f-comp").value; pintar(); };
    $("descargar").onclick = descargar;
    addEventListener("resize", () => S && pintar());
  } catch (e) {
    $("titulo").innerHTML = `<span class="error">No se pudieron cargar los datos (${esc(e.message)}). Abre la página desde un servidor: python3 -m http.server -d docs</span>`;
  }
})();
