"""
Límites distritales de Piura para el mapa de la página (se corre una sola vez, no a diario).

Toma el GeoJSON distrital público de github.com/juaneladio/peru-geojson (límites INEI 2007, licencia MPL 2.0),
se queda con Piura y convierte cada distrito en un trazado SVG ya proyectado y simplificado, para que la
página no necesite librerías de mapas. Resultado: docs/data/piura_distritos.json.

Ojo: por ser de 2007, no trae Veintiséis de Octubre (creado en 2013 a partir del distrito de Piura), y
Bellavista (Sullana) viene sin polígono.
"""
import json
import math
import urllib.request

from comun import guardar

URL = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_distrital_simple.geojson"
ANCHO = 600


def main():
    g = json.load(urllib.request.urlopen(URL, timeout=120))
    # Bellavista (Sullana, 200602) viene sin geometría en la fuente: queda fuera del mapa
    feats = [f for f in g["features"] if f["properties"]["IDDPTO"] == "20" and f["geometry"]]
    anillos = lambda geo: geo["coordinates"] if geo["type"] == "Polygon" else [r for p in geo["coordinates"] for r in p]
    pts = [p for f in feats for r in anillos(f["geometry"]) for p in r]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = math.cos(math.radians((lat0 + lat1) / 2))  # corrige el ancho de los grados de longitud
    escala = ANCHO / ((lon1 - lon0) * k)
    alto = round((lat1 - lat0) * escala)
    distritos = {}
    for f in feats:
        partes = []
        for r in anillos(f["geometry"]):
            xy = []
            for lon, lat in r:
                p = (round((lon - lon0) * k * escala, 1), round((lat1 - lat) * escala, 1))
                if not xy or p != xy[-1]:
                    xy.append(p)
            if len(xy) > 3:
                partes.append("M" + "L".join(f"{x:g},{y:g}" for x, y in xy) + "Z")
        p = f["properties"]
        distritos[p["IDDIST"]] = {"nombre": p["NOMBDIST"], "provincia": p["NOMBPROV"], "d": "".join(partes)}
    assert len(distritos) >= 63, len(distritos)
    guardar("piura_distritos.json", {
        "fuente": "INEI 2007, vía github.com/juaneladio/peru-geojson (MPL 2.0)",
        "url": "https://github.com/juaneladio/peru-geojson",
        "nota": "Límites de 2007: Veintiséis de Octubre (2013) aparece dentro del distrito de Piura. "
                "Bellavista (Sullana) viene sin polígono en la fuente y no se dibuja.",
        "viewBox": f"0 0 {ANCHO} {alto}",
        "distritos": distritos,
    })


if __name__ == "__main__":
    main()
