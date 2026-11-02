"""
Avance físico y ubicación (provincia, distrito) de las inversiones con gasto en Piura.

Fuente: MEF, Detalle de inversiones (DETALLE_INVERSIONES.csv, incluye el avance del Formato 12-B).
Lee el archivo por partes mientras se descarga y guarda solo las inversiones cuyo código único (CUI)
aparece como proyecto en docs/data/gasto_piura.json o en una obra activa de docs/data/infobras_piura.json, o que
están ubicadas en Piura y tienen PIM este año.
Resultado: docs/data/inversiones_piura.json. Requiere haber corrido antes gasto_mef.py (e infobras.py, si existe).
"""
import json
import urllib.request

import pandas as pd

from comun import DATOS, fecha_modificacion, guardar, verificar_espacio

URL = "https://fs.datosabiertos.mef.gob.pe/datastorefiles/DETALLE_INVERSIONES.csv"
COLUMNAS = ["CODIGO_UNICO", "DEPARTAMENTO", "PROVINCIA", "DISTRITO", "COSTO_ACTUALIZADO",
            "PIM_ANIO_ACTUAL", "AVANCE_FISICO", "AVANCE_EJECUCION", "TIENE_F12B", "IND_IOARR_EMERG"]


def main():
    verificar_espacio()
    gasto = json.loads((DATOS / "gasto_piura.json").read_text(encoding="utf-8"))
    i_tipo, i_cod = gasto["columnas"].index("tipo"), gasto["columnas"].index("codigo")
    proyectos = {f[i_cod] for f in gasto["filas"] if f[i_tipo] == "2"}
    obras = DATOS / "infobras_piura.json"
    cui_obras = {str(o["cui"]).strip() for o in json.loads(obras.read_text(encoding="utf-8"))["obras"] if o["cui"]} if obras.exists() else set()

    fecha = fecha_modificacion(URL)
    print(f"Leyendo {URL} (modificado {fecha})")
    partes, n = [], 0
    with urllib.request.urlopen(URL, timeout=120) as r:
        for ch in pd.read_csv(r, dtype=str, encoding="utf-8-sig", usecols=COLUMNAS, chunksize=50_000):
            verificar_espacio()
            n += len(ch)
            pim = pd.to_numeric(ch["PIM_ANIO_ACTUAL"], errors="coerce").fillna(0)
            partes.append(ch[ch["CODIGO_UNICO"].isin(proyectos | cui_obras) | ((ch["DEPARTAMENTO"] == "PIURA") & (pim > 0))])
    df = pd.concat(partes).drop_duplicates("CODIGO_UNICO")
    for c in ["COSTO_ACTUALIZADO", "AVANCE_FISICO", "AVANCE_EJECUCION"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").round(2)

    encontrados = len(proyectos & set(df["CODIGO_UNICO"]))
    print(f"{n:,} inversiones leídas; {len(df):,} guardadas; "
          f"{encontrados} de {len(proyectos)} proyectos del gasto encontrados por CUI; "
          f"{len(cui_obras & set(df['CODIGO_UNICO']))} de {len(cui_obras)} CUI de obras activas de Infobras")
    df = df.astype(object).where(df.notna(), None)  # NaN no es JSON válido
    guardar("inversiones_piura.json", {
        "fuente": "MEF, Detalle de inversiones (datos abiertos; avance físico del Formato 12-B)",
        "url": URL,
        "fecha_corte": fecha,
        "proyectos_gasto": len(proyectos),
        "proyectos_encontrados": encontrados,
        "columnas": ["cui", "departamento", "provincia", "distrito", "costo_actualizado", "pim_anio",
                     "avance_fisico", "avance_financiero", "tiene_f12b", "ioarr_emergencia"],
        "filas": df[COLUMNAS].values.tolist(),
    })


if __name__ == "__main__":
    main()
