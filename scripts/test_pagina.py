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
                    return [...usados].filter(v => v !== '--c' && !css.getPropertyValue(v).trim()); }""")
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
    print(f"OK: {len(PESTANAS)} pestañas a 1280 y 375 px, enlace antiguo, año de Dengue, rótulos del gráfico, pestañas, compartir, títulos de la portada y aviso de datos viejos")


if __name__ == "__main__":
    main()
