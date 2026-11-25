"""
Precios de alimentos en los mercados de Piura (SISAP del Midagri): variación de la 2.ª quincena del mes anterior al mes en
curso, como el gráfico de Lima que circula, y comparación con lo habitual en esas mismas fechas de los 4 años anteriores.

Fuente: Midagri, SISAP «Precios en ciudades», región Piura (mercados mayoristas y minoristas de Piura).
El SISAP no tiene descarga documentada: alguien exporta a mano la tabla con el botón «Exportar a Excel» y deja el archivo en
data/raw/sisap/ (instrucciones en scripts/actualizacion_local.md). Este script:
  1. lee todos los .xls de data/raw/sisap/ (son tablas HTML) y suma sus precios al historial data/sisap_piura.json
     (un precio nuevo reemplaza al de la misma fecha, producto y mercado);
  2. calcula las variaciones y guarda docs/data/precios_sisap.json.
Uso: python3 scripts/precios_sisap.py
"""
import html
import json
import re
import statistics
from datetime import date, timedelta
from pathlib import Path

from comun import RAIZ, guardar

ORIGEN = RAIZ / "data" / "raw" / "sisap"
HISTORIAL = RAIZ / "data" / "sisap_piura.json"
URL = "http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/"
# (nombre en la página, nombre original en el SISAP de Piura, producto del gráfico de Lima al que reemplaza). El nombre en la
# página es simple (ronda de simbología, 24/11/2026): «Pollo» y no «Carne de pollo (eviscerado)»; el original se guarda y se
# muestra en el globo y en la tabla. DESCRIPCION: lo que se mide, cuando el nombre simple no lo dice.
PRODUCTOS = [
    ("Zanahoria", "Zanahoria", None),
    ("Papa yungay", "Papa yungay", "papa blanca"),
    ("Ajo", "Ajo criollo o napuri", None),
    ("Papa amarilla", "Papa amarilla", None),
    ("Choclo", "Choclo (tipo cusco)", None),
    ("Palta", "Palta fuerte", None),
    ("Frijol castilla", "Frijol castilla", None),
    ("Arroz superior", "Arroz superior", "arroz corriente"),
    ("Plátano seda congo", "Platano seda congo", "plátano seda"),
    ("Vainita", "Vainita americana", None),
    ("Tomate", "Tomate", None),
    ("Lenteja", "Lenteja", None),
    # básicos de la zona agregados en la ronda de precios (todos con datos de 2022 a 2026 en las exportaciones)
    ("Limón sutil", "Limon sutil bolsa", None),
    ("Cebolla roja", "Cebolla cabeza roja", None),
    ("Camote morado", "Camote morado", None),
    ("Yuca", "Yuca blanca", None),
    ("Plátano bellaco", "Platano bellaco", None),
    ("Pollo", "Carne de pollo (eviscerado)", None),
    ("Huevos", "Huevos rosados", None),
    # procesados de alto peso en la canasta y mango (ronda del 24/11/2026; cebolla blanca y lechuga no están en el SISAP de Piura)
    ("Azúcar rubia", "Azucar rubia nacional (granel)", None),
    ("Aceite vegetal", "Aceite clásico botella 900 ml", None),
    ("Leche en tarro", "Leche reconstituida (azul) 395 gr", None),
    ("Mango", "Mango edward", None),
]
# El SISAP cambió la presentación del aceite en 2024 (botella de 1 l → 900 ml): la serie se empalma con la anterior.
# Ambas vienen en S/ por litro y lo habitual compara variaciones en %, así que el tamaño no altera el cálculo.
EMPALME = {"Aceite clásico botella 900 ml": "Aceite clásico botella x 1l"}
# Pesos para el promedio: ponderación de la subclase en el IPC de Lima Metropolitana, base dic. 2021 (INEI, Metodología
# del IPC de Lima Metropolitana, p. 21). No hay pesos publicados por producto ni para Piura. El peso de una subclase se
# reparte en partes iguales entre los productos de esta lista que caen en ella.
SUBCLASES = {
    "011101": ("Arroz de todas clases", 1.210, ["Arroz superior"]),
    "011202": ("Carne de ave", 3.070, ["Pollo"]),
    "011401": ("Leche", 1.303, ["Leche en tarro"]),
    "011404": ("Huevos", 0.706, ["Huevos"]),
    "011501": ("Aceites comestibles", 0.384, ["Aceite vegetal"]),
    "011601": ("Frutas frescas", 2.425, ["Palta", "Plátano seda congo", "Plátano bellaco", "Limón sutil", "Mango"]),
    "011702": ("Hortalizas cultivadas por su fruto", 0.680, ["Choclo", "Tomate", "Vainita"]),
    "011703": ("Hortalizas de raíz o bulbo", 0.619, ["Zanahoria", "Ajo", "Cebolla roja"]),
    "011704": ("Legumbres secas", 0.296, ["Frijol castilla", "Lenteja"]),
    "011706": ("Tubérculos y raíces", 0.936, ["Papa yungay", "Papa amarilla", "Camote morado", "Yuca"]),
    "011801": ("Azúcar", 0.369, ["Azúcar rubia"]),
}
PESO = {n: (c, sub, w / len(ps)) for c, (sub, w, ps) in SUBCLASES.items() for n in ps}
DESCRIPCION = {"Pollo": "Pollo entero eviscerado (limpio, sin vísceras), por kg",
               "Leche en tarro": "Tarro azul de 395 g, por kg; el SISAP la registra como «leche reconstituida», no como evaporada",
               "Aceite vegetal": "Botella de 900 ml (hasta 2023, de 1 litro), por litro"}
TIPOS = {"Mayorista": "mayorista", "Minorista": "minorista"}
POR_UNIDAD = {"Kilogramo", "Litro"}  # ya vienen por kg (o litro); el resto se divide por su equivalencia en kg
ANIOS_HIST, MINIMO_HIST = 4, 3
# Un producto entra al gráfico solo con al menos 2 fechas con precio en cada periodo del año en curso. Con 3 se perdería un
# producto cada vez que el SISAP salta un día: la 2.ª quincena de octubre de 2026 tiene 3 fechas como máximo (24/11/2026)
MINIMO_FECHAS = 2


def leer_exportacion(ruta):
    """Filas (fecha ISO, producto SISAP, tipo, S/ por kg) de una tabla exportada. Cada precio trae en su atributo `rel`
    la fecha, la unidad con su equivalencia en kg, la región, el producto y el mercado."""
    texto = ruta.read_text(encoding="latin-1")
    for rel, valor in re.findall(r'<td class=numero rel="([^"]*)">([^<]*)</td>', texto):
        izq, der = rel.split("~", 1)
        dia, unidad = izq.split(",", 1)
        m = re.match(r"(.*)\(([\d.]+) kg\./lt\.\)$", unidad)
        partes = html.unescape(der).split(",")
        tipo, producto = partes[-1], ",".join(partes[1:-1])
        v = valor.strip().replace(",", "")
        if not v or v == "-" or tipo not in TIPOS or not m:
            continue
        kg = float(m.group(2))
        precio = float(v) if m.group(1) in POR_UNIDAD or kg == 0 else float(v) / kg
        d, mes, a = dia.split("/")
        yield f"{a}-{mes}-{d}", producto, TIPOS[tipo], round(precio, 4)


def actualizar_historial():
    """Suma al historial los precios de las exportaciones de data/raw/sisap/ (solo los productos de PRODUCTOS)."""
    hist = json.loads(HISTORIAL.read_text(encoding="utf-8")) if HISTORIAL.exists() else {"precios": {}}
    sisap = {p[1] for p in PRODUCTOS} | set(EMPALME.values())
    archivos = sorted(ORIGEN.glob("*.xls"))
    for ruta in archivos:
        n = 0
        for dia, prod, tipo, precio in leer_exportacion(ruta):
            if prod in sisap:
                hist["precios"].setdefault(f"{prod}|{tipo}", {})[dia] = precio
                n += 1
        # una consulta muy larga vuelve vacía sin avisar (pasó con todo 2023): mejor detenerse que publicar sin datos
        if n == 0:
            raise SystemExit(f"{ruta.name} no trae precios de los productos elegidos: ¿la consulta volvió vacía? "
                             "Expórtala por tramos más cortos (por ejemplo, por trimestre).")
        print(f"{ruta.name}: {n} precios")
    hist["precios"] = {k: dict(sorted(v.items())) for k, v in sorted(hist["precios"].items())}
    HISTORIAL.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return hist["precios"]


def mes_anterior(a, m):
    return (a - 1, 12) if m == 1 else (a, m - 1)


def ventanas(corte, fechas):
    """Periodo reciente: el mes del último dato, del 1 al día del corte (si tiene menos de 2 fechas, el mes anterior
    completo). Base: la 2.ª quincena (16 a fin de mes) del mes anterior al periodo reciente. Devuelve, como desfase
    de año a año, (año, mes, día de fin) del reciente y (año, mes) de la base."""
    a, m, fin = corte.year, corte.month, corte.day
    if sum(1 for f in fechas if f.year == a and f.month == m and f.day <= fin) < 2:
        a, m = mes_anterior(a, m)
        fin = 31
    return (a, m, fin), mes_anterior(a, m)


def tramo(a, m, d0, d1):
    """Fechas ISO del día d0 al d1 (recortado al fin de mes) del mes m del año a."""
    ultimo = ((date(a + (m == 12), m % 12 + 1, 1)) - timedelta(days=1)).day
    return f"{a}-{m:02d}-{d0:02d}", f"{a}-{m:02d}-{min(d1, ultimo):02d}"


def promedio(serie, desde, hasta):
    v = [p for f, p in serie.items() if desde <= f <= hasta]
    return (sum(v) / len(v), len(v)) if v else (None, 0)


def calcular(precios, corte=None):
    todas = sorted({f for s in precios.values() for f in s})
    corte = date.fromisoformat(corte or todas[-1])
    (ar, mr, fin), (ab, mb) = ventanas(corte, [date.fromisoformat(f) for f in todas])

    def periodos(desfase):
        r = tramo(ar - desfase, mr, 1, fin)
        b = tramo(ab - desfase, mb, 16, 31)
        return b, r

    (b0, r0) = periodos(0)
    salida = {"fuente": "Midagri, SISAP «Precios en ciudades», mercados de Piura", "url": URL, "fecha_corte": corte.isoformat(),
              "base": list(b0), "reciente": list(r0),
              "fechas_base": [f for f in todas if b0[0] <= f <= b0[1]], "fechas_reciente": [f for f in todas if r0[0] <= f <= r0[1]],
              "anios": [ar - k for k in range(ANIOS_HIST, 0, -1)], "productos": []}
    for nombre, sisap, reemplaza in PRODUCTOS:
        cod, sub, peso = PESO[nombre]
        fila = {"nombre": nombre, "sisap": sisap, "reemplaza": reemplaza, "subclase": f"{cod} {sub}", "peso": round(peso, 4),
                **({"descripcion": DESCRIPCION[nombre]} if nombre in DESCRIPCION else {}),
                **({"sisap_antes": EMPALME[sisap]} if sisap in EMPALME else {})}
        for tipo in TIPOS.values():
            serie = {**precios.get(f"{EMPALME.get(sisap)}|{tipo}", {}), **precios.get(f"{sisap}|{tipo}", {})}
            por_anio, precio, base_anio, fechas = {}, {}, {}, {}
            for k in range(ANIOS_HIST + 1):
                b, r = periodos(k)
                pb, nb = promedio(serie, *b)
                pr, nr = promedio(serie, *r)
                precio[ar - k], base_anio[ar - k] = pr, pb
                fechas[str(ar - k)] = [nb, nr]  # fechas con precio en la base y en el periodo reciente de ese año
                por_anio[ar - k] = (pr / pb - 1) * 100 if pb and pr else None
            actual = por_anio.pop(ar)
            actual = round(actual, 1) if actual is not None else None
            hist = [v for v in por_anio.values() if v is not None]
            anterior = precio.get(ar - 1)
            pb = base_anio[ar]
            # años de referencia con variación: los mismos que entran en la mediana de lo habitual
            ref = [a for a, v in por_anio.items() if v is not None]
            habitual = round(statistics.median(hist), 1) if len(hist) >= MINIMO_HIST else None
            fila[tipo] = {
                "base": round(pb, 2) if pb else None, "reciente": round(precio[ar], 2) if precio[ar] else None, "var": actual,
                "anios": {str(a): None if v is None else round(v, 1) for a, v in sorted(por_anio.items())},
                # mediana de los años con dato; con menos de 3 no se considera «habitual»
                "habitual": habitual,
                # precio mediano de cada periodo en los años de lo habitual (soles de cada año, sin ajustar por inflación)
                "habitual_base": round(statistics.median(base_anio[a] for a in ref), 2) if habitual is not None else None,
                "habitual_reciente": round(statistics.median(precio[a] for a in ref), 2) if habitual is not None else None,
                "fechas": fechas,
                # ¿entra al gráfico? al menos MINIMO_FECHAS fechas con precio en cada periodo del año en curso
                "suficiente": min(fechas[str(ar)]) >= MINIMO_FECHAS,
                # precio del periodo reciente frente al mismo periodo del año anterior
                "vs_anio_anterior": round((precio[ar] / anterior - 1) * 100, 1) if precio[ar] and anterior else None,
            }
        salida["productos"].append(fila)
    salida["minimo_fechas"] = MINIMO_FECHAS
    salida["promedio"] = {t: promedio_ponderado(salida["productos"], t) for t in TIPOS.values()}
    return salida


def promedio_ponderado(productos, tipo):
    """Variación promedio y lo habitual promedio, ponderados por PESO, solo con los productos del gráfico que tienen
    lo habitual (así se compara lo mismo con lo mismo)."""
    filas = [(x["peso"], x[tipo]) for x in productos if x[tipo]["suficiente"] and x[tipo]["var"] is not None
             and x[tipo]["habitual"] is not None]
    if not filas:
        return None
    w = sum(p for p, _ in filas)
    return {"var": round(sum(p * f["var"] for p, f in filas) / w, 1),
            "habitual": round(sum(p * f["habitual"] for p, f in filas) / w, 1), "n": len(filas)}


if __name__ == "__main__":
    guardar("precios_sisap.json", calcular(actualizar_historial()))
    import precios_mensual  # series mensuales, historial para la infografía y canasta estimada
    precios_mensual.main()
