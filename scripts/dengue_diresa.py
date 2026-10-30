"""
Dengue 2026 en Piura desde la sala situacional semanal de la DIRESA Piura (PDF en gob.pe).

Busca la sala más reciente, descarga el PDF a una carpeta temporal y extrae, ubicando cada tabla por su
título (no por número de página):
  - casos, formas clínicas, confirmados, probables y fallecidos por provincia;
  - casos por distrito y semana (los distritos que el PDF lista; el resto viene como "otros distritos");
  - casos por semana para toda la región y dengue grave por semana;
  - hospitalizados por semana y por establecimiento.
Cada tabla se valida contra los totales del propio PDF. Si no cuadra, se guarda como null y se anota el
motivo en "validaciones", para que la página no la muestre. Resultado: docs/data/dengue_2026.json.

Uso: python3 scripts/dengue_diresa.py            (sala más reciente; no hace nada si ya está procesada)
     python3 scripts/dengue_diresa.py archivo.pdf (prueba con un PDF local)
"""
import json
import re
import sys
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path

import pdfplumber
import pypdf

from comun import DATOS, descargar, guardar, verificar_espacio

LISTADO = "https://www.gob.pe/institucion/regionpiura-diresa/informes-publicaciones?term=sala%20situacional"
SALIDA = DATOS / "dengue_2026.json"
NUM = re.compile(r"^\d{1,3}(,\d{3})*(\.\d+)?%?$|^\d+(\.\d+)?%?$")  # 1,234 · 12.5 · 18.06%
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre",
         "noviembre", "diciembre"]


class NoCuadra(Exception):
    pass


def n(t):
    """Número del PDF ('1,234' -> 1234). Lanza NoCuadra si el texto está cortado (p. ej. '1,1')."""
    if not NUM.match(t):
        raise NoCuadra(f"valor ilegible: {t!r}")
    t = t.replace(",", "").rstrip("%")
    return float(t) if "." in t else int(t)


def cuadra(nombre, a, b):
    if a != b:
        raise NoCuadra(f"{nombre}: {a} ≠ {b}")


def ultima_sala():
    """(número de SE, página de la publicación, enlace al PDF) de la sala más reciente del año."""
    abrir = lambda u: urllib.request.urlopen(u, timeout=60).read().decode("utf-8", "replace")
    salas = re.findall(r'href="(/institucion/regionpiura-diresa/informes-publicaciones/\d+-sala-situacional-s-e-n-0*'
                       r'(\d+)-(\d{4})-epidemiologia)"', abrir(LISTADO))
    if not salas:
        raise SystemExit("No se encontró ninguna sala situacional en " + LISTADO)
    ruta, se, anio = max(salas, key=lambda s: (int(s[2]), int(s[1])))
    pagina = "https://www.gob.pe" + ruta
    pdf = re.search(r'https://cdn\.www\.gob\.pe/uploads/document/file/[^"]+\.pdf', abrir(pagina))
    if not pdf:
        raise SystemExit("No se encontró el PDF en " + pagina)
    return int(se), int(anio), pagina, pdf.group(0)


class Pdf:
    """El texto por líneas sale de pypdf (lee mejor estas tablas); las coordenadas, de pdfplumber."""
    def __init__(self, ruta):
        self.textos = [p.extract_text() or "" for p in pypdf.PdfReader(ruta).pages]
        self.plumber = pdfplumber.open(ruta)

    def pagina(self, titulo):
        """Índice de la primera página cuyo texto contiene el título."""
        for i, t in enumerate(self.textos):
            if titulo in t:
                return i
        raise NoCuadra(f"no se encontró la tabla «{titulo}»")

    def texto(self, titulo):
        return self.textos[self.pagina(titulo)]

    def lineas(self, titulo):
        return [l.strip() for l in self.texto(titulo).splitlines() if l.strip()]


def corte(pdf):
    """Semana y fecha de corte del encabezado: '(*) SE 42-2026 Actualizado al 27 de octubre'."""
    m = re.search(r"SE (\d+)-(\d{4}) Actualizado al (\d+) de (\w+)", pdf.textos[1])
    se, anio, dia, mes = m.groups()
    return int(se), f"{anio}-{MESES.index(mes.lower()) + 1:02d}-{int(dia):02d}"


def provincias(pdf):
    """Tabla por provincia. Columnas: semana, acumulados, TIA, S, A, G, confirmados, %, probables, %, fallecidos."""
    cols = ["semana", "casos", "tia", "sin_alarma", "con_alarma", "grave", "confirmados", "pct_c", "probables",
            "pct_p", "fallecidos", "letalidad"]
    filas = {}
    for l in pdf.lineas("según Provincias"):
        m = re.match(r"^([A-ZÑ][A-Za-zÑñ ]+?) ((?:[\d.,]+ ?)+)$", l)
        if not m:
            continue
        nombre, vals = m.group(1).strip().upper(), m.group(2).split()
        if nombre == "IMPORTADOS":
            vals.insert(2, "0")  # los importados no tienen TIA
        if len(vals) != len(cols):
            continue
        filas[nombre] = dict(zip(cols, map(n, vals)))
    total = filas.pop("TOTAL", None)
    if not total or len(filas) < 9:
        raise NoCuadra(f"tabla por provincia incompleta ({len(filas)} filas)")
    for c in ["semana", "casos", "sin_alarma", "con_alarma", "grave", "confirmados", "probables", "fallecidos"]:
        cuadra(f"provincias, columna {c}", sum(f[c] for f in filas.values()), total[c])
    cuadra("formas clínicas = casos", total["sin_alarma"] + total["con_alarma"] + total["grave"], total["casos"])
    cuadra("confirmados + probables = casos", total["confirmados"] + total["probables"], total["casos"])
    return total, [{"provincia": k, **{c: v[c] for c in ["semana", "casos", "grave", "confirmados", "probables",
                                                          "fallecidos"]}} for k, v in filas.items()]


def defunciones(pdf):
    """Fila 'Defunciones' de la tabla por tipo de diagnóstico: confirmados, probables y total del año en curso."""
    t = pdf.texto("Casos de Dengue por Tipo de Diagnóstico y Formas Clínicas")
    m = re.search(r"^Defunciones ((?:[\d.,]+ ?){8})$", t, re.M)
    if not m:
        raise NoCuadra("no se encontró la fila de defunciones")
    v = [n(x) for x in m.group(1).split()][4:7]
    cuadra("defunciones confirmadas + probables", v[0] + v[1], v[2])
    return dict(zip(["confirmadas", "probables", "total"], v))


def formas_semana(pdf, total):
    """Casos por semana según forma clínica: {forma: [casos por semana o None si el valor viene cortado]}."""
    ls = pdf.lineas("Casos de Dengue por Semanas Epidemiológicas según Formas Clínicas")
    semanas = next(l.split() for l in ls if re.fullmatch(r"1 2 3( \d+)*", l))
    res = {}
    for forma, clave in [("SIN SIGNOS DE ALARMA", "sin_alarma"), ("CON SIGNOS DE ALARMA", "con_alarma"),
                         ("GRAVE", "grave")]:
        l = next(l for l in ls if re.match(rf"DENGUE {forma} \d", l))
        vals = l[len(f"DENGUE {forma} "):].split()
        valores = []
        for v in vals:
            try:
                valores.append(n(v))
            except NoCuadra:
                valores.append(None)  # cortado en el PDF
        if len(valores) != len(semanas):
            raise NoCuadra(f"formas por semana, {clave}: {len(valores)} valores para {len(semanas)} semanas")
        if None not in valores:
            cuadra(f"formas por semana, suma de {clave}", sum(valores), total[clave])
        res[clave] = valores
    return res


def distritos(pdf):
    """Tabla distrito x semana. Se lee por coordenadas porque las semanas sin casos vienen en blanco.
    Devuelve (filas, total, avisos): las filas que no cuadran consigo mismas se excluyen y se anotan en avisos."""
    i_pag = pdf.pagina("Según Distrito y Tasa")
    palabras = [((w["x0"] + w["x1"]) / 2, w["top"], w["text"]) for w in pdf.plumber.pages[i_pag].extract_words()]
    X_NOMBRE = 170  # a la izquierda: provincia y distrito; a la derecha: números
    # Agrupa en filas las palabras numéricas cuya altura difiere en menos de 4 puntos
    filas = []
    for x, y, t in sorted((p for p in palabras if p[0] > X_NOMBRE), key=lambda p: p[1]):
        if filas and y - filas[-1][0] < 4:
            filas[-1][1].append((x, t))
        else:
            filas.append((y, [(x, t)]))
    # Cabecera de semanas: la primera fila con al menos 5 enteros consecutivos
    def consecutivos(f):
        s = [int(t) for _, t in sorted(f) if t.isdigit()]
        return len(s) >= 5 and s == list(range(s[0], s[0] + len(s)))
    i_cab = next((i for i, (_, f) in enumerate(filas) if consecutivos(f)), None)
    if i_cab is None:
        raise NoCuadra("no se encontró la cabecera de semanas en la tabla por distrito")
    semanas = [(x, int(t)) for x, t in sorted(filas[i_cab][1]) if t.isdigit()]
    xs_sem = [x for x, _ in semanas]
    paso = (xs_sem[-1] - xs_sem[0]) / (len(xs_sem) - 1)
    # Filas de datos: debajo de la cabecera, con al menos 3 números y con nombre a la izquierda
    # La fila TOTAL viene en texto vertical y se lee aparte: se corta la tabla antes de ella
    y_total = min((y for x, y, t in palabras if x < X_NOMBRE and t == "TOTAL"), default=1e9) - 6
    datos = [(y, sorted(f)) for y, f in filas[i_cab + 1:]
             if y < y_total and sum(bool(NUM.match(t)) for _, t in f) >= 3]
    nombres = [(x, y, t) for x, y, t in palabras if x < X_NOMBRE and filas[i_cab][0] < y < y_total]
    datos = [(y, f) for y, f in datos if any(abs(y2 - y) < 4 for _, y2, _ in nombres)]
    # Columnas fijas (total, TIA, I semestre, II semestre) a partir de la primera fila completa
    completa = next((f for _, f in datos if len(f) == 5 + len(semanas)), None)
    if not completa:
        raise NoCuadra("no hay ninguna fila completa en la tabla por distrito")
    xs_fijas = [x for x, _ in completa[:4]]
    # Cada palabra del nombre va a la fila de datos más cercana en altura (los nombres largos ocupan 2 líneas)
    texto = defaultdict(list)
    for x, y, t in nombres:
        k = min(range(len(datos)), key=lambda k: abs(datos[k][0] - y))
        if abs(datos[k][0] - y) < 12:
            texto[k].append((y, x, t))
    salida = []
    for k, (y, f) in enumerate(datos):
        ws = sorted(texto[k])
        prov = " ".join(t for _, x, t in ws if x < 85)
        dist = " ".join(t for _, x, t in ws if x >= 85)
        fila = {"provincia": prov, "distrito": dist or prov, "semanas": {}}
        for x, t in f:
            if t.endswith("%") or x > xs_sem[-1] + paso / 2:
                continue
            if x < xs_sem[0] - paso / 2:
                i = min(range(4), key=lambda i: abs(xs_fijas[i] - x))
                fila[["total", "tia", "semestre_1", "semestre_2"][i]] = n(t)
            else:
                i = min(range(len(xs_sem)), key=lambda i: abs(xs_sem[i] - x))
                fila["semanas"][semanas[i][1]] = n(t)
        salida.append(fila)
    # Fila TOTAL: viene en texto vertical; pypdf la entrega como una lista de números sueltos
    ls = [l.strip() for l in pdf.textos[i_pag].splitlines() if l.strip()]
    i = max(k for k, l in enumerate(ls) if l.startswith("IMPORTADO"))
    tot = []
    for l in ls[i + 1:]:
        if not NUM.match(l):
            break
        tot.append(n(l))
    if len(tot) < 4 + len(semanas):
        raise NoCuadra("no se pudo leer la fila TOTAL de la tabla por distrito")
    total = {"total": tot[0], "semestre_1": tot[2], "semestre_2": tot[3],
             "semanas": dict(zip([s for _, s in semanas], tot[4:4 + len(semanas)]))}
    # Validaciones duras: cada semana y los semestres deben sumar el TOTAL del PDF
    for s in total["semanas"]:
        cuadra(f"distritos, semana {s}", sum(f["semanas"].get(s, 0) for f in salida), total["semanas"][s])
    cuadra("distritos, total = semestres", total["semestre_1"] + total["semestre_2"], total["total"])
    # Validación por fila: si una fila no cuadra consigo misma, no se publica
    buenas, avisos = [], []
    s1 = sum(f.get("semestre_1", 0) for f in salida)
    if s1 != total["semestre_1"]:
        avisos.append(f"La columna del I semestre suma {s1} y el TOTAL dice {total['semestre_1']}")
    for f in salida:
        sem = sum(f["semanas"].values())
        if sem != f.get("semestre_2") or f.get("semestre_1", 0) + sem != f.get("total"):
            avisos.append(f"{f['distrito']}: las semanas suman {sem}, el II semestre dice {f.get('semestre_2')} "
                          f"y el total {f.get('total')}; fila no publicada")
        else:
            buenas.append(f)
    return buenas, total, avisos


def hospitalizados(pdf):
    """Hospitalizados por establecimiento y semana; cada fila termina con su total."""
    ls = pdf.lineas("Casos Hospitalizados de Dengue por Establecimientos de Salud")
    semanas = next(l.split() for l in ls if re.fullmatch(r"1 2 3( \d+)*", l))
    k = len(semanas) + 1
    filas, nombre = [], []
    for l in ls[ls.index(" ".join(semanas)) + 1:]:
        toks = l.split()
        cola = 0
        while cola < len(toks) and NUM.match(toks[-1 - cola]):
            cola += 1
        if cola >= k:
            nombre.append(" ".join(toks[:-k]))
            filas.append((" ".join(x for x in nombre if x), [n(t) for t in toks[-k:]]))
            nombre = []
        else:
            nombre.append(l)
    total = next((v for nom, v in filas if nom.startswith("Total general")), None)
    filas = [(nom, v) for nom, v in filas if not nom.startswith("Total general")]
    if not total:
        raise NoCuadra("no se encontró la fila 'Total general' de hospitalizados")
    for nom, v in filas + [("Total general", total)]:
        cuadra(f"hospitalizados, {nom}", sum(v[:-1]), v[-1])
    # La tabla no lista todos los establecimientos: lo listado no puede superar el total de cada semana
    for i, s in enumerate(semanas + ["total"]):
        listado = sum(v[i] for _, v in filas)
        if listado > total[i]:
            raise NoCuadra(f"hospitalizados, semana {s}: los establecimientos suman {listado} > total {total[i]}")
    otros = total[-1] - sum(v[-1] for _, v in filas)
    return {"semanas": dict(zip(map(int, semanas), total[:-1])), "total": total[-1],
            "establecimientos": sorted([[nom, v[-1]] for nom, v in filas], key=lambda x: -x[1])
                                + ([["Otros establecimientos (no listados en el PDF)", otros]] if otros else [])}


def extraer(ruta):
    validaciones, res = {}, {}

    def intentar(nombre, f):
        try:
            res[nombre] = f()
            validaciones[nombre] = "ok"
        except (NoCuadra, StopIteration, ValueError, AttributeError) as e:
            res[nombre] = None
            validaciones[nombre] = f"no publicado: {e or type(e).__name__}"

    pdf = Pdf(ruta)
    with pdf.plumber:
        se, fecha = corte(pdf)
        intentar("provincias", lambda: provincias(pdf))
        intentar("defunciones", lambda: defunciones(pdf))
        intentar("distritos", lambda: distritos(pdf))
        intentar("hospitalizados", lambda: hospitalizados(pdf))
        total = res["provincias"][0] if res["provincias"] else None
        intentar("formas_semana", lambda: formas_semana(pdf, total) if total else None)

    # Serie semanal de la región: las semanas de la tabla por distrito salen de su fila TOTAL; las demás, de
    # la suma de las tres formas clínicas. Se valida contra el acumulado del año.
    def serie():
        if not (total and res["distritos"] and res["formas_semana"]):
            raise NoCuadra("faltan tablas para armar la serie")
        fs, tot_d = res["formas_semana"], res["distritos"][1]["semanas"]
        casos = {}
        for i in range(len(fs["grave"])):
            s = i + 1
            if s in tot_d:
                casos[s] = tot_d[s]
            elif None in (fs["sin_alarma"][i], fs["con_alarma"][i], fs["grave"][i]):
                raise NoCuadra(f"serie semanal: valor cortado en la semana {s}")
            else:
                casos[s] = fs["sin_alarma"][i] + fs["con_alarma"][i] + fs["grave"][i]
        cuadra("serie semanal = acumulado", sum(casos.values()), total["casos"])
        grave = fs["grave"] if None not in fs["grave"] else None
        return [[s, c, grave[s - 1] if grave else None] for s, c in casos.items()]
    intentar("serie", serie)
    return se, fecha, res, validaciones


def main():
    verificar_espacio()
    if len(sys.argv) > 1:
        ruta, pagina, enlace = Path(sys.argv[1]), "(archivo local)", sys.argv[1]
        se_pub = None
    else:
        se_pub, anio, pagina, enlace = ultima_sala()
        if SALIDA.exists() and json.loads(SALIDA.read_text())["se"] == se_pub:
            print(f"La sala SE {se_pub}-{anio} ya está procesada.")
            return
    with tempfile.TemporaryDirectory() as tmp:
        if se_pub is not None:
            ruta = Path(tmp) / "sala.pdf"
            print("Descargando", enlace)
            descargar(enlace, ruta)
        se, fecha, r, val = extraer(ruta)
    for k, v in val.items():
        print(f"  {k}: {v}")
    total, provs = r["provincias"] or (None, None)
    dist = r["distritos"]
    guardar("dengue_2026.json", {
        "fuente": "DIRESA Piura, Sala situacional de salud (Oficina de Epidemiología)",
        "url": pagina,
        "pdf": enlace,
        "se": se,
        "fecha_corte": fecha,
        "validaciones": val,
        "nota": "Casos confirmados y probables (C+P). Las cifras de semanas recientes se corrigen en salas posteriores.",
        "totales": total and {k: total[k] for k in ["semana", "casos", "sin_alarma", "con_alarma", "grave",
                                                    "confirmados", "probables", "fallecidos"]},
        "defunciones": r["defunciones"],
        "provincias": provs,
        "serie": r["serie"],
        "distritos": dist and dist[0],
        "distritos_total": dist and dist[1],
        "avisos": dist[2] if dist else [],
        "hospitalizados": r["hospitalizados"],
    })


if __name__ == "__main__":
    main()
