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
