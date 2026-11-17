"""
Lluvia diaria de las estaciones convencionales del Senamhi en el departamento de Piura (pestaña Clima).

Fuente: el mapa de estaciones del Senamhi (https://www.senamhi.gob.pe/mapas/mapa-estaciones-2/). La lista de estaciones
viene en el HTML del mapa; la ventana de cada estación (map_red_graf.php) trae un gráfico con la lluvia diaria de los
últimos ~31 días. No es una descarga oficial: se leen los arreglos del gráfico. Si el Senamhi cambia la página, el script
se detiene con un mensaje y la página conserva el último dato con su fecha.

Solo estaciones convencionales al día (estado REAL): las automáticas solo publican las últimas 24 h corridas y las
«diferidas» llegan con un mes de retraso. Un día sin dato queda como null (nunca como 0).

Resultado: docs/data/lluvia_piura.json. Uso: python3 scripts/lluvia_senamhi.py
"""
import json
import re
import sys
import time

from comun import abrir, guardar

MAPA = "https://www.senamhi.gob.pe/mapas/mapa-estaciones-2/"
ESTACION = MAPA + "map_red_graf.php?cod={cod}&estado={estado}&tipo_esta={ico}&cate={cate}&cod_old="
CONVENCIONALES = {"CO", "CP", "MAP", "PLU"}  # climatológica ordinaria y principal, agrometeorológica principal, pluviométrica
CAJA = (-6.4, -4.0, -81.4, -79.2)  # lat y lon del departamento de Piura, con margen; se confirma con «Dep.: PIURA»
SERIES = ["105012", "105106", "104058"]  # Bernal (Bajo Piura, 31 km de la ciudad), Morropón y Ayabaca: series de 30 días
MINIMO = 10  # estaciones de Piura que deben leerse; menos indica que la página cambió


def leer(url):
    with abrir(url, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def arreglo(texto):
    """'[1.0, null, 2.5]' → [1.0, None, 2.5]"""
    return [None if x.strip() in ("null", "") else float(x) for x in texto.strip().rstrip(",").split(",")]


def estacion(e):
    """Lluvia diaria de una estación: dict con ubicación y serie [[fecha, mm o None], …], o None si no es de Piura."""
    h = leer(ESTACION.format(**e))
    sub = re.search(r"Dep\.:\s*([^<]+?)\s*Prov\.:\s*([^<]+?)\s*Dist\.:\s*([^<]+?)\s*<br>", h)
    if not sub:
        raise ValueError(f"{e['nom']} ({e['cod']}): no se encontró la ubicación (¿cambió la página?)")
    if sub.group(1).strip().upper() != "PIURA":
        return None
    fechas = re.search(r"categories\s*:\s*\[([^\]]*)\]", h)
    pp = re.search(r"name\s*:\s*'Precipitaci[^']*'.*?data\s*:\s*\[([^\]]*)\]", h, re.S)
    if not (fechas and pp):
        raise ValueError(f"{e['nom']} ({e['cod']}): no se encontró la serie de precipitación")
    fechas = re.findall(r"'(\d{4}-\d{2}-\d{2})'", fechas.group(1))
    valores = arreglo(pp.group(1))
    if len(fechas) != len(valores):
        raise ValueError(f"{e['nom']} ({e['cod']}): {len(fechas)} fechas y {len(valores)} valores")
    return {"cod": e["cod"], "nombre": e["nom"].strip(), "provincia": sub.group(2).strip(), "distrito": sub.group(3).strip(),
            "lat": e["lat"], "lon": e["lon"], "serie": [[f, v] for f, v in zip(fechas, valores)]}


def main():
    # el mapa escribe algunas coordenadas sin el cero inicial (-.1172), que no es JSON válido
    lista = [json.loads(re.sub(r"(:\s*-?)\.(\d)", r"\g<1>0.\2", m)) for m in re.findall(r'\{"nom":[^{}]*\}', leer(MAPA))]
    if not lista:
        sys.exit("No se encontró la lista de estaciones en el mapa del Senamhi (¿cambió la página?)")
    candidatas = [e for e in lista if e.get("cate") in CONVENCIONALES and e.get("estado") == "REAL"
                  and CAJA[0] <= e["lat"] <= CAJA[1] and CAJA[2] <= e["lon"] <= CAJA[3]]
    print(f"Estaciones en el mapa: {len(lista)}; convencionales al día cerca de Piura: {len(candidatas)}")
    estaciones, errores = [], []
    for e in candidatas:
        try:
            x = estacion(e)
            if x:
                estaciones.append(x)
        except (OSError, ValueError) as err:
            errores.append(str(err))
        time.sleep(0.5)  # sin apuro: una consulta cada medio segundo
    for err in errores:
        print("  Aviso:", err)
    if len(estaciones) < MINIMO:
        sys.exit(f"Solo se leyeron {len(estaciones)} estaciones de Piura (mínimo {MINIMO}): no se guarda nada")
    faltan = [c for c in SERIES if c not in {x["cod"] for x in estaciones}]
    if faltan:
        print("  Aviso: faltan estaciones de las series:", faltan)
    con_dato = [f for x in estaciones for f, v in x["serie"] if v is not None]
    ultimo = max(con_dato)
    print(f"Estaciones de Piura: {len(estaciones)}; último día con dato: {ultimo} "
          f"({sum(1 for x in estaciones if dict(x['serie']).get(ultimo) is not None)} con dato ese día)")
    guardar("lluvia_piura.json", {
        "fuente": "Senamhi, mapa de estaciones (estaciones convencionales)",
        "url": MAPA,
        "fecha_corte": ultimo,
        "series": SERIES,
        "estaciones": sorted(estaciones, key=lambda x: x["nombre"]),
    })


if __name__ == "__main__":
    main()
