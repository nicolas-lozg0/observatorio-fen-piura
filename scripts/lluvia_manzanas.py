"""
Lluvia de CHIRPS v3 (mensual, celdas de 0,05°) unida a las manzanas del Censo 2025 de todo el departamento de Piura.

Se corre a mano (los rásters y el censo no van al repositorio: data/raw/ y data/procesado/ están en .gitignore):
  - rásters: data/raw/chirps/**/PIURA_{AÑO}_{MES}.tif (MES en palabras, ENERO, o en número, 01). Archivos nuevos se
    leen sin cambiar el código: el año y el mes salen del nombre.
  - censo: los mismos tabulados y cartografía de scripts/censo_inei.py.

Qué hace:
  1. Lee los GeoTIFF con tifffile (sin GDAL), comprueba que todos tengan la misma grilla y lee el tipo de ráster
     (PixelIsArea o PixelIsPoint) de las GeoKeys para ubicar bien la esquina de cada celda.
  2. Asigna a cada manzana la celda que contiene su centroide (punto interior si el centroide cae fuera del polígono);
     si esa celda no tiene dato, la celda válida más cercana (flag_celda_vecina = 1). Calcula también la interpolación
     bilineal (_bil) como prueba de robustez.
  3. Guarda las bases para el análisis econométrico (data/procesado/, no se publican), el diccionario, la capa liviana
     de la página (docs/data/lluvia_celdas.geojson), un mapa de control y una tabla de control (privado/).

Uso: python3 scripts/lluvia_manzanas.py [--meses 1,2,3,4]
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import censo_inei as censo
from comun import PERU, RAIZ, guardar, verificar_espacio

RASTERS = RAIZ / "data" / "raw" / "chirps"
SALIDA = RAIZ / "data" / "procesado"
PRIVADO = RAIZ / "privado"
DEPARTAMENTO = "20"
NODATA = -9999
NORMAL = (1991, 2020)  # periodo de la normal para las anomalías (cuando llegue la serie completa)
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre", "noviembre",
         "diciembre"]
ABREV = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]
ARCHIVO = re.compile(r"PIURA_(\d{4})_([A-Za-zÑñ]+|\d{1,2})\.tif$", re.I)
KX_LAT = 110.57  # km por grado de latitud; el de longitud se corrige por cos(latitud)

# Fuente que se cita en la base y en la página
FUENTE = ("CHIRPS v3.0 mensual (Climate Hazards Center, UC Santa Barbara), recortado al departamento de Piura; "
          "base entregada por la UDEP el 18/11/2026")

# Nombres de los indicadores del censo en la base (las letras son las de censo_inei.INDICADORES)
NOMBRES = {"a": "sin_desague", "b": "sin_agua_red", "c": "agua_no_diaria", "d": "agua_menos_24h", "e": "menores_15",
           "f": "mayores_65", "g": "sin_essalud_privado", "h": "paredes_precarias", "i": "piso_tierra"}

# Puntos de control: centro poblado principal (el de más manzanas) de cada distrito, ubicado con la cartografía
CONTROL = [("Piura centro", "200101"), ("Castilla", "200104"), ("Veintiséis de Octubre", "200115"),
           ("Catacaos", "200105"), ("Tambogrande", "200114"), ("Sullana", "200601"), ("Paita", "200501"),
           ("Huancabamba", "200301"), ("Chulucanas", "200401")]

# Referencias de estaciones (mm), copiadas de documentos publicados; la estación no tiene coordenadas en esas fuentes,
# así que se compara con la celda del centro poblado.
# INDECI/OEA (2009), Mapa de peligros de la ciudad de Piura, vol. I, cuadro 12 (estación Miraflores, Senamhi), p. 88:
#   https://sigrid.cenepred.gob.pe/docs/PARA%20PUBLICAR/INDECI/INFORME%20PRINCIPAL%20DEL%20%20ESTUDIO%20MAPA%20DE%20PELIGROS%20DE%20PIURA%20(VOLUMEN%20I).pdf
# Proyecto Especial Chira-Piura, Informe hidrometeorológico de marzo 2017 (N.° 3) y abril 2017 (N.° 4):
#   https://cdn.www.gob.pe/uploads/document/file/3274125/ y .../3274124/
ESTACIONES = [
    ("Miraflores (Castilla)", "Castilla", 1983, [324.5, 161.7, 427.1, 778.4], "INDECI/OEA, cuadro 12"),
    ("Miraflores (Castilla)", "Castilla", 1998, [769.2, 501.8, 479.9, 90.9], "INDECI/OEA, cuadro 12"),
    ("Miraflores (Castilla)", "Castilla", 2017, [None, None, 500.8, 7.1], "PECHP, informes de marzo y abril 2017"),
    ("Chulucanas", "Chulucanas", 2017, [None, None, 1154.6, 73.6], "PECHP, informes de marzo y abril 2017"),
    ("Tambogrande", "Tambogrande", 2017, [None, None, 1149.8, 107.7], "PECHP, informes de marzo y abril 2017"),
    ("Sullana", "Sullana", 2017, [None, None, 423.4, 11.8], "PECHP, informes de marzo y abril 2017"),
]


# --------------------------------------------------------------------------------------------------------------------
# Rásters
# --------------------------------------------------------------------------------------------------------------------
def mes_de(texto):
    t = censo.norm(texto)
    if t.isdigit():
        return int(t)
    t = "setiembre" if t == "septiembre" else t
    if t not in MESES:
        sys.exit(f"Mes «{texto}» no reconocido en el nombre del archivo")
    return MESES.index(t) + 1


def leer_tif(ruta):
    """Devuelve (matriz, georreferencia) de un GeoTIFF de una banda, leyendo las etiquetas GeoTIFF a mano."""
    import tifffile
    with tifffile.TiffFile(ruta) as t:
        tags = t.pages[0].tags
        a = t.asarray().astype("float64")
        escala = tags[33550].value      # ModelPixelScale: (dx, dy, dz)
        tie = tags[33922].value         # ModelTiepoint: (I, J, K, X, Y, Z)
        claves = tags[34735].value      # GeoKeyDirectory: encabezado de 4 y luego claves de 4 en 4
        nodata = float(tags[42113].value) if 42113 in tags else None
        origen = tags[269].value if 269 in tags else ""
    geokeys = {claves[k]: claves[k + 3] for k in range(4, len(claves), 4)}
    tipo = geokeys.get(1025, 1)         # GTRasterTypeGeoKey: 1 = PixelIsArea, 2 = PixelIsPoint
    dx, dy = escala[0], escala[1]
    oeste, norte = tie[3] - tie[0] * dx, tie[4] + tie[1] * dy
    if tipo == 2:                       # el punto de amarre es el centro de la celda: la esquina está media celda antes
        oeste, norte = oeste - dx / 2, norte + dy / 2
    if geokeys.get(2048) != 4326:
        sys.exit(f"{ruta.name}: sistema de referencia {geokeys.get(2048)}, se esperaba EPSG:4326 (WGS84)")
    a[a == nodata] = np.nan
    return a, {"oeste": round(oeste, 6), "norte": round(norte, 6), "dx": round(dx, 9), "dy": round(dy, 9),
               "filas": a.shape[0], "cols": a.shape[1], "tipo": tipo, "origen": origen}


def cargar_rasters(meses):
    """Lee todos los rásters, comprueba que compartan la grilla y devuelve (lluvia[año][mes], grilla, años completos)."""
    archivos = sorted(p for p in RASTERS.rglob("*.tif") if ARCHIVO.search(p.name))
    if not archivos:
        sys.exit(f"No hay archivos PIURA_AÑO_MES.tif en {RASTERS}")
    lluvia, grilla = {}, None
    for p in archivos:
        anio, mes = int(ARCHIVO.search(p.name)[1]), mes_de(ARCHIVO.search(p.name)[2])
        a, g = leer_tif(p)
        # el archivo de origen de CHIRPS queda en la etiqueta del TIFF: debe coincidir con el año y el mes del nombre
        if g["origen"] and f"{anio}.{mes:02d}" not in g["origen"]:
            sys.exit(f"{p.name}: la etiqueta dice que viene de {g['origen']}")
        g.pop("origen")
        if grilla is None:
            grilla = g
        elif g != grilla:
            sys.exit(f"{p.name}: grilla distinta {g} frente a {grilla}")
        lluvia.setdefault(anio, {})[mes] = a
    validas = [~np.isnan(m) for d in lluvia.values() for m in d.values()]
    if any((v != validas[0]).any() for v in validas):
        sys.exit("Las celdas con dato no son las mismas en todos los rásters")
    completos = sorted(y for y, d in lluvia.items() if all(m in d for m in meses))
    incompletos = sorted(set(lluvia) - set(completos))
    print(f"Rásters: {len(archivos)} archivos, años completos para la ventana {meses}: {completos}"
          + (f"; incompletos (no se usan): {incompletos}" if incompletos else ""))
    print(f"Grilla: {grilla['filas']} × {grilla['cols']} celdas de {grilla['dx']}°, esquina noroeste ({grilla['oeste']}, "
          f"{grilla['norte']}), {'PixelIsArea' if grilla['tipo'] == 1 else 'PixelIsPoint'}; celdas con dato: {validas[0].sum()}")
    return lluvia, grilla, completos, validas[0]


def nombre_ventana(meses):
    return "".join(MESES[m - 1][0] for m in meses)  # 1-4 → «efma»


def variables_celda(lluvia, completos, meses, v):
    """Matrices de lluvia por variable: mensual, acumulado de la ventana, mes más lluvioso y su número."""
    out = {}
    for y in completos:
        pila = np.stack([lluvia[y][m] for m in meses])
        for k, m in enumerate(meses):
            out[f"lluvia_{ABREV[m - 1]}_{y}"] = pila[k]
        out[f"lluvia_{v}_{y}"] = pila.sum(axis=0)
        out[f"lluvia_max_{y}"] = pila.max(axis=0)
        out[f"mes_max_{y}"] = np.where(np.isnan(pila[0]), np.nan, np.array(meses)[np.nan_to_num(pila, nan=-1).argmax(axis=0)])
    # Anomalías frente a la normal: solo si están todos los años del periodo NORMAL (llegará con la serie 1981-2025)
    normal = [y for y in range(NORMAL[0], NORMAL[1] + 1)]
    if all(y in completos for y in normal):
        norm_v = np.mean([out[f"lluvia_{v}_{y}"] for y in normal], axis=0)
        out[f"normal_{v}_{NORMAL[0]}_{NORMAL[1]}"] = norm_v
        for y in completos:
            out[f"anom_{v}_{y}"] = out[f"lluvia_{v}_{y}"] - norm_v                      # mm sobre la normal
            out[f"anomp_{v}_{y}"] = 100 * out[f"lluvia_{v}_{y}"] / np.where(norm_v > 0, norm_v, np.nan)  # % de la normal
    else:
        print(f"Anomalías: pendientes (faltan años del periodo {NORMAL[0]}-{NORMAL[1]})")
    return out


# --------------------------------------------------------------------------------------------------------------------
# Unión de puntos con la grilla
# --------------------------------------------------------------------------------------------------------------------
def ubicar(lon, lat, g, valida):
    """Celda de cada punto, distancia al borde de esa celda y, si no tiene dato, la celda válida más cercana."""
    col = np.floor((lon - g["oeste"]) / g["dx"]).astype(int)
    fila = np.floor((g["norte"] - lat) / g["dy"]).astype(int)
    dentro = (fila >= 0) & (fila < g["filas"]) & (col >= 0) & (col < g["cols"])
    kx = 111.32 * np.cos(np.radians(lat))
    o = g["oeste"] + col * g["dx"]
    n = g["norte"] - fila * g["dy"]
    borde = np.minimum(np.minimum(lon - o, o + g["dx"] - lon) * kx, np.minimum(n - lat, lat - (n - g["dy"])) * KX_LAT)
    con_dato = dentro.copy()
    con_dato[dentro] = valida[fila[dentro], col[dentro]]
    vecina = ~con_dato
    dist = np.zeros(len(lon))
    if vecina.any():
        fi, ci = np.nonzero(valida)
        cx = g["oeste"] + (ci + 0.5) * g["dx"]
        cy = g["norte"] - (fi + 0.5) * g["dy"]
        # distancia del punto al rectángulo de cada celda válida (0 si está dentro), en km
        ddx = np.maximum(np.abs(lon[vecina, None] - cx[None]) - g["dx"] / 2, 0) * kx[vecina, None]
        ddy = np.maximum(np.abs(lat[vecina, None] - cy[None]) - g["dy"] / 2, 0) * KX_LAT
        d = np.hypot(ddx, ddy)
        k = d.argmin(axis=1)
        fila[vecina], col[vecina], dist[vecina] = fi[k], ci[k], d[np.arange(len(k)), k]
    return fila, col, np.where(dentro, borde, np.nan), vecina, dist


def bilineal(m, lon, lat, g):
    """Interpolación bilineal entre los centros de las 4 celdas vecinas; sin dato en alguna, se reparte el peso entre
    las que tienen dato."""
    fx = (lon - g["oeste"]) / g["dx"] - 0.5
    fy = (g["norte"] - lat) / g["dy"] - 0.5
    j0, i0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - j0, fy - i0
    suma, peso = np.zeros(len(lon)), np.zeros(len(lon))
    for di, dj, w in ((0, 0, (1 - ty) * (1 - tx)), (0, 1, (1 - ty) * tx), (1, 0, ty * (1 - tx)), (1, 1, ty * tx)):
        i, j = i0 + di, j0 + dj
        ok = (i >= 0) & (i < g["filas"]) & (j >= 0) & (j < g["cols"])
        val = np.full(len(lon), np.nan)
        val[ok] = m[i[ok], j[ok]]
        ok &= ~np.isnan(val)
        suma[ok] += w[ok] * val[ok]
        peso[ok] += w[ok]
    return np.where(peso > 0, suma / np.where(peso > 0, peso, 1), np.nan)


def autoprueba():
    """Comprobación mínima de ubicar() y bilineal() con una grilla de 2 × 2."""
    g = {"oeste": 0.0, "norte": 0.0, "dx": 1.0, "dy": 1.0, "filas": 2, "cols": 2}
    valida = np.array([[True, False], [True, True]])
    lon, lat = np.array([0.5, 1.5, 0.25]), np.array([-0.5, -0.3, -1.9])
    f, c, borde, vec, dist = ubicar(lon, lat, g, valida)
    assert list(f) == [0, 0, 1] and list(c) == [0, 0, 0] and list(vec) == [False, True, False], (f, c, vec)
    assert abs(dist[1] - 0.5 * 111.32 * np.cos(np.radians(-0.3))) < 1e-6 and abs(borde[2] - 0.1 * KX_LAT) < 1e-6
    m = np.array([[0.0, np.nan], [10.0, 20.0]])
    assert abs(bilineal(m, np.array([0.5]), np.array([-1.0]), g)[0] - 5) < 1e-9   # entre 0 y 10
    assert abs(bilineal(m, np.array([1.0]), np.array([-1.5]), g)[0] - 15) < 1e-9  # entre 10 y 20


# --------------------------------------------------------------------------------------------------------------------
# Censo
# --------------------------------------------------------------------------------------------------------------------
def manzanas():
    """Manzanas del departamento con tabulado y polígono: indicadores, centroide y metadatos."""
    import geopandas
    import pyogrio
    datos, _, P, V = censo.cargar(DEPARTAMENTO)
    ind = censo.indicadores(datos["P"], datos["V"], P, V)
    dp = datos["P"]
    ind["provincia"], ind["distrito"], ind["ccpp"], ind["centro_poblado"] = dp[3].values, dp[4].values, dp[6].values, dp[5].values
    disp = ind["codigo"].str.endswith("9999")
    perdidas = (ind[disp].groupby(["ubigeo", "distrito"])[["v", "p"]].sum().reset_index()
                .rename(columns={"v": "viviendas", "p": "poblacion"}))
    print(f"Tabulados: {len(ind)} filas en {ind['ubigeo'].nunique()} distritos; dispersas agrupadas (9999, sin polígono): "
          f"{disp.sum()} con {ind.loc[disp, 'v'].sum()} viviendas y {ind.loc[disp, 'p'].sum()} habitantes")
    capa = pyogrio.list_layers(censo.MANZANAS)[0][0]
    mz = pyogrio.read_dataframe(censo.MANZANAS, layer=capa, where=f"UBIGEO LIKE '{DEPARTAMENTO}%'",
                                columns=["UBIGEO", "ZONA", "MANZANA"])
    if mz.crs is None or mz.crs.to_epsg() != 4326:
        mz = mz.to_crs(4326)
    mz["codigo"] = mz["UBIGEO"] + mz["ZONA"] + mz["MANZANA"]
    if mz["codigo"].duplicated().any():
        sys.exit("Códigos de manzana repetidos en la cartografía")
    tab = ind[~disp]
    u = geopandas.GeoDataFrame(tab.merge(mz[["codigo", "ZONA", "MANZANA", "geometry"]], on="codigo", how="left"), crs=4326)
    sin = u["geometry"].isna()
    resumen = {"tabulados": len(ind), "dispersas": int(disp.sum()), "con_tabulado": len(tab), "sin_poligono": int(sin.sum()),
               "poligonos_departamento": len(mz), "poligonos_sin_tabulado": len(set(mz["codigo"]) - set(tab["codigo"])),
               "distritos_tabulados": int(ind["ubigeo"].nunique()), "distritos_cartografia": int(mz["UBIGEO"].nunique()),
               "viv_sin_poligono": int(u.loc[sin, "v"].sum()), "perdidas_dispersas": perdidas}
    print(f"Unión con la cartografía: {(~sin).sum()} de {len(tab)} manzanas con polígono; sin polígono: {sin.sum()} "
          f"({u.loc[sin, 'v'].sum()} viviendas); polígonos del departamento sin tabulado: {resumen['poligonos_sin_tabulado']} "
          f"de {len(mz)}")
    u = u[~sin].reset_index(drop=True)
    utm = u.to_crs(32717)
    cen = utm.centroid
    fuera = ~cen.within(utm.geometry)
    cen[fuera] = utm.geometry[fuera].representative_point()
    pt = geopandas.GeoSeries(cen, crs=32717).to_crs(4326)
    u["lon"], u["lat"], u["flag_punto_interior"] = pt.x.values, pt.y.values, fuera.astype(int).values
    u["km2"] = utm.area.values / 1e6
    u["flag_extensa"] = ((u["km2"] > censo.EXTENSA_KM2) & (u["v"] < censo.EXTENSA_DENSIDAD * u["km2"])).astype(int)
    # Hexágono de cada manzana como en censo_inei.hexagonos: centroide plano en WGS84 del polígono sin simplificar
    import warnings
    import h3
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # aviso de centroide en coordenadas geográficas: es a propósito, igual que en censo_inei
        c84 = u.geometry.centroid
    for res in (9, 10):
        u[f"hex{res}"] = [h3.latlng_to_cell(c.y, c.x, res) for c in c84]
    print(f"Centroides: {fuera.sum()} manzanas usan el punto interior porque su centroide cae fuera del polígono")
    return pd.DataFrame(u.drop(columns="geometry")), resumen


def puntos_control(base):
    """Centro de cada punto de control: promedio de los centroides de las manzanas del centro poblado más grande
    (en número de manzanas) de su distrito."""
    filas = []
    for nombre, ubigeo in CONTROL:
        d = base[base["ubigeo"] == ubigeo]
        if d.empty:
            sys.exit(f"Punto de control {nombre}: sin manzanas en el ubigeo {ubigeo}")
        cp = d["ccpp"].value_counts().index[0]
        d = d[d["ccpp"] == cp]
        filas.append({"punto": nombre, "ubigeo": ubigeo, "centro_poblado": d["centro_poblado"].iloc[0],
                      "lon": d["lon"].mean(), "lat": d["lat"].mean()})
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------------------------------------------------
# Salidas
# --------------------------------------------------------------------------------------------------------------------
def etiquetas(cols, v, meses):
    """Etiqueta de Stata (máx. 80 caracteres) de cada variable."""
    fijas = {
        "codigo": "Código de manzana INEI (ubigeo + zona + manzana)", "ubigeo": "Ubigeo del distrito (INEI)",
        "provincia": "Provincia", "distrito": "Distrito", "ccpp": "Código del centro poblado (INEI)",
        "centro_poblado": "Nombre del centro poblado", "zona": "Zona censal", "manzana": "Manzana",
        "lon": "Longitud del centroide de la manzana (WGS84)", "lat": "Latitud del centroide de la manzana (WGS84)",
        "flag_punto_interior": "1 = se usó el punto interior (el centroide caía fuera)",
        "km2": "Área de la manzana (km2)", "flag_extensa": "1 = manzana extensa (>0,05 km2 y <1000 viv/km2)",
        "flag_pocos_viv": "1 = menos de 10 viviendas (indicadores de vivienda poco estables)",
        "flag_pocos_pob": "1 = menos de 30 personas (indicadores de población poco estables)",
        "id_celda": "Celda CHIRPS asignada (fila_columna, desde la esquina noroeste)",
        "fila_celda": "Fila de la celda CHIRPS (0 = norte)", "col_celda": "Columna de la celda CHIRPS (0 = oeste)",
        "lon_celda": "Longitud del centro de la celda CHIRPS", "lat_celda": "Latitud del centro de la celda CHIRPS",
        "dist_borde_km": "Distancia del centroide al borde más cercano de su celda (km)",
        "flag_celda_vecina": "1 = su celda no tiene dato; se usó la celda válida más cercana",
        "dist_vecina_km": "Distancia del centroide a la celda vecina usada (km)",
        "n_manzanas_celda": "Manzanas de la base que comparten la celda", "n_viviendas_celda": "Viviendas que comparten la celda",
        "n_manzanas": "Manzanas asignadas a la celda", "n_manzanas_vecina": "Manzanas asignadas por ser la celda más cercana",
        "viviendas": "Viviendas particulares con ocupantes presentes", "poblacion": "Población censada",
        "n_distritos": "Distritos con manzanas en la celda", "distrito_principal": "Distrito con más manzanas en la celda",
        "ubigeo_principal": "Ubigeo del distrito con más manzanas en la celda",
        "sin_essalud_privado_max": "Máximo posible sin EsSalud ni seguro privado (personas)",
    }
    texto = {k: r for k, r, *_ in censo.INDICADORES}
    out = {}
    for c in cols:
        base, bil = (c[:-4], " (bilineal)") if c.endswith("_bil") else (c, "")
        p = base.split("_")
        if base in fijas:
            e = fijas[base]
        elif base.endswith(("_n", "_d")) and base[:-2] in NOMBRES.values():
            k = [x for x, n in NOMBRES.items() if n == base[:-2]][0]
            e = f"{texto[k]}: {'numerador' if base.endswith('_n') else 'denominador'}"
        elif p[0] == "lluvia" and p[1] in ABREV:
            e = f"Lluvia de {MESES[ABREV.index(p[1])]} {p[2]} (mm, CHIRPS v3)"
        elif p[0] == "lluvia" and p[1] == v:
            e = f"Lluvia acumulada {MESES[meses[0] - 1]}-{MESES[meses[-1] - 1]} {p[2]} (mm, CHIRPS v3)"
        elif p[0] == "lluvia" and p[1] == "max":
            e = f"Lluvia del mes más lluvioso de {MESES[meses[0] - 1]}-{MESES[meses[-1] - 1]} {p[2]} (mm)"
        elif p[0] == "mes" and p[1] == "max":
            e = f"Mes más lluvioso de {p[2]} (1 = enero)"
        elif p[0] == "normal":
            e = f"Normal {p[2]}-{p[3]} del acumulado {v} (mm)"
        elif p[0] == "anom":
            e = f"Anomalía del acumulado {v} {p[2]} frente a la normal (mm)"
        elif p[0] == "anomp":
            e = f"Acumulado {v} {p[2]} como % de la normal"
        else:
            sys.exit(f"Variable sin etiqueta: {c}")
        out[c] = (e + bil)[:80]
    return out


def guardar_stata(df, ruta, etq):
    largos = [c for c in df.columns if len(c) > 32]
    if largos:
        sys.exit(f"Nombres de más de 32 caracteres para Stata: {largos}")
    d = df.copy()
    for c in d.columns:
        if d[c].dtype == bool:
            d[c] = d[c].astype("int8")
    d.to_stata(ruta, write_index=False, version=118, variable_labels=etq,
               data_label="Lluvia CHIRPS v3 y Censo 2025 (INEI), Piura")


def diccionario(cols_mz, cols_celda, etq, v, meses, completos, g):
    """Diccionario de variables y nota metodológica, en Markdown."""
    hoy = datetime.now(PERU).strftime("%d/%m/%Y")
    vent = f"{MESES[meses[0] - 1]} a {MESES[meses[-1] - 1]}"

    def calculo(c):
        b = c[:-4] if c.endswith("_bil") else c
        if c.endswith("_bil"):
            return "Interpolación bilineal entre los centros de las 4 celdas vecinas en el centroide de la manzana; si alguna no tiene dato, el peso se reparte entre las otras. Solo para robustez."
        if b.startswith("lluvia_max_"):
            return f"Máximo de los meses {vent} en la celda."
        if b.startswith(f"lluvia_{v}_"):
            return f"Suma de los meses {vent} en la celda."
        if b.startswith("lluvia_"):
            return "Valor del ráster mensual en la celda asignada."
        if b.endswith(("_n", "_d")):
            return "Tabulados del Censo 2025 (INEI), como en scripts/censo_inei.py. En la base por celda, suma de las manzanas."
        return ""

    def unidad(c):
        if c.startswith(("lluvia_", "normal_", "anom_")):
            return "mm"
        if c.startswith("anomp_"):
            return "%"
        if c.endswith("_km"):
            return "km"
        if c == "km2":
            return "km²"
        if c in ("lon", "lat", "lon_celda", "lat_celda"):
            return "grados"
        if c.startswith(("flag_",)):
            return "0/1"
        if c.endswith(("_n", "_d", "_max")) or c.startswith("n_") or c in ("viviendas", "poblacion"):
            return "conteo"
        return ""

    def tabla(cols):
        filas = ["| Variable | Descripción | Unidad | Cálculo |", "| --- | --- | --- | --- |"]
        for c in cols:
            filas.append(f"| `{c}` | {etq[c]} | {unidad(c)} | {calculo(c)} |")
        return "\n".join(filas)

    return f"""# Diccionario: lluvia (CHIRPS) y Censo 2025 por manzana y por celda

Generado por `scripts/lluvia_manzanas.py` el {hoy}. Años: {', '.join(map(str, completos))}. Meses: {vent}.

## Fuentes

- **Lluvia**: {FUENTE}. Rásters mensuales en mm, celdas de {g['dx']}° (unos 5,5 km), WGS84, {g['filas']} × {g['cols']} celdas
  con esquina noroeste en ({g['oeste']}; {g['norte']}) (PixelIsArea: el origen es la esquina de la celda, no su centro).
- **Censo**: INEI, Censos Nacionales 2025, tabulados «Pob viv hogar - Mz Agrupadas - Piura» y cartografía de manzanas
  (base MANZANA CPV2025). Los indicadores son los mismos de la pestaña Vulnerabilidad (`scripts/censo_inei.py`).

## Archivos

- `lluvia_manzana.csv` / `.dta`: una fila por manzana (con tabulado y polígono).
- `lluvia_celda.csv` / `.dta`: una fila por celda CHIRPS con al menos una manzana; los indicadores suman numeradores y
  denominadores de sus manzanas (el porcentaje de la celda es suma de numeradores / suma de denominadores).

## Regla de unión

1. Centroide de cada manzana calculado en UTM 17 S (EPSG:32717) y llevado a WGS84. Si cae fuera del polígono (manzanas en
   forma de U, por ejemplo), se usa un punto interior (`flag_punto_interior = 1`).
2. La manzana toma la celda que contiene ese punto (`id_celda` = fila_columna, contando desde la esquina noroeste).
3. Si esa celda no tiene dato (sobre todo en la costa, donde el recorte deja celdas vacías), se usa la celda con dato más
   cercana (`flag_celda_vecina = 1`, con la distancia en `dist_vecina_km`).
4. Las manzanas «dispersas agrupadas» (código terminado en 9999) no tienen polígono y no están en la base.

## Nota metodológica (en lenguaje simple)

- **La lluvia cambia de celda en celda (unos 5,5 km), no de manzana en manzana.** Todas las manzanas de una celda tienen
  el mismo valor: en la Ciudad de Piura, cientos de manzanas comparten una celda. En cualquier regresión a nivel de
  manzana, los errores estándar deben agruparse por `id_celda` (por ejemplo, `vce(cluster id_celda)` en Stata). Sin eso,
  la precisión se exagera mucho. `n_manzanas_celda` dice cuántas manzanas comparten cada valor.
- **Lluvia no es inundación.** En la ciudad, el daño de 2017 dependió del desborde del río Piura y del drenaje (la altura
  del terreno, la distancia al río y a los drenes), que la celda no capta. Dos manzanas de la misma celda pueden haber
  tenido una inundada y la otra seca.
- **Los meses disponibles pueden no capturar todo el evento.** En 1983 las lluvias siguieron en mayo y junio (en la
  estación Miraflores: 379 mm en mayo y 192 mm en junio, según INDECI/OEA), fuera de la ventana de {vent}. El acumulado
  de 1983 subestima el evento frente a 1998, que terminó antes.
- CHIRPS es una estimación por satélite calibrada con estaciones; no reemplaza la medición de un pluviómetro, sobre todo
  en lluvias muy intensas y localizadas.
- Las celdas valen para todo el departamento, pero el censo por manzana solo cubre los distritos que trae el tabulado
  (ver `notas/avance_lluvia_manzanas.md`).
- Anomalías: cuando llegue la serie completa, el script calcula la normal {NORMAL[0]}-{NORMAL[1]} y las variables
  `normal_{v}_{NORMAL[0]}_{NORMAL[1]}`, `anom_{v}_AÑO` (mm) y `anomp_{v}_AÑO` (% de la normal). Hoy están pendientes.

## Variables de `lluvia_manzana`

{tabla(cols_mz)}

## Variables de `lluvia_celda`

{tabla(cols_celda)}
"""


def mapa_control(lluvia_celda, g, valida, base, ctrl, v, anio):
    """PNG de control: grilla CHIRPS sobre el límite departamental y sobre la Ciudad de Piura."""
    import geopandas
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pyogrio
    dist = pyogrio.read_dataframe(censo.LIMITES, where=f"UBIGEO LIKE '{DEPARTAMENTO}%'", columns=["UBIGEO"])
    dist = dist.to_crs(4326) if dist.crs is not None and dist.crs.to_epsg() != 4326 else dist
    dep = dist.dissolve()
    extent = [g["oeste"], g["oeste"] + g["cols"] * g["dx"], g["norte"] - g["filas"] * g["dy"], g["norte"]]
    xs = g["oeste"] + np.arange(g["cols"] + 1) * g["dx"]
    ys = g["norte"] - np.arange(g["filas"] + 1) * g["dy"]
    fig, ax = plt.subplots(1, 2, figsize=(16, 9))
    for k, a in enumerate(ax):
        a.imshow(np.ma.masked_invalid(lluvia_celda), extent=extent, cmap="Blues", origin="upper", alpha=0.85)
        a.vlines(xs, extent[2], extent[3], color="0.6", lw=0.3)
        a.hlines(ys, extent[0], extent[1], color="0.6", lw=0.3)
        dist.boundary.plot(ax=a, color="0.35", lw=0.4)
        dep.boundary.plot(ax=a, color="red", lw=1.2)
        a.plot(ctrl["lon"], ctrl["lat"], "o", ms=4, color="orange", mec="k")
        for _, r in ctrl.iterrows():
            a.annotate(r["punto"], (r["lon"], r["lat"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
        a.set_aspect(1 / np.cos(np.radians(-5.2)))
    ax[0].set_xlim(extent[0], extent[1]); ax[0].set_ylim(extent[2], extent[3])
    ax[0].set_title(f"Grilla CHIRPS ({g['dx']}°) y límite del departamento (rojo); azul = lluvia {v} {anio}", fontsize=9)
    ciudad = base[base["ubigeo"].isin(["200101", "200104", "200115"])]
    ax[1].plot(ciudad["lon"], ciudad["lat"], ",", color="k", alpha=0.5)
    x0, x1, y0, y1 = ciudad["lon"].min() - 0.03, ciudad["lon"].max() + 0.03, ciudad["lat"].min() - 0.03, ciudad["lat"].max() + 0.03
    ax[1].set_xlim(x0, x1); ax[1].set_ylim(y0, y1)
    for i in range(g["filas"]):
        for j in range(g["cols"]):
            cx, cy = g["oeste"] + (j + 0.5) * g["dx"], g["norte"] - (i + 0.5) * g["dy"]
            if x0 < cx < x1 and y0 < cy < y1:
                ax[1].text(cx, cy, f"{i}_{j}\n{lluvia_celda[i, j]:.0f}", ha="center", va="center", fontsize=7, color="navy")
    ax[1].set_title("Ciudad de Piura: celdas (fila_columna y mm), límites distritales y centroides de manzanas", fontsize=9)
    PRIVADO.mkdir(exist_ok=True)
    ruta = PRIVADO / "control_grilla_chirps.png"
    fig.tight_layout(); fig.savefig(ruta, dpi=130); plt.close(fig)
    print(f"Mapa de control: {ruta.relative_to(RAIZ)}")


def informe_control(lluvia, completos, meses, g, valida, ctrl, base, resumen, v):
    """Tablas de control en Markdown (privado/lluvia_control.md); su contenido pasa al resumen de avance."""
    f, c, _, vec, _ = ubicar(ctrl["lon"].values, ctrl["lat"].values, g, valida)
    ctrl = ctrl.assign(id_celda=[f"{a}_{b}" for a, b in zip(f, c)], vecina=vec)
    L = ["## Tabla de control: lluvia en la celda de cada punto (mm)", "",
         "| Punto | Centro poblado | Celda | " + " | ".join(f"{ABREV[m - 1]} {y}" for y in completos for m in meses) + " |",
         "| --- | --- | --- | " + " | ".join("---:" for _ in completos for _ in meses) + " |"]
    for k, r in ctrl.iterrows():
        vals = [lluvia[y][m][f[k], c[k]] for y in completos for m in meses]
        L.append(f"| {r['punto']} | {r['centro_poblado'].title()} | {r['id_celda']}{' (vecina)' if r['vecina'] else ''} | "
                 + " | ".join(f"{x:.0f}" for x in vals) + " |")
    L += ["", "## Comparación con estaciones (mm)", "",
          "| Estación | Año | Celda del punto | Mes | Estación | CHIRPS | Fuente |", "| --- | --- | --- | --- | ---: | ---: | --- |"]
    pos = ctrl.set_index("punto")
    for est, punto, y, vals, fuente in ESTACIONES:
        if y not in completos:
            continue
        i, j = f[list(pos.index).index(punto)], c[list(pos.index).index(punto)]
        for m, x in zip([1, 2, 3, 4], vals):
            if x is not None and m in meses:
                L.append(f"| {est} | {y} | {i}_{j} ({punto}) | {MESES[m - 1]} | {x:.1f} | {lluvia[y][m][i, j]:.1f} | {fuente} |")
        if all(x is not None for x in vals) and meses == [1, 2, 3, 4]:
            L.append(f"| {est} | {y} | {i}_{j} ({punto}) | **enero-abril** | **{sum(vals):.1f}** | "
                     f"**{sum(lluvia[y][m][i, j] for m in meses):.1f}** | {fuente} |")
    L += ["", "## Celdas con exactamente 0 mm", "", "| Año | Mes | Celdas con 0 | Celdas < 1 mm | de |", "| --- | --- | ---: | ---: | ---: |"]
    for y in completos:
        for m in meses:
            a = lluvia[y][m][valida]
            L.append(f"| {y} | {MESES[m - 1]} | {(a == 0).sum()} | {(a < 1).sum()} | {valida.sum()} |")
    L += ["", "## Mediana departamental del acumulado (mm, celdas con dato)", ""]
    for y in completos:
        s = sum(lluvia[y][m] for m in meses)[valida]
        L.append(f"- {y}: mediana {np.median(s):.0f}, percentil 90 {np.percentile(s, 90):.0f}, máximo {s.max():.0f}")
    vec_d = (base.groupby(["provincia", "distrito"]).agg(manzanas=("codigo", "size"), con_vecina=("flag_celda_vecina", "sum"),
                                                         viviendas=("v", "sum"),
                                                         viv_vecina=("v", lambda s: s[base.loc[s.index, "flag_celda_vecina"] == 1].sum()),
                                                         dist_max_km=("dist_vecina_km", "max"))
             .reset_index())
    vec_d = vec_d[vec_d["con_vecina"] > 0].sort_values("viv_vecina", ascending=False)
    L += ["", f"## Manzanas en celdas sin dato (se usó la celda vecina): {int(base['flag_celda_vecina'].sum())} manzanas, "
          f"{int(base.loc[base['flag_celda_vecina'] == 1, 'v'].sum())} viviendas", "",
          "| Provincia | Distrito | Manzanas | Con vecina | Viviendas | Viviendas con vecina | Distancia máx. (km) |",
          "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in vec_d.iterrows():
        L.append(f"| {r['provincia'].title()} | {r['distrito'].title()} | {r['manzanas']} | {r['con_vecina']} | {r['viviendas']} | "
                 f"{r['viv_vecina']} | {r['dist_max_km']:.1f} |")
    n = base.groupby("id_celda").agg(m=("codigo", "size"), v=("v", "sum"))
    q = n["m"].quantile([0.25, 0.5, 0.75, 0.9]).round(0)
    top = n.sort_values("m", ascending=False).head(10)
    L += ["", "## Manzanas por celda", "",
          f"- Celdas con al menos una manzana: {len(n)} (de {valida.sum()} con dato).",
          f"- Manzanas por celda: mínimo {n['m'].min()}, cuartil 1 {q[0.25]:.0f}, mediana {q[0.5]:.0f}, cuartil 3 {q[0.75]:.0f}, "
          f"percentil 90 {q[0.9]:.0f}, máximo {n['m'].max()}.",
          f"- Celdas con una sola manzana: {(n['m'] == 1).sum()}; con 100 o más: {(n['m'] >= 100).sum()} "
          f"({100 * n.loc[n['m'] >= 100, 'm'].sum() / n['m'].sum():.0f} % de las manzanas).", "",
          "| Celda | Manzanas | Viviendas | Distrito principal |", "| --- | ---: | ---: | --- |"]
    princ = base.groupby("id_celda")["distrito"].agg(lambda s: s.value_counts().index[0])
    for k, r in top.iterrows():
        L.append(f"| {k} | {r['m']} | {r['v']} | {princ[k].title()} |")
    pd_ = resumen["perdidas_dispersas"]
    L += ["", "## Cobertura del censo", "",
          f"- Tabulados: {resumen['tabulados']} filas en {resumen['distritos_tabulados']} distritos (la cartografía tiene "
          f"{resumen['distritos_cartografia']} distritos y {resumen['poligonos_departamento']} polígonos de manzana).",
          f"- Dispersas agrupadas (9999, sin polígono, fuera de la base): {resumen['dispersas']} filas, "
          f"{int(pd_['viviendas'].sum())} viviendas y {int(pd_['poblacion'].sum())} habitantes.",
          f"- Manzanas tabuladas sin polígono: {resumen['sin_poligono']} ({resumen['viv_sin_poligono']} viviendas).",
          f"- Polígonos del departamento sin tabulado: {resumen['poligonos_sin_tabulado']}.", "",
          "| Distrito | Viviendas dispersas | Habitantes dispersos |", "| --- | ---: | ---: |"]
    for _, r in pd_.sort_values("viviendas", ascending=False).iterrows():
        L.append(f"| {r['distrito'].title()} ({r['ubigeo']}) | {r['viviendas']} | {r['poblacion']} |")
    ruta = PRIVADO / "lluvia_control.md"
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Tablas de control: {ruta.relative_to(RAIZ)}")


CORTES_MM = [500, 1000, 1500, 2000]  # 5 franjas fijas e iguales para todos los años: <500, 500-1000, …, ≥2000 mm
CORTES_PCT = [50, 100, 150, 200]  # en % de lo normal (cuando llegue la serie completa)
MIN_CELDAS = 2  # contornos cerrados de menos de 2 celdas CHIRPS (~60 km²): ruido de la interpolación, se descartan
SUBDIVISION, SUAVIZADO = 5, 0.4  # cada celda se parte en 5 × 5 para trazar las curvas; suavizado gaussiano de 0,4 celdas


def departamento():
    """Límite del departamento (INEI, CPV 2025) en WGS84: unión de sus distritos. Sigue la línea de costa."""
    import pyogrio
    import shapely
    d = pyogrio.read_dataframe(censo.LIMITES, where=f"UBIGEO LIKE '{DEPARTAMENTO}%'", columns=["UBIGEO"])
    d = d.to_crs(4326) if d.crs is not None and d.crs.to_epsg() != 4326 else d
    return shapely.make_valid(shapely.union_all(d.geometry.values))


def franja_costera(g, valida, dep):
    """Diagnóstico de la versión anterior (cuadrados): cuántas celdas con dato caen en parte o del todo sobre el mar."""
    from shapely.geometry import box
    tierra = []
    for i, j in zip(*np.nonzero(valida)):
        o, n = g["oeste"] + j * g["dx"], g["norte"] - i * g["dy"]
        c = box(o, n - g["dy"], o + g["dx"], n)
        tierra.append(c.intersection(dep).area / c.area)
    t = np.array(tierra)
    print(f"Celdas con dato: {len(t)}; con algo fuera del departamento (mar o vecinos): {(t < 0.999).sum()}; "
          f"con menos de la mitad dentro: {(t < 0.5).sum()}; con menos del 10 % dentro: {(t < 0.1).sum()}")


def franjas(celda, g, valida, completos, v, meses, dep):
    """Franjas de lluvia acumulada por año (polígonos entre isoyetas), recortadas al departamento:
    docs/data/lluvia_franjas_{año}.geojson. Cada franja trae su clase y el punto donde va su cifra."""
    import shapely
    from scipy import ndimage
    from shapely.geometry import mapping
    from shapely.ops import polylabel
    from skimage import measure
    # las celdas sin dato (todas fuera del departamento) toman el valor de la celda con dato más cercana: así las curvas no
    # se cierran artificialmente en el borde del recorte; después se cortan al límite del departamento
    cerca = ndimage.distance_transform_edt(~valida, return_distances=False, return_indices=True)
    F = SUBDIVISION
    k = (np.arange(g["filas"] * F) + 0.5) / F - 0.5, (np.arange(g["cols"] * F) + 0.5) / F - 0.5  # en unidades de celda
    filas, cols = np.meshgrid(*k, indexing="ij")
    area_min = MIN_CELDAS * g["dx"] * g["dy"]
    normal = celda.get(f"normal_{v}_{NORMAL[0]}_{NORMAL[1]}")
    series = [(y, celda[f"lluvia_{v}_{y}"], "", CORTES_MM, "mm") for y in completos]
    if normal is not None:  # % de lo normal, solo con la serie completa
        series += [(y, 100 * celda[f"lluvia_{v}_{y}"] / np.where(normal > 0, normal, np.nan), "_pct", CORTES_PCT, "% de lo normal")
                   for y in completos]
    for y, matriz, sufijo, cortes, unidad in series:
        fina = ndimage.gaussian_filter(ndimage.map_coordinates(matriz[tuple(cerca)], [filas, cols], order=1, mode="nearest"),
                                       SUAVIZADO * F)
        borde = np.pad(fina, 1, constant_values=-1e9)  # todo contorno se cierra dentro del marco
        descartados = 0

        def sobre(t):
            """Zona con lluvia ≥ t: regla par-impar sobre los contornos cerrados, sin los de menos de MIN_CELDAS."""
            nonlocal descartados
            zona = shapely.Polygon()
            for c in measure.find_contours(borde, t):
                if len(c) < 4:
                    continue
                lon = g["oeste"] + (c[:, 1] - 0.5) / F * g["dx"]
                lat = g["norte"] - (c[:, 0] - 0.5) / F * g["dy"]
                anillo = shapely.make_valid(shapely.Polygon(np.column_stack([lon, lat])))
                if anillo.area < area_min:
                    descartados += 1
                    continue
                zona = shapely.symmetric_difference(zona, anillo)
            return zona
        # franja k = (≥ corte k−1) − (≥ corte k), dentro del departamento
        ge = [dep] + [shapely.intersection(dep, sobre(t)) for t in cortes]
        feats = []
        for clase in range(len(cortes) + 1):
            franja = ge[clase] if clase == len(cortes) else shapely.difference(ge[clase], ge[clase + 1])
            franja = shapely.set_precision(shapely.simplify(franja, 0.003), 1e-4)
            partes = [p for p in getattr(franja, "geoms", [franja]) if p.geom_type == "Polygon" and not p.is_empty]
            if not partes:
                continue
            mayor = max(partes, key=lambda p: p.area)
            punto = polylabel(mayor, tolerance=0.01)  # el punto más adentro de su parte más grande: ahí va la cifra
            feats.append({"type": "Feature", "properties": {"clase": clase, "etiqueta": [round(punto.y, 4), round(punto.x, 4)]},
                          "geometry": mapping(shapely.MultiPolygon(partes))})
        print(f"Franjas {y}{sufijo}: {len(feats)} clases; {descartados} contornos de menos de {MIN_CELDAS} celdas descartados")
        guardar(f"lluvia_franjas_{y}{sufijo}.geojson", {"type": "FeatureCollection", "anio": y, "cortes": cortes, "unidad": unidad,
                                                         "variable": f"Lluvia acumulada {MESES[meses[0] - 1]}-{MESES[meses[-1] - 1]} ({unidad})",
                                                         "fuente": FUENTE, "features": feats})


def capa_sectores(celda, completos, v, meses, base):
    """Lluvia de cada manzana, hexágono y localidad de la pestaña Vulnerabilidad: docs/data/lluvia_sectores.json y lluvia_detalle.json.
    Usa las mismas manzanas y hexágonos que los archivos del censo de la página. Manzana: su celda (por el centroide, como en
    lluvia_manzana). Hexágono: promedio de sus manzanas (sin las extensas, como el hexágono) ponderado por viviendas.
    Localidad: promedio de todas sus manzanas con polígono, ponderado por viviendas."""
    import json
    from comun import DATOS
    # cada arreglo trae un valor por año y, cuando exista la normal (serie completa), la normal al final: así la página puede
    # pasar de mm a % de lo normal con un solo parámetro (LLUVIA_MODO en index.html)
    clave_normal = f"normal_{v}_{NORMAL[0]}_{NORMAL[1]}"
    con_normal = clave_normal in celda
    vals = np.stack([celda[f"lluvia_{v}_{y}"] for y in completos] + ([celda[clave_normal]] if con_normal else []), axis=-1)
    b = base.set_index("codigo")
    leer = lambda n: json.loads((DATOS / n).read_text(encoding="utf-8"))
    cp = leer("censo_piura.json")
    celdas, indice, mzs, locs = [], {}, {}, {}

    def promedio(d):
        w = d["v"].to_numpy(float)
        x = vals[d["fila_celda"], d["col_celda"]]
        return [int(round(a)) for a in np.average(x, axis=0, weights=w if w.sum() > 0 else None)]

    for loc in cp["localidades"]:
        if loc["id"] == "metro":
            h = {9: cp["hexagonos"]["features"], 10: leer("censo_hex10.json")["features"]}
            mz = leer("censo_manzanas.json")["features"]
        else:
            d = leer(loc["archivo"])
            h, mz = {9: d["hexagonos"]["features"]}, d["manzanas"]["features"]  # las localidades no tienen hexágonos de 130 m
        cods = [f["id"] for f in mz]
        faltan = set(cods) - set(b.index)
        if faltan:
            sys.exit(f"{loc['nombre']}: {len(faltan)} manzanas de la página no están en la base, ej. {sorted(faltan)[:5]}")
        sub = b.loc[cods]
        for cod, r in sub.iterrows():
            c = (r["fila_celda"], r["col_celda"])
            if c not in indice:
                indice[c] = len(celdas)
                celdas.append([int(round(a)) for a in vals[c]])
            mzs[cod] = indice[c]
        w = sub["v"].to_numpy(float)
        # centro del círculo de la vista por localidad: centroide de sus manzanas ponderado por viviendas
        out = {"prom": promedio(sub), "centro": [round(float(np.average(sub["lat"], weights=w)), 5),
                                                 round(float(np.average(sub["lon"], weights=w)), 5)]}
        sin_ext = sub[sub["flag_extensa"] == 0]
        for res, feats in h.items():
            grupos = {k: promedio(d) for k, d in sin_ext.groupby(f"hex{res}")}
            ids = [f["id"] for f in feats]
            no = [i for i in ids if i not in grupos]
            if no or len(grupos) != len(ids):
                sys.exit(f"{loc['nombre']}, H3 {res}: {len(no)} hexágonos de la página sin manzanas y {len(grupos) - len(ids) + len(no)} "
                         f"de más; la asignación no coincide con censo_inei.py")
            out[f"h{res}"] = grupos
        locs[loc["id"]] = out
        print(f"Lluvia por sector, {loc['nombre']}: {len(cods)} manzanas, {' y '.join(str(len(x)) for x in h.values())} hexágonos; "
              f"promedio {dict(zip(completos, out['prom']))}")
    meta = {"anios": completos, "fuente": FUENTE, "url": "https://www.chc.ucsb.edu/data/chirps3", "fecha_corte": "2026-11-18",
            "variable": f"Lluvia acumulada {MESES[meses[0] - 1]}-{MESES[meses[-1] - 1]} (mm)", "normal": con_normal}
    # lo que la pestaña usa al abrirse (localidades y hexágonos de 350 m) y, aparte, el detalle que solo se pide al acercar
    # el mapa (hexágonos de 130 m y manzanas), como los archivos del censo
    guardar("lluvia_sectores.json", {**meta, "localidades": {k: {"prom": x["prom"], "centro": x["centro"], "h9": x["h9"]}
                                                             for k, x in locs.items()}})
    guardar("lluvia_detalle.json", {**meta, "celdas": celdas, "manzanas": mzs, "h10": locs["metro"]["h10"]})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meses", default="1,2,3,4", help="meses de la ventana, en orden (ej. 12,1,2,3 no se admite aún)")
    meses = [int(x) for x in ap.parse_args().meses.split(",")]
    if meses != sorted(meses) or not all(1 <= m <= 12 for m in meses):
        # shortcut: una ventana que cruza el año (dic-mar) necesitaría sumar meses del año anterior; se agrega si se pide
        sys.exit("La ventana debe ser de meses crecientes del mismo año (1 a 12)")
    autoprueba()
    verificar_espacio()
    v = nombre_ventana(meses)

    lluvia, g, completos, valida = cargar_rasters(meses)
    celda = variables_celda(lluvia, completos, meses, v)

    base, resumen = manzanas()
    lon, lat = base["lon"].values, base["lat"].values
    fila, col, borde, vec, dist = ubicar(lon, lat, g, valida)
    base["fila_celda"], base["col_celda"] = fila, col
    base["id_celda"] = [f"{a}_{b}" for a, b in zip(fila, col)]
    base["lon_celda"] = (g["oeste"] + (col + 0.5) * g["dx"]).round(4)
    base["lat_celda"] = (g["norte"] - (fila + 0.5) * g["dy"]).round(4)
    base["dist_borde_km"] = np.round(borde, 3)
    base["flag_celda_vecina"] = vec.astype(int)
    base["dist_vecina_km"] = np.where(vec, np.round(dist, 3), np.nan)
    for nombre, m in celda.items():
        base[nombre] = m[fila, col]
    for nombre, m in celda.items():
        if nombre.startswith("lluvia_"):
            base[nombre + "_bil"] = bilineal(m, lon, lat, g)
    base["n_manzanas_celda"] = base.groupby("id_celda")["codigo"].transform("size")
    base["n_viviendas_celda"] = base.groupby("id_celda")["v"].transform("sum")
    if base[f"lluvia_{v}_{completos[0]}"].isna().any():
        sys.exit("Hay manzanas sin lluvia asignada")
    print(f"Celda vecina: {vec.sum()} manzanas ({base.loc[vec, 'v'].sum()} viviendas); distancia máxima {dist.max():.1f} km")

    # Base por manzana: nombres claros para los indicadores y orden de columnas
    ren = {"p": "poblacion", "v": "viviendas", "ZONA": "zona", "MANZANA": "manzana", "g_max": "sin_essalud_privado_max"}
    for k, n in NOMBRES.items():
        ren[f"{k}_n"], ren[f"{k}_d"] = f"{n}_n", f"{n}_d"
    base["flag_pocos_viv"] = (base["v"] < censo.MINIMO["viv"]).astype(int)
    base["flag_pocos_pob"] = (base["p"] < censo.MINIMO["pob"]).astype(int)
    mz = base.rename(columns=ren)
    ident = ["codigo", "ubigeo", "provincia", "distrito", "ccpp", "centro_poblado", "zona", "manzana", "lon", "lat",
             "flag_punto_interior", "km2", "flag_extensa", "flag_pocos_viv", "flag_pocos_pob"]
    geo = ["id_celda", "fila_celda", "col_celda", "lon_celda", "lat_celda", "dist_borde_km", "flag_celda_vecina",
           "dist_vecina_km", "n_manzanas_celda", "n_viviendas_celda"]
    censo_cols = ["viviendas", "poblacion"] + [f"{n}_{s}" for n in NOMBRES.values() for s in "nd"] + ["sin_essalud_privado_max"]
    lluvia_cols = list(celda) + [c + "_bil" for c in celda if c.startswith("lluvia_")]
    mz = mz[ident + geo + censo_cols + lluvia_cols]
    mz["km2"] = mz["km2"].round(5)
    mz["lon"], mz["lat"] = mz["lon"].round(6), mz["lat"].round(6)
    for c in lluvia_cols:
        mz[c] = mz[c].round(2)

    # Base por celda: suma de numeradores y denominadores
    suma = censo_cols
    ce = (mz.groupby("id_celda").agg(fila_celda=("fila_celda", "first"), col_celda=("col_celda", "first"),
                                     lon_celda=("lon_celda", "first"), lat_celda=("lat_celda", "first"),
                                     n_manzanas=("codigo", "size"), n_manzanas_vecina=("flag_celda_vecina", "sum"),
                                     n_distritos=("ubigeo", "nunique"),
                                     ubigeo_principal=("ubigeo", lambda s: s.value_counts().index[0]),
                                     **{c: (c, "sum") for c in suma}).reset_index())
    ce["distrito_principal"] = ce["ubigeo_principal"].map(mz.groupby("ubigeo")["distrito"].first())
    for nombre, m in celda.items():
        ce[nombre] = np.round(m[ce["fila_celda"], ce["col_celda"]], 2)
    ce = ce[["id_celda", "fila_celda", "col_celda", "lon_celda", "lat_celda", "n_manzanas", "n_manzanas_vecina",
             "n_distritos", "ubigeo_principal", "distrito_principal"] + suma + list(celda)]
    if ce["viviendas"].sum() != mz["viviendas"].sum():
        sys.exit("La base por celda no suma las mismas viviendas que la base por manzana")

    SALIDA.mkdir(parents=True, exist_ok=True)
    etq_mz, etq_ce = etiquetas(mz.columns, v, meses), etiquetas(ce.columns, v, meses)
    mz.to_csv(SALIDA / "lluvia_manzana.csv", index=False, encoding="utf-8")
    ce.to_csv(SALIDA / "lluvia_celda.csv", index=False, encoding="utf-8")
    guardar_stata(mz, SALIDA / "lluvia_manzana.dta", etq_mz)
    guardar_stata(ce, SALIDA / "lluvia_celda.dta", etq_ce)
    (SALIDA / "diccionario_lluvia.md").write_text(diccionario(list(mz.columns), list(ce.columns), {**etq_mz, **etq_ce},
                                                              v, meses, completos, g), encoding="utf-8")
    print(f"Bases: {len(mz)} manzanas y {len(ce)} celdas en {SALIDA.relative_to(RAIZ)}")

    # Capas de la página: isoyetas por año y lluvia de cada sector, manzana y localidad de la pestaña Vulnerabilidad
    dep = departamento()
    franja_costera(g, valida, dep)
    franjas(celda, g, valida, completos, v, meses, dep)
    capa_sectores(celda, completos, v, meses, base)

    ctrl = puntos_control(base)
    mapa_control(celda[f"lluvia_{v}_{2017 if 2017 in completos else completos[-1]}"], g, valida, base, ctrl, v,
                 2017 if 2017 in completos else completos[-1])
    informe_control(lluvia, completos, meses, g, valida, ctrl, base, resumen, v)


if __name__ == "__main__":
    main()
