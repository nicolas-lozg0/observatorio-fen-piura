# Sistema de diseño del Observatorio FEN Piura

Los tokens viven al inicio del `<style>` de `docs/index.html` (bloque `:root`). Todo componente usa esos tokens: si hace falta un valor nuevo, se agrega aquí y en `:root`, no suelto en una regla.

Punto de partida: la identidad de https://www.udep.edu.pe/fen/ (azul marino institucional, fondo claro, sobriedad), sin el logo de la UDEP y con "Prototipo, no oficial" visible en la cabecera.

## Principios

1. **Un solo acento.** El azul `--acento` marca lo importante: Piura, el año en curso y el botón principal. Lo demás es neutro.
2. **El rojo es un estado, no un adorno.** Solo para alertas: la cifra de obras paralizadas, el semáforo «Muy lento» y "Dato no actualizado".
3. **Jerarquía con tipografía, tamaño y espacio.** Sin íconos decorativos, sin líneas ni cajas que no informen. Los paneles son superficies blancas separadas por espacio.
4. **Títulos que dicen el hallazgo.** Salen de reglas fijas sobre los datos (documentadas en "Fuentes y método"); si ninguna aplica, el título es la pregunta.
5. **Cada cifra con su fuente y fecha.**

## Color

| Token | Valor | Uso |
| --- | --- | --- |
| `--marino` / `--marino-2` | `#002856` / `#001d40` | Cabecera, barra fija, pestañas |
| `--sobre-marino` | `#c9d7f2` | Texto secundario sobre marino |
| `--titulo` | `= --marino` | Títulos y cifras |
| `--acento` / `--acento-hover` | `#2a78d6` / `#1f63b8` | Piura, 2026, botón principal, enlaces, pestaña activa |
| `--acento-suave` | `#e6effb` | Fondo de "En trámite" y del recuadro sin alertas |
| `--alerta` / `--alerta-suave` | `#c81e2b` / `#fdecee` | Solo alertas |
| `--fondo` / `--superficie` | `#eef2f7` / `#ffffff` | Fondo de página / paneles |
| `--texto`, `--texto-2`, `--texto-3` | `#14202e`, `#3e4751`, `#56616e` | Texto principal, secundario y notas. `--texto-3` da 5,5:1 sobre `--fondo` y 6,1:1 sobre blanco (mínimo 4,5:1) |
| `--linea`, `--pista`, `--esqueleto` | `#dbe2eb`, `#d6e5f7`, `#e2e8f0` | Bordes de tablas y controles, fondo de barras, esqueletos de carga |

**Colores de datos** (validados con la skill dataviz; no se usan en la interfaz):
- Comparación (años de brote del dengue, IPC nacional): `--comp1` `#b48b40`, `--comp2` `#aa5e7d`, `--comp3` `#2f7442`.
- Escala secuencial del mapa: `--q1` a `--q5`, de `#cde2fb` a `#184f95`. En el mapa de Salud colorea los casos de dengue por distrito.
- Escala de Vulnerabilidad (sectores y manzanas, 5 clases): `--v1` a `--v5`, de crema casi neutra a rojo oscuro (`#fbf2d0`, `#eab151`, `#d36800`, `#a71a00`, `#5f0000`), con claridad pareja en OKLCH (0,96 a 0,30). Relleno opaco y las calles del mapa encima en modo «multiplicar». Validada con dataviz tal como se ve: claridad monótona, saltos de 0,06 o más, vecinos con ΔE de 13,7 o más con daltonismo y 16,6 o más con visión normal. Falla a propósito dos reglas (aprobado): la crema casi no contrasta con el mapa (cada hexágono lleva un borde gris fino) y el tono pasa de amarillo a rojo. La vista de número usa los mismos 5 tonos. «Pocos casos» va en `--neutro`. Los cortes van por familia de indicadores (glosario, «Rangos del mapa»).
- Lluvia (mm en 24 h): `--ll1` a `--ll5`, el azul 250 a 700 de dataviz (`#86b6ef` a `#0d366b`), validado con `--ordinal`. Los círculos son lo medido en estación; las celdas al 45 % de opacidad, la estimación satelital.
- Temperatura del aire: `--gris-ref` `#aab4c0` (1997), `--gris-ref-claro` `#ccd3dc` (2016) y `--calor` `#f08c2a`, solo para sombrear con 22 % de opacidad lo que 2026 pasa sobre la mediana (por debajo, `--acento` al 15 %).
- Semáforo del presupuesto anual: `--ritmo-ok` `#1a9a8a` (a ritmo), `--ritmo-lento` `#c98200` (algo lento) y `--ritmo-muy-lento` (= `--alerta`, muy lento). Solo para la ejecución del presupuesto del año frente al calendario, siempre con su texto al lado. Separación para daltonismo de 12,3 o más y contraste de 3:1 o más sobre blanco; sobre `--pista` baja de 3:1, por eso el texto es obligatorio.

La página está fija en modo claro (`data-theme="light"`, porque se incrustará en la web de la UDEP). Los tokens tienen versión oscura por si se activa.

## Tipografía

| Token | Valor |
| --- | --- |
| `--f-titulo` | Montserrat 700 y 800 (títulos y cifras) |
| `--f-texto` | Nunito Sans 400 y 700 (texto, tablas, ejes) |
| `--f-codigo` | Monoespaciada del sistema; **solo** para códigos (CUI, ubigeo) |

Las fuentes están en `docs/fuentes/` (licencia OFL); no dependen de Google.

Escala 1,25 sobre 16 px:

| Token | Tamaño | Uso |
| --- | --- | --- |
| `--t-xs` | 13 px | Pies de fuente, rótulos de mini-gráficas, ejes |
| `--t-sm` | 15 px | Notas, tablas, frases de panel |
| `--t-base` | 16 px | Texto |
| `--t-md` | 20 px | Títulos de panel en la portada, avance en la tabla de gasto |
| `--t-lg` | 25 px | Títulos de pestaña |
| `--t-xl` | 31 px | Cifra de tarjetas anchas |
| `--t-2xl` | 39 px | Cifra principal de cada panel |

Reglas:
- Números tabulares (`font-variant-numeric: tabular-nums`) en toda la página, para que las cifras se alineen en tablas, tarjetas y ejes.
- `text-wrap: balance` en los títulos (sin palabras sueltas en la última línea) y `pretty` en los párrafos.
- Sin cursivas ni mayúsculas sostenidas en etiquetas.

## Espacio, radios y sombras

- **Espacios** en múltiplos de 4 y 8 px: `--e1` 4, `--e2` 8, `--e3` 12, `--e4` 16, `--e5` 24, `--e6` 32, `--e7` 48, `--e8` 64. Se agrupa con espacio: más espacio entre grupos que dentro de ellos.
- **Radios**: `--r-panel` 16 px (paneles, detalle), `--r-control` 8 px (selectores, globos, avisos), `--r-pastilla` para botones, distintivos y barras.
- **Radios concéntricos**: el radio interior es igual al radio exterior menos el relleno. Un panel de 16 px con relleno de 24 px deja el contenido en ángulo recto; el esqueleto de carga, con relleno de 24 px, usa `--r-control`.
- **Sombra**: solo `--sombra-flotante`, para lo que flota sobre la página (aviso "Enlace copiado", definición de un término, globo de los gráficos). Los paneles no llevan sombra ni borde.

## Componentes

- **Panel** (`panel()` en el código): título, cifra principal (`--t-2xl`), unidad, distintivo de estado si aplica, mini-gráfica, una frase, enlace "Ver [pestaña] →" (solo en la portada) y pie con fuente y fecha. Si la tarjeta tiene un cálculo que explicar, el pie termina en "· Cómo se calcula", un botón que despliega la nota debajo (sin ventana). Puede llevar un subtítulo (`sub`) bajo el título.
- **Mini-gráfica** (`chispa()`): sin ejes. Rotula el valor inicial y el final con su periodo, y debajo el periodo que cubre. El gráfico completo, con ejes, está en cada pestaña.
- **Medidor**: barra de avance en `--acento` sobre `--pista`. En el presupuesto del año, la barra toma el color del semáforo, lleva su texto («A ritmo», «Algo lento», «Muy lento») y una marca vertical con lo esperado: el porcentaje del año transcurrido. La marca mide 3 px, sobresale 4 px arriba y abajo de la barra, va en `--texto` y lleva un borde de 1 px del color de la tarjeta (así se ve sobre el rojo, el ámbar y el verde azulado). Lo esperado sale de una sola función (`esperadoGasto()`) con un solo redondeo (`esperadoFmt()`). La marca no lleva rótulo: arriba de la tabla o de la barra va una leyenda con una muestra de la marca, "Lo esperado a la fecha: 86 % del año" (`leyendaEsperado()`).
- **Panel destacado y compacto** (portada): el hallazgo más urgente (dengue) en `.destacado`, que ocupa dos filas; los otros 4 en `.compacto` (cifra `--t-xl`, sin frase), en 2 x 2 y de igual alto.
- **Lista visual** (`.lista-visual`): nombre corto (salta de línea, nunca se corta con "…"), monto destacado con su porcentaje del total y una línea de metadatos con etiquetas grises (`.etiqueta`). Sin barras.
- **Barras horizontales** (`.barras-h`): una medida por categoría, ordenadas por esa medida; la categoría y el conteo como texto arriba, el monto al final de la barra. "Otras" siempre al final. Un solo color (`--acento`).
- **Gráfico de puntos** (`.puntos`, `graficoPais()`): una fila por categoría, ordenadas de mayor a menor; puntos en `--texto-3` y la categoría propia (Piura) en `--acento`, más grande y con su nombre y valor en negrita; una línea punteada para el total del país. Cuando hay dos medidas (número y costo), dos gráficos lado a lado (`.dos-graficos`), cada uno ordenado por su valor y con el puesto de Piura arriba. El gris es contexto a propósito (no compite con Piura); la tabla está en el detalle.
- **Barras dobles** (`barrasDobles()`): una fila por categoría con dos barras, número y monto, cada una con su propia escala (provincias de Obras).
- **Término con definición** (`g()` y `ayudas()`): subrayado punteado sutil en la primera aparición del término en cada tarjeta o párrafo. Es un botón con `aria-describedby="definicion"`: la definición se abre al pasar el cursor, con el foco o al tocar, y se cierra con Esc o al tocar fuera. Todas las definiciones están en `DEFINICIONES`, incluidas las causas de paralización (`DEFINICIONES.causas`: causa, definición, fuente y URL), que se marcan con `gc()`.
- **Nombres legibles**: entidades con nombre completo en mayúscula inicial y siglas entre paréntesis como las usa la prensa ("Ministerio de Desarrollo e Inclusión Social (Midis)"), desde `data/nombres_entidades.json`; si falta una, `legible()` aplica la regla al nombre original. Nombres cortos de obras desde `data/nombres_cortos_obras.json` o `nombreCorto()`.
- **Pares de barras** (`.pares`, `paresPais()`): Piura frente al país en dos medidas que comparten la misma escala, para que se vea cuánto pesa una frente a la otra. Piura va en `--titulo` y el país en el gris `--o-resto`. El rótulo «Piura» o «País» va junto a cada barra y el valor al final, sin ejes ni leyenda aparte. Se usa en la tarjeta del Resumen y en el bloque de obras paralizadas.
- **Barra apilada de concentración** (`.barra-costo`, `barraCosto()`): un tramo por cada uno de los 5 primeros, en `--o1` a `--o5` (azul marino de oscuro a claro), y un tramo gris `--o-resto` con el resto, separados por 2 px. Cada tramo es un botón: el número va dentro si cabe (container query) y el nombre y el monto salen en la ventana de las definiciones (cursor, foco o toque; Esc cierra). La tinta de cada tramo (`--oi1`…) cumple 4,5:1. La paleta se validó con el validador de dataviz: ΔE ≥ 15 entre tramos vecinos con visión normal y ≥ 14 con daltonismo.
- **Lista compacta** (`.lista-top`): la línea 1 lleva la muestra con el número, el nombre (salta de línea, sin truncar) y, a la derecha, el monto y el porcentaje en columnas con cifras tabulares. La línea 2, más tenue, lleva lugar · tiempo y las etiquetas. Las filas se separan con una línea `--linea`. En celular, la línea 2 usa todo el ancho.
- **Mapa** (`mapaBase()`): Leaflet 1.9.4 y markercluster 1.5.3 desde cdnjs, y leaflet-gesture-handling 1.2.2 desde jsDelivr, con SRI, cargados solo al abrir la pestaña. Fondo gris claro de Esri (World Light Gray, sin clave) con sus nombres de calles y lugares encima, y el crédito «Mapa base: © Esri, HERE, Garmin, © colaboradores de OpenStreetMap». CARTO Positron pide clave desde 2026. Todos los mapas miden 60 % del alto de la ventana (máximo 560 px; en celular, 420 px) y no atrapan el desplazamiento de la página: en computadora se acerca con Ctrl + rueda y en celular el mapa se mueve con dos dedos. Si no carga, lo dice.
- **Gráfico por día** (`graficoMeses()` con `op.dias`): el mismo gráfico de líneas o barras, con fechas dd/mm contadas desde el último día. `op.sinCero` deja que el eje no parta de 0 (temperaturas), `op.hi` da la misma escala a varios gráficos (las tres series de lluvia) y un `null` es un día sin dato: sin barra y «sin dato» en el globo, nunca 0.
- **Tarjetas de Clima**: cada una termina en «Más detalle: [fuente] →» (enlace a la fuente original, en otra pestaña) y en el pie de siempre. El radar usa el botón principal «Ver radar en vivo»; con `RADAR_IFRAME = true` se muestra incrustado (`.radar`, 420 px de alto) y el botón queda debajo.
- **Mapa de sectores y manzanas** (Vulnerabilidad): el mismo `mapaBase()`. Selector de localidad, indicador y «Ver» (porcentaje o número por hectárea), con la nota «% muestra dónde el problema es más común; número, dónde hay más hogares afectados». Título con el indicador en palabras («Viviendas sin desagüe por red pública»). Niveles según el zoom (350 m, 130 m solo en Ciudad de Piura, manzanas), uno a la vez, en las dos vistas. Clases fijas: servicios y vivienda en palabras con su cifra («Casi todas (80–100 %)»); la vista de número usa afectados por hectárea de manzana (densidad neta). Leyenda: la unidad, una barra apilada con el reparto de toda la localidad en sus sectores de 350 m, los rótulos y una frase generada con los datos («De cada 100 viviendas de…»). Debajo del mapa, los 5 sectores críticos y la comparación entre localidades: barras horizontales de mayor a menor %, con el color de su clase, una línea punteada del promedio de las zonas urbanas, el % y el número con el mismo peso, la localidad elegida destacada y un titular que contrasta el mayor % con el mayor número.
- **Mapa de lluvia** (Clima): solo el departamento de Piura, con lo de afuera oscurecido (máscara al 35 %). Leyenda en dos líneas: la barra de mm y los símbolos. Estaciones como círculos con el color de su clase y el tamaño según los mm; menos de 1 mm, círculo blanco; sin dato, contorno punteado. Nombre y mm junto a las 5 con más lluvia (a la izquierda si chocan); el resto, al pasar el cursor. Debajo, el top 5 en una línea y la ventana de la estimación satelital.
- **Disposición de Clima**: en computadora, 6 columnas: ENFEN (4, con el texto y el gráfico del Niño 1+2 lado a lado) y mar (2); radar y lluvia (3 y 3, del mismo alto); series (6). En celular, una columna en ese orden; el ENFEN muestra la etiqueta y una línea, y «Ver más» abre los puntos clave y el gráfico.
- **Frases con casas** (Vulnerabilidad): una fila por distrito (o la localidad y la Ciudad de Piura como referencia), de mayor a menor %, con el texto «N de cada 10» y 10 casas en SVG en línea: las afectadas en `--v4`, el resto en `--neutro`; la fracción llena una casa de abajo hacia arriba. La fila de casas lleva `role="img"` con la misma frase y no es enfocable; en el celular va debajo del texto.
- **Los 5 sectores más críticos** (Vulnerabilidad): titular generado (distrito donde están), subtítulo con el criterio, y filas-botón con nombre y distrito, una barra (largo = viviendas del sector, relleno = afectadas) y la cifra. Clic o Enter: el mapa va al sector, lo resalta con un borde y abre su globo.
- **Regla de las tarjetas de Clima y del Resumen** (ronda 20): el cuerpo dice qué pasa y qué significa en lenguaje simple; lo técnico (tipo de dato, fuente de cada tramo, correcciones, umbrales no oficiales, desde cuándo hay serie) va a «Cómo se calcula» o al globo de un término.
- **Temperatura del aire** (Clima, ancho completo): titular «Piura está X °C más caliente que lo normal para esta época», cifra grande con la anomalía y una línea con el promedio de 7 días y lo normal. Encima del gráfico, la frase «Comparamos con los dos Niños…» y la leyenda en una línea. Gráfico de 90 días con promedios móviles de 7 días: franja de lo normal (percentiles 10 a 90, `--neutro`) con su mediana (`--texto-3`), sombreado entre 2026 y la mediana (`--calor` o `--acento`, sin rellenar hasta el eje), 1997 en `--gris-ref` y 2016 en `--gris-ref-claro`, finas; solo 2026 lleva rótulo al final («2026: 34,7 °C»). Bajo 640 px no se dibujan 1997 ni 2016 (clase `.solo-ancho`). Pie: «Fuente: reanálisis ERA5-Land y modelo de pronóstico (Copernicus/ECMWF), vía Open-Meteo. Datos al … · Cómo se calcula».
- **Ríos** (Clima, ancho completo, debajo de la temperatura): dos columnas (Piura | Chira), apiladas en el celular. Cada una abre con una frase generada (`fraseRio()`): la pastilla del aviso del Senamhi (`--aviso-amarillo`, `--aviso-naranja`, `--aviso-rojo`; «Sin aviso» en `--neutro`), qué dice el aviso en palabras (si es un afluente, «que desemboca en el …») y la tendencia del nivel (±5 cm en 6 horas; `tendenciaRio()`). Con aviso naranja o rojo la frase va en negrita. Debajo, «Nivel: 0,57 m · hora» chico, con globo («no es profundidad del río»), y el gráfico con el área bajo la línea en `--ll1` (el agua) y la hora cada 4 horas (cada 8 bajo 500 px).
- **Tarjeta de El Niño** (portada, ancho completo, debajo de la pregunta): titular con el mensaje, 3 columnas (estado del ENFEN con su etiqueta y la magnitud; mar frente a Paita y aire en Piura con cifra grande), una línea con los ríos (la misma frase de Clima resumida; con aviso naranja o rojo, recuadro con borde del color oficial y negrita), «Ver clima →» y pie con la fuente y la fecha de cada dato. En el celular, las columnas se apilan con cifras más chicas.
- **Grilla del Resumen**: 6 tarjetas del mismo ancho, 3 × 2 en la computadora (2 × 3 en la tablet, una columna en el celular); cada fila a la medida de su contenido. Orden: dengue, camas, Vulnerabilidad (lo que pesa en una emergencia); gasto, obras, precios. La de Vulnerabilidad: titular con la proporción («Más de 1 de cada 4…», `fraccionTxt()`), cifra, 10 casas de unos 22 px y el distrito con el mayor %.
- **Lluvia de 30 días** (Clima): tres gráficos de barras chicos (costa, valle medio y sierra) con la misma escala (máximo de los tres, entre 20 y 60 mm; lo que pasa de 60 se corta y lleva su valor), total de 30 días como cifra destacada, ubicación en una línea bajo el nombre, fechas cada 7 días, 0 mm con marca gris en la base, y un selector de estación debajo de cada uno. Todas las fechas de lluvia salen de `diaLluvia()` («lunes 16/11»).
- **Radar**: la imagen más reciente enlazada a su servidor, del mismo alto que el mapa (`object-fit: contain`); si no carga, la tarjeta lo dice y deja el botón «Ver radar en vivo».
- **Etiqueta de estado** (`.etiqueta-estado`): el estado del ENFEN en una pastilla grande; en rojo `--alerta` solo si es una alerta.
- **Botones**:
  - principal (`.boton`, "Siguiente"): relleno `--acento`;
  - secundario (`.boton-2`, "Ver detalle", "Ver más"): borde `--linea` y texto `--acento`.
  - Todos miden al menos 44 px de alto.
- **Distintivos de estado**: solo dos, siempre con ícono y texto. "Dato no actualizado desde…" (reloj, rojo) y "En trámite" (reloj de arena, azul suave). Una cifra que pide atención (obras paralizadas) va en el rojo de alerta, sin etiqueta (clase `cifra-alerta`). Lo pendiente se dice en la frase del panel, con borde punteado.
- **Tabla comparativa** (Gasto): una fila por concepto y una columna por vista. En celular, el concepto va arriba y las dos vistas lado a lado.
- **Carga y errores**: esqueletos mientras llegan los datos. Si una fuente no carga, su panel lo dice y sugiere volver a cargar.

## Movimiento

Breve y útil, solo como respuesta a una acción:
- al cambiar de pestaña, el contenido aparece en 160 ms;
- al abrir "Ver detalle", el cuerpo aparece y la flecha gira;
- "Enlace copiado" sube desde abajo.

Con `prefers-reduced-motion: reduce` no hay animaciones ni transiciones.
