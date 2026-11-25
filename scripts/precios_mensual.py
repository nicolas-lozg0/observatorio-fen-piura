"""
Precios mensuales de alimentos en Piura (SISAP) y estimación de cuánto subió la canasta básica de alimentos en el año.

Lee el historial diario del SISAP (data/sisap_piura.json, que arma scripts/precios_sisap.py) y guarda:
  - docs/data/sisap_historial.json: el mismo historial diario, para la infografía de la quincena (docs/infografia/);
  - docs/data/precios_mensual.json: por producto (mercado mayorista), precio promedio mensual por kg, variación mensual,
    índice acumulado del año (diciembre del año anterior = 100) en 2024, 2025 y 2026 y lo habitual (promedio de 2024 y 2025);
    el diésel de Piura (Osinergmin) en el mismo formato, y las fechas de los dos shocks;
  - docs/data/canasta_estimada.json: variación de la canasta básica de alimentos de Costa urbana con pesos fijos del INEI.

Decisiones (avance_tarea_conjunta2.md):
  - mes con precio: al menos MINIMO_FECHAS fechas con precio; si no, el mes queda vacío;
  - el mes en curso (parcial) se compara en todos los años con los mismos días (del 1 al día del último dato);
  - lo habitual: promedio de 2024 y 2025 (2022 se excluye por el alza de fertilizantes y 2023 por El Niño costero);
  - canasta: pesos = valor de cada producto en la canasta de Costa urbana del INEI (año base 2010), precios minoristas;
    la parte que el SISAP no cubre se mueve como el IPC nacional de alimentos (dentro del hogar) o de restaurantes (fuera).
Uso: python3 scripts/precios_mensual.py (precios_sisap.py lo llama al final)
"""
import json
import re
from datetime import date

import pdfplumber

from comun import DATOS, RAIZ, abrir, guardar
from ipc_inei import lineas
from precios_sisap import EMPALME, HISTORIAL, PRODUCTOS

MINIMO_FECHAS = 2
ANIOS = [2024, 2025, 2026]
HABITUAL = [2024, 2025]
UMBRAL_SEPARA = 2  # puntos: «se separa de lo habitual» desde el primer mes en que la diferencia acumulada pasa de esto y no vuelve
CANASTA_COSTA_URBANA_2025 = 247  # S/ por persona al mes: línea de pobreza extrema de Costa urbana 2025 (lineas_pobreza.json)
CRUDO_IPC = RAIZ / "data" / "raw" / "inei_ipc"

# Canasta Básica de Alimentos (CBA) de Costa urbana: INEI, «Metodología para la medición de la pobreza» (nota01.pdf),
# Anexo N.° 02 «Canasta básica de consumo alimentario valorizada en soles per cápita día, por dominios geográficos, del año
# base 2010», págs. 62 a 66. El archivo docs/data/canasta_pesos.json trae los 110 productos con su valor.
FUENTE_PESOS = {"documento": "INEI, Encuesta Nacional de Hogares: Metodología para la medición de la pobreza (nota01)",
                "cuadro": "Anexo N.° 02: Canasta básica de consumo alimentario valorizada en soles per cápita día, por dominios "
                          "geográficos, del año base 2010", "paginas": "62 a 66",
                "url": "https://www.inei.gob.pe/media/cifras_de_pobreza/nota01.pdf"}
# Correspondencia SISAP → producto de la canasta (número del anexo). Los dudosos llevan su nota.
CORRESPONDENCIA = {
    "Arroz superior": (5, "En la canasta es arroz corriente a granel; el SISAP de Piura solo registra arroz superior."),
    "Pollo": (21, None),
    "Leche en tarro": (30, "En la canasta es leche evaporada; el SISAP registra «leche reconstituida» en tarro azul (la de mayor venta)."),
    "Huevos": (34, None),
    "Aceite vegetal": (35, None),
    "Azúcar rubia": (84, "La canasta no distingue azúcar rubia de blanca."),
    "Tomate": (56, None),
    "Zanahoria": (58, None),
    "Cebolla roja": (46, "En la canasta es «cebolla de cabeza», sin color; la roja es la más común en la costa."),
    "Choclo": (47, None),
    "Limón sutil": (61, None),
    "Palta": (66, "En la canasta es palta criolla o corriente; el SISAP registra palta fuerte."),
    "Plátano seda congo": (69, None),
    "Lenteja": (75, None),
    "Camote morado": (76, "En la canasta es «camote», sin variedad."),
    "Papa amarilla": (78, None),
    "Papa yungay": (79, "La canasta dice «papa blanca»; la yungay es la papa blanca más común."),
    "Yuca": (81, None),
    "Ajo": (92, "Ajo entero; el ajo molido a granel (n.° 93) es otro producto y queda sin cubrir."),
}
FUERA_DEL_HOGAR = range(103, 111)  # comidas fuera del hogar: se mueven como «Restaurantes y hoteles» del IPC


def mensual(serie, a, m, hasta=31):
    """Promedio de los días con precio del mes (hasta el día `hasta`), o None con menos de MINIMO_FECHAS fechas."""
    v = [p for f, p in serie.items() if f.startswith(f"{a}-{m:02d}") and int(f[8:]) <= hasta]
    return round(sum(v) / len(v), 4) if len(v) >= MINIMO_FECHAS else None


def series(precios, tipo):
    """{producto: serie diaria} de un mercado, con el aceite empalmado (botella de 1 litro antes de 2024)."""
    return {nombre: {**precios.get(f"{EMPALME.get(sisap)}|{tipo}", {}), **precios.get(f"{sisap}|{tipo}", {})}
            for nombre, sisap, _ in PRODUCTOS}


def tabla_mensual(serie, mes_fin, dia_fin):
    """{año: {«precio»: [12], «indice»: [12], «var»: [12]}} para ANIOS. El mes mes_fin se corta en dia_fin en todos los años."""
    out = {}
    for a in ANIOS:
        base = mensual(serie, a - 1, 12)
        precio = [mensual(serie, a, m, dia_fin if m == mes_fin else 31) if (a < ANIOS[-1] or m <= mes_fin) else None
                  for m in range(1, 13)]
        # los años anteriores solo hasta el mes en curso: así se compara el mismo tramo
        precio = [p if m <= mes_fin else None for m, p in enumerate(precio, 1)]
        indice = [round(100 * p / base, 2) if p and base else None for p in precio]
        prev = [base] + precio[:-1]
        var = [round(100 * (p / q - 1), 2) if p and q else None for p, q in zip(precio, prev)]
        out[str(a)] = {"diciembre_anterior": base, "precio": precio, "indice": indice, "var": var}
    return out


def promedio(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 2) if len(xs) == len(HABITUAL) else None


def separacion(dif):
    """Primer mes (1-12) desde el cual la diferencia acumulada supera UMBRAL_SEPARA en valor absoluto, con el mismo signo,
    hasta el último mes con dato. None si no se separa."""
    vals = [(m, d) for m, d in enumerate(dif, 1) if d is not None]
    if not vals or abs(vals[-1][1]) <= UMBRAL_SEPARA:
        return None
    signo = 1 if vals[-1][1] > 0 else -1
    desde = None
    for m, d in vals:
        desde = (desde or m) if d * signo > UMBRAL_SEPARA else None
    return desde


def productos_mensual(precios, ultimo):
    mes_fin, dia_fin = ultimo.month, ultimo.day
    serie = series(precios, "mayorista")
    out = []
    for nombre, sisap, _ in PRODUCTOS:
        t = tabla_mensual(serie[nombre], mes_fin, dia_fin)
        hab = [promedio([t[str(a)]["indice"][k] for a in HABITUAL]) for k in range(12)]
        hab_var = [promedio([t[str(a)]["var"][k] for a in HABITUAL]) for k in range(12)]
        act = t[str(ANIOS[-1])]
        dif = [round(i - h, 2) if i is not None and h is not None else None for i, h in zip(act["indice"], hab)]
        dif_var = [round(v - h, 2) if v is not None and h is not None else None for v, h in zip(act["var"], hab_var)]
        ult = next((d for d in reversed(dif) if d is not None), None)
        out.append({"nombre": nombre, "sisap": sisap, "anios": t, "habitual": {"indice": hab, "var": hab_var},
                    "diferencia": dif, "diferencia_var": dif_var, "acumulada": ult, "separa": separacion(dif)})
    return out


def diesel():
    """Diésel de Piura en el mismo formato (índice: diciembre del año anterior = 100) y el mes en que empieza la subida."""
    d = json.loads((DATOS / "diesel_piura.json").read_text(encoding="utf-8"))
    p = {x["mes"]: x["precio"] for x in d["serie"]}
    out = {}
    for a in ANIOS:
        base = p.get(f"{a - 1}-12")
        out[str(a)] = [round(100 * p[f"{a}-{m:02d}"] / base, 2) if base and p.get(f"{a}-{m:02d}") else None for m in range(1, 13)]
    hab = [promedio([out[str(a)][k] for a in HABITUAL]) for k in range(12)]
    # inicio de la subida: primer mes del año en curso cuyo precio supera en 5 % o más al de diciembre anterior
    sube = next((m for m, v in enumerate(out[str(ANIOS[-1])], 1) if v and v >= 105), None)
    return {"fuente": d["fuente"], "url": d["url"], "producto": d["producto"], "fecha_corte": d["fecha_corte"], "indice": out, "habitual": hab,
            "sube_desde": sube, "precio_dic": p.get(f"{ANIOS[-1] - 1}-12"),
            "precio_ultimo": next(x["precio"] for x in reversed(d["serie"]) if x["precio"])}


# ---------- IPC nacional de alimentos y de restaurantes (INEI, Cuadro 1), para la parte de la canasta que no cubre el SISAP ----------
def ipc_acumulado(mes):
    """Variación acumulada (diciembre anterior → mes) de «01.1. Alimentos» y «11. Restaurantes y hoteles» del IPC nacional,
    del informe técnico de ese mes (Cuadro 1). La URL del PDF sale de docs/data/ipc_piura.json."""
    serie = json.loads((DATOS / "ipc_piura.json").read_text(encoding="utf-8"))["serie"]
    url = next((x["pdf"] for x in serie if x["mes"] == mes), None)
    if not url:
        return None
    ruta = CRUDO_IPC / f"{mes}.pdf"
    if not ruta.exists():
        CRUDO_IPC.mkdir(parents=True, exist_ok=True)
        with abrir(url) as r:
            ruta.write_bytes(r.read())
    num = r"(-?\d+,\d+)"
    res = {}
    with pdfplumber.open(ruta) as pdf:
        en_cuadro = False
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            # el Cuadro 1 de los anexos es el IPC nacional por divisiones (en algunos PDF el título sale con letras separadas)
            if re.search(r"Cuadro 1\b", texto):
                en_cuadro = True
            elif re.search(r"Cuadro [2-9]\b", texto):
                en_cuadro = False
            if not en_cuadro:
                continue
            for l in lineas(pagina):
                for clave, patron in (("alimentos", r"01\.1\.? Alimentos"), ("restaurantes", r"11\.? Restaurantes y [Hh]oteles")):
                    m = re.fullmatch(rf"{patron} {num} {num} {num} {num}", l)
                    if m and clave not in res:
                        res[clave] = float(m.group(3).replace(",", "."))  # columna «Ene. - mes»
    return res if len(res) == 2 else None


def pesos_canasta():
    """docs/data/canasta_pesos.json: los 110 productos de la CBA con sus gramos (Anexo N.° 01) y su valor en soles por persona al
    día (Anexo N.° 02) en Costa urbana, leídos del PDF del INEI (se guarda en data/raw/inei_pobreza/)."""
    ruta = RAIZ / "data" / "raw" / "inei_pobreza" / "nota01.pdf"
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with abrir(FUENTE_PESOS["url"]) as r:
            ruta.write_bytes(r.read())
    patron = re.compile(r"^(\d{1,3}) (.+?)((?: (?:-|\d+,\d+)){7})$")
    filas = {}
    with pdfplumber.open(ruta) as pdf:
        for clave, paginas in (("gramos", range(56, 61)), ("valor", range(61, 66))):  # índices 0: págs. 57-61 y 62-66
            for k in paginas:
                for l in (pdf.pages[k].extract_text() or "").split("\n"):
                    m = patron.match(l.strip())
                    if m:
                        v = m.group(3).split()[0]  # primera columna: Costa urbana
                        f = filas.setdefault(int(m.group(1)), {"n": int(m.group(1)), "nombre": m.group(2).strip()})
                        f[f"{clave}_costa_urbana"] = 0.0 if v == "-" else float(v.replace(",", "."))
    assert sorted(filas) == list(range(1, 111)), f"se esperaban 110 productos y hay {len(filas)}"
    prod = [f for _, f in sorted(filas.items())]
    total = sum(f["valor_costa_urbana"] for f in prod)
    assert 4.2 < total < 4.35, total  # S/ 4,27 por persona al día en 2010 (unos S/ 130 al mes)
    guardar("canasta_pesos.json", {**FUENTE_PESOS, "dominio": "Costa urbana", "unidad_valor": "soles por persona al día (precios de 2010)",
                                   "unidad_gramos": "gramos por persona al día", "total_valor": round(total, 5), "productos": prod})


def canasta(precios, mes_fin, mes_ipc):
    """Variación de la canasta de Costa urbana de diciembre anterior a `mes_fin`, en 2024, 2025 y 2026, con pesos fijos."""
    filas = json.loads((DATOS / "canasta_pesos.json").read_text(encoding="utf-8"))["productos"]
    total = sum(f["valor_costa_urbana"] for f in filas)
    peso = {f["n"]: f["valor_costa_urbana"] / total for f in filas}
    fuera = sum(peso[n] for n in FUERA_DEL_HOGAR)
    resultados = {}
    for tipo in ("minorista", "mayorista"):
        serie = series(precios, tipo)
        # cubiertos: con precio en diciembre anterior y en el mes final de los tres años (la cobertura es la misma en todos)
        cubiertos = [p for p, (n, _) in CORRESPONDENCIA.items()
                     if all(mensual(serie[p], a - 1, 12) and mensual(serie[p], a, mes_fin) for a in ANIOS)]
        cob = sum(peso[CORRESPONDENCIA[p][0]] for p in cubiertos)
        por_anio = {}
        for a in ANIOS:
            var = {p: 100 * (mensual(serie[p], a, mes_fin) / mensual(serie[p], a - 1, 12) - 1) for p in cubiertos}
            cub = sum(peso[CORRESPONDENCIA[p][0]] * v for p, v in var.items()) / cob
            ipc = ipc_acumulado(f"{a}-{mes_fin:02d}") if mes_fin <= mes_ipc else None
            b = (cob * cub + (1 - cob - fuera) * ipc["alimentos"] + fuera * ipc["restaurantes"]) if ipc else None
            por_anio[str(a)] = {"cubierta": round(cub, 2), "a": round(cub, 2), "b": round(b, 2) if b is not None else None,
                                "ipc": ipc, "productos": {p: round(v, 1) for p, v in var.items()}}
        resultados[tipo] = {"cubiertos": cubiertos, "cobertura": round(100 * cob, 1), "anios": por_anio,
                            "habitual": {k: promedio([por_anio[str(a)][k] for a in HABITUAL]) for k in ("a", "b", "cubierta")}}
    return {"fuente_pesos": FUENTE_PESOS, "mes_fin": mes_fin, "fuera_del_hogar": round(100 * fuera, 1),
            "canasta_soles": CANASTA_COSTA_URBANA_2025,
            "correspondencia": [{"sisap": p, "canasta": n, "nombre_canasta": next(f["nombre"] for f in filas if f["n"] == n),
                                 "peso": round(100 * peso[n], 2), "nota": nota} for p, (n, nota) in CORRESPONDENCIA.items()],
            "sin_canasta": [p for p, _, _ in PRODUCTOS if p not in CORRESPONDENCIA],
            **resultados}


def main():
    precios = json.loads(HISTORIAL.read_text(encoding="utf-8"))["precios"]
    todas = sorted({f for s in precios.values() for f in s})
    ultimo = date.fromisoformat(todas[-1])
    guardar("sisap_historial.json", {"fuente": "Midagri, SISAP «Precios en ciudades», mercados de Piura",
                                     "url": "http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/",
                                     "fecha_corte": ultimo.isoformat(), "precios": precios})
    if not (DATOS / "canasta_pesos.json").exists():
        pesos_canasta()
    ipc = json.loads((DATOS / "ipc_piura.json").read_text(encoding="utf-8"))["ultimo_mes"]
    mes_ipc = int(ipc[5:]) if ipc.startswith(str(ultimo.year)) else 0
    # canasta: hasta el último mes completo que tenga IPC publicado (hoy, octubre)
    mes_canasta = min(mes_ipc, ultimo.month - 1 if ultimo.day < 28 else ultimo.month)
    guardar("precios_mensual.json", {
        "fuente": "Midagri, SISAP «Precios en ciudades», mercados mayoristas de Piura", "fecha_corte": ultimo.isoformat(),
        "mes_fin": ultimo.month, "dia_fin": ultimo.day, "anios": ANIOS, "habitual": HABITUAL, "minimo_fechas": MINIMO_FECHAS,
        "umbral_separa": UMBRAL_SEPARA, "productos": productos_mensual(precios, ultimo), "diesel": diesel(),
        "shocks": {"enfen": {"fecha": "2026-02-13", "texto": "Alerta de El Niño costero",
                             "fuente": "ENFEN, Comunicado Oficial N.° 03-2026 (13/02/2026): «dispone la activación del Estado de "
                                       "Alerta de El Niño Costero»",
                             "url": "https://www.senamhi.gob.pe/load/file/02204SENA-209.pdf"}}})
    guardar("canasta_estimada.json", {"fecha_corte": ultimo.isoformat(), "ipc_hasta": ipc, **canasta(precios, mes_canasta, mes_ipc)})


if __name__ == "__main__":
    main()
