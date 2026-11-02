"""
Obras públicas en Piura según Infobras (Contraloría): conteo por estado y lista de obras en ejecución y paralizadas.

Solo se usa el estado y la causa de paralización. El avance físico no se publica desde aquí: el archivo de datos
abiertos no trae avances posteriores a marzo de 2026 ni obras registradas después (verificado el 02/11/2026
contra las fichas web). El avance físico se toma del MEF por código único de inversión (inversiones_mef.py).

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
    "Causal de paralización": "causal",
    "Fecha de paralización": "fecha_paralizacion",
    "Número de dias paralizado": "dias_paralizado",
    "Costo de obra en soles según ET en soles": "costo_et",
    "Marca Reconstrucción con Cambios (Si/No)": "rcc",
}
# Infobras pierde la Ñ en algunos nombres (la reemplaza por un espacio)
CORRECCIONES = {"PARI AS": "PARIÑAS"}
ACTIVAS = {"En Ejecución", "Paralizada"}  # las que se listan; las demás solo se cuentan
NUMEROS = {"costo_et", "dias_paralizado"}


def numero(v):
    """Infobras escribe algunos decimales con espacio ('1205287 56' = 1205287.56)."""
    if v in (None, ""):
        return None
    try:
        return float(str(v).strip().replace(" ", "."))
    except ValueError:
        return None


def periodo(anio, mes):
    """Año y mes como número de meses (para comparar), o None."""
    try:
        return int(anio) * 12 + int(mes)
    except (TypeError, ValueError):
        return None


def avance_futuro(anio, mes, fecha_consulta):
    """True si el mes del avance no ha terminado a la fecha de consulta del archivo (dd/mm/aaaa): mes actual o posterior."""
    _, m, a = fecha_consulta.split("/")
    p = periodo(anio, mes)
    return p is not None and p >= periodo(a, m)


assert avance_futuro("2026", "11", "02/11/2026") and not avance_futuro("2026", "10", "02/11/2026")
assert not avance_futuro(None, None, "02/11/2026")


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
        AVANCE = ["Año de avance", "Mes de avance"]
        ix = {t: titulos.index(t) for t in [*CAMPOS, *AVANCE, "Departamento", "Estado de ejecución"]}

        estados, nacional, obras, futuras, ultimo, por_cui = Counter(), 0, [], 0, 0, Counter()
        for f in filas:
            if avance_futuro(*(f[ix[c]] for c in AVANCE), fecha_consulta):
                futuras += 1  # se excluye la fila completa
                continue
            nacional += 1
            cui = str(f[ix["Codigo unico de inversión"]] or "").strip()
            if cui not in ("", "0"):
                por_cui[cui] += 1  # en todo el país y en cualquier estado: una inversión puede tener obras en varias regiones
            if f[ix["Departamento"]] != "PIURA":
                continue
            estado = f[ix["Estado de ejecución"]] or "Sin dato"
            estados[estado] += 1
            ultimo = max(ultimo, periodo(f[ix["Año de avance"]], f[ix["Mes de avance"]]) or 0)
            if estado in ACTIVAS:
                o = {corto: f[ix[largo]] for largo, corto in CAMPOS.items()}
                o["distrito"] = CORRECCIONES.get(o["distrito"], o["distrito"])
                obras.append({"estado": estado, **{k: numero(v) if k in NUMEROS else v for k, v in o.items()}})
        hoja.parent.close()

    for o in obras:  # el avance físico del MEF es de toda la inversión; se indica cuántas obras la componen
        o["obras_en_cui"] = por_cui.get(str(o["cui"] or "").strip(), 0)

    if not estados:
        raise SystemExit("No se encontraron obras de Piura: revisar el archivo de Infobras.")
    print(f"{nacional:,} obras en el país ({futuras} excluidas por fecha de avance futura); Piura: {dict(estados)}")
    guardar("infobras_piura.json", {
        "fuente": "Contraloría General de la República, Infobras (Dataset de obras públicas)",
        "url": PAGINA,
        "fecha_corte": fecha_consulta,
        "obras_piura": sum(estados.values()),
        "por_estado": dict(estados.most_common()),
        # mes más reciente con avance registrado en Piura (año*12 + mes) y filas excluidas en todo el país
        "ultimo_avance": {"anio": (ultimo - 1) // 12, "mes": (ultimo - 1) % 12 + 1} if ultimo else None,
        "excluidas_fecha_futura": futuras,
        "obras": sorted(obras, key=lambda o: -(o["costo_et"] or 0)),
    })


if __name__ == "__main__":
    main()
