"""
Gasto público en Piura según el MEF (Presupuesto y Ejecución de Gasto, archivo diario).

Descarga el CSV del año en curso y lo lee por partes mientras llega, sin guardarlo en disco
(pesa unos 8 GB). Se queda solo con las filas de Piura y las agrega por nivel de gobierno,
entidad, programa presupuestal y producto/proyecto. Resultado: docs/data/gasto_piura.json.

Cada fila agregada lleva un "ámbito" para que la página permita elegir qué es "gasto en Piura":
  1 = el gasto se ubica en Piura (DEPARTAMENTO_META), 2 = la entidad tiene sede en Piura
  (DEPARTAMENTO_EJECUTORA), 3 = ambas cosas.

Cómo leer los montos: las filas con MES_EJE = 0 traen PIA y PIM; las de los meses 1 a 12 traen
la ejecución mensual. Por eso el avance es suma(devengado) / suma(PIM) sobre todas las filas.

Entidad: en gobiernos locales PLIEGO viene vacío y cada municipalidad es una unidad ejecutora;
por eso la entidad es el pliego (nacional y regional) o la ejecutora (local).
"""
import time
import urllib.error
from datetime import datetime

import pandas as pd

from comun import PERU, abrir, fecha_modificacion, guardar, verificar_espacio

ANIO = datetime.now(PERU).year
ARCHIVO = "https://fs.datosabiertos.mef.gob.pe/datastorefiles/{}-Gasto-Diario.csv"
CLAVE = ["NIVEL_GOBIERNO", "ENTIDAD", "PROGRAMA_PPTO", "TIPO_ACT_PROY", "PRODUCTO_PROYECTO"]
NOMBRES = {
    "NIVEL_GOBIERNO": "NIVEL_GOBIERNO_NOMBRE",
    "ENTIDAD": "ENTIDAD_NOMBRE",
    "PROGRAMA_PPTO": "PROGRAMA_PPTO_NOMBRE",
    "PRODUCTO_PROYECTO": "PRODUCTO_PROYECTO_NOMBRE",
}
MONTOS = ["MONTO_PIA", "MONTO_PIM", "MONTO_DEVENGADO"]
COLUMNAS = ["DEPARTAMENTO_META_NOMBRE", "DEPARTAMENTO_EJECUTORA_NOMBRE", "NIVEL_GOBIERNO", "NIVEL_GOBIERNO_NOMBRE",
            "PLIEGO", "PLIEGO_NOMBRE", "SEC_EJEC", "EJECUTORA_NOMBRE", "PROGRAMA_PPTO", "PROGRAMA_PPTO_NOMBRE",
            "TIPO_ACT_PROY", "PRODUCTO_PROYECTO", "PRODUCTO_PROYECTO_NOMBRE", *MONTOS]
LUGAR, SEDE = 1, 2


def filtrar_piura(ch):
    """Deja solo las filas de Piura y añade AMBITO (1 lugar del gasto, 2 sede, 3 ambos)."""
    ambito = (ch["DEPARTAMENTO_META_NOMBRE"] == "PIURA") * LUGAR + (ch["DEPARTAMENTO_EJECUTORA_NOMBRE"] == "PIURA") * SEDE
    p = ch.assign(AMBITO=ambito)[ambito > 0].copy()
    local = p["NIVEL_GOBIERNO"] == "M"
    p["ENTIDAD"] = p["SEC_EJEC"].where(local, p["PLIEGO"])
    p["ENTIDAD_NOMBRE"] = p["EJECUTORA_NOMBRE"].where(local, p["PLIEGO_NOMBRE"])
    for c in MONTOS:
        p[c] = pd.to_numeric(p[c])
    return p


def agregar(df):
    return df.groupby(["AMBITO", *CLAVE], as_index=False)[MONTOS].sum()


def resumen(agr, ambito=LUGAR):
    """PIM, devengado y avance (%) por nivel de gobierno y total, para un ámbito."""
    d = agr[(agr["AMBITO"] & ambito) > 0]
    t = d.groupby("NIVEL_GOBIERNO")[["MONTO_PIM", "MONTO_DEVENGADO"]].sum()
    t.loc["TOTAL"] = t.sum()
    t["AVANCE"] = 100 * t["MONTO_DEVENGADO"] / t["MONTO_PIM"]
    return t


def archivo_del_anio():
    """(año, URL, fecha) del archivo diario del año en curso; si el MEF aún no lo publica (404, por ejemplo
    a inicios de enero), el del año anterior. La página muestra el año y la fecha, y avisa si el dato envejece."""
    for anio in (ANIO, ANIO - 1):
        url = ARCHIVO.format(anio)
        try:
            return anio, url, fecha_modificacion(url)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            print(f"El MEF aún no publica {url}.")
    raise SystemExit("No hay archivo de gasto diario del MEF ni del año en curso ni del anterior.")


def main():
    verificar_espacio()
    anio, url, fecha = archivo_del_anio()
    print(f"Leyendo {url} (modificado {fecha})")
    partes, nombres, n, t0 = [], {k: {} for k in NOMBRES}, 0, time.time()
    with abrir(url) as r:  # los reintentos cubren la conexión, no un corte a mitad de la descarga
        for i, ch in enumerate(pd.read_csv(r, dtype=str, encoding="utf-8", encoding_errors="replace",
                                               usecols=COLUMNAS, chunksize=500_000)):
            if i % 4 == 0:
                verificar_espacio()
            n += len(ch)
            p = filtrar_piura(ch)
            for k, col in NOMBRES.items():
                nombres[k].update(zip(p[k], p[col]))
            partes.append(agregar(p))
            print(f"  {n:,} filas leídas, {time.time() - t0:.0f} s", flush=True)
    agr = agregar(pd.concat(partes))
    if agr.empty:
        raise SystemExit("No se encontró ninguna fila de Piura: revisar el archivo del MEF.")

    for ambito, nombre in [(LUGAR, "lugar del gasto"), (SEDE, "sede de la entidad")]:
        print(f"\nResumen ({nombre}), millones de S/:")
        print((resumen(agr, ambito)[["MONTO_PIM", "MONTO_DEVENGADO"]] / 1e6).round(1).join(resumen(agr, ambito)["AVANCE"].round(1)))

    agr[MONTOS] = agr[MONTOS].round(2)
    guardar("gasto_piura.json", {
        "fuente": "MEF, Presupuesto y Ejecución de Gasto (datos abiertos, archivo diario)",
        "url": url,
        "fecha_corte": fecha,
        "anio": anio,
        "filas_leidas": n,
        "columnas": ["ambito", "nivel", "entidad", "programa", "tipo", "codigo", "pia", "pim", "devengado"],
        "filas": agr.values.tolist(),
        "nombres": {"nivel": nombres["NIVEL_GOBIERNO"], "entidad": nombres["ENTIDAD"],
                    "programa": nombres["PROGRAMA_PPTO"], "codigo": nombres["PRODUCTO_PROYECTO"]},
    })


if __name__ == "__main__":
    main()
