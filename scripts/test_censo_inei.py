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
# 7 clases: 6 cortes crecientes entre 0 y 100; las edades con cortes propios
for i in d["indicadores"]:
    assert len(i["cortes"]) == 6 and all(0 < a < b < 100 for a, b in zip(i["cortes"], i["cortes"][1:])), (i["k"], i["cortes"])
assert {i["k"]: i["cortes"] for i in d["indicadores"]}["e"] == [15, 20, 25, 30, 35, 40]
assert {i["k"]: i["cortes"] for i in d["indicadores"]}["a"] == [5, 10, 20, 40, 60, 80]
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

assert len(ids) == c["con_poligono"] == sum(x["manzanas"] for x in d["distritos"].values())
# Totales por distrito = manzanas del mapa + dispersas (en los denominadores de viviendas y población)
for u, x in d["distritos"].items():
    for k in ks:
        assert 0 <= x[k][0] <= x[k][1], (u, k)
    assert x["v"] == suma[u]["b"][1] + x["dispersas"]["v"], u
    assert x["p"] == suma[u]["e"][1] + x["dispersas"]["p"], u
    assert x["b"][0] >= suma[u]["b"][0] and x["e"][0] >= suma[u]["e"][0], u
print(f"OK: {len(ids)} manzanas, {len(ks)} indicadores, coincidencia {100 * c['tasa']:.2f} %, {RUTA.stat().st_size / 2**20:.2f} MB")
