"""
Exposición del terreno por manzana del Censo 2025 (todo el departamento de Piura), con dos medidas:

  1. HAND (Height Above Nearest Drainage, altura sobre el cauce más cercano): cuántos metros está el terreno por encima del
     río o dren más cercano. Mide la exposición al DESBORDE de ríos y drenes.
     Fuente: GLO-30 HAND, derivado del Copernicus DEM GLO-30 (ASF / NASA, versión v1 2021), bucket público de AWS
     s3://glo-30-hand (https://registry.opendata.aws/glo-30-hand/), teselas de 1° × 1°, 1 segundo de arco (~30 m).
  2. Depresiones del terreno (agua EMPOZADA por lluvia): cuánto se llenaría cada punto si se rellenaran las hondonadas del
     modelo de terreno (relleno de depresiones por reconstrucción morfológica). Una manzana en una hondonada sin salida
     acumula el agua de lluvia. Fuente: Copernicus DEM GLO-30 (ESA / Airbus, s3://copernicus-dem-30m), misma grilla.

Ambos salen de un modelo de SUPERFICIE (TanDEM-X, imágenes de 2011 a 2015): incluye techos y árboles.

Se corre a mano. Por el espacio en disco, cada tesela se descarga, se procesa y se borra; en data/raw/hand/ (fuera del
repositorio) quedan el mosaico del HAND del departamento (decímetros, comprimido) y la caché de Nominatim.

Salidas:
  - data/procesado/hand_manzana.csv: una fila por manzana con tabulado y polígono (las mismas de lluvia_manzana).
  - privado/hand_validacion.md y privado/hand_control.png: validación con las listas congeladas en notas/hand_lista_previa.md.

Uso: python3 scripts/hand_manzanas.py   (--validar: solo la validación)
Ojo: --validar reescribe privado/hand_validacion.md; la sección «Limitaciones de la validación» se agregó a mano el
22/11/2026 y habría que copiarla de nuevo. El HAND quedó en pausa hasta tener datos de validación independientes.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

import censo_inei as censo
from comun import RAIZ, verificar_espacio

CRUDO = RAIZ / "data" / "raw" / "hand"
SALIDA = RAIZ / "data" / "procesado"
PRIVADO = RAIZ / "privado"
URL_HAND = "https://glo-30-hand.s3.amazonaws.com/v1/2021/Copernicus_DSM_COG_10_{t}_HAND.tif"
URL_DEM = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{t}_DEM/Copernicus_DSM_COG_10_{t}_DEM.tif"
# Teselas con manzanas de la base (las 3 del sur, S07, caen en el desierto de Sechura, sin manzanas)
TESELAS = ["S05_00_W082_00", "S05_00_W081_00", "S05_00_W080_00", "S06_00_W082_00", "S06_00_W081_00", "S06_00_W080_00"]
PASO = 1 / 3600  # 1 segundo de arco
POCOS_PIXELES = 3  # manzanas con menos píxeles (sumando fracciones) se marcan; su valor sale igual, ponderado
PROF_DEPRESION = 0.5  # m: un píxel está «en depresión» si se llenaría más de esto
METRO = ["200101", "200104", "200115"]


# ------------------------------------------------------------------------------------------------------------------
# Lectura de teselas
# ------------------------------------------------------------------------------------------------------------------
def bajar(url, destino):
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    for intento in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "observatorio-fen-piura/1.0"}),
                                        timeout=300) as r:
                destino.write_bytes(r.read())
            return destino
        except OSError as e:
            print(f"  descarga falló ({e}); nuevo intento en {30 * (intento + 1)} s")
            time.sleep(30 * (intento + 1))
    sys.exit(f"No se pudo descargar {url}")


def leer(ruta):
    """Matriz y esquina noroeste del píxel (0, 0), con el convenio de cada archivo (el HAND es PixelIsArea con el amarre
    medio píxel corrido; el DEM es PixelIsPoint): los dos quedan en la misma grilla de centros."""
    import tifffile
    with tifffile.TiffFile(ruta) as t:
        p = t.pages[0]
        a = p.asarray().astype("float64")
        tie, esc = p.tags[33922].value, p.tags[33550].value
        ks = p.tags[34735].value
        tipo = {ks[k]: ks[k + 3] for k in range(4, len(ks), 4)}.get(1025, 1)
    oeste, norte = tie[3], tie[4]
    if tipo == 2:
        oeste, norte = oeste - esc[0] / 2, norte + esc[1] / 2
    assert abs(esc[0] - PASO) < 1e-12 and a.shape == (3600, 3600), (ruta, esc, a.shape)
    return a, oeste, norte


def depresiones(dem):
    """Profundidad de llenado: DEM con las hondonadas rellenas (reconstrucción por erosión desde el borde) menos el DEM."""
    from skimage.morphology import reconstruction
    semilla = dem.copy()
    semilla[1:-1, 1:-1] = dem.max()
    return reconstruction(semilla, dem, method="erosion") - dem


# ------------------------------------------------------------------------------------------------------------------
# Estadística zonal ponderada por la fracción de cada píxel dentro del polígono
# ------------------------------------------------------------------------------------------------------------------
def zonal(polis, codigos, capas, oeste, norte, acum):
    """Para cada polígono, los píxeles de su caja, el área de cada píxel que cae dentro (peso) y el valor de cada capa;
    se acumulan en acum[codigo] porque una manzana puede cruzar el borde de una tesela."""
    import shapely
    b = shapely.bounds(polis)
    c0 = np.floor((b[:, 0] - oeste) / PASO).astype(int)
    c1 = np.floor((b[:, 2] - oeste) / PASO).astype(int)
    f0 = np.floor((norte - b[:, 3]) / PASO).astype(int)
    f1 = np.floor((norte - b[:, 1]) / PASO).astype(int)
    c0, f0 = np.clip(c0, 0, 3599), np.clip(f0, 0, 3599)
    c1, f1 = np.clip(c1, 0, 3599), np.clip(f1, 0, 3599)
    idx, fi, ci = [], [], []
    for k in range(len(polis)):
        ff, cc = np.meshgrid(np.arange(f0[k], f1[k] + 1), np.arange(c0[k], c1[k] + 1), indexing="ij")
        idx.append(np.full(ff.size, k)); fi.append(ff.ravel()); ci.append(cc.ravel())
    idx, fi, ci = np.concatenate(idx), np.concatenate(fi), np.concatenate(ci)
    cajas = shapely.box(oeste + ci * PASO, norte - (fi + 1) * PASO, oeste + (ci + 1) * PASO, norte - fi * PASO)
    w = shapely.area(shapely.intersection(cajas, polis[idx])) / PASO ** 2  # fracción de píxel (0 a 1)
    ok = w > 1e-6
    idx, fi, ci, w = idx[ok], fi[ok], ci[ok], w[ok]
    for k in np.unique(idx):
        s = idx == k
        a = acum.setdefault(codigos[k], {"w": [], **{n: [] for n in capas}})
        a["w"].append(w[s])
        for n, m in capas.items():
            a[n].append(m[fi[s], ci[s]])


def cuantil(v, w, q):
    o = np.argsort(v)
    cw = np.cumsum(w[o])
    return float(v[o][np.searchsorted(cw, q * cw[-1])])


def resumir(acum):
    filas = []
    for cod, a in acum.items():
        w = np.concatenate(a["w"]); h = np.concatenate(a["hand"]); d = np.concatenate(a["dep"])
        filas.append({"codigo": cod, "hand_mediana": cuantil(h, w, .5), "hand_min": float(h.min()), "hand_p10": cuantil(h, w, .1),
                      "hand_pct_area_2m": 100 * w[h < 2].sum() / w.sum(), "hand_pct_area_5m": 100 * w[h < 5].sum() / w.sum(),
                      "dep_media": float(np.average(d, weights=w)), "dep_max": float(d.max()),
                      "dep_pct_area": 100 * w[d > PROF_DEPRESION].sum() / w.sum(), "pixeles": float(w.sum())})
    return pd.DataFrame(filas)


# ------------------------------------------------------------------------------------------------------------------
# Manzanas
# ------------------------------------------------------------------------------------------------------------------
def manzanas():
    """Polígonos (WGS84) de las manzanas con tabulado del departamento, con su centro poblado y su hexágono de 350 m (igual
    que censo_inei: centroide plano del polígono sin simplificar)."""
    import warnings
    import h3
    import pyogrio
    base = pd.read_csv(SALIDA / "lluvia_manzana.csv", dtype={"codigo": str, "ubigeo": str, "ccpp": str},
                       usecols=["codigo", "ubigeo", "distrito", "ccpp", "centro_poblado", "viviendas", "lon", "lat", "km2"])
    capa = pyogrio.list_layers(censo.MANZANAS)[0][0]
    mz = pyogrio.read_dataframe(censo.MANZANAS, layer=capa, where="UBIGEO LIKE '20%'", columns=["UBIGEO", "ZONA", "MANZANA"])
    mz = mz.to_crs(4326) if mz.crs is not None and mz.crs.to_epsg() != 4326 else mz
    mz["codigo"] = mz["UBIGEO"] + mz["ZONA"] + mz["MANZANA"]
    mz = mz[mz["codigo"].isin(base["codigo"])].merge(base, on="codigo")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        c = mz.geometry.centroid
    mz["hex9"] = [h3.latlng_to_cell(p.y, p.x, 9) for p in c]
    return mz


# ------------------------------------------------------------------------------------------------------------------
# Validación con las listas congeladas (notas/hand_lista_previa.md)
# ------------------------------------------------------------------------------------------------------------------
# (nombre, distrito, tipo, regla): tipo «inundado» o «alto» (HAND) o «empozada» (depresiones). Regla: hexágonos cuyo
# nombre de OpenStreetMap contiene alguno de los textos; «punto» (lugar en Nominatim, manzanas a menos de 300 m);
# «ccpp» (nombre del centro poblado en el censo)
DESBORDE = [
    ("Centro de Piura (Plaza de Armas – calle Loreto)", "Piura", "inundado", ("punto", "Plaza de Armas de Piura")),  # «Plaza de Armas, Piura» devolvía la de Catacaos
    ("Urb. Los Cocos del Chipe", "Piura", "inundado", ("hex", ["Cocos del Chipe"])),
    ("Urb. Quinta Ana María", "Piura", "inundado", ("hex", ["Quinta Ana Mar"])),
    ("Urb. Miraflores", "Castilla", "inundado", ("hex", ["Miraflores Country Club", "Rosales de Miraflores"])),
    ("Castilla: Puente Cáceres y Hospital de Castilla", "Castilla", "inundado", ("punto", "Puente Cáceres, Piura, Perú")),
    ("Urb. Santa Isabel", "Piura", "inundado", ("punto", "Santa Isabel, Piura, Perú")),
    ("Catacaos (ciudad)", "Catacaos", "inundado", ("ccpp", ["CATACAOS"])),
    ("Cucúngara", "Cura Mori", "inundado", ("ccpp", ["CUCUNGARA"])),
    ("Pedregal Grande, Chato Chico y Monte Sullón", "Catacaos", "inundado", ("ccpp", ["PEDREGAL GRANDE", "CHATO CHICO", "MONTE SULLON"])),
    ("Los Algarrobos (1.ª a 5.ª etapa)", "Piura", "alto", ("hex", ["Los Algarrobos"])),
    ("Santa María del Pinar", "Piura", "alto", ("hex", ["Santa Maria del Pinar"])),
    ("Urb. Bello Horizonte", "Piura", "alto", ("hex", ["Bello Horizonte"])),
    ("Las Mercedes (al oeste)", "Piura", "alto", ("hex", ["Las Mercedes"])),
    ("San Eduardo", "Piura", "alto", ("hex", ["San Eduardo"])),
]
EMPOZADA = [(n, d, "empozada", r) for n, d, r in [
    ("Urb. El Chilcal", "Piura", ("punto", "El Chilcal, Piura, Perú")),
    ("Urb. Bancarios", "Piura", ("punto", "Urbanización Bancarios, Piura, Perú")),
    ("Urb. Santa Ana", "Piura", ("punto", "Urbanización Santa Ana, Piura, Perú")),
    ("Urb. Los Petroleros", "Piura", ("punto", "Los Petroleros, Piura, Perú")),
    ("Urb. Mariscal Tito", "Piura", ("punto", "Mariscal Tito, Piura, Perú")),
    ("Ignacio Merino", "Piura", ("hex", ["Ignacio Merino"])),
    ("Santa Isabel", "Piura", ("punto", "Santa Isabel, Piura, Perú")),
    ("Petroperú", "Piura", ("punto", "Petroperú, Piura, Perú")),
    ("A. H. Paredes Maceda", "Piura", ("punto", "Paredes Maceda, Piura, Perú")),
    ("Micaela Bastidas", "Piura", ("punto", "Micaela Bastidas, Piura, Perú")),
    ("Coliseo", "Piura", ("punto", "Coliseo Municipal, Piura, Perú")),
    ("Los Polvorines", "Veintiséis de Octubre", ("hex", ["Polvorines"])),
    ("Los Médanos", "Castilla", ("punto", "Los Médanos, Castilla, Piura, Perú")),
    ("A. H. La Primavera", "Castilla", ("hex", ["La Primavera"])),
    ("Hospital (Castilla)", "Castilla", ("punto", "Hospital Cayetano Heredia, Castilla, Piura, Perú")),
    ("Don Bosco", "Castilla", ("punto", "Don Bosco, Castilla, Piura, Perú")),
    ("Mercado (Castilla)", "Castilla", ("punto", "Mercado de Castilla, Piura, Perú")),
    ("Tacna", "Castilla", ("punto", "Avenida Tacna, Castilla, Piura, Perú")),
    ("Las Montero", "Castilla", ("punto", "Las Montero, Castilla, Piura, Perú")),
    ("San Bernardo", "Castilla", ("hex", ["San Bernardo"])),
    ("A. H. Calixto Balarezo", "Castilla", ("punto", "Calixto Balarezo, Castilla, Piura, Perú")),
    ("El Indio", "Castilla", ("hex", ["El Indio"])),
]]
CAJA_PIURA = (-80.75, -5.30, -80.55, -5.10)  # oeste, sur, este, norte: Nominatim solo busca dentro de la ciudad


def nominatim(q, cache):
    """Coordenadas de un lugar con Nominatim (OpenStreetMap), dentro de la caja de la ciudad; con caché en disco."""
    if q in cache:
        return cache[q]
    o, s, e, n = CAJA_PIURA
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "viewbox": f"{o},{n},{e},{s}", "bounded": 1})
    time.sleep(1.1)  # política de uso: una consulta por segundo
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "observatorio-fen-piura/1.0"}), timeout=60) as r:
        res = json.loads(r.read().decode())
    cache[q] = [float(res[0]["lat"]), float(res[0]["lon"]), res[0]["display_name"]] if res else None
    return cache[q]


def sector(mz, hexnames, regla, cache):
    tipo, valor = regla
    if tipo == "hex":
        ids = [h for h, n in hexnames.items() if any(v.lower() in n.lower() for v in valor)]
        return mz[mz["hex9"].isin(ids)], f"{len(ids)} sectores del censo"
    if tipo == "ccpp":
        return mz[mz["centro_poblado"].isin(valor)], "centro poblado del censo"
    p = nominatim(valor, cache)
    if not p:
        return mz.iloc[0:0], "no se encontró en OpenStreetMap"
    d = np.hypot((mz["lon"] - p[1]) * 110.6 * np.cos(np.radians(p[0])), (mz["lat"] - p[0]) * 110.6)
    return mz[d < 0.3], f"300 m alrededor de «{p[2].split(',')[0]}»"


def validar(mz, est):
    import geopandas as gpd
    PRIVADO.mkdir(exist_ok=True)
    cache_f = CRUDO / "nominatim.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    hexnames = {}
    for f in json.loads((RAIZ / "docs" / "data" / "censo_piura.json").read_text())["hexagonos"]["features"]:
        hexnames[f["id"]] = f["properties"].get("n") or ""
    d = mz.drop(columns="geometry").merge(est, on="codigo")
    ciudad = d[d["ubigeo"].isin(METRO)]
    L = ["# Validación del HAND y de las depresiones (agua empozada)", "",
         "Listas congeladas el 22/11/2026 en notas/hand_lista_previa.md, antes de calcular.", ""]
    filas = []
    for nombre, dist, tipo, regla in DESBORDE + EMPOZADA:
        s, como = sector(d, hexnames, regla, cache)
        filas.append({"sector": nombre, "distrito": dist, "tipo": tipo, "como": como, "manzanas": len(s),
                      "viviendas": int(s["viviendas"].sum()), "hand": s["hand_mediana"].median() if len(s) else np.nan,
                      "pct_bajo5": 100 * (s["hand_mediana"] < 5).mean() if len(s) else np.nan,
                      "dep": s["dep_pct_area"].median() if len(s) else np.nan, "codigos": list(s["codigo"])})
    cache_f.parent.mkdir(parents=True, exist_ok=True)
    cache_f.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    t = pd.DataFrame(filas)
    # HAND
    L += ["## 1. HAND y desborde del 27 de marzo de 2017", "",
          "| Sector | Distrito | Grupo | Cómo se ubicó | Manzanas | Viviendas | HAND mediano (m) | % manzanas < 5 m | ¿Cumple? |",
          "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |"]
    for _, r in t[t["tipo"] != "empozada"].iterrows():
        ok = "—" if not r["manzanas"] else ("sí" if (r["hand"] < 5) == (r["tipo"] == "inundado") else "no")
        L.append(f"| {r['sector']} | {r['distrito']} | {r['tipo']} | {r['como']} | {r['manzanas']} | {r['viviendas']} | "
                 f"{'' if pd.isna(r['hand']) else f'{r.hand:.1f}'} | {'' if pd.isna(r['pct_bajo5']) else f'{r.pct_bajo5:.0f}'} | {ok} |")
    inu = t[(t.tipo == "inundado") & (t.manzanas > 0)]; alt = t[(t.tipo == "alto") & (t.manzanas > 0)]
    c1, c2 = (inu.hand < 5).sum(), (alt.hand > 5).sum()
    L += ["", f"**Criterio**: inundados con HAND < 5 m: {c1} de {len(inu)}; altos con HAND > 5 m: {c2} de {len(alt)}. "
          f"**{'Se cumple' if c1 > len(inu) / 2 and c2 > len(alt) / 2 else 'No se cumple'}.**", ""]
    # umbrales: % de manzanas bajo 2 y 5 m en cada grupo
    def pct(df, col, u): return 100 * (df[col] < u).mean() if len(df) else np.nan
    mi = d[d["codigo"].isin(sum(inu["codigos"], []))]; ma = d[d["codigo"].isin(sum(alt["codigos"], []))]
    L += ["| Manzanas | HAND < 2 m | HAND < 5 m | HAND mediano |", "| --- | ---: | ---: | ---: |"]
    for n, g in (("de sectores inundados", mi), ("de sectores altos", ma), ("toda la Ciudad de Piura", ciudad)):
        L.append(f"| {n} ({len(g)}) | {pct(g, 'hand_mediana', 2):.0f} % | {pct(g, 'hand_mediana', 5):.0f} % | {g['hand_mediana'].median():.1f} m |")
    # Copernicus EMS 2017
    carpeta = next((Path(a) for a in sys.argv[1:] if not a.startswith("--")), CRUDO / "ems")
    ems = sorted(carpeta.glob("**/*crisis_information_poly.shp"))
    if ems:
        pts = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.lon, d.lat), crs=4326)
        dentro = set()
        for f in ems:
            g = gpd.read_file(f).to_crs(4326)
            dentro |= set(gpd.sjoin(pts, g[["geometry"]], predicate="within")["codigo"])
        e1 = d[d.codigo.isin(dentro)]; e0 = d[~d.codigo.isin(dentro)]
        L += ["", "### Mapa de Copernicus EMS (EMSR199, radar del 26 y 30 de marzo de 2017)", "",
              f"Manzanas con el centroide en zona inundada: {len(e1)} ({int(e1.viviendas.sum())} viviendas).", "",
              "| Manzanas | HAND < 2 m | HAND < 5 m |", "| --- | ---: | ---: |",
              f"| en zona inundada según Copernicus ({len(e1)}) | {pct(e1, 'hand_mediana', 2):.0f} % | {pct(e1, 'hand_mediana', 5):.0f} % |",
              f"| resto del departamento ({len(e0)}) | {pct(e0, 'hand_mediana', 2):.0f} % | {pct(e0, 'hand_mediana', 5):.0f} % |"]
    # Depresiones
    med = ciudad["dep_pct_area"].median()
    L += ["", "## 2. Depresiones (agua empozada) y cuencas ciegas de INDECI/OEA (2009)", "",
          f"% del área de cada manzana con más de {PROF_DEPRESION} m de profundidad de llenado. Mediana de la Ciudad de Piura: {med:.0f} %.", "",
          "| Sector | Distrito | Cómo se ubicó | Manzanas | % del área en depresión (mediana) | ¿Sobre la mediana de la ciudad? |",
          "| --- | --- | --- | ---: | ---: | --- |"]
    emp = t[t.tipo == "empozada"]
    for _, r in emp.iterrows():
        ok = "—" if not r["manzanas"] else ("sí" if r["dep"] > med else "no")
        L.append(f"| {r['sector']} | {r['distrito']} | {r['como']} | {r['manzanas']} | {'' if pd.isna(r['dep']) else f'{r.dep:.0f}'} | {ok} |")
    ub = emp[emp.manzanas > 0]
    c3 = (ub.dep > med).sum()
    L += ["", f"**Criterio**: {c3} de {len(ub)} sectores ubicados están sobre la mediana de la ciudad. "
          f"**{'Se cumple' if c3 > len(ub) / 2 else 'No se cumple'}.**", ""]
    # Distribución por localidad
    locs = {"Ciudad de Piura": ciudad, **{n: d[(d.centro_poblado == c) & (d.ubigeo == u)] for n, c, u in
            [("Sullana", "SULLANA", "200601"), ("Paita", "PAITA", "200501"), ("Talara", "TALARA", "200701"),
             ("Catacaos", "CATACAOS", "200105"), ("Chulucanas", "CHULUCANAS", "200401")]}}
    L += ["## 3. Distribución del HAND mediano por manzana", "",
          "| Localidad | Manzanas | p10 | Mediana | p90 | < 2 m | < 5 m | Área en depresión (mediana) |",
          "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for n, g in locs.items():
        q = g["hand_mediana"].quantile([.1, .5, .9])
        L.append(f"| {n} | {len(g)} | {q[.1]:.1f} | {q[.5]:.1f} | {q[.9]:.1f} | {pct(g, 'hand_mediana', 2):.0f} % | "
                 f"{pct(g, 'hand_mediana', 5):.0f} % | {g['dep_pct_area'].median():.0f} % |")
    pocas = (d["pixeles"] < POCOS_PIXELES)
    L += ["", f"Manzanas con menos de {POCOS_PIXELES} píxeles (sumando fracciones): {pocas.sum()} de {len(d)} "
          f"({100 * pocas.mean():.0f} %); su valor sale igual, ponderado por la parte de cada píxel, y se marcan con hand_pocos_pixeles = 1.", ""]
    L += sesgo_urbano(mz.merge(est, on="codigo"))
    (PRIVADO / "hand_validacion.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    t.drop(columns="codigos").to_csv(PRIVADO / "hand_validacion_sectores.csv", index=False)
    mapa_control(mz.merge(est, on="codigo"), t)
    print("\n".join(L))


def sesgo_urbano(g):
    """Sesgo del modelo de superficie: compara el HAND de cada manzana de la Ciudad de Piura con el de los píxeles sin
    manzanas (terreno abierto: calles anchas, parques, chacras, descampados) a menos de 300 m."""
    import shapely
    import tifffile
    info = json.loads((CRUDO / "hand_piura_dm.json").read_text())
    c = g[g["ubigeo"].isin(METRO)].copy()
    o, s_, e, n = c.total_bounds
    o, s_, e, n = o - .005, s_ - .005, e + .005, n + .005
    c0 = int((o - info["oeste_esquina"]) / PASO); c1 = int((e - info["oeste_esquina"]) / PASO)
    f0 = int((info["norte_esquina"] - n) / PASO); f1 = int((info["norte_esquina"] - s_) / PASO)
    h = tifffile.imread(CRUDO / "hand_piura_dm.tif")[f0:f1 + 1, c0:c1 + 1] / 10
    ff, cc = np.meshgrid(np.arange(f0, f1 + 1), np.arange(c0, c1 + 1), indexing="ij")
    ox, oy = info["oeste_esquina"] + (cc + .5) * PASO, info["norte_esquina"] - (ff + .5) * PASO
    # centro del píxel dentro de alguna manzana (índice espacial: comparar contra la unión de todas era muy lento)
    pts = shapely.points(ox.ravel(), oy.ravel())
    dentro = shapely.STRtree(c.geometry.values).query(pts, predicate="within")[0]
    construido = np.zeros(pts.size, bool); construido[dentro] = True; construido = construido.reshape(ox.shape)
    abierto_h = np.where(construido, np.nan, h)
    k = 10  # ~300 m
    dif = []
    for _, r in c.iterrows():
        j = int((r["lon"] - o) / PASO); i = int((n - r["lat"]) / PASO)
        v = abierto_h[max(0, i - k):i + k + 1, max(0, j - k):j + k + 1]
        v = v[~np.isnan(v)]
        dif.append(r["hand_mediana"] - np.median(v) if v.size >= 10 else np.nan)
    c["dif"] = dif
    densidad = c["viviendas"] / c["km2"].clip(lower=1e-4)
    alta = densidad >= densidad.quantile(.75)
    L = ["## 4. Sesgo urbano (modelo de superficie)", "",
         "Diferencia entre el HAND mediano de cada manzana y la mediana del HAND de los píxeles sin manzanas a menos de 300 m.", "",
         "| Manzanas de la Ciudad de Piura | Manzanas | Diferencia mediana (m) | Manzanas más altas que su entorno abierto |",
         "| --- | ---: | ---: | ---: |"]
    for nom, m in (("todas", c["dif"].notna()), ("las más densas (25 % con más viviendas por km²)", alta & c["dif"].notna()),
                   ("las menos densas (75 % restante)", ~alta & c["dif"].notna())):
        x = c.loc[m, "dif"]
        L.append(f"| {nom} | {len(x)} | {x.median():+.1f} | {100 * (x > 0).mean():.0f} % |")
    L.append("")
    return L


def mapa_control(g, t):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = g[g["ubigeo"].isin(METRO)]
    fig, ax = plt.subplots(1, 2, figsize=(18, 9))
    for a, col, tit, cm, vmax in ((ax[0], "hand_mediana", "HAND mediano por manzana (m)", "viridis", 12),
                                  (ax[1], "dep_pct_area", f"% del área en depresión (> {PROF_DEPRESION} m)", "Blues", 100)):
        c.plot(column=col, ax=a, cmap=cm, vmin=0, vmax=vmax, legend=True, linewidth=0)
        for _, r in t.iterrows():
            if not r["manzanas"]:
                continue
            s = c[c["codigo"].isin(r["codigos"])]
            if s.empty:
                continue
            color = {"inundado": "red", "alto": "black", "empozada": "orange"}[r["tipo"]]
            if (col == "hand_mediana") == (r["tipo"] == "empozada"):
                continue
            s.boundary.plot(ax=a, color=color, linewidth=.6)
            p = s.union_all().centroid
            a.annotate(r["sector"][:22], (p.x, p.y), fontsize=6, color=color)
        a.set_title(tit + (" — rojo: inundados 2017; negro: altos" if col == "hand_mediana" else " — naranja: cuencas ciegas INDECI"), fontsize=9)
        a.set_aspect(1 / np.cos(np.radians(5.2)))
    fig.tight_layout(); fig.savefig(PRIVADO / "hand_control.png", dpi=110); plt.close(fig)


def main():
    verificar_espacio()
    import shapely
    mz = manzanas()
    if "--validar" in sys.argv:  # solo la validación, con hand_manzana.csv y el mosaico ya calculados
        return validar(mz, pd.read_csv(SALIDA / "hand_manzana.csv", dtype={"codigo": str}))
    print(f"Manzanas: {len(mz)}")
    acum, mosaico = {}, {}
    tmp = CRUDO / "teselas"
    for t in TESELAS:
        fh, fd = tmp / f"hand_{t}.tif", tmp / f"dem_{t}.tif"
        bajar(URL_HAND.format(t=t), fh); bajar(URL_DEM.format(t=t), fd)
        h, oeste, norte = leer(fh)
        dem, o2, n2 = leer(fd)
        assert abs(oeste - o2) < 1e-9 and abs(norte - n2) < 1e-9, (t, oeste, o2, norte, n2)
        dep = depresiones(dem)
        caja = shapely.box(oeste, norte - 1, oeste + 1, norte)
        sel = shapely.intersects(mz.geometry.values, caja)
        if sel.any():
            zonal(shapely.intersection(mz.geometry.values[sel], caja), mz["codigo"].values[sel], {"hand": h, "dep": dep}, oeste, norte, acum)
        mosaico[t] = (np.clip(np.round(h * 10), 0, 65535).astype("uint16"), oeste, norte)
        print(f"Tesela {t}: {sel.sum()} manzanas; HAND {np.nanmin(h):.0f} a {np.nanmax(h):.0f} m; "
              f"depresiones > {PROF_DEPRESION} m en {100 * (dep > PROF_DEPRESION).mean():.1f} % de la tesela", flush=True)
        fh.unlink(); fd.unlink()  # sin espacio para guardar las teselas originales
    est = resumir(acum)
    est["hand_pocos_pixeles"] = (est["pixeles"] < POCOS_PIXELES).astype(int)
    falta = set(mz["codigo"]) - set(est["codigo"])
    if falta:
        sys.exit(f"{len(falta)} manzanas sin píxeles, ej. {sorted(falta)[:5]}")
    SALIDA.mkdir(parents=True, exist_ok=True)
    est.round(3).to_csv(SALIDA / "hand_manzana.csv", index=False)
    guardar_mosaico(mosaico)
    validar(mz, est)


def guardar_mosaico(mosaico):
    """Mosaico del HAND de las 6 teselas en decímetros (uint16, comprimido) con su georreferencia en un JSON aparte."""
    import tifffile
    oes = sorted({v[1] for v in mosaico.values()}); nor = sorted({v[2] for v in mosaico.values()}, reverse=True)
    m = np.zeros((3600 * len(nor), 3600 * len(oes)), dtype="uint16")
    for a, o, n in mosaico.values():
        i, j = nor.index(n), oes.index(o)
        m[i * 3600:(i + 1) * 3600, j * 3600:(j + 1) * 3600] = a
    tifffile.imwrite(CRUDO / "hand_piura_dm.tif", m, compression="zlib", tile=(512, 512))
    (CRUDO / "hand_piura_dm.json").write_text(json.dumps({"oeste_esquina": oes[0], "norte_esquina": nor[0], "paso_grados": PASO,
                                                          "unidad": "decímetros", "fuente": "GLO-30 HAND v1 (2021)"}))
    print(f"Mosaico: {(CRUDO / 'hand_piura_dm.tif').stat().st_size / 2**20:.0f} MB")


if __name__ == "__main__":
    main()
