"""
Dengue histórico en Piura (2000-2025) desde los datos abiertos del CDC-Minsa.

El portal bloquea las descargas automáticas (error 418), así que el CSV se descarga a mano y se deja en
data/raw/ (que no se sube al repositorio). Cada fila del CSV es un caso y no hay identificador: las filas
idénticas son casos distintos y se cuentan todas. Se guarda solo el conteo de Piura por distrito, año,
semana epidemiológica, forma clínica y tipo de diagnóstico (C confirmado, P probable), sin edad ni sexo.
Resultado: docs/data/dengue_historico.json.

Uso: python3 scripts/dengue_historico.py [ruta del CSV]
"""
import sys

import pandas as pd

from comun import RAIZ, guardar, verificar_espacio

CSV = RAIZ / "data" / "raw" / "datos_abiertos_vigilancia_dengue_2000_2025_0.csv"
URL = "https://www.datosabiertos.gob.pe/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue"
FECHA_ARCHIVO = "2026-10-22"  # fecha de modificación del archivo en el portal (revisada a mano)
TIPOS = {"DENGUE SIN SIGNOS DE ALARMA": "S", "DENGUE CON SIGNOS DE ALARMA": "A", "DENGUE GRAVE": "G"}
CLAVE = ["ano", "semana", "ubigeo", "tipo", "tipo_dx"]


def contar(df):
    """Casos de Piura por clave. Usa size(), que cuenta las filas idénticas por separado."""
    p = df[df["departamento"] == "PIURA"].assign(tipo=lambda x: x["enfermedad"].map(TIPOS))
    if p["tipo"].isna().any():
        raise SystemExit("Forma clínica desconocida: " + str(p.loc[p["tipo"].isna(), "enfermedad"].unique()))
    return p.groupby(CLAVE).size().rename("casos").reset_index(), p


def main():
    verificar_espacio()
    ruta = sys.argv[1] if len(sys.argv) > 1 else CSV
    df = pd.read_csv(ruta, dtype=str, usecols=["departamento", "provincia", "distrito", "enfermedad", "ano",
                                                "semana", "tipo_dx", "ubigeo"])
    agr, piura = contar(df)
    assert agr["casos"].sum() == len(piura), "el conteo debe conservar todas las filas"
    agr[["ano", "semana"]] = agr[["ano", "semana"]].astype(int)
    agr = agr.sort_values(CLAVE)
    print(f"{len(df):,} casos en el país; {len(piura):,} en Piura; {len(agr):,} filas agregadas")
    print(agr.groupby(["ano", "tipo_dx"])["casos"].sum().unstack(fill_value=0).tail(6))
    distritos = piura.drop_duplicates("ubigeo").set_index("ubigeo")
    # El archivo trae la Ñ ya perdida (carácter de reemplazo U+FFFD, p. ej. "PARI�AS"); en Piura solo puede ser Ñ
    distritos = distritos[["provincia", "distrito"]].replace("\ufffd", "Ñ", regex=True)
    guardar("dengue_historico.json", {
        "fuente": "CDC-Minsa, Vigilancia epidemiológica de dengue (datos abiertos)",
        "url": URL,
        "fecha_corte": FECHA_ARCHIVO,
        "nota": "Distrito según el registro de vigilancia. Tipos: S sin signos de alarma, A con signos de alarma, "
                "G grave. Diagnóstico: C confirmado, P probable.",
        "columnas": CLAVE + ["casos"],
        "filas": agr.values.tolist(),
        "distritos": {u: [r["provincia"], r["distrito"]] for u, r in distritos.iterrows()},
    })


if __name__ == "__main__":
    main()
