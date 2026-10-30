"""
Obras públicas en Piura según Infobras (Contraloría): conteo por estado y lista de obras en ejecución y paralizadas.

Infobras publica cada día un Excel con todas las obras del país; el nombre del archivo lleva la
fecha, así que el enlace se toma de la página de descargas. Se guarda solo Piura y no se guardan
nombres de personas (supervisores, residentes). Resultado: docs/data/infobras_piura.json.
"""
import html
import re
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path

import openpyxl

from comun import descargar, guardar, verificar_espacio

BASE = "https://infobras.contraloria.gob.pe"
PAGINA = BASE + "/InfobrasWeb/DataSets"
CAMPOS = {  # columna en Infobras -> nombre corto en el JSON
    "Código INFOBRAS": "codigo_infobras",
    "Nombre de obra": "obra",
    "Entidad Pública": "entidad",
    "Nivel de gobierno": "nivel",
    "Codigo unico de inversión": "cui",
    "Provincia": "provincia",
    "Distrito": "distrito",
    "Avance Físico Real Acumulado (%)": "avance_fisico",
    "Año de avance": "anio_avance",
    "Mes de avance": "mes_avance",
    "Causal de paralización": "causal",
    "Fecha de paralización": "fecha_paralizacion",
    "Número de dias paralizado": "dias_paralizado",
    "Costo de obra en soles según ET en soles": "costo_et",
    "Marca Reconstrucción con Cambios (Si/No)": "rcc",
}
# Infobras pierde la Ñ en algunos nombres (la reemplaza por un espacio)
CORRECCIONES = {"PARI AS": "PARIÑAS"}
ACTIVAS = {"En Ejecución", "Paralizada"}  # las que se listan; las demás solo se cuentan
NUMEROS = {"avance_fisico", "costo_et", "dias_paralizado"}


def numero(v):
    """Infobras escribe algunos decimales con espacio ('1205287 56' = 1205287.56)."""
    if v in (None, ""):
        return None
    try:
        return float(str(v).strip().replace(" ", "."))
    except ValueError:
        return None


def enlace_descarga():
    pagina = urllib.request.urlopen(PAGINA, timeout=60).read().decode("utf-8", "replace")
    m = re.search(r'href="(/InfobrasWeb/Archivo/DownloadFile\?filename=DataSet-Obras-Publicas[^"]+)"', pagina)
    if not m:
        raise SystemExit("No se encontró el enlace del dataset de obras en " + PAGINA)
    return BASE + html.unescape(m.group(1)).replace(" ", "%20")


def main():
    verificar_espacio()
    url = enlace_descarga()
    print("Descargando", url)
    with tempfile.TemporaryDirectory() as tmp:
        archivo = Path(tmp) / "obras.xlsx"
        descargar(url, archivo)
        hoja = openpyxl.load_workbook(archivo, read_only=True).worksheets[0]
        filas = hoja.iter_rows(values_only=True)
        cabecera = [next(filas) for _ in range(4)]
        fecha_consulta = str(cabecera[2][0]).replace("Fecha de consulta:", "").strip()
        titulos = [str(t).strip() if t else "" for t in cabecera[3]]
        ix = {t: titulos.index(t) for t in [*CAMPOS, "Departamento", "Estado de ejecución"]}

        estados, nacional, obras = Counter(), 0, []
        for f in filas:
            nacional += 1
            if f[ix["Departamento"]] != "PIURA":
                continue
            estado = f[ix["Estado de ejecución"]] or "Sin dato"
            estados[estado] += 1
            if estado in ACTIVAS:
                o = {corto: f[ix[largo]] for largo, corto in CAMPOS.items()}
                o["distrito"] = CORRECCIONES.get(o["distrito"], o["distrito"])
                obras.append({"estado": estado, **{k: numero(v) if k in NUMEROS else v for k, v in o.items()}})
        hoja.parent.close()

    if not estados:
        raise SystemExit("No se encontraron obras de Piura: revisar el archivo de Infobras.")
    print(f"{nacional:,} obras en el país; Piura: {dict(estados)}")
    guardar("infobras_piura.json", {
        "fuente": "Contraloría General de la República, Infobras (Dataset de obras públicas)",
        "url": PAGINA,
        "fecha_corte": fecha_consulta,
        "obras_piura": sum(estados.values()),
        "por_estado": dict(estados.most_common()),
        "obras": sorted(obras, key=lambda o: -(o["costo_et"] or 0)),
    })


if __name__ == "__main__":
    main()
