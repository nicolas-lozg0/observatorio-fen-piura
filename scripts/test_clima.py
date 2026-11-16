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

# ENFEN: encabezado del comunicado N° 20 (texto real del PDF)
TEXTO = ("COMISIÓN MULTISECTORIAL ENCARGADA DEL ESTUDIO NACIONAL DEL FENÓMENO “EL NIÑO” – ENFEN Decreto Supremo N° 007-2017-PRODUCE "
         "COMUNICADO OFICIAL ENFEN N°20-2026 13 noviembre 2026 Alerta de El Niño Costero1 EL NIÑO COSTERO CONTINUARÍA")
assert enfen.leer_comunicado(TEXTO) == ("20-2026", date(2026, 11, 13), "Alerta de El Niño costero"), enfen.leer_comunicado(TEXTO)
assert enfen.leer_comunicado(TEXTO.replace("Alerta de El Niño Costero", "No activo"))[2] == "No activo"
print("OK")
