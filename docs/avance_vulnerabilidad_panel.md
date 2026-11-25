# Vulnerabilidad: panel unificado, íconos, sectores y «Lluvia y localidades» (25/11/2026)

Cambios en la pestaña Vulnerabilidad de `docs/index.html` y decisiones tomadas. Sin push: pendiente de revisión.

## A. Un solo panel para el indicador

- Controles, resumen, mapa y sectores están ahora en una sola tarjeta (`#vul-panel`).
- Los controles (localidad, indicador, ver) quedan fijos al desplazarse, justo debajo de la barra superior de la página. La altura de esa barra se mide en vivo y se guarda en `--alto-fija`. En el celular, los tres selectores van en una sola fila para no tapar el contenido.
- En la PC (≥ 1024 px), el resumen va a la izquierda (1/3) y el mapa a la derecha (2/3), con la leyenda pegada arriba del mapa. Los sectores van debajo, a todo el ancho. En el celular, todo va en una columna: controles, resumen, mapa y sectores.
- Se quitaron los títulos de tarjeta «Mapa por sectores» y «Sectores»; quedan subtítulos livianos. El texto de ayuda y «¿Cómo se calcula cada indicador?» van en una sola línea bajo los controles.

## B. Íconos y lista de sectores

**Escala de los íconos.** Se decide una vez para la localidad elegida, con el porcentaje exacto (no el redondeado) del indicador en esa localidad:

- **10 % o más**: fila de 10 íconos por distrito o sub-área, como antes («3 de cada 10»).
- **Menos de 10 %**:
  - la cifra principal va en una cuadrícula de 10 × 10 íconos de unos 13 px cada uno (150 px de ancho; en el celular, centrada, con un máximo de 160 px);
  - los afectados se pintan desde la esquina superior izquierda, por filas, y el ícono parcial va en un tono intermedio (como en la fila de 10);
  - la frase va al lado: «2 de cada 100 personas de 15 años o más de la ciudad de Piura no saben leer ni escribir». Si el redondeo da 0, dice «menos de 1 de cada 100».
  - Cada distrito o sub-área lleva una barra corta del color del indicador, con su % al final y la frase en texto. Todas usan la misma escala: de 0 al máximo de las filas, redondeado hacia arriba a un múltiplo de 5 (a un entero si es menor que 5 %). La escala se rotula una sola vez («Barras de 0 a 3 %»).
- La cuadrícula y cada barra llevan la frase completa como texto alternativo.
- La tarjeta del Resumen (portada) sigue la misma regla, mediante `iconosVul`. Hoy muestra «sin desagüe», con 26,7 %, así que sigue con la fila de 10.
- «Días» y «horas sin agua» no son porcentajes: siguen sin íconos.

**Mínimos de los sectores** (`MIN_SECTOR`):

| Indicador en la localidad | Orden | Mínimo |
| --- | --- | --- |
| < 10 % | número de personas o viviendas afectadas | 200 personas o 50 viviendas u hogares |
| ≥ 10 % | el de antes (servicios: más de la mitad, por número; población: por %) | 100 personas o 30 viviendas u hogares |
| días u horas | por promedio, como antes | el del mapa (30) |

Se mantuvieron los mínimos propuestos. En 192 combinaciones de localidad e indicador bajo:
- 15 dejan menos de 5 sectores en la lista, pero en 12 de ellas es porque casi no hay casos, no por el mínimo;
- solo 3 (en localidades chicas, como El Alto) pierden sectores por el mínimo;
- bajarlo a 100/30 recupera solo 2 de esas 3.

**Título de la lista.** Con un indicador bajo: «Sectores con más personas que no saben leer ni escribir». Con uno alto, población mantiene «Sectores con mayor proporción de…». Servicios y vivienda mantienen «Los 5 sectores más críticos…», porque su orden es por número (entre los sectores con más de la mitad afectada) y «mayor proporción» sería inexacto.

**Nombres de los sectores** (`scripts/censo_inei.py`, función `nombres_osm`; se vuelve a correr solo esta parte con `--solo-nombres`). Orden de prioridad:

1. Zona residencial que contiene el centro del sector.
2. Barrio o caserío a menos de 400 m.
3. Vía principal a menos de 300 m.
4. **Nuevo**: hito con nombre a menos de 300 m (colegio, mercado, iglesia, parque, plaza, posta u hospital, comisaría, bomberos, estadio).
5. **Nuevo**: calle de cualquier clase con nombre a menos de 300 m.
6. **Nuevo**: «Sector al norte, sur, este u oeste de [barrio o zona más cercana]», sin límite de distancia. La dirección es la del eje dominante.

Ya no queda ningún «Sector sin nombre». Las pruebas lo verifican en `scripts/test_censo_inei.py` y `scripts/test_pagina.py`.

Resultado (1512 sectores de 350 m en las 26 localidades): antes, 240 sin nombre; ahora, 1382 «Sector cerca de…» (barrio, vía, hito o calle), 116 «Sector al norte/sur/este/oeste de…» y 14 por la zona residencial que los contiene. Las respuestas de Overpass quedan guardadas en `data/raw/osm/` (fuera del repositorio): volver a correr `--solo-nombres` no consulta otra vez.

## C. «Lluvia y localidades»: un solo bloque con dos vistas

- Se eliminó «Explorar relaciones», junto con la vista por manzana en la página. Debajo del mapa de lluvia hay un selector «Barras | Gráfico de puntos»; por defecto, Barras.
- **Las dos vistas comparten el titular y la nota.** El titular se arma en palabras, sin coeficientes:
  - describe la tendencia según la correlación sin ponderar entre localidades:
    - |r| < 0,2: «no hay una relación clara»;
    - 0,2 a 0,4: «tiende a ser más alto o más bajo (relación débil)»;
    - 0,4 a 0,6: la misma frase, sin adjetivo;
    - ≥ 0,6: «(relación marcada)»;
  - nombra las localidades del cuadrante destacado.
- **Cuadrante destacado:** por encima del promedio simple (sin ponderar) de las localidades en las dos variables.
  - Es el mismo en las barras. Ahí reemplaza al «tercio superior» anterior, para que el titular y las filas resaltadas coincidan.
  - Rótulo con lluvia × indicador: «Más lluvia y sin desagüe», «Más lluvia y adobe o tapia», etc. Es el mismo texto corto de las barras, cambiando «Mucha» por «Más».
  - Con un par personalizado: «Más X y más Y».
- **Preguntas guiadas** (cambian el indicador del panel de arriba, y el panel cambia la pregunta):
  1. ¿Llovió más donde hay menos desagüe? (sin desagüe por red pública)
  2. ¿Coinciden lluvia y viviendas frágiles? (paredes de material precario)
  3. ¿Llovió más donde hay más adobe? (paredes de adobe o tapia)
  4. ¿Coinciden lluvia y falta de agua? (sin agua por red pública)
  5. ¿Llovió más donde hay más pisos de tierra? (piso de tierra)

  Si el indicador del panel no tiene pregunta, el selector muestra «Indicador elegido arriba: …».
- **Personalizar** (desplegable): cualquier par entre los 23 indicadores, la lluvia de los cuatro años, viviendas y población. El color por provincia (leyenda en círculos) solo existe ahí.
- **Gráfico:**
  - eje horizontal: la lluvia del año del mapa; eje vertical: el indicador del panel;
  - líneas punteadas en el promedio simple de cada eje y sombreado suave en el cuadrante, con su rótulo;
  - puntos con área según las viviendas (r = 3 + 0,045·√viviendas, con tope de 16 px), en gris neutro, y en el color de acento los del cuadrante;
  - títulos de los ejes horizontales y con unidades (el del eje vertical va arriba, en HTML, para que salte de línea en el celular).
- **Regla de etiquetas:** se rotulan solo la localidad elegida, la Ciudad de Piura, las del cuadrante y los extremos (mínimo y máximo de cada eje), en ese orden de prioridad. Cada etiqueta prueba cuatro posiciones (derecha, izquierda, arriba, abajo); si choca con un punto, con otra etiqueta o con el rótulo del cuadrante, no se dibuja y queda en el globo. En el celular, la Ciudad de Piura suele quedar sin etiqueta porque está en el grupo más denso.
- **Detalle** (desplegable): correlación sin ponderar y ponderada por viviendas, el número de localidades y una nota sobre el peso de la Ciudad de Piura en la ponderada.
- La nota de CHIRPS aparece solo cuando la lluvia está en un eje (en barras, siempre).
- **Sincronía:** el año de la lluvia, el indicador y la localidad elegidos arriba se reflejan en las dos vistas. La localidad elegida lleva un borde oscuro en el gráfico de puntos.

## D. Binscatter por manzana (privado, no se publica)

- Script: `privado/binscatter_lluvia.py`.
- Gráficos: `privado/binscatter/*.png`, uno por cada uno de los 21 indicadores en %, con 2017 y 1998 en el mismo gráfico. Cada PNG tiene su tabla en un CSV del mismo nombre.
- Índice: `privado/binscatter_lluvia.md`.
- Método:
  - 20 tramos de manzanas por cuantiles de la lluvia de enero a abril;
  - en cada tramo, el % del indicador (suma de numeradores / suma de denominadores, es decir, ponderado por viviendas, hogares o personas);
  - intervalo del 95 % con el error del cociente agrupado por `id_celda` (unas 200 celdas).
- Stata: al final de `data/procesado/ejemplo_lluvia.do`, con `binsreg` (`nbins(20)`, `[aw = denominador]`, `vce(cluster id_celda)`) y un comentario sobre cómo leerlo. **No se probó:** `binsreg` no está en SSC y su instalación desde GitHub (`net install …`, la línea está en el .do) quedó pendiente para hacerla a mano.

## Capturas

En `privado/capturas_panel/` (375 y 1280 px): panel con sin desagüe (fila de 10) y con no sabe leer ni escribir (cuadrícula de 100 y barras), sectores, controles fijos al desplazarse y «Lluvia y localidades» en barras y en puntos con la pregunta del adobe.

# Segunda ronda: lectura y distribución (25/11/2026)

## 1. Tira de puntos en lugar de barras (indicadores bajo 10 %)

- Las barras «de 0 a 3 %» se reemplazaron por una sola tira horizontal:
  - un eje de 0 al máximo, redondeado hacia arriba a un múltiplo de 5 % (a un entero si es menor que 5 %), con marcas y etiquetas en 0, el medio y el máximo;
  - un punto por distrito en el color del indicador, con su nombre y % arriba;
  - una raya vertical oscura para la localidad completa, con su nombre y % debajo;
  - sin relleno ni pista de fondo.
- Si las etiquetas chocan, suben a otra fila (hasta tres), con una guía fina al punto.
- En la Ciudad de Piura, los puntos son los tres distritos y la marca es la ciudad. En otra localidad, el punto es la Ciudad de Piura (referencia) y la marca es la localidad.
- Debajo va una oración resumen («Va de 1,4 % en Piura a 2,4 % en Castilla.»). Las frases «2 de cada 100…» de cada distrito quedan como texto alternativo de la tira.
- La tira se vuelve a dibujar si cambia el ancho.

## 2. Sectores

- Todas las barras tienen el mismo largo: la barra completa es el 100 % del sector y la parte coloreada, la proporción afectada (en días u horas, la parte de los 7 días o de las 168 horas).
- El número va en el texto: «737 de 738 viviendas, 100 %».
- Títulos:
  - servicios, vivienda y hogar con ≥ 10 %: «Sectores con más viviendas sin agua por red pública: los 5 están en Veintiséis de Octubre». El subtítulo mantiene el criterio (más de la mitad, ordenados por número);
  - población con ≥ 10 %: «Sectores con mayor proporción de…»;
  - cualquier indicador bajo 10 %: «Sectores con más…».
- La lista ya estaba dentro del panel del indicador, a todo el ancho debajo del resumen y del mapa; se dejó así.
- Al hacer clic en un sector, la página sube al mapa (en el celular, el mapa queda arriba de la lista).
- El sector sin nombre de «sin agua por red pública» quedó corregido con el nuevo paso de nombres (vía, hito o «al norte de [barrio]»). No queda ninguno sin nombre.

## 3. Íconos parciales

- El ícono parcial ya no va en un tono intermedio (se leía como otra categoría). Ahora va recortado de izquierda a derecha (clipPath) en el mismo color, sobre el gris de las no afectadas.
- **Decisión:** se acordó un ancho mínimo del 20 %, pero se probó y una franja así se lee como un «1» (lo mismo que anotaba el código de una ronda anterior). Por eso el parcial se dibuja solo desde un cuarto de ícono, con su fracción real. Bajo eso no se pinta nada, lo que es coherente con la frase redondeada («3 de cada 10»).
- Verificado en Chromium (Brave). **Falta Safari:** Playwright no trae WebKit en este Mac (macOS 12). Hay que abrirlo a mano.

## 4. Controles fijos

- `scroll-margin-top` (barra de la página + controles + 12 px) en todo lo que tiene `id` en la pestaña. Al saltar desde un enlace o un sector, nada queda debajo de los controles. Las alturas se miden en vivo (`--alto-fija`, `--alto-controles`).
- Un poco de espacio arriba de la línea de ayuda y del resumen.
- En el celular, los controles son una sola fila de 44 px: los rótulos «Localidad», «Indicador» y «Ver» quedan solo para lectores de pantalla.

## 5. Gráfico de puntos

- Los puntos del cuadrante van en el color del indicador (paleta del mapa: #a71a00 en servicios, vivienda y hogar; #6d47b5 en población) y 2 px más grandes. El resto va en gris medio (`--gris-medio`, #8a94a0).
- **Validación con dataviz** (`validate_palette.js`, modo claro, superficie blanca):
  - color del indicador contra el gris: separación con daltonismo ΔE 21–22 y visión normal ΔE 22–28;
  - contraste ≥ 3:1;
  - el gris «falla» el piso de croma a propósito: es el gris de contexto, no una categoría.
- Sombreado del cuadrante: el mismo tono del indicador al 9 %.
- Rótulo del cuadrante: va en la primera esquina libre del cuadrante (arriba a la derecha, arriba a la izquierda, abajo a la derecha o abajo a la izquierda) sin tapar puntos ni etiquetas. Si ninguna está libre, va arriba del área de puntos, alineado a la derecha.
- Líneas de promedio más marcadas (texto secundario, 1,25 px, rayas 5-3). «Promedio» va fuera del área de datos: a la derecha de la horizontal y arriba de la vertical.
- La leyenda usa círculos de los mismos colores. Con «Color por provincia», se mantiene la paleta categórica.

## 6. Lluvia y localidades

- Nueva línea de introducción: «¿Las localidades con estas carencias son también las que recibieron más lluvia en los Niños pasados?».
- En la PC, el mapa de lluvia ocupa la mitad izquierda (440 px de alto, encuadrado al departamento) y el año, la leyenda, la frase y la nota de CHIRPS van a la derecha. Así ya no sobra gris a los costados.
- En el celular, todo va en una columna, con el mapa de 300 px.

## 7. Detalle

- Se eliminó la tarjeta «Detalle». Al final de «Lluvia y localidades» queda una línea con «Por distrito» y «Ver datos detallados» (al abrirse, ocupan todo el ancho), seguida de la nota de cobertura y la fuente.

## Capturas de la segunda ronda

En `privado/capturas_panel/ronda2/` (375 y 1280 px):
- `no_lee_tira_*`: tira de puntos;
- `sin_agua_red_*`: íconos parciales y sectores;
- `lluvia_puntos_desague_*`: gráfico de puntos con una pregunta guiada;
- `desplazamiento_0…3_*`: la pestaña en cuatro posiciones de desplazamiento.
