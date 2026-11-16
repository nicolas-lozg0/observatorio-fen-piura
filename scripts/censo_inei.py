"""
Censo 2025 (INEI) por manzana para la pestaña Vulnerabilidad: Piura metropolitana (Piura, Castilla y Veintiséis de Octubre).

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
import unicodedata
from pathlib import Path

import pandas as pd

from comun import DATOS, RAIZ, guardar, verificar_espacio

CRUDO = RAIZ / "data" / "raw" / "inei_censo2025"
TABULADOS = CRUDO / "tabulados" / "CPV 2025 - Pob viv hogar - Mz Agrupadas - Piura.xlsx"
MANZANAS = CRUDO / "cartografia" / "manzanas" / "base MANZANA CPV2025.gdb"
LIMITES = CRUDO / "cartografia" / "distritos" / "Límites distritales - CPV2025" / "DISTRITOS26.shp"
# Piura metropolitana: se buscan por nombre en los tabulados (provincia de Piura) y se verifica su ubigeo
DISTRITOS = ["PIURA", "CASTILLA", "VEINTISEIS DE OCTUBRE"]
CODIGO = re.compile(r"\d{11}[0-9A-ZÑ]{3,4}")  # ubigeo (6) + zona (5) + manzana (3, o 4 con letra; 9999 = dispersas)
MINIMO = {"viv": 10, "pob": 30}  # por debajo, la manzana va en gris («Pocos casos») en ese indicador
TOLERANCIA = 1e-5  # simplificación en grados (≈ 1 m en Piura)
DECIMALES = 5      # coordenadas con 5 decimales (≈ 1 m)

# Materiales de paredes que cuentan como precarios (decisión de Germán Vega, ronda 12)
PRECARIOS = ["adobe", "tapia", "quincha (cana con barro)", "piedra con barro", "madera (pona, tornillo, etc)", "triplay/ calamina/ estera"]

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
     "Viviendas con paredes exteriores de adobe, tapia, quincha, piedra con barro, madera o triplay, calamina o estera",
     "Viviendas particulares con ocupantes presentes"),
    ("i", "Piso de tierra", "viv",
     "Viviendas con piso de tierra",
     "Viviendas particulares con ocupantes presentes"),
]


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


def redondear(c):
    return [redondear(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], DECIMALES), round(c[1], DECIMALES)]


def main():
    verificar_espacio()
    import geopandas  # noqa: F401  (falla aquí, con un mensaje claro, si faltan las librerías locales)
    import pyogrio
    import shapely
    from shapely.geometry import mapping

    datos, enc = {}, {}
    for h, nombre in (("P", "POBLACION"), ("V", "VIVIENDA")):
        datos[h], enc[h] = leer_hoja(nombre)
    if (datos["P"][0] != datos["V"][0]).any():
        sys.exit("Las hojas POBLACION y VIVIENDA no traen las mismas manzanas en el mismo orden")

    # Distritos: ubigeo verificado en los datos (provincia de Piura), no supuesto
    dp0 = datos["P"]
    nombres = {norm(d).upper(): d for d in DISTRITOS}
    ubis = (dp0[(dp0[3].map(norm) == "piura") & dp0[4].map(lambda x: norm(x).upper() in nombres)]
            .groupby(1)[4].first().to_dict())
    if len(ubis) != len(DISTRITOS):
        sys.exit(f"Se esperaban {len(DISTRITOS)} distritos y se encontraron {ubis}")
    print("Ubigeos:", ubis)
    sel = dp0[1].isin(ubis)
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
    dispersa = ind["codigo"].str.endswith("9999")
    print(f"Manzanas: {len(ind)}; dispersas agrupadas (9999): {dispersa.sum()} con {ind.loc[dispersa, 'p'].sum()} habitantes "
          f"y {ind.loc[dispersa, 'v'].sum()} viviendas")

    # Cartografía: solo los tres distritos; llave UBIGEO + ZONA + MANZANA
    info = pyogrio.read_info(MANZANAS)
    capa = pyogrio.list_layers(MANZANAS)[0][0]
    print(f"Cartografía: capa {capa}, {info['features']} polígonos, {info['crs']}")
    lista = ",".join(f"'{u}'" for u in ubis)
    mz = pyogrio.read_dataframe(MANZANAS, layer=capa, where=f"UBIGEO IN ({lista})", columns=["UBIGEO", "ZONA", "MANZANA"])
    if mz.crs is None or mz.crs.to_epsg() != 4326:
        mz = mz.to_crs(4326)
    mz["codigo"] = mz["UBIGEO"] + mz["ZONA"] + mz["MANZANA"]
    if mz["codigo"].duplicated().any():
        sys.exit(f"Códigos de manzana repetidos en la cartografía: {mz.loc[mz['codigo'].duplicated(), 'codigo'].tolist()[:10]}")
    tab = ind[~dispersa]
    unidos = tab.merge(mz[["codigo", "geometry"]], on="codigo", how="left")
    sin_poligono = unidos.loc[unidos["geometry"].isna(), "codigo"].tolist()
    poligonos_sin_tabulado = int((~mz["codigo"].isin(tab["codigo"])).sum())
    tasa = 1 - len(sin_poligono) / len(tab)
    print(f"Unión: {len(tab) - len(sin_poligono)} de {len(tab)} manzanas con polígono ({100 * tasa:.2f} %); "
          f"sin polígono: {sin_poligono[:20]}; polígonos sin tabulado (sin población o en las dispersas): {poligonos_sin_tabulado}")

    unidos = unidos[unidos["geometry"].notna()]
    geoms = shapely.set_precision(shapely.simplify(unidos["geometry"].values, TOLERANCIA, preserve_topology=True), 10 ** -DECIMALES)
    vacias = shapely.is_empty(geoms).sum()
    if vacias:
        sys.exit(f"{vacias} manzanas quedaron vacías al simplificar: baja TOLERANCIA")

    # Límites de los tres distritos (INEI, CPV 2025): solo el contorno, para orientarse en el mapa
    dist = pyogrio.read_dataframe(LIMITES, where=f"UBIGEO IN ({lista})", columns=["UBIGEO"])
    if dist.crs is None or dist.crs.to_epsg() != 4326:
        dist = dist.to_crs(4326)
    if sorted(dist["UBIGEO"]) != sorted(ubis):
        sys.exit(f"Límites distritales: se encontraron {sorted(dist['UBIGEO'])}")
    limites = [{"type": "Feature", "id": u, "properties": {}, "geometry": (lambda g: {"type": g["type"], "coordinates": redondear(g["coordinates"])})(
        mapping(shapely.set_precision(shapely.simplify(geo, 1e-4, preserve_topology=True), 10 ** -DECIMALES)))}
        for u, geo in zip(dist["UBIGEO"], dist.geometry)]

    claves = [k for k, *_ in INDICADORES]
    feats = []
    for (_, r), geo in zip(unidos.iterrows(), geoms):
        g = mapping(geo)
        props = {"u": r["ubigeo"], "p": int(r["p"]), "v": int(r["v"])}
        for k in claves:
            props[k] = [int(r[k + "_n"]), int(r[k + "_d"])] + ([int(r["g_max"])] if k == "g" else [])
        feats.append({"type": "Feature", "id": r["codigo"], "properties": props,
                      "geometry": {"type": g["type"], "coordinates": redondear(g["coordinates"])}})

    # Totales por distrito: suman numeradores y denominadores, con las manzanas dispersas (no se promedian porcentajes)
    distritos = {}
    for u, d in ind.groupby("ubigeo"):
        disp = d["codigo"].str.endswith("9999")
        distritos[u] = {"nombre": ubis[u], "manzanas": int((~disp & d["codigo"].isin(unidos["codigo"])).sum()),
                        "dispersas": {"grupos": int(disp.sum()), "p": int(d.loc[disp, "p"].sum()), "v": int(d.loc[disp, "v"].sum())},
                        "p": int(d["p"].sum()), "v": int(d["v"].sum()),
                        **{k: [int(d[k + "_n"].sum()), int(d[k + "_d"].sum())] for k in claves}}
        distritos[u]["g"].append(int(d["g_max"].sum()))
    guardar("censo_piura.json", {
        "type": "FeatureCollection",
        "fuente": "INEI, Censos Nacionales 2025, tabulados por manzana entregados el 13/11/2026",
        "url": "https://www.inei.gob.pe/",
        "fecha_corte": "2026-11-13",
        "ambito": "Piura metropolitana: distritos de Piura, Castilla y Veintiséis de Octubre",
        "minimo": MINIMO,
        "indicadores": [{"k": k, "rotulo": rot, "tipo": t, "numerador": n, "denominador": d} for k, rot, t, n, d in INDICADORES],
        "validaciones": validaciones,
        "coincidencia": {"tabuladas": len(tab), "con_poligono": len(tab) - len(sin_poligono), "tasa": round(tasa, 4),
                         "sin_poligono": sin_poligono, "poligonos_sin_tabulado": poligonos_sin_tabulado},
        "distritos": distritos,
        "limites": limites,
        "features": feats,
    })
    tam = (DATOS / "censo_piura.json").stat().st_size / 2**20
    print(f"Tamaño: {tam:.2f} MB")
    if tam > 3:
        print("Aviso: pasa de 3 MB; sube TOLERANCIA o baja DECIMALES")


if __name__ == "__main__":
    main()
