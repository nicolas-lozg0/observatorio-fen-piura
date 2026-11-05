"""
Índice de precios al consumidor (IPC) de Piura: variación mensual, acumulada en el año y en 12 meses.

Fuente: INEI, Informe Técnico mensual "Variación de los Indicadores de Precios de la Economía" (PDF), Cuadro 2
("Variación porcentual del IPC Nacional y de principales ciudades"). El INEI publica un informe cada mes (el día 1,
con los datos del mes anterior) y los nombres de los PDF no siguen un patrón, así que se leen de la lista de la
biblioteca virtual. Solo se descargan los informes que aún no están en docs/data/ipc_piura.json.
Resultado: docs/data/ipc_piura.json.
"""
import html
import json
import re
import tempfile
from pathlib import Path

import pdfplumber

from comun import DATOS, abrir, guardar, verificar_espacio  # abrir envía User-Agent: el INEI lo exige

BASE = "https://www.inei.gob.pe"
LISTA = BASE + "/biblioteca-virtual/boletines/informe-de-precios/{}/"  # 10 informes por página, el más reciente primero
PAGINAS = 3  # 30 informes = 30 meses: 24 de serie y margen para verificar la variación en 12 meses
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre",
         "noviembre", "diciembre"]
CONTROL = {"2026-02": (0.48, 2.28)}  # dato publicado por el INEI para Piura (mensual, 12 meses), verificado a mano
NUM = r"(-?\d+,\d+)"


def listar(pagina):
    """Informes de una página de la lista: [(fecha de publicación dd/mm/aaaa, título, url del PDF)]."""
    t = abrir(LISTA.format(pagina)).read().decode("utf-8", "replace")
    filas = re.findall(r'(?s)rel="([^"]+\.pdf)">\s*<td[^>]*>\s*([\d/]+)\s*</td>\s*<td>(.*?)</td>', t)
    return [(f, html.unescape(n).strip(), BASE + rel) for rel, f, n in filas]


def lineas(pagina, tol=2.0, hueco=2.0):
    """Arma las líneas de texto agrupando caracteres por altura. En varios informes el cuadro tiene una inclinación
    mínima y extract_text() de pdfplumber mezcla sus columnas, por eso no se usa aquí."""
    filas = []
    for c in sorted(pagina.chars, key=lambda c: (round(c["top"]), c["x0"])):
        for f in filas:
            if abs(f[0] - c["top"]) <= tol:
                f[1].append(c)
                break
        else:
            filas.append([c["top"], [c]])
    salida = []
    for _, cs in sorted(filas, key=lambda f: f[0]):
        cs.sort(key=lambda c: c["x0"])
        t = cs[0]["text"]
        for a, b in zip(cs, cs[1:]):
            t += (" " if b["x0"] - a["x1"] > hueco else "") + b["text"]
        salida.append(" ".join(t.split()))
    return salida


def fila(lineas_, nombre, mes):
    """Valores (mensual, acumulada, 12 meses) de una ciudad. En enero y diciembre el cuadro trae solo dos columnas:
    en enero, mensual = acumulada; en diciembre, acumulada = 12 meses."""
    for l in lineas_:
        m = re.fullmatch(rf"{nombre} {NUM} {NUM}(?: {NUM})?", l)
        if m:
            v = [float(x.replace(",", ".")) for x in m.groups() if x]
            if len(v) == 3:
                return v
            return {1: [v[0], v[0], v[1]], 12: [v[0], v[1], v[1]]}.get(mes)  # dos columnas en otro mes: no se adivina
    return None


def leer_pdf(ruta):
    """Busca el Cuadro 2 (IPC por ciudades) y devuelve el mes ('aaaa-mm') y los valores de Piura y Nacional."""
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            if "Cuadro 2" not in (pagina.extract_text() or ""):
                continue
            ls = lineas(pagina)
            patron = rf"(?i)({'|'.join(MESES)}|septiembre) (\d{{4}})"
            mes = next((re.fullmatch(patron, l) for l in ls if re.fullmatch(patron, l)), None)
            if not mes:
                continue
            m = MESES.index(mes.group(1).lower().replace("septiembre", "setiembre")) + 1
            piura, nac = fila(ls, "Piura", m), fila(ls, "Nacional", m)
            if piura and nac:
                return f"{mes.group(2)}-{m:02d}", piura, nac
    return None


assert fila(["Piura 0,11 1,95"], "Piura", 1) == [0.11, 0.11, 1.95]
assert fila(["Piura 0,10 2,00"], "Piura", 12) == [0.10, 2.00, 2.00]
assert fila(["Piura 0,48 0,59 2,28"], "Piura", 2) == [0.48, 0.59, 2.28]
assert fila(["Piura 0,48 0,59"], "Piura", 5) is None


def compuesta(mensuales):
    """Variación compuesta (%) de varias variaciones mensuales (%)."""
    r = 1.0
    for x in mensuales:
        r *= 1 + x / 100
    return 100 * (r - 1)


assert abs(compuesta([1, 1]) - 2.01) < 1e-9


def verificar(serie):
    """Compara la variación en 12 meses y la acumulada del INEI con la que resulta de componer las mensuales."""
    por_mes = {s["mes"]: s for s in serie}
    avisos = []
    for s in serie:
        a, m = map(int, s["mes"].split("-"))
        previos = [f"{a - (m - k <= 0)}-{(m - k - 1) % 12 + 1:02d}" for k in range(12)]  # el mes y los 11 anteriores
        if all(p in por_mes for p in previos):
            c = compuesta(por_mes[p]["mensual"] for p in previos)
            if abs(c - s["doce_meses"]) > 0.1:  # 12 valores redondeados a 2 decimales
                avisos.append(f"{s['mes']}: 12 meses {s['doce_meses']} frente a {c:.2f} compuesto")
        en_anio = [f"{a}-{k:02d}" for k in range(1, m + 1)]
        if all(p in por_mes for p in en_anio):
            c = compuesta(por_mes[p]["mensual"] for p in en_anio)
            if abs(c - s["acumulada"]) > 0.06:
                avisos.append(f"{s['mes']}: acumulada {s['acumulada']} frente a {c:.2f} compuesta")
    for mes, (mensual, doce) in CONTROL.items():
        if mes in por_mes and (por_mes[mes]["mensual"], por_mes[mes]["doce_meses"]) != (mensual, doce):
            avisos.append(f"{mes}: no coincide con el dato de control {mensual} y {doce}")
    return avisos


def main():
    verificar_espacio()
    ruta = DATOS / "ipc_piura.json"
    previo = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"serie": []}
    serie = {s["mes"]: s for s in previo["serie"]}
    leidos = {s["pdf"] for s in previo["serie"]}

    informes = [i for pagina in range(1, PAGINAS + 1) for i in listar(pagina)]

    nuevos = [i for i in informes if i[2] not in leidos]
    print(f"{len(informes)} informes en la lista; {len(nuevos)} por leer")
    with tempfile.TemporaryDirectory() as tmp:
        for fecha_pub, titulo, url in nuevos:
            archivo = Path(tmp) / "informe.pdf"
            try:
                with abrir(url) as r, open(archivo, "wb") as f:
                    f.write(r.read())
            except OSError as e:
                print("  No se pudo descargar", url, e)
                continue
            verificar_espacio()
            r = leer_pdf(archivo)
            if not r:
                print(f"  Sin cuadro de ciudades: {titulo}")
                continue
            mes, piura, nac = r
            serie[mes] = {"mes": mes, "mensual": piura[0], "acumulada": piura[1], "doce_meses": piura[2],
                          "nacional_mensual": nac[0], "nacional_doce_meses": nac[2],
                          "publicado": "-".join(reversed(fecha_pub.split("/"))), "pdf": url}
            print(f"  {mes}: Piura {piura}, Nacional {nac}")

    lista = sorted(serie.values(), key=lambda s: s["mes"])
    if not lista:
        raise SystemExit("No se pudo leer ningún informe del INEI.")
    avisos = verificar(lista)
    for a in avisos:
        print("  AVISO", a)
    datos = {
        "fuente": "INEI, Informe Técnico de Variación de los Indicadores de Precios de la Economía (Cuadro 2)",
        "url": LISTA.format(1),
        "fecha_corte": lista[-1]["publicado"],
        "ultimo_mes": lista[-1]["mes"],
        "avisos": avisos,
        "serie": lista,
    }
    # Sin cambios en los datos no se reescribe el archivo: evita commits que solo cambian la hora de proceso
    if {k: v for k, v in previo.items() if k != "procesado"} == datos:
        print("Sin informes nuevos: ipc_piura.json no cambia.")
        return
    guardar("ipc_piura.json", datos)


if __name__ == "__main__":
    main()
