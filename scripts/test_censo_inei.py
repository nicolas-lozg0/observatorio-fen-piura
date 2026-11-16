"""
Prueba de docs/data/censo_piura.json (salida de censo_inei.py). No necesita los archivos del INEI: corre también en
GitHub Actions. Revisa sumas, rango 0-100 %, tasa de coincidencia, validaciones, tamaño y coordenadas.
Correr: python3 scripts/test_censo_inei.py
"""
import json
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "docs" / "data" / "censo_piura.json"
d = json.loads(RUTA.read_text(encoding="utf-8"))
ks = [i["k"] for i in d["indicadores"]]

assert ks == list("abcdefghi"), ks
assert RUTA.stat().st_size < 3 * 2**20, "el archivo debe pesar menos de 3 MB"
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

assert len(ids) == c["con_poligono"] == sum(x["manzanas"] for x in d["distritos"].values())
# Totales por distrito = manzanas del mapa + dispersas (en los denominadores de viviendas y población)
for u, x in d["distritos"].items():
    for k in ks:
        assert 0 <= x[k][0] <= x[k][1], (u, k)
    assert x["v"] == suma[u]["b"][1] + x["dispersas"]["v"], u
    assert x["p"] == suma[u]["e"][1] + x["dispersas"]["p"], u
    assert x["b"][0] >= suma[u]["b"][0] and x["e"][0] >= suma[u]["e"][0], u
print(f"OK: {len(ids)} manzanas, {len(ks)} indicadores, coincidencia {100 * c['tasa']:.2f} %, {RUTA.stat().st_size / 2**20:.2f} MB")
