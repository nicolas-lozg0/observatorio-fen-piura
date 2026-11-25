# Tarea conjunta 2: Vulnerabilidad (distribución) y Precios (25/11/2026)

Sin push: pendiente de revisión.

## Bloque I. Vulnerabilidad: distribución y lectura

**1. Distribución del panel del indicador**
- **PC (≥ 1024 px):**
  - columna izquierda (1/3): el resumen (cifra y visual por distrito), «Cómo se reparten…» (frase y 5 clases, en lista) y la lista de sectores, compacta (nombre arriba; barra y cifra en una línea);
  - columna derecha (2/3): solo el mapa, con su leyenda de colores pegada arriba. El mapa estira su alto hasta igualar la columna izquierda (mínimo 560 px), sin agregar espacio;
  - el mapa se vuelve a encuadrar cuando cambia de alto, mientras la persona no lo haya movido ni acercado.
- **Celular y tableta:** la columna izquierda se disuelve (`display: contents`) y cada bloque toma su orden: controles, resumen, mapa, «Cómo se reparten» y sectores.
- La barra de reparto dejó de ser la leyenda del mapa. Sobre el mapa queda siempre la leyenda compacta (5 muestras con su rango); en población, que no tiene reparto, la izquierda queda con resumen y sectores.

**2. Controles fijos**
- Al quedar fijos, se compactan a una fila sin rótulos visibles (unos 52 px, con sombra suave). Los rótulos siguen para lectores de pantalla.
- El cambio se decide por la posición del panel, no por la de los controles, para que el cambio de alto no oscile.
- `scroll-margin-top` (barra de la página + controles + 12 px) en todo lo que tiene `id` en la pestaña. Al hacer clic en un sector, la página sube al mapa.
- Verificado con capturas desplazando la página (`desplazamiento_*`): al pasar por debajo de los controles, el contenido queda tapado solo por esa fila compacta.

**3. Días y horas sin agua**
- Por distrito o sub-área, una tira de 7 casillas (L M M J V S D en letra chica):
  - días: se pintan tantas casillas como días sin agua en promedio, la última en parte;
  - horas: cada casilla se pinta en la proporción del día sin agua (72 de 168 horas = 43 % de cada día).
- La parte pintada se dibuja con el ancho del rectángulo, que equivale a recortarlo; no hizo falta un clipPath.
- Frases cortas: «Veintiséis de Octubre: 0,7 días a la semana sin agua», «Castilla: 76 de 168 horas a la semana sin agua». La definición va una sola vez, en la nota.
- La tarjeta del Resumen (portada) muestra sin desagüe, no estos indicadores: no cambia.

**4. Lluvia y localidades**
- El gráfico de puntos es la vista por defecto («Gráfico de puntos | Barras»).
- PC: a la izquierda (1/3), el año, la leyenda de lluvia, el mapa (340 px de alto, encuadrado al departamento), su frase y la nota de CHIRPS. A la derecha (2/3), la comparación: titular, pregunta guiada y gráfico (o barras, con el mismo titular).
- Celular: el año primero (manda en las dos vistas), luego la comparación y después el mapa con su frase.
- Concordancia de los titulares, revisada para todos los indicadores:
  - «los días sin agua por semana tienden a ser más altos»;
  - «las horas sin agua por semana tienden a ser más altas»;
  - «la población tiende a ser más alta»;
  - «el porcentaje de … tiende a ser más alto»;
  - con otro eje horizontal: «donde los días sin agua por semana son mayores».
  - Lo comprueba `scripts/test_pagina.py`.
- Margen interno de 18 px (el radio máximo, 16 px, más el borde) en los dos ejes: ningún punto se corta. Hay una prueba para eso.

**5. Se mantiene lo acordado:** tira de puntos bajo 10 %, barras de sectores de largo fijo, casas y personas parciales recortadas, ningún «Sector sin nombre» y sectores dentro del panel.

**Pruebas:** `scripts/test_pagina.py` pasa completo, incluidas las 598 combinaciones de localidad e indicador. Además, se corrigió una carrera de tiempo en la prueba de «Dato no actualizado», que contaba los avisos antes de que se dibujaran.

**Capturas:** en `privado/capturas_tarea2/vulnerabilidad/`, a 375 y 1280 px:
- `panel_sin_desague_*`, `panel_dias_sin_agua_*` y `panel_horas_sin_agua_*`;
- `lluvia_fragiles_*` (pregunta «¿Coinciden lluvia y viviendas frágiles?»);
- `desplazamiento_0…2_*`.

## Bloque II. Precios

**Hecho:**
- **Parte A, infografía:** `docs/infografia/precios_quincena.html` + `.js` + `README.md`.
  - Lee `data/sisap_historial.json` y `precios_sisap.json`; tiene controles y parámetros en la URL (`corte`, `desde`, `hasta`, `mercado`, `comparar`, `orden`) y el botón «Descargar PNG» (2x, fondo blanco).
  - **Prueba:** con los valores por defecto, 0 diferencias con `precios_sisap.json` en los 23 productos × 2 mercados y en el promedio. Se igualó el redondeo de los empates exactos al de Python, para que coincidan.
  - Quedó enlazada en el detalle de Precios.
- **Parte B, datos mensuales:** `scripts/precios_mensual.py` genera `docs/data/precios_mensual.json`:
  - mayorista, mínimo 2 fechas por mes, variación m/m e índice con diciembre anterior = 100 para 2024, 2025 y 2026;
  - lo habitual = promedio de 2024 y 2025; noviembre, del 1 al 23 en los tres años;
  - papa yungay y tomate quedan sin «habitual»: el SISAP no tiene su precio de diciembre de 2023.
- **Parte C, un producto a la vez:**
  - selector y lista ordenada por la diferencia acumulada (por defecto, plátano seda congo, +58 puntos);
  - gráfico 1 (índice, sombreado naranja/azul), gráfico 2 (barras de la diferencia mensual) y diésel, alineados;
  - «se separa» = primer mes desde el cual la diferencia acumulada supera 2 puntos y no vuelve a bajar.
- **Shocks:**
  - alerta de El Niño costero: **ENFEN, Comunicado Oficial N.° 03-2026, 13/02/2026** («dispone la activación…»; PDF del Senamhi 02204SENA-209). El N.° 01 (15/01) solo pasó a «Vigilancia».
  - diésel: `scripts/diesel_osinergmin.py` → `docs/data/diesel_piura.json`, con el diésel B5 S-50 UV en los grifos de Piura (Osinergmin, reporte mensual PRICE), de enero de 2024 a octubre de 2026. Pasa de S/ 15,27 por galón en febrero a S/ 19,97 en marzo de 2026 (+31 %) y llega a S/ 26,41 en octubre. La marca va en marzo (el primer mes en que supera en 5 % el precio de diciembre).
- **Parte D, canasta estimada:** `docs/data/canasta_pesos.json` y `canasta_estimada.json`.
  - **Pesos:** INEI, «Metodología para la medición de la pobreza» (nota01.pdf), Anexo N.° 02, págs. 62-66: canasta valorizada en soles por persona al día, Costa urbana, año base 2010, 110 productos (S/ 4,27 por día). No hay canasta de Piura ni de la costa norte.
  - **Correspondencia:** 19 productos del SISAP. Dudosos: arroz superior → arroz corriente, leche reconstituida → leche evaporada, palta fuerte → palta criolla, papa yungay → papa blanca. Sin producto en la canasta: frijol castilla, vainita, plátano bellaco y mango.
  - **Cobertura:** 33,6 % del valor de la canasta (17 productos con datos en los tres años). Las comidas fuera del hogar pesan 31,3 %.
  - **Resultado, diciembre a octubre, precios minoristas:**

    | Año | Parte cubierta = (a) | (b), resto con el IPC nacional | IPC nacional: alimentos / restaurantes |
    | --- | ---: | ---: | ---: |
    | 2024 | +3,6 % | +2,3 % | +0,9 % / +2,5 % |
    | 2025 | +1,5 % | +1,5 % | +0,8 % / +2,4 % |
    | **2026** | −4,8 % | **+1,6 %** | +5,9 % / +3,8 % |
    | Lo habitual | +2,5 % | +1,9 % | |

    En soles: unos S/ 4 más por persona al mes, S/ 16 para una familia de 4. Con precios mayoristas, (b) da +1,1 % en 2026.
- **Parte E:** la pestaña quedó en el orden título → canasta estimada → producto → IPC → canasta oficial → detalle. La tarjeta del Resumen ahora da la canasta estimada.

**Ajustes finales:**
- **Líneas de 2024 y 2025** (gráficos del producto y del diésel): ahora se distinguen por el trazo y el tono, sin dejar de ser grises de contexto. 2024 va punteada (gris `#aab4c0`) y 2025 continua (gris medio `#8a94a0`), las dos de 1,5 px. Cada una lleva un rótulo chico al final («2024», «2025»); si dos rótulos chocan, el de abajo baja. La leyenda repite el trazo (rayita punteada o continua).
- **Diésel:** la descarga empieza en diciembre de 2023 (S/ 18,66 por galón), la base del índice de 2024. Sin ella no salían 2024 ni «lo habitual».
- **GitHub Actions:** paso opcional `diesel`, que corre `diesel_osinergmin.py` y luego `precios_mensual.py` y aparece en el resumen de fuentes opcionales. El SISAP se sigue exportando a mano; al correr `precios_sisap.py`, este llama a `precios_mensual.py` al final.
- **Pruebas:**
  - `scripts/test_precios_sisap.py`: regla de «se separa», mes parcial, mínimo de fechas, 110 productos de la canasta (S/ 4,27 al día), la fórmula de (b), el IPC de enero a octubre de 2026, el índice con diciembre = 100 y las fechas de los shocks;
  - `scripts/test_pagina.py`: orden de la pestaña, tarjeta de la canasta (y la misma cifra en el Resumen), producto por defecto y orden de la lista, líneas (2024 punteada), marcas, barras, clic en la lista, «se separa» en el titular, tablas, enlace a la infografía;
  - infografía: 0 diferencias con `precios_sisap.json` y descarga de un PNG válido.
  - Todo pasa (598 combinaciones de Vulnerabilidad incluidas).
- **Capturas**, en `privado/capturas_tarea2/precios/`:
  - `precios_*` (pestaña completa con plátano seda congo, el producto por defecto);
  - `producto_papa_amarilla_*` (segundo producto);
  - `resumen_*`;
  - el PNG de la infografía, `precios_quincena_piura_2026-11-23.png` (1920 × 2276 px).
- `data/raw/` y `data/procesado/` siguen en `.gitignore`. Los PDF descargados (INEI y Osinergmin) quedan en `data/raw/`.
