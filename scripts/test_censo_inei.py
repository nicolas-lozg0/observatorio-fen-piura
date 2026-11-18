"""
Prueba de la salida de censo_inei.py: docs/data/censo_piura.json (base, con los hexágonos de 350 m), censo_hex10.json
(hexágonos de 131 m) y censo_manzanas.json. No necesita los archivos del INEI: corre también en GitHub Actions.
Revisa sumas, rango 0-100 %, tasa de coincidencia, validaciones, tamaño, coordenadas y cortes de las clases.
Correr: python3 scripts/test_censo_inei.py
"""
import json
from pathlib import Path

DATOS = Path(__file__).resolve().parent.parent / "docs" / "data"
RUTA = DATOS / "censo_piura.json"
d = json.loads(RUTA.read_text(encoding="utf-8"))
d["features"] = json.loads((DATOS / "censo_manzanas.json").read_text(encoding="utf-8"))["features"]
h10 = json.loads((DATOS / "censo_hex10.json").read_text(encoding="utf-8"))
ks = [i["k"] for i in d["indicadores"]]

assert ks == list("abcdefghi"), ks
for nombre in ("censo_piura.json", "censo_hex10.json", "censo_manzanas.json"):
    assert (DATOS / nombre).stat().st_size < 3 * 2**20, f"{nombre} debe pesar menos de 3 MB"
assert RUTA.stat().st_size < 0.5 * 2**20, "la base (se carga al abrir la pestaña) debe ser liviana"
# 5 clases: 4 cortes fijos crecientes entre 0 y 100 (ronda 17: una escala en palabras para servicios y vivienda)
cortes = {i["k"]: i["cortes"] for i in d["indicadores"]}
for k, c in cortes.items():
    assert len(c) == 4 and all(0 < a < b < 100 for a, b in zip(c, c[1:])), (k, c)
assert all(cortes[k] == [5, 20, 50, 80] for k in "abcdhi")
assert [len(i.get("palabras", [])) for i in d["indicadores"]] == [5, 5, 5, 5, 0, 0, 0, 5, 5]
assert cortes["e"] == [15, 20, 25, 30] and cortes["f"] == [4, 8, 12, 16] and cortes["g"] == [30, 50, 65, 80]
assert "adobe" in [i for i in d["indicadores"] if i["k"] == "h"][0]["numerador"] and "no incluye adobe" in [i for i in d["indicadores"] if i["k"] == "h"][0]["numerador"]
# Localidades: Ciudad de Piura primero y luego los centros poblados de 2000 viviendas o más, cada uno con su archivo
locs = d["localidades"]
assert locs[0]["id"] == "metro" and locs[0]["nombre"] == "Ciudad de Piura" and len(locs) == 8, [x["id"] for x in locs]
for x in locs:
    assert all(0 <= x[k][0] <= x[k][1] for k in ks), x["id"]
    if x["id"] == "metro":
        continue
    assert x["v"] >= 2000 and (DATOS / x["archivo"]).stat().st_size < 1 * 2**20, (x["id"], x["v"])
    f = json.loads((DATOS / x["archivo"]).read_text(encoding="utf-8"))
    mzl = [m["properties"] for m in f["manzanas"]["features"] if "km2" not in m["properties"]]
    assert "hex10" not in f  # ronda 17: las localidades van de 350 m a manzanas
    for nivel in ("hexagonos",):  # los hexágonos de cada localidad suman lo mismo que sus manzanas
        for k in ks:
            assert sum(h["properties"][k][1] for h in f[nivel]["features"]) == sum(m[k][1] for m in mzl), (x["id"], nivel, k)
    # el total de la localidad (con sus dispersas) es la suma de sus manzanas con polígono más las dispersas
    assert x["v"] == sum(m["properties"]["v"] for m in f["manzanas"]["features"]) + x["dispersas"]["v"], x["id"]
assert set(d["distritos"]) == {"200101", "200104", "200115"}, d["distritos"].keys()
assert all(v["filas_con_diferencia"] == 0 for v in d["validaciones"]), [v for v in d["validaciones"] if v["filas_con_diferencia"]]
c = d["coincidencia"]
assert c["tasa"] >= 0.99 and c["con_poligono"] == c["tabuladas"] - len(c["sin_poligono"]), c

ids = set()
suma = {u: {k: [0, 0] for k in ks} for u in d["distritos"]}
for f in d["features"]:
    p = f["properties"]
    assert f["id"] not in ids and not f["id"].endswith("9999"), f["id"]  # sin repetidos ni dispersas en el mapa
    ids.add(f["id"])
    assert f["id"].startswith(p["u"]) and p["u"] in d["distritos"], f["id"]
    for k in ks:
        n, den = p[k][:2]
        assert 0 <= n <= den, (f["id"], k, p[k])  # porcentaje entre 0 y 100
        suma[p["u"]][k][0] += n
        suma[p["u"]][k][1] += den
    assert p["g"][0] <= p["g"][2] <= p["g"][1], (f["id"], p["g"])  # mínimo ≤ máximo ≤ población
    assert p["a"][1] == p["b"][1] == p["h"][1] == p["i"][1] == p["v"] and p["e"][1] == p["p"], f["id"]
    lon, lat = f["geometry"]["coordinates"][0][0][0] if f["geometry"]["type"] == "MultiPolygon" else f["geometry"]["coordinates"][0][0]
    assert -81.4 < lon < -79.2 and -6.4 < lat < -4.0, (f["id"], lon, lat)  # WGS84 (no UTM), dentro del departamento de Piura

# Manzanas extensas (campus de la UDEP, aeropuerto): marcadas con su área; el resto, sin marca
def km2_aprox(geo):
    """Área aproximada (fórmula del cordón, grados → km² con cos 5,2° ≈ 0,996), sin librerías: corre en Actions."""
    anillo = lambda r: abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:]))) / 2
    pols = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
    return sum(anillo(p[0]) - sum(anillo(h) for h in p[1:]) for p in pols) * 111.32 ** 2 * 0.996


extensas = {f["id"]: f["properties"] for f in d["features"] if "km2" in f["properties"]}
assert {"20010100300059", "20010401400006A"} <= set(extensas), "el campus de la UDEP y el aeropuerto deben ser extensas"
for k, p in extensas.items():
    assert p["km2"] > 0.05 and p["v"] < 1000 * p["km2"], (k, p["km2"], p["v"])
for f in d["features"]:
    if "km2" not in f["properties"]:  # área aproximada en grados → km² (cos 5,2° ≈ 0,996): ninguna grande y vacía sin marca
        km2 = km2_aprox(f["geometry"])
        assert not (km2 > 0.06 and f["properties"]["v"] < 900 * km2), (f["id"], km2, f["properties"]["v"])
# Denominador 0 en algún indicador: existen (la página no las dibuja); nunca un numerador mayor que 0 sobre 0
assert any(f["properties"]["d"][1] == 0 for f in d["features"])
assert all(not (f["properties"][k][1] == 0 and f["properties"][k][0] > 0) for f in d["features"] for k in ks)

# Hexágonos: suman exactamente las manzanas que no son extensas (numeradores, denominadores y número de manzanas)
hx = d["hexagonos"]["features"]
assert d["hexagonos"]["resolucion"] == 9 and d["hexagonos"]["minimo"] == 30
assert h10["resolucion"] == 10 and h10["minimo"] == 20
normales = [f["properties"] for f in d["features"] if "km2" not in f["properties"]]
for nivel in (hx, h10["features"]):  # los dos niveles suman lo mismo que las manzanas
    assert len({h["id"] for h in nivel}) == len(nivel)
    assert sum(h["properties"]["m"] for h in nivel) == len(normales)
    for k in ks:
        for j in (0, 1):
            assert sum(h["properties"][k][j] for h in nivel) == sum(p[k][j] for p in normales), (k, j)
        assert all(0 <= h["properties"][k][0] <= h["properties"][k][1] for h in nivel), k
assert sum(1 for h in hx if h["properties"]["n"]) > 0.8 * len(hx), "la mayoría de los sectores debe tener nombre"
assert all(set(i["frase"]) and len(i["frase"]) == 3 for i in d["indicadores"])

# Ciudad de Piura: sus manzanas del mapa; la coincidencia cuenta las de todas las localidades
assert len(ids) == locs[0]["manzanas"] == sum(x["manzanas"] for x in d["distritos"].values())
assert c["con_poligono"] == sum(x["manzanas"] for x in locs)
# Totales por distrito = manzanas del mapa + dispersas (en los denominadores de viviendas y población)
for u, x in d["distritos"].items():
    for k in ks:
        assert 0 <= x[k][0] <= x[k][1], (u, k)
    assert x["v"] == suma[u]["b"][1] + x["dispersas"]["v"], u
    assert x["p"] == suma[u]["e"][1] + x["dispersas"]["p"], u
    assert x["b"][0] >= suma[u]["b"][0] and x["e"][0] >= suma[u]["e"][0], u
print(f"OK: {len(ids)} manzanas, {len(ks)} indicadores, coincidencia {100 * c['tasa']:.2f} %, {RUTA.stat().st_size / 2**20:.2f} MB")

# Vista de número (ronda 17): densidad por hectárea de manzana. Cada sector trae el área de sus manzanas, que suma la de ellas,
# y los cortes de densidad son fijos por grupo de indicadores
dens = {i["k"]: i["densidad"] for i in d["indicadores"]}
assert all(dens[k] == [5, 10, 20, 40] for k in "abcdhif") and dens["e"] == [10, 20, 40, 80] and dens["g"] == [25, 50, 100, 200]
assert all(h["properties"]["ha"] > 0 for h in d["hexagonos"]["features"] + h10["features"])
assert all("ha" in f["properties"] for f in d["features"])
area_mz = sum(f["properties"]["ha"] for f in d["features"] if "km2" not in f["properties"])
area_hex = sum(h["properties"]["ha"] for h in d["hexagonos"]["features"])
assert abs(area_mz - area_hex) / area_mz < 0.01, (area_mz, area_hex)
print(f"Densidad: {area_hex:.0f} ha de manzanas en los sectores de Ciudad de Piura (manzanas: {area_mz:.0f} ha)")

# Nombres de los sectores (ronda 18): «Sector …» o vacío, sin «Asentamiento Humano» ni «AA.HH.» (pasan a «A. H.»), sin espacios dobles
import re as _re
nombres = [h["properties"]["n"] for h in d["hexagonos"]["features"]]
assert all(n == "" or n.startswith("Sector ") for n in nombres), [n for n in nombres if n and not n.startswith("Sector ")][:5]
assert not [n for n in nombres if _re.search(r"(?i)asentamiento humano|AA\.?HH|  ", n)], [n for n in nombres if _re.search(r"(?i)asentamiento humano|AA\.?HH|  ", n)][:5]
assert "Piura metropolitana" not in RUTA.read_text(encoding="utf-8")

# Resumen de la portada (rondas 19 y 20): la ciudad y cada distrito, sin desagüe por red pública, iguales al archivo completo
res = json.loads((RUTA.parent / "censo_resumen.json").read_text(encoding="utf-8"))
assert res["sin_desague"] == locs[0]["a"], res["sin_desague"]
assert res["distritos_sin_desague"] == [[x["nombre"], *x["a"]] for x in d["distritos"].values()], res["distritos_sin_desague"]
assert sum(x[1] for x in res["distritos_sin_desague"]) == res["sin_desague"][0]
