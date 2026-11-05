"""
Gasto de emergencia por el Fenómeno El Niño (FEN) en Piura, según la consulta del MEF
"Ejecución del Gasto de Emergencia" (https://apps5.mineco.gob.pe/emergencia_lluvias/).

La consulta tiene una página de "Descargas - Datos Abiertos" que entrega un CSV con todo el año al
pulsar "Exportar a CSV" (formulario ASP.NET). Este script hace esa misma consulta.

Ojo: en ese CSV los nombres de las columnas de montos están corridos una posición respecto de lo
que muestra el navegador del MEF (por ejemplo, el marco presupuestal viene bajo MONTO_ASIGNACION).
Por eso el script compara las sumas del CSV con el TOTAL del navegador y asigna cada monto a la
columna cuya suma coincide; si no coinciden, se detiene. Resultado: docs/data/fen_piura.json.
"""
import html
import io
import re
import urllib.parse
import urllib.request
from datetime import datetime
from http.cookiejar import CookieJar

import pandas as pd

from comun import PERU, guardar, verificar_espacio

BASE = "https://apps5.mineco.gob.pe/emergencia_lluvias"
DESCARGA = BASE + "/Descarga/DatosAbiertos/Default.aspx"
NAVEGADOR = BASE + "/Navegador/Navegar.aspx"
P = "ctl00$ctl00$CPH1$RptPH1$"
ANIO = datetime.now(PERU).year
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
MONTOS = ["MONTO_ASIGNACION", "MARCO_PRESUPUESTAL", "MONTO_CERTIFICADO", "MONTO_COMPROMETIDO_ANUAL", "MONTO_DEVENGADO"]


def campos_ocultos(pagina):
    f = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*>', pagina):
        n, v = re.search(r'name="([^"]+)"', m.group(0)), re.search(r'value="([^"]*)"', m.group(0))
        f[n.group(1)] = html.unescape(v.group(1)) if v else ""
    return f


def descargar_csv(web, anio):
    pagina = web.open(DESCARGA, timeout=60).read().decode("utf-8", "replace")
    datos = {**campos_ocultos(pagina), P + "LstAnoEje": str(anio), P + "btnExportarCSV": "Exportar a CSV"}
    r = web.open(DESCARGA, urllib.parse.urlencode(datos).encode(), timeout=180)
    if "csv" not in (r.headers.get("Content-Type") or "").lower():
        raise SystemExit("La consulta FEN no devolvió un CSV (puede haber cambiado el formulario).")
    return pd.read_csv(io.BytesIO(r.read()), dtype=str, encoding="utf-8-sig")


def total_navegador(web):
    """Fila TOTAL del navegador: marco presupuestal, certificación, compromiso anual, devengado; y fecha."""
    texto = html.unescape(re.sub(r"<[^>]+>", "|", web.open(NAVEGADOR, timeout=60).read().decode("utf-8", "replace")))
    texto = re.sub(r"[\s|]+", "|", texto)
    m = re.search(r"\|TOTAL\|([\d,]+)\|([\d,]+)\|([\d,]+)\|([\d,]+)\|", texto)
    f = re.search(r"actualización:\|(\d+)\|de\|(\w+)\|de\|(\d{4})", texto)
    if not m:
        raise SystemExit("No se pudo leer el TOTAL del navegador FEN.")
    if not f:  # sin fecha, la página no podría avisar que el dato quedó viejo
        raise SystemExit("No se pudo leer la fecha de actualización del navegador FEN.")
    total = dict(zip(["marco", "certificado", "comprometido", "devengado"], (int(x.replace(",", "")) for x in m.groups())))
    fecha = f"{int(f.group(3))}-{MESES.index(f.group(2).lower()) + 1:02d}-{int(f.group(1)):02d}"
    return total, fecha


def main():
    verificar_espacio()
    web = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    # A inicios de año la consulta puede no tener aún el año en curso: se usa el anterior.
    # shortcut: no verificado en un mes de enero real; si el navegador del MEF muestra otro año, la comparación
    # de totales de abajo no cuadra y el script se detiene con error (no publica cifras mezcladas).
    anio, df = ANIO, None
    try:
        df = descargar_csv(web, anio)
    except SystemExit as e:
        print(f"Consulta FEN {anio}: {e}")
    if df is None or df.empty:
        anio = ANIO - 1
        print(f"Se usa el año {anio}.")
        df = descargar_csv(web, anio)
    total, fecha = total_navegador(web)
    for c in MONTOS:
        df[c] = pd.to_numeric(df[c])
    sumas = df[MONTOS].sum()
    columna = {}
    for k, v in total.items():  # columna del CSV cuya suma coincide con el TOTAL del navegador
        coincide = [c for c in MONTOS if abs(sumas[c] - v) < 1]
        if v and not coincide:
            raise SystemExit(f"El CSV no cuadra con el navegador para '{k}': {v:,} vs {sumas.to_dict()}")
        columna[k] = coincide[0] if coincide else "MONTO_DEVENGADO"
    print("Columnas usadas:", columna, "| total nacional:", total)

    df["AMBITO"] = (df["DEPARTAMENTO_META_NOMBRE"] == "PIURA") * 1 + (df["DEPARTAMENTO_EJECUTORA_NOMBRE"] == "PIURA") * 2
    p = df[df["AMBITO"] > 0].rename(columns={v: k for k, v in columna.items()})
    clave = ["AMBITO", "TIPO_GOBIERNO_NOMBRE", "PLIEGO_NOMBRE", "PRODUCTO_PROYECTO", "PRODUCTO_PROYECTO_NOMBRE"]
    agr = p.groupby(clave, as_index=False)[list(total)].sum()
    print(f"Piura: {len(p)} filas; marco {agr['marco'].sum():,.0f}; devengado {agr['devengado'].sum():,.0f}")
    guardar("fen_piura.json", {
        "fuente": "MEF, Ejecución del Gasto de Emergencia - Fenómeno El Niño (Consulta Amigable, datos abiertos)",
        "url": BASE + "/Navegador/default.aspx",
        "fecha_corte": fecha,
        "anio": anio,
        "total_nacional": total,
        "columnas": ["ambito", "nivel", "pliego", "codigo", "nombre", *total],
        "filas": agr.values.tolist(),
    })


if __name__ == "__main__":
    main()
