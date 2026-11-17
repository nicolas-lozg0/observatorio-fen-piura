"""
Prueba de los lectores de Clima con textos de ejemplo (sin red): lluvia del Senamhi, temperatura del mar (OPeNDAP) y
comunicado del ENFEN. Correr: python3 scripts/test_clima.py
"""
from datetime import date

import enfen
import lluvia_senamhi
import tsm_paita

# Senamhi: ventana de estación con un día sin dato (null) y otra de fuera de Piura
VENTANA = """subtitle: { text: "Dep.: PIURA Prov.: MORROPON Dist.: MORROPON<br>Lat.: 5° S" },
xAxis: [{ categories: ['2026-11-14','2026-11-15','2026-11-16'] }],
series: [{ name: 'Precipitaci\\u00F3n', type: 'column', data: [2.1, 34.3, null, ] },
         { name: 'Temp. max', data: [32.8, 31.0, null] }]"""
lluvia_senamhi.leer = lambda url: VENTANA
e = lluvia_senamhi.estacion({"nom": "MORROPON ", "cod": "105106", "estado": "REAL", "ico": "M", "cate": "CO", "lat": -5.2, "lon": -80.0})
assert e["nombre"] == "MORROPON" and e["provincia"] == "MORROPON", e
assert e["serie"] == [["2026-11-14", 2.1], ["2026-11-15", 34.3], ["2026-11-16", None]], e["serie"]  # null no es 0
lluvia_senamhi.leer = lambda url: VENTANA.replace("PIURA", "LAMBAYEQUE")
assert lluvia_senamhi.estacion({"nom": "X", "cod": "1", "estado": "REAL", "ico": "M", "cate": "CO", "lat": 0, "lon": 0}) is None
try:  # si la página cambia y no trae la serie, debe fallar (no guardar ceros)
    lluvia_senamhi.leer = lambda url: VENTANA.replace("Precipitaci", "Lluvia")
    lluvia_senamhi.estacion({"nom": "X", "cod": "1", "estado": "REAL", "ico": "M", "cate": "CO", "lat": 0, "lon": 0})
    raise AssertionError("debía fallar sin serie de precipitación")
except ValueError:
    pass

# OPeNDAP: valores en orden y el valor de relleno como sin dato
ASCII = "Dataset {...}\n---\nsst.sst[3][1][1]\n[0][0], 27.3\n[1][0], -9.96921E36\n[2][0], 27.48\n\nsst.time[3]\n82860.0"
assert tsm_paita.valores(ASCII) == [27.3, None, 27.48], tsm_paita.valores(ASCII)

# IMERG: rejilla de OPeNDAP (el −9999,9 es sin dato) y celdas dentro del departamento
import imerg_piura  # noqa: E402
TXT = "Dataset {...}\n---\nprecipitation.precipitation[1][2][3]\n[0][0], 0.5, -9999.9, 2\n[0][1], 1, 1.5, 0\n"
assert imerg_piura.rejilla(TXT, 2, 3) == [[0.5, None, 2.0], [1.0, 1.5, 0.0]]
anillos = imerg_piura.anillos_piura()
assert imerg_piura.dentro(-80.63, -5.19, anillos) and not imerg_piura.dentro(-81.4, -5.1, anillos)  # Piura sí; el mar no
assert not imerg_piura.dentro(-80.45, -3.57, anillos)  # Tumbes no

# NOAA CPC, Niño 1+2: cifras pegadas («20.6-0.1») y cabeceras que no son datos
import nino12_cpc  # noqa: E402
CPC = (" Weekly SST data starts week centered on 2Sept1981\n\n                Nino1+2      Nino3        Nino34        Nino4\n"
       " Week          SST SSTA     SST SSTA     SST SSTA     SST SSTA\n"
       " 02SEP1981     20.6-0.1     24.8-0.1     26.5-0.2     28.3-0.3\n"
       " 11NOV2026     27.1 5.4     29.4 4.3     29.9 3.2     29.9 1.3\n")
assert nino12_cpc.leer(CPC) == [["1981-09-02", 20.6, -0.1], ["2026-11-11", 27.1, 5.4]], nino12_cpc.leer(CPC)

# ENFEN: números de comunicado en la portada (texto real de los enlaces); el más reciente se compara por (año, número)
PORTADA = '<a href="/download/x/">Comunicado Oficial Enfen N° 20-2026</a> <a href="/download/y/">Comunicado Oficial Enfen N° 19-2026</a>'
assert enfen.numeros(PORTADA) == [(2026, 20), (2026, 19)], enfen.numeros(PORTADA)
assert max(enfen.numeros(PORTADA + "Comunicado Oficial Enfen N° 1-2027")) == (2027, 1)  # el N.° 1 de 2027 es más reciente que el 20 de 2026

# Manual: el JSON del ENFEN tiene los campos que usa la tarjeta, con fechas válidas
import json  # noqa: E402
from comun import DATOS  # noqa: E402
c = json.loads((DATOS / "enfen_comunicado.json").read_text(encoding="utf-8"))
assert {"numero", "fecha_corte", "estado", "magnitud", "horizonte", "puntos", "url_pdf", "proximo", "paita_costera"} <= set(c), set(c)
assert 2 <= len(c["puntos"]) <= 3 and all(len(p.split()) <= 20 for p in c["puntos"]), c["puntos"]
assert date.fromisoformat(c["fecha_corte"]) < date.fromisoformat(c["proximo"])
print("OK")
