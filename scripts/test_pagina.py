"""
Prueba de la página (docs/index.html) en un navegador sin ventana, antes de subir cambios.

Revisa, en escritorio (1280 px) y celular (375 px):
  - que cada dirección #pestaña muestre solo su pestaña y la marque en el menú;
  - que la página no se desplace de lado, ni con el detalle abierto;
  - que ninguna tabla larga (más de 15 filas) se vea sin abrir "Ver detalle";
  - que no haya errores en la consola ni tokens de diseño (var(--…)) sin definir;
  - que un enlace antiguo (#alertas) abra Obras con el detalle desplegado;
  - que el año de la pestaña Dengue sea el de la sala de la DIRESA;
  - que los rótulos del gráfico semanal de dengue no se encimen ni se salgan del gráfico;
  - que las pestañas midan al menos 44 px de alto, y que estén el botón de compartir y los enlaces "Siguiente";
  - que los 5 títulos de la portada tengan texto y que el de salud cuadre con el mes de su cifra y su comparación;
  - que el título del dengue siga la regla de semanas completas (las preliminares no cuentan) y que el semáforo del
    presupuesto cambie en 5 y 15 puntos;
  - que los mapas de Obras y Salud (Leaflet) se dibujen, o digan claramente que no cargaron;
  - los nombres cortos de obras, las duraciones en años y meses y los nombres legibles de entidades;
  - que el título y el color de las obras paralizadas sigan la regla frente al país, y que cada causa tenga definición;
  - que un dato de camas de SUSALUD que no cuadra se marque para revisar, y uno normal no;
  - que aparezca "Dato no actualizado" si se simula una fecha 60 días después.

Requiere Playwright (pip3 install playwright) y un navegador Chromium: usa Brave o Chrome si están
instalados (Playwright no trae navegador para macOS 12); otro, con la variable NAVEGADOR=/ruta/al/ejecutable.
Uso: python3 scripts/test_pagina.py
"""
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

DOCS = Path(__file__).resolve().parent.parent / "docs"
PESTANAS = ["resumen", "dengue", "gasto", "obras", "salud", "precios", "fuentes"]
NAVEGADORES = [os.environ.get("NAVEGADOR"), "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
               "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
fallos = []


def revisar(condicion, mensaje):
    if not condicion:
        fallos.append(mensaje)


def puerto_libre():
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def abrir_navegador(p):
    ruta = next((r for r in NAVEGADORES if r and Path(r).exists()), None)
    return p.chromium.launch(executable_path=ruta, headless=True) if ruta else p.chromium.launch(headless=True)


def main():
    puerto = puerto_libre()
    # salida del servidor a /dev/null: si se leyera por una tubería sin vaciarla, podría bloquearse
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(puerto), "-d", str(DOCS)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://localhost:{puerto}/index.html"
    try:
        time.sleep(1)
        with sync_playwright() as p:
            nav = abrir_navegador(p)
            for ancho in (1280, 375):
                pg = nav.new_page(viewport={"width": ancho, "height": 900})
                errores = []
                pg.on("pageerror", lambda e: errores.append(str(e)))
                pg.on("console", lambda m: m.type == "error" and errores.append(m.text))
                pg.goto(base + "#resumen")
                pg.wait_for_function("document.querySelectorAll('#resumen-paneles .panel').length >= 5", timeout=15000)
                for t in PESTANAS:
                    pg.evaluate(f"location.hash = '#{t}'")
                    pg.wait_for_timeout(300)
                    r = pg.evaluate(f"""() => {{
                        const s = document.getElementById('{t}'), de = document.documentElement;
                        const visibles = [...document.querySelectorAll('.pestana')].filter(x => !x.hidden).map(x => x.id);
                        const actual = document.querySelector('.pestanas a[aria-current="page"]')?.getAttribute('href');
                        const tablas = [...s.querySelectorAll('table')].filter(tb => !tb.closest('details'))
                            .map(tb => tb.querySelectorAll('tbody tr').length);
                        const desborde1 = de.scrollWidth - de.clientWidth;
                        s.querySelectorAll('details').forEach(d => d.open = true);
                        const desborde2 = de.scrollWidth - de.clientWidth;
                        s.querySelectorAll('details').forEach(d => d.open = false);
                        return {{ visibles, actual, tablas, desborde1, desborde2 }};
                    }}""")
                    revisar(r["visibles"] == [t], f"{ancho}px #{t}: se ven {r['visibles']}")
                    revisar(r["actual"] == f"#{t}", f"{ancho}px #{t}: el menú marca {r['actual']}")
                    revisar(max(r["desborde1"], r["desborde2"]) <= 0,
                            f"{ancho}px #{t}: la página se desplaza de lado ({r['desborde1']} / {r['desborde2']} px con detalle)")
                    largas = [n for n in r["tablas"] if n > 15]
                    revisar(not largas,
                            f"{ancho}px #{t}: tablas visibles sin abrir el detalle ({r['tablas']} filas)")
                pg.evaluate("location.hash = '#alertas'")
                pg.wait_for_timeout(300)
                r = pg.evaluate("() => ({ tab: [...document.querySelectorAll('.pestana')].filter(x => !x.hidden).map(x => x.id),"
                                " abierto: document.querySelector('#obras details').open })")
                revisar(r == {"tab": ["obras"], "abierto": True}, f"{ancho}px #alertas: {r}")
                anio = pg.evaluate("() => [document.querySelector('#t-dengue .anio-d').textContent,"
                                   " String(D.d26?.fecha_corte ?? '').slice(0, 4)]")
                revisar(anio[0] == anio[1] and anio[0].isdigit(), f"{ancho}px: año de Dengue {anio[0]} y de la sala {anio[1]}")
                # Rótulos del gráfico semanal: cajas reales, sin choques entre ellas ni fuera del gráfico
                pg.evaluate("location.hash = '#dengue'")
                pg.wait_for_timeout(500)
                r = pg.evaluate("""() => {
                    const svg = document.querySelector('#g-semanas svg'), w = svg.viewBox.baseVal.width;
                    const c = [...svg.querySelectorAll('text.rotulo')].map(t => { const b = t.getBBox();
                        return { t: t.textContent, x0: b.x, y0: b.y, x1: b.x + b.width, y1: b.y + b.height }; });
                    const choques = c.flatMap((a, i) => c.slice(i + 1).filter(b => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1)
                        .map(b => a.t + ' / ' + b.t));
                    return { n: c.length, choques, fuera: c.filter(a => a.x0 < 0 || a.x1 > w || a.y0 < 0).map(a => a.t) };
                }""")
                revisar(r["n"] >= 2 and not r["choques"] and not r["fuera"],
                        f"{ancho}px gráfico de dengue: {r['n']} rótulos, se enciman {r['choques']}, fuera {r['fuera']}")
                r = pg.evaluate("""() => ({ alto: Math.min(...[...document.querySelectorAll('.pestanas a')].map(a => a.getBoundingClientRect().height)),
                    compartir: !!document.getElementById('compartir'), siguientes: document.querySelectorAll('.siguiente a').length,
                    actualizado: document.getElementById('actualizado').textContent })""")
                revisar(r["alto"] >= 44, f"{ancho}px: pestañas de {r['alto']:.0f} px (mínimo 44)")
                revisar(r["compartir"] and r["siguientes"] == len(PESTANAS) and r["actualizado"].startswith("Actualizado al"),
                        f"{ancho}px: compartir {r['compartir']}, enlaces Siguiente {r['siguientes']}, «{r['actualizado']}»")
                # Todo var(--token) usado en la página (estilos y SVG generados) debe estar definido
                sin_definir = pg.evaluate("""() => { const css = getComputedStyle(document.documentElement);
                    const usados = new Set([...document.documentElement.outerHTML.matchAll(/var\\((--[\\w-]+)[),]/g)].map(m => m[1]));
                    return [...usados].filter(v => !['--c', '--x', '--p', '--n'].includes(v) && !css.getPropertyValue(v).trim()); }""")
                revisar(not sin_definir, f"{ancho}px: tokens sin definir: {sin_definir}")
                revisar(not errores, f"{ancho}px: errores en la consola: {errores[:3]}")
                pg.close()
            # Títulos de la portada: 5 con texto; el de salud, por regla, solo si la serie y la cifra son del mismo mes
            pg = nav.new_page()
            pg.goto(base + "#resumen")
            pg.wait_for_function("document.querySelectorAll('#resumen-paneles .panel').length >= 5", timeout=15000)
            r = pg.evaluate("""() => {
                const t = [...document.querySelectorAll('#resumen-paneles .panel h3')].map(h => h.textContent.trim());
                const o = ocupacionSerie(), sal = t.find(x => /salud|ocupación de camas/i.test(x));
                let esperado = '¿Está preparada la salud?';
                if (o?.dir) esperado = `La ocupación de camas ${o.dir} frente a hace un año`;
                const regla = !o?.prev || (o.oc(o.u) - o.oc(o.prev) >= 1 ? 'sube' : o.oc(o.u) - o.oc(o.prev) <= -1 ? 'baja' : 'se mantiene') === o.dir;
                // con la serie desfasada un mes, el título vuelve a la pregunta
                D.camas = { ...D.camas, periodo: 'agosto de 1999' };
                const desfasada = ocupacionSerie() === null;
                return { t, sal, esperado, regla, desfasada };
            }""")
            revisar(len(r["t"]) == 5 and all(r["t"]), f"títulos de la portada: {r['t']}")
            # Dengue: tendencia de las 4 últimas semanas completas; cambiar una semana preliminar no la mueve
            r2 = pg.evaluate("""() => {
                const d = D.d26, t = tendenciaDengue(d), titulo = document.querySelector('#resumen-paneles .destacado h3').textContent.trim();
                const prelim = { ...d, serie: d.serie.map(([s, c]) => [s, s > d.se - PRELIMINAR ? 0 : c]) };
                const sube = { ...d, serie: d.serie.map(([s, c]) => [s, s <= d.se - PRELIMINAR && s > d.se - PRELIMINAR - 4 ? c * 3 : c]) };
                const baja = { ...d, serie: d.serie.map(([s, c]) => [s, s <= d.se - PRELIMINAR && s > d.se - PRELIMINAR - 4 ? 0 : c]) };
                return { titulo, esperado: `El dengue ${t.dir} en las últimas 4 semanas completas`, igual: tendenciaDengue(prelim).dir === t.dir,
                  sube: tendenciaDengue(sube).dir, baja: tendenciaDengue(baja).dir,
                  semaforo: [semaforo(80, 85)[1], semaforo(79.9, 85)[1], semaforo(70, 85)[1], semaforo(69.9, 85)[1]],
                  nombres: [nombreCorto("  "), nombreCorto("A".repeat(90)).length, nombreCorto("MEJORAMIENTO DE LA I E SAN JOSE EN LA LOCALIDAD DE CASTILLA DISTRITO DE CASTILLA"),
                    nombreCorto("AGUA POTABLE EN LAS LOCALIDADES DE SULLANA Y MARCAVELICA DE LA PROVINCIA DE SULLANA DEPARTAMENTO DE PIURA"),
                    distritoDengue({ distrito: "SALITRAL (MOR)", provincia: "MORROPON" }),
                    duracion(0), duracion(250), duracion(365.25 * 4 + 3), duracion(640)],
                  entidades: [legible("MUNICIPALIDAD DISTRITAL DE LA UNION"), legible("MUNICIPALIDAD DISTRITAL DE SAN MIGUEL DE EL FAIQUE"),
                    legible("MANCOMUNIDAD MUNICIPAL SIMON RODRIGUEZ - MMSR")] };
            }""")
            revisar(r2["titulo"] == r2["esperado"] and r2["igual"] and r2["sube"] == "sube" and r2["baja"] == "baja",
                    f"regla del dengue: {r2}")
            revisar(r2["semaforo"] == ["ok", "lento", "lento", "muy-lento"], f"semáforo: {r2['semaforo']}")
            revisar(r2["nombres"] == ["Obra sin nombre", 90, "I.E. san jose", "Agua potable en las localidades de Sullana y Marcavelica", "Salitral (Morropón)", "menos de 1 mes", "8 meses", "4 años", "1 año y 9 meses"],
                    f"nombres cortos y duraciones: {r2['nombres']}")
            # Camas: dato de SUSALUD que no cuadra se marca (no se corrige); un dato normal no
            r4 = pg.evaluate("""() => [!!datoCamaRaro({ reporto: true, camas: 8, dias_cama: 95, pacientes_dia: 98 }, "setiembre de 2026"),
                !!datoCamaRaro({ reporto: true, camas: 10, dias_cama: 300, pacientes_dia: 200 }, "setiembre de 2026"),
                diasMes("febrero de 2028")]""")
            revisar(r4 == [True, False, 29], f"datos de camas a revisar: {r4}")
            # Obras revisadas a mano: las reactivadas se señalan en la lista, sin cambiar la cifra de paralizadas
            r5 = pg.evaluate("""() => { const t = document.querySelectorAll('#resumen-paneles .panel')[2].querySelector('.cifra').textContent;
                const act = D.obras.obras.filter(x => !APARTE[x.codigo_infobras]);
                return { cifra: t.trim() === String(act.filter(x => x.estado === "Paralizada").length),
                  reactivadas: act.filter(reactivada).map(x => x.codigo_infobras).sort() }; }""")
            revisar(r5["cifra"] and r5["reactivadas"] == ["114837", "88999"], f"obras revisadas a mano: {r5}")
            # Obras frente al país: título y color siguen la regla de 1 punto; cada causa de Piura tiene definición
            r3 = pg.evaluate("""() => {
                const act = D.obras.obras.filter(x => !APARTE[x.codigo_infobras]), par = act.filter(x => x.estado === "Paralizada");
                const c = obrasPais(act, par), tarjeta = document.querySelectorAll('#resumen-paneles .panel')[2];
                const sube = obrasPais(act, [...par, ...act.filter(x => x.estado !== "Paralizada").slice(0, Math.ceil(act.length * .02))]);
                const titulos = [tituloPais({ comp: "similar", costoAlto: true }),
                  tituloPais({ ...c, costoAlto: c.cP >= COSTO_ALTO * (c.cP + 1) })];
                return { ok: !!c, titulos, costoAlto: c.costoAlto === (c.cP >= 1.5 * c.cN), titulo: tarjeta.querySelector('h3').textContent.trim() === tituloPais(c),
                  rojo: tarjeta.classList.contains('cifra-alerta') === (c.comp === "mas"), mas: sube.comp,
                  sinDef: [...new Set(par.map(x => x.causal).filter(Boolean))].filter(k => !defCausa(k)) };
            }""")
            revisar(r3["costoAlto"] and r3["titulos"][0] == "Pocas obras paralizadas, pero de alto costo" and r3["titulos"][1] in ("Obras paralizadas en la proporción del país", "Más obras paralizadas que el país",
                    "Menos obras paralizadas que el país"), f"regla de costo alto: {r3}")
            revisar(r3["ok"] and r3["titulo"] and r3["rojo"] and r3["mas"] == "mas" and not r3["sinDef"], f"obras frente al país y causas: {r3}")
            # Barra del costo de las paralizadas: 5 tramos y el resto suman el total; el tramo abre su nombre y monto
            pg.evaluate("location.hash = '#obras'")
            pg.wait_for_selector("#obras-paneles .barra-costo")
            pg.locator("#obras-paneles .tramo").first.click()
            r6 = pg.evaluate("""() => { const ps = [...document.querySelectorAll('#obras-paneles .tramo')].map(b => +b.style.getPropertyValue('--p'));
                return { n: ps.length, suma: ps.reduce((a, b) => a + b, 0), caja: !$('definicion').hidden && $('definicion').textContent }; }""")
            revisar(r6["n"] == 6 and abs(r6["suma"] - 1) < 1e-3 and str(r6["caja"]).startswith("1. "), f"barra del costo: {r6}")
            pg.keyboard.press("Escape")
            revisar(r2["entidades"] == ["Municipalidad Distrital de La Unión", "Municipalidad Distrital de San Miguel de El Faique",
                                        "Mancomunidad Municipal Simón Rodríguez (MMSR)"], f"nombres de entidades: {r2['entidades']}")
            # Mapas con Leaflet: dibujados, o con su mensaje si el CDN no respondió
            for tab, mapa in (("obras", "mapa-obras"), ("salud", "mapa-salud")):
                pg.evaluate(f"location.hash = '#{tab}'")
                pg.wait_for_function(f"document.querySelector('#{mapa} .leaflet-interactive, #{mapa} .sin-datos')", timeout=20000)
                n = pg.evaluate(f"document.querySelectorAll('#{mapa} path.leaflet-interactive').length")
                revisar(n >= 60 or pg.evaluate(f"!!document.querySelector('#{mapa} .sin-datos')"), f"mapa {mapa}: {n} distritos")
            revisar(r["sal"] == r["esperado"] and r["regla"] and r["desfasada"],
                    f"título de salud «{r['sal']}», esperado «{r['esperado']}», regla {r['regla']}, serie desfasada {r['desfasada']}")
            pg.close()
            # Aviso de datos viejos: con el reloj 60 días adelante deben aparecer avisos
            pg = nav.new_page()
            pg.clock.set_fixed_time(datetime.now() + timedelta(days=60))
            pg.goto(base + "#resumen")
            pg.wait_for_function("document.querySelectorAll('#resumen-paneles .panel').length >= 5", timeout=15000)
            n = pg.evaluate("document.querySelectorAll('#resumen-paneles .vencido').length")
            revisar(n >= 3, f"con 60 días de retraso simulado se ven {n} avisos 'Dato no actualizado' en el resumen")
            nav.close()
    finally:
        srv.terminate()
    if fallos:
        print("FALLA:\n  " + "\n  ".join(fallos))
        sys.exit(1)
    print(f"OK: {len(PESTANAS)} pestañas a 1280 y 375 px, enlace antiguo, año de Dengue, rótulos del gráfico, pestañas, compartir, títulos de la portada, regla del dengue, semáforo, mapas y aviso de datos viejos")


if __name__ == "__main__":
    main()
