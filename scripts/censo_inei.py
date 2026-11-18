"""
Censo 2025 (INEI) por manzana para la pestaña Vulnerabilidad: Ciudad de Piura (Piura, Castilla y Veintiséis de Octubre)
y los centros poblados urbanos de 2000 viviendas o más de los otros distritos de la provincia de Piura.

Se corre a mano, una sola vez (el censo no cambia). Los archivos de origen los entregó el INEI y no van al repositorio
(data/raw/ está en .gitignore):
  - tabulados: data/raw/inei_censo2025/tabulados/CPV 2025 - Pob viv hogar - Mz Agrupadas - Piura.xlsx
  - manzanas:  data/raw/inei_censo2025/cartografia/manzanas/base MANZANA CPV2025.gdb
Librerías: requirements-local.txt (geopandas y pyogrio para leer el .gdb).

Qué hace:
  1. Lee las hojas POBLACION y VIVIENDA y ubica cada columna por el texto completo de su encabezado (filas 5 a 8),
     no por su posición. Descarta las notas al pie (filas sin código de manzana).
  2. Valida que las categorías de cada bloque sumen su total y reporta las diferencias.
  3. Une los tabulados con los polígonos de manzanas (UBIGEO + ZONA + MANZANA) y reporta la tasa de coincidencia.
     Las manzanas que terminan en 9999 (dispersas agrupadas, sin polígono) no van al mapa; sí entran en el total del distrito.
  4. Guarda docs/data/censo_piura.json: GeoJSON en WGS84, geometría simplificada, con numerador y denominador de
     cada indicador por manzana, los totales por distrito y las validaciones.

Uso: python3 scripts/censo_inei.py
"""
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd

from comun import DATOS, RAIZ, guardar, verificar_espacio

CRUDO = RAIZ / "data" / "raw" / "inei_censo2025"
TABULADOS = CRUDO / "tabulados" / "CPV 2025 - Pob viv hogar - Mz Agrupadas - Piura.xlsx"
MANZANAS = CRUDO / "cartografia" / "manzanas" / "base MANZANA CPV2025.gdb"
LIMITES = CRUDO / "cartografia" / "distritos" / "Límites distritales - CPV2025" / "DISTRITOS26.shp"
# Ciudad de Piura: se buscan por nombre en los tabulados (provincia de Piura) y se verifica su ubigeo
DISTRITOS = ["PIURA", "CASTILLA", "VEINTISEIS DE OCTUBRE"]
CODIGO = re.compile(r"\d{11}[0-9A-ZÑ]{3,4}")  # ubigeo (6) + zona (5) + manzana (3, o 4 con letra; 9999 = dispersas)
MINIMO = {"viv": 10, "pob": 30}  # por debajo, la manzana va en gris («Pocos casos») en ese indicador
TOLERANCIA = 1e-5  # simplificación en grados (≈ 1 m en Piura)
# Manzana «extensa»: el INEI la traza de calle a calle e incluye terreno sin viviendas (el campus de la UDEP, el
# aeropuerto, chacras). Con más de 0,05 km² y menos de 1000 viviendas por km², su color cubriría ese terreno: se dibuja
# solo el contorno punteado y no entra en los hexágonos (sí en el total del distrito).
EXTENSA_KM2, EXTENSA_DENSIDAD = 0.05, 1000
DECIMALES = 5      # coordenadas con 5 decimales (≈ 1 m)

# Materiales de paredes que cuentan como precarios (decisión de Germán Vega; sin adobe desde la ronda 16: en la
# Ciudad de Piura es el 1,4 % de las viviendas y es un material tradicional, no improvisado)
PRECARIOS = ["tapia", "quincha (cana con barro)", "piedra con barro", "madera (pona, tornillo, etc)", "triplay/ calamina/ estera"]

# Indicadores: k, rótulo, tipo (denominador de viviendas o de población), numerador y denominador en palabras.
# Los de agua y desagüe se expresan como carencia para que, en todo el mapa, más oscuro sea más vulnerable.
INDICADORES = [
    ("a", "Sin desagüe por red pública", "viv",
     "Viviendas cuyo servicio higiénico no está conectado a la red pública de desagüe (ni dentro de la vivienda ni fuera de ella dentro de la edificación)",
     "Viviendas particulares con ocupantes presentes (total del bloque de servicio higiénico)"),
    ("b", "Sin agua por red pública", "viv",
     "Viviendas cuyo abastecimiento de agua no proviene de la red pública",
     "Viviendas particulares con ocupantes presentes"),
    ("c", "Sin agua todos los días", "viv",
     "Viviendas con agua de red pública o pilón que no la tienen todos los días de la semana",
     "Viviendas con agua de red pública o pilón de uso público (el INEI solo pregunta la frecuencia a ellas)"),
    ("d", "Sin agua las 24 horas", "viv",
     "Viviendas con agua todos los días que la tienen menos de 24 horas al día",
     "Viviendas con agua todos los días"),
    ("e", "Menores de 15 años", "pob",
     "Población de 0 a 14 años (el censo agrupa las edades en 0 a 14, 15 a 29…; no hay un corte en 18)",
     "Población censada"),
    ("f", "De 65 años a más", "pob",
     "Población de 65 años a más",
     "Población censada"),
    ("g", "Sin EsSalud ni seguro privado", "pob",
     "Población sin EsSalud ni seguro privado, como mínimo: población − EsSalud − seguro privado. Una persona puede tener "
     "más de un seguro y el censo no dice cuántas tienen los dos; por eso se da el mínimo y, en cada manzana, el rango posible. "
     "Es una aproximación: no mide informalidad laboral (el censo no pregunta por el empleo)",
     "Población censada"),
    ("h", "Paredes de material precario", "viv",
     "Viviendas con paredes exteriores de tapia, quincha, piedra con barro, madera o triplay, calamina o estera (no incluye adobe)",
     "Viviendas particulares con ocupantes presentes"),
    ("i", "Piso de tierra", "viv",
     "Viviendas con piso de tierra",
     "Viviendas particulares con ocupantes presentes"),
]


# Frases en lenguaje simple: [sujeto, verbo en singular, verbo en plural] para «1 de cada 4 viviendas no tiene…» y
# «6 de cada 10 personas no tienen…». El sujeto incluye la base cuando no es el total (c y d).
FRASES = {
    "a": ["viviendas", "no tiene desagüe por red pública", "no tienen desagüe por red pública"],
    "b": ["viviendas", "no tiene agua por red pública", "no tienen agua por red pública"],
    "c": ["viviendas con agua de red pública o pilón", "no la tiene todos los días", "no la tienen todos los días"],
    "d": ["viviendas con agua todos los días", "no la tiene las 24 horas", "no la tienen las 24 horas"],
    "e": ["personas", "es menor de 15 años", "son menores de 15 años"],
    "f": ["personas", "tiene 65 años o más", "tienen 65 años o más"],
    "g": ["personas", "no tiene EsSalud ni seguro privado", "no tienen EsSalud ni seguro privado"],
    "h": ["viviendas", "tiene paredes de material precario", "tienen paredes de material precario"],
    "i": ["viviendas", "tiene piso de tierra", "tienen piso de tierra"],
}


def norm(s):
    """Texto de encabezado comparable: sin tildes, en minúscula y con espacios simples."""
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def leer_hoja(nombre):
    """Devuelve (datos, encabezados): filas con código de manzana y el encabezado completo de cada columna."""
    crudo = pd.read_excel(TABULADOS, sheet_name=nombre, header=None, dtype=str)
    # el encabezado ocupa las filas 5 a 8 (índices 4 a 7); la fila 9 solo dice «Abs.»
    cab, arrastre, encabezados = crudo.iloc[4:8], [None] * 4, []
    for c in range(crudo.shape[1]):
        for nivel in range(4):
            v = cab.iat[nivel, c]
            if pd.notna(v):  # celda combinada: el texto se arrastra a la derecha hasta que aparece otro del mismo nivel
                arrastre[nivel] = norm(v)
                arrastre[nivel + 1:] = [None] * (3 - nivel)
        encabezados.append(" | ".join(x for x in arrastre if x))
    cuerpo = crudo.iloc[9:]
    es_dato = cuerpo[0].fillna("").str.fullmatch(CODIGO)
    notas = cuerpo[~es_dato & cuerpo[0].notna()]
    datos = cuerpo[es_dato].reset_index(drop=True)
    for c in range(9, crudo.shape[1]):
        datos[c] = pd.to_numeric(datos[c]).fillna(0).astype(int)
    print(f"{nombre}: {len(datos)} filas de datos; {len(notas)} filas de notas al pie descartadas")
    return datos, encabezados


def columna(enc, texto):
    """Índice de la única columna cuyo encabezado completo es `texto`."""
    t = norm(texto)
    hay = [i for i, e in enumerate(enc) if e == t]
    if len(hay) != 1:
        sys.exit(f"Encabezado «{texto}»: {len(hay)} columnas (se esperaba 1). ¿Cambió el formato del archivo?")
    return hay[0]


def categorias(enc, prefijo, total):
    """Columnas de un bloque: las que empiezan con `prefijo`, sin su total ni subtotales."""
    p = norm(prefijo) + " |"
    cols = [i for i, e in enumerate(enc) if e.startswith(p) and i != total and not e.endswith("| total")]
    if not cols:
        sys.exit(f"Bloque «{prefijo}»: sin columnas")
    return cols


def validar(datos, enc, P, V):
    """Comprueba que cada bloque sume su total. Devuelve una lista de {bloque, filas, diferencia}."""
    pob, viv = P["pob"], V["vpop"]
    dv, ev = datos["V"], enc["V"]
    t_red = columna(ev, "Distribución del agua por red pública | Total")
    t_sem = columna(ev, "Disponibilidad de agua por red pública y pilón o pileta de uso público todos los días de la semana | Total")
    t_dia = columna(ev, "Disponibilidad de agua todos los días | Total")
    t_alg = columna(ev, "Disponibilidad de agua algunos días | Total")
    t_sh = columna(ev, "Servicio higiénico está conectado | Total")
    bloques = [  # (nombre, hoja, total, prefijo del bloque)
        ("Sexo", "P", pob, "Población censada | Sexo"),
        ("Grandes grupos de edad", "P", pob, "Población censada | Grandes grupos de edad"),
        ("Material de las paredes", "V", viv, "Material predominante en las paredes exteriores"),
        ("Material de los techos", "V", viv, "Material predominante en los techos"),
        ("Material de los pisos", "V", viv, "Material predominante en los pisos"),
        ("Abastecimiento de agua", "V", viv, "Abastecimiento de agua proveniente"),
        ("Distribución del agua por red pública", "V", t_red, "Distribución del agua por red pública"),
        ("Agua todos los días de la semana", "V", t_sem,
         "Disponibilidad de agua por red pública y pilón o pileta de uso público todos los días de la semana"),
        ("Horas de agua (con agua todos los días)", "V", t_dia, "Disponibilidad de agua todos los días | Rango de horas"),
        ("Días de agua (con agua algunos días)", "V", t_alg, "Disponibilidad de agua algunos días | Número de días"),
        ("Horas de agua (con agua algunos días)", "V", t_alg, "Disponibilidad de agua algunos días | Rango de horas"),
        ("Servicio higiénico", "V", t_sh, "Servicio higiénico está conectado"),
        ("Fuente de energía eléctrica", "V", viv, "Fuente principal de energía eléctrica de la vivienda"),
    ]
    res = []
    for nombre, h, tot, pref in bloques:
        d = datos[h]
        dif = d[categorias(enc[h], pref, tot)].sum(axis=1) - d[tot]
        res.append({"bloque": nombre, "filas_con_diferencia": int((dif != 0).sum()), "diferencia": int(dif.sum())})
    # totales que deben coincidir con una categoría de otro bloque
    col = lambda t: dv[columna(ev, t)]
    cruces = [
        ("Total de distribución = red pública", dv[t_red], col("Abastecimiento de agua proveniente | Red pública")),
        ("Total de agua todos los días de la semana = red pública + pilón", dv[t_sem],
         col("Abastecimiento de agua proveniente | Red pública") + col("Abastecimiento de agua proveniente | Pilón o pileta de uso público")),
        ("Total con agua todos los días = «Sí»", dv[t_dia],
         col("Disponibilidad de agua por red pública y pilón o pileta de uso público todos los días de la semana | Sí")),
        ("Total con agua algunos días = «No»", dv[t_alg],
         col("Disponibilidad de agua por red pública y pilón o pileta de uso público todos los días de la semana | No")),
        ("Total de servicio higiénico = viviendas con ocupantes presentes", dv[t_sh], dv[viv]),
        ("Con al menos un seguro + sin seguro = población", datos["P"][P["al_menos"]] + datos["P"][P["sin_seguro"]], datos["P"][pob]),
    ]
    for nombre, a, b in cruces:
        dif = a - b
        res.append({"bloque": nombre, "filas_con_diferencia": int((dif != 0).sum()), "diferencia": int(dif.sum())})
    return res


def indicadores(dp, dv, P, V):
    """Numerador y denominador de cada indicador por manzana (tabla indexada por código)."""
    r = pd.DataFrame({"codigo": dp[0], "ubigeo": dp[1], "p": dp[P["pob"]], "v": dv[V["vpop"]]})
    T, ES, PR = dp[P["pob"]], dp[P["essalud"]], dp[P["privado"]]
    dobles = dp[P["seguros"]].sum(axis=1) - dp[P["al_menos"]]  # afiliaciones de más (personas con dos o más seguros)
    g_min = (T - ES - PR).clip(lower=0)
    g_max = pd.concat([T - pd.concat([ES, PR], axis=1).max(axis=1), g_min + dobles], axis=1).min(axis=1)
    pares = {
        "a": (dv[V["sh_total"]] - dv[V["red_dentro"]] - dv[V["red_fuera"]], dv[V["sh_total"]]),
        "b": (dv[V["vpop"]] - dv[V["agua_red"]], dv[V["vpop"]]),
        "c": (dv[V["semana_no"]], dv[V["semana_total"]]),
        "d": (dv[V["dia_total"]] - dv[V["dia_24"]], dv[V["dia_total"]]),
        "e": (dp[P["e0_14"]], T),
        "f": (dp[P["e65"]], T),
        "g": (g_min, T),
        "h": (dv[V["precarios"]].sum(axis=1), dv[V["vpop"]]),
        "i": (dv[V["tierra"]], dv[V["vpop"]]),
    }
    for k, (n, d) in pares.items():
        r[k + "_n"], r[k + "_d"] = n.astype(int), d.astype(int)
    r["g_max"] = g_max.astype(int)
    return r


# Dos niveles de sectores: H3 9 (unos 350 m de lado a lado, arista de 201 m) hasta zoom 14 y H3 10 (unos 131 m) en zoom 15.
# Mínimo de la base para dibujar: 30 en el nivel 9; 20 en el 10 (con 30 quedaría oculto el 10 % de las viviendas).
NIVELES = {9: 30, 10: 20}
# API pública de OpenStreetMap y un espejo de la lista del wiki de OSM, por si el principal está cargado
OVERPASS_ESPEJOS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
# Cortes de las 5 clases (en %), fijos a propósito (ronda 17): una sola escala en palabras para servicios y vivienda, y
# los cortes de la ronda 16 para los demográficos. No se mueven aunque una clase quede casi vacía: así se compara entre localidades.
ESCALA = [5, 20, 50, 80]
PALABRAS = ["Casi ninguna", "Pocas", "Menos de la mitad", "Más de la mitad", "Casi todas"]
CORTES = {**{k: ESCALA for k in "abcdhi"}, "e": [15, 20, 25, 30], "f": [4, 8, 12, 16], "g": [30, 50, 65, 80]}
# Clases de la vista de número: afectados por hectárea de manzana (densidad neta, sin calles ni terreno vacío, para que
# no cambie entre niveles). Viviendas y mayores de 65 comparten escala; menores de 15 y sin seguro son muchas más personas.
DENSIDAD = {**{k: [5, 10, 20, 40] for k in "abcdhif"}, "e": [10, 20, 40, 80], "g": [25, 50, 100, 200]}
NOTAS = {"e": "Más alto = más población dependiente (no es una carencia).",
         "f": "Más alto = más población dependiente (no es una carencia)."}
# Localidades además de Ciudad de Piura: centros poblados de los otros distritos de la provincia con al menos estas
# viviendas (ronda 16: con 2000 entran 7; con 500 entraban 31, muchos con 2 a 5 hexágonos). Nombre con tildes para la página.
PROVINCIA = "2001"
LOCALIDAD_MIN = 2000
NOMBRES_LOC = {"CATACAOS": "Catacaos", "TAMBO GRANDE": "Tambogrande", "LA UNION": "La Unión", "LA ARENA": "La Arena",
               "LAS LOMAS": "Las Lomas", "CUCUNGARA": "Cucúngara (Cura Mori)",
               "LA LEGUA-SAN JACINTO (LA LEGUA)": "La Legua–San Jacinto (Catacaos)"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", norm(s)).strip("_")


def hexagonos(unidos, claves, res):
    """Suma numeradores y denominadores de las manzanas (sin las extensas) en hexágonos H3, por el centroide."""
    import h3
    filas = unidos[~unidos["extensa"]].copy()
    cen = filas["geometry"].map(lambda g: g.centroid)
    filas["hex"] = [h3.latlng_to_cell(c.y, c.x, res) for c in cen]
    cols = ["p", "v", "g_max", "km2"] + [k + s for k in claves for s in ("_n", "_d")]
    suma = filas.groupby("hex")[cols].sum()
    suma["m"] = filas.groupby("hex").size()
    suma["u"] = filas.groupby("hex")["ubigeo"].agg(lambda s: s.value_counts().index[0])  # distrito con más manzanas
    feats = []
    for cell, r in suma.iterrows():
        anillo = [[round(lng, DECIMALES), round(lat, DECIMALES)] for lat, lng in h3.cell_to_boundary(cell)]
        props = {"u": r["u"], "m": int(r["m"]), "p": int(r["p"]), "v": int(r["v"]), "ha": round(float(r["km2"]) * 100, 2)}  # ha de manzanas
        for k in claves:
            props[k] = [int(r[k + "_n"]), int(r[k + "_d"])] + ([int(r["g_max"])] if k == "g" else [])
        lat, lng = h3.cell_to_latlng(cell)
        feats.append({"type": "Feature", "id": cell, "properties": props, "centro": [round(lat, 5), round(lng, 5)],
                      "geometry": {"type": "Polygon", "coordinates": [anillo + anillo[:1]]}})
    return feats


def consulta_overpass(q, cache):
    """Respuesta de Overpass para la consulta q. Se guarda en data/raw/osm/ (fuera del repositorio): al volver a correr el
    script no se consulta otra vez. Si el servidor principal está cargado (502 o 504), se prueba un espejo público."""
    import urllib.parse
    import urllib.request
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["elements"]
    for intento, url in enumerate(OVERPASS_ESPEJOS * 2, 1):
        pedido = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(),
                                        headers={"User-Agent": "observatorio-fen-piura/1.0"})  # rechaza agentes que imitan un navegador (406)
        try:
            with urllib.request.urlopen(pedido, timeout=240) as r:
                texto = r.read().decode("utf-8")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(texto, encoding="utf-8")
            return json.loads(texto)["elements"]
        except OSError as e:
            if intento == 2 * len(OVERPASS_ESPEJOS):
                raise
            print(f"  Overpass ({url.split('/')[2]}) falló ({e}); se prueba de nuevo en {20 * intento} s")
            time.sleep(20 * intento)


def nombres_osm(hexs, loc):
    """Nombre reconocible de cada hexágono con OpenStreetMap (una sola consulta a Overpass por localidad):
    1) zona residencial con nombre que contiene el centro; 2) barrio o caserío a menos de 400 m; 3) «cerca de [vía]» a menos
    de 300 m. Si nada aplica, queda vacío (la página dice «sector sin nombre»)."""
    from shapely.geometry import LineString, Point, Polygon
    la = [h["centro"][0] for h in hexs]
    lo = [h["centro"][1] for h in hexs]
    caja = f"{min(la) - .01},{min(lo) - .01},{max(la) + .01},{max(lo) + .01}"
    q = (f'[out:json][timeout:180];(node["place"~"^(neighbourhood|suburb|quarter|hamlet|village|isolated_dwelling)$"]["name"]({caja});'
         f'way["landuse"="residential"]["name"]({caja});'
         f'way["highway"~"^(trunk|primary|secondary|tertiary)$"]["name"]({caja}););out geom;')
    el = consulta_overpass(q, CRUDO.parent / "osm" / f"overpass_{loc}.json")
    zonas = [(Polygon([(p["lon"], p["lat"]) for p in e["geometry"]]), e["tags"]["name"]) for e in el
             if e["type"] == "way" and e["tags"].get("landuse") == "residential" and len(e.get("geometry", [])) >= 4]
    lugares = [(Point(e["lon"], e["lat"]), e["tags"]["name"]) for e in el if e["type"] == "node"]
    vias = [(LineString([(p["lon"], p["lat"]) for p in e["geometry"]]), e["tags"]["name"]) for e in el
            if e["type"] == "way" and "highway" in e["tags"] and len(e.get("geometry", [])) >= 2]
    print(f"OpenStreetMap: {len(zonas)} zonas residenciales, {len(lugares)} barrios o caseríos y {len(vias)} vías con nombre")
    grado = 111_320  # metros por grado (aprox.)
    for h in hexs:
        c = Point(h["centro"][1], h["centro"][0])
        z = [n for p, n in zonas if p.is_valid and p.contains(c)]
        cerca = lambda xs: min(((g.distance(c) * grado, n) for g, n in xs), default=(1e9, None))
        d1, n1 = cerca(lugares)
        d2, n2 = cerca(vias)
        # ronda 18: «Sector [nombre]» si el centro cae en la zona; «Sector cerca de [nombre]» si es un barrio o vía cercana
        h["properties"]["n"] = (f"Sector {limpiar_nombre(z[0])}" if z else f"Sector cerca de {limpiar_nombre(n1)}" if d1 < 400
                                else f"Sector cerca de {limpiar_nombre(n2)}" if d2 < 300 else "")
    return hexs


MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e", "en"}


def limpiar_nombre(s):
    """Nombres uniformes: «Asentamiento Humano», «AA.HH.», «AAHH» y «A.H.» pasan a «A. H.»; sin espacios dobles; un nombre
    todo en mayúsculas pasa a mayúscula inicial (las palabras cortas, en minúscula)."""
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(?i)^(asentamiento\s+humano|a\.?\s?a\.?\s?h\.?\s?h\.?|a\.\s?h\.)\s*", "A. H. ", s)
    resto = s[6:] if s.startswith("A. H. ") else s
    if resto.isupper() and len(resto.split()) > 1:
        palabras = resto.lower().split()
        resto = " ".join(w if j and w in MINUSCULAS else w[:1].upper() + w[1:] for j, w in enumerate(palabras))
        s = ("A. H. " if s.startswith("A. H. ") else "") + resto
    return s


def redondear(c):
    return [redondear(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], DECIMALES), round(c[1], DECIMALES)]


def resumen(localidades, distritos):
    """Resumen mínimo para la portada (ronda 19): así la portada no carga el censo entero. La ciudad de Piura y, por distrito
    (ronda 20), las viviendas sin desagüe por red pública: [nombre, sin desagüe, viviendas]."""
    m = localidades[0]
    return {"fuente": "INEI, Censos Nacionales 2025, tabulados por manzana entregados el 13/11/2026",
            "url": "https://www.inei.gob.pe/", "fecha_corte": "2026-11-13", "nombre": m["nombre"],
            "viviendas": m["v"], "sin_desague": m["a"],
            "distritos_sin_desague": [[d["nombre"], *d["a"]] for d in distritos.values()]}


def main():
    verificar_espacio()
    import geopandas  # falla aquí, con un mensaje claro, si faltan las librerías locales
    import pyogrio
    import shapely
    from shapely.geometry import mapping

    datos, enc = {}, {}
    for h, nombre in (("P", "POBLACION"), ("V", "VIVIENDA")):
        datos[h], enc[h] = leer_hoja(nombre)
    if (datos["P"][0] != datos["V"][0]).any():
        sys.exit("Las hojas POBLACION y VIVIENDA no traen las mismas manzanas en el mismo orden")

    # Provincia de Piura (ubigeo 2001xx). Distritos de Ciudad de Piura: ubigeo verificado en los datos, no supuesto
    dp0 = datos["P"]
    nombres = {norm(d).upper(): d for d in DISTRITOS}
    ubis = (dp0[(dp0[3].map(norm) == "piura") & dp0[4].map(lambda x: norm(x).upper() in nombres)]
            .groupby(1)[4].first().to_dict())
    if len(ubis) != len(DISTRITOS):
        sys.exit(f"Se esperaban {len(DISTRITOS)} distritos y se encontraron {ubis}")
    print("Ubigeos de Ciudad de Piura:", ubis)
    sel = dp0[1].str.startswith(PROVINCIA)
    for h in datos:
        datos[h] = datos[h][sel].reset_index(drop=True)
    ep, ev = enc["P"], enc["V"]
    cP = lambda t: columna(ep, t)
    cV = lambda t: columna(ev, t)
    seg = "Población censada | Afiliada a algún seguro de salud | "
    P = {"pob": cP("Población censada | Total"),
         "e0_14": cP("Población censada | Grandes grupos de edad | De 0 a 14"),
         "e65": cP("Población censada | Grandes grupos de edad | De 65 a más"),
         "al_menos": cP(seg + "Cuenta con al menos un tipo de seguro"),
         "sin_seguro": cP(seg + "No cuenta con seguro de salud"),
         "essalud": cP(seg + "ESSALUD"), "privado": cP(seg + "Seguro privado de salud"),
         "seguros": [cP(seg + s) for s in ("Seguro Integral de Salud (SIS)", "ESSALUD", "Seguro de Fuerzas Armadas o Policiales",
                                           "Seguro privado de salud", "Otro seguro")]}
    par = "Material predominante en las paredes exteriores | "
    sem = "Disponibilidad de agua por red pública y pilón o pileta de uso público todos los días de la semana | "
    sh = "Servicio higiénico está conectado | "
    V = {"vpop": cV(par + "Total de viviendas particulares con ocupantes presentes"),
         "precarios": [cV(par + m) for m in PRECARIOS],
         "tierra": cV("Material predominante en los pisos | Tierra"),
         "agua_red": cV("Abastecimiento de agua proveniente | Red pública"),
         "semana_total": cV(sem + "Total"), "semana_no": cV(sem + "No"),
         "dia_total": cV("Disponibilidad de agua todos los días | Total"),
         "dia_24": cV("Disponibilidad de agua todos los días | Rango de horas | 24 horas"),
         "sh_total": cV(sh + "Total"), "red_dentro": cV(sh + "Red pública de desagüe dentro de la vivienda"),
         "red_fuera": cV(sh + "Red pública de desagüe fuera de la vivienda pero dentro de la edificación")}

    validaciones = validar(datos, enc, P, V)
    for v in validaciones:
        print(f"  {'OK ' if not v['filas_con_diferencia'] else 'DIF'} {v['bloque']}: "
              f"{v['filas_con_diferencia']} filas con diferencia (suma {v['diferencia']})")
    sP = datos["P"][P["seguros"]].sum().sum() - datos["P"][P["al_menos"]].sum()
    print(f"Seguros: la suma de los tipos supera a «al menos un seguro» en {sP} (no son excluyentes)")

    ind = indicadores(datos["P"], datos["V"], P, V)
    ind["ccpp"] = datos["P"][6].values
    ind["nombre_ccpp"] = datos["P"][5].values
    # Localidad de cada manzana: Ciudad de Piura (los 3 distritos completos) o un centro poblado urbano de otro distrito
    # de la provincia con LOCALIDAD_MIN viviendas o más (las dispersas de ese centro poblado cuentan en su total)
    clave = ind["ubigeo"] + "-" + ind["ccpp"]
    tam = ind[~ind["ubigeo"].isin(ubis)].groupby(clave)["v"].sum()
    elegidas = sorted(tam[tam >= LOCALIDAD_MIN].index, key=lambda k: -tam[k])
    nombres_ccpp = ind.groupby(clave)["nombre_ccpp"].first()
    if set(nombres_ccpp[elegidas]) != set(NOMBRES_LOC):
        sys.exit(f"Centros poblados con {LOCALIDAD_MIN} viviendas o más: {dict(nombres_ccpp[elegidas])}; revisa NOMBRES_LOC")
    ind["loc"] = None
    ind.loc[ind["ubigeo"].isin(ubis), "loc"] = "metro"
    for k in elegidas:
        ind.loc[clave == k, "loc"] = slug(NOMBRES_LOC[nombres_ccpp[k]])
    ind = ind[ind["loc"].notna()].reset_index(drop=True)
    print("Localidades:", {k: int(tam[k]) for k in elegidas})
    dispersa = ind["codigo"].str.endswith("9999")
    print(f"Manzanas: {len(ind)}; dispersas agrupadas (9999): {dispersa.sum()} con {ind.loc[dispersa, 'p'].sum()} habitantes "
          f"y {ind.loc[dispersa, 'v'].sum()} viviendas")

    # Cartografía de los distritos con alguna localidad; llave UBIGEO + ZONA + MANZANA
    info = pyogrio.read_info(MANZANAS)
    capa = pyogrio.list_layers(MANZANAS)[0][0]
    print(f"Cartografía: capa {capa}, {info['features']} polígonos, {info['crs']}")
    lista = ",".join(f"'{u}'" for u in sorted(ind["ubigeo"].unique()))
    mz = pyogrio.read_dataframe(MANZANAS, layer=capa, where=f"UBIGEO IN ({lista})", columns=["UBIGEO", "ZONA", "MANZANA"])
    if mz.crs is None or mz.crs.to_epsg() != 4326:
        mz = mz.to_crs(4326)
    mz["codigo"] = mz["UBIGEO"] + mz["ZONA"] + mz["MANZANA"]
    if mz["codigo"].duplicated().any():
        sys.exit(f"Códigos de manzana repetidos en la cartografía: {mz.loc[mz['codigo'].duplicated(), 'codigo'].tolist()[:10]}")
    tab = ind[~dispersa]
    unidos = tab.merge(mz[["codigo", "geometry"]], on="codigo", how="left")
    sin_poligono = unidos.loc[unidos["geometry"].isna(), "codigo"].tolist()
    metro_cod = set(mz.loc[mz["UBIGEO"].isin(ubis), "codigo"])
    poligonos_sin_tabulado = len(metro_cod - set(tab["codigo"]))
    tasa = 1 - len(sin_poligono) / len(tab)
    print(f"Unión: {len(tab) - len(sin_poligono)} de {len(tab)} manzanas con polígono ({100 * tasa:.2f} %); "
          f"sin polígono: {sin_poligono[:20]}; polígonos de Ciudad de Piura sin tabulado: {poligonos_sin_tabulado}")

    unidos = unidos[unidos["geometry"].notna()].reset_index(drop=True)
    # área real en km² (UTM 17 S, metros), con la geometría sin simplificar
    unidos["km2"] = geopandas.GeoSeries(unidos["geometry"].values, crs=4326).to_crs(32717).area.values / 1e6
    unidos["extensa"] = (unidos["km2"] > EXTENSA_KM2) & (unidos["v"] < EXTENSA_DENSIDAD * unidos["km2"])
    ext = unidos["extensa"] & (unidos["loc"] == "metro")
    print(f"Manzanas extensas en Ciudad de Piura (> {EXTENSA_KM2} km² y < {EXTENSA_DENSIDAD} viv/km²): {int(ext.sum())}; "
          f"en las otras localidades: {int((unidos['extensa'] & ~ext).sum())}")
    geoms = shapely.set_precision(shapely.simplify(unidos["geometry"].values, TOLERANCIA, preserve_topology=True), 10 ** -DECIMALES)
    vacias = shapely.is_empty(geoms).sum()
    if vacias:
        sys.exit(f"{vacias} manzanas quedaron vacías al simplificar: baja TOLERANCIA")

    # Límites de los tres distritos de Ciudad de Piura (INEI, CPV 2025): solo el contorno, para orientarse en el mapa
    lm = ",".join(f"'{u}'" for u in ubis)
    dist = pyogrio.read_dataframe(LIMITES, where=f"UBIGEO IN ({lm})", columns=["UBIGEO"])
    if dist.crs is None or dist.crs.to_epsg() != 4326:
        dist = dist.to_crs(4326)
    if sorted(dist["UBIGEO"]) != sorted(ubis):
        sys.exit(f"Límites distritales: se encontraron {sorted(dist['UBIGEO'])}")
    limites = [{"type": "Feature", "id": u, "properties": {}, "geometry": (lambda g: {"type": g["type"], "coordinates": redondear(g["coordinates"])})(
        mapping(shapely.set_precision(shapely.simplify(geo, 1e-4, preserve_topology=True), 10 ** -DECIMALES)))}
        for u, geo in zip(dist["UBIGEO"], dist.geometry)]

    claves = [k for k, *_ in INDICADORES]
    unidos["feat"] = [{"type": "Feature", "id": r["codigo"],
                       "properties": {"u": r["ubigeo"], "p": int(r["p"]), "v": int(r["v"]), "ha": round(float(r["km2"]) * 100, 3),
                                      **({"km2": round(float(r["km2"]), 3)} if r["extensa"] else {}),  # solo en las extensas
                                      **{k: [int(r[k + "_n"]), int(r[k + "_d"])] + ([int(r["g_max"])] if k == "g" else []) for k in claves}},
                       "geometry": (lambda g: {"type": g["type"], "coordinates": redondear(g["coordinates"])})(mapping(geo))}
                      for (_, r), geo in zip(unidos.iterrows(), geoms)]

    def totales(d):
        """Suma de numeradores y denominadores (con las dispersas), viviendas, población y manzanas del mapa."""
        disp = d["codigo"].str.endswith("9999")
        t = {"manzanas": int((~disp & d["codigo"].isin(unidos["codigo"])).sum()),
             "dispersas": {"grupos": int(disp.sum()), "p": int(d.loc[disp, "p"].sum()), "v": int(d.loc[disp, "v"].sum())},
             "p": int(d["p"].sum()), "v": int(d["v"].sum()), **{k: [int(d[k + "_n"].sum()), int(d[k + "_d"].sum())] for k in claves}}
        t["g"].append(int(d["g_max"].sum()))
        return t

    distritos = {u: {"nombre": ubis[u], **totales(d)} for u, d in ind[ind["loc"] == "metro"].groupby("ubigeo")}
    localidades, archivos = [], []
    for loc in ["metro"] + [slug(NOMBRES_LOC[nombres_ccpp[k]]) for k in elegidas]:
        u = unidos[unidos["loc"] == loc]
        hexs = nombres_osm(hexagonos(u, claves, 9), loc)  # solo el nivel 9 lleva nombres: de ahí salen los sectores críticos
        hexs10 = hexagonos(u, claves, 10)
        oculto = {res: 100 * sum(h["properties"]["v"] for h in hs if h["properties"]["a"][1] < NIVELES[res]) / max(1, int(u["v"].sum()))
                  for res, hs in ((9, hexs), (10, hexs10))}
        nombre = "Ciudad de Piura" if loc == "metro" else next(v for v in NOMBRES_LOC.values() if slug(v) == loc)
        print(f"{nombre}: {len(u)} manzanas, {len(hexs)} hexágonos de 350 m (ocultos {oculto[9]:.1f} % de las viviendas) "
              f"y {len(hexs10)} de 130 m (ocultos {oculto[10]:.1f} %); con nombre: {sum(1 for h in hexs if h['properties']['n'])}")
        b = shapely.bounds(shapely.union_all(u["geometry"].values))
        fila = {"id": loc, "nombre": nombre, "caja": [[round(b[1], 4), round(b[0], 4)], [round(b[3], 4), round(b[2], 4)]],
                **totales(ind[ind["loc"] == loc])}
        if loc == "metro":
            metro_hex = hexs
            guardar("censo_hex10.json", {"resolucion": 10, "minimo": NIVELES[10], "features": hexs10})
            guardar("censo_manzanas.json", {"type": "FeatureCollection", "features": u["feat"].tolist()})
            archivos += ["censo_hex10.json", "censo_manzanas.json"]
        else:
            fila["archivo"] = f"censo_loc_{loc}.json"
            # sin el nivel de 130 m (ronda 17): en pueblos menos densos ocultaba hasta el 42 % de las viviendas
            guardar(fila["archivo"], {"hexagonos": {"resolucion": 9, "minimo": NIVELES[9], "features": hexs},
                                      "manzanas": {"type": "FeatureCollection", "features": u["feat"].tolist()}})
            archivos.append(fila["archivo"])
        localidades.append(fila)
        time.sleep(2)  # una consulta a Overpass por localidad, sin apuro

    # La base (se carga al abrir la pestaña): indicadores, Ciudad de Piura con sus hexágonos de 350 m y la tabla de
    # localidades. Lo demás (hexágonos de 130 m, manzanas y cada localidad) se carga cuando hace falta.
    guardar("censo_piura.json", {
        "fuente": "INEI, Censos Nacionales 2025, tabulados por manzana entregados el 13/11/2026",
        "url": "https://www.inei.gob.pe/",
        "fecha_corte": "2026-11-13",
        "ambito": "Provincia de Piura: Ciudad de Piura (distritos de Piura, Castilla y Veintiséis de Octubre) y los centros poblados "
                  f"urbanos de {LOCALIDAD_MIN} viviendas o más de los otros distritos",
        "minimo": MINIMO,
        "indicadores": [{"k": k, "rotulo": rot, "tipo": t, "numerador": n, "denominador": d, "frase": FRASES[k],
                         "cortes": CORTES[k], "densidad": DENSIDAD[k], **({"palabras": PALABRAS} if CORTES[k] is ESCALA else {}),
                         **({"nota": NOTAS[k]} if k in NOTAS else {})} for k, rot, t, n, d in INDICADORES],
        "hexagonos": {"resolucion": 9, "minimo": NIVELES[9], "nombres": "© colaboradores de OpenStreetMap (ODbL)", "features": metro_hex},
        "validaciones": validaciones,
        "coincidencia": {"tabuladas": len(tab), "con_poligono": len(tab) - len(sin_poligono), "tasa": round(tasa, 4),
                         "sin_poligono": sin_poligono, "poligonos_sin_tabulado": poligonos_sin_tabulado},
        "distritos": distritos,
        "localidades": localidades,
        "limites": limites,
    })
    guardar("censo_resumen.json", resumen(localidades, distritos))
    for nombre in ["censo_piura.json"] + archivos:
        tam_mb = (DATOS / nombre).stat().st_size / 2**20
        print(f"Tamaño de {nombre}: {tam_mb:.2f} MB" + (" (pasa de 3 MB)" if tam_mb > 3 else ""))

if __name__ == "__main__":
    main()
