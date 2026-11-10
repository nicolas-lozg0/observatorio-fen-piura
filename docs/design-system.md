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
| `--t-xs` | 12 px | Pies de fuente, rótulos de mini-gráficas, ejes |
| `--t-sm` | 14 px | Notas, tablas, frases de panel |
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
- **Medidor**: barra de avance en `--acento` sobre `--pista`. En el presupuesto del año, la barra toma el color del semáforo, lleva su texto («A ritmo», «Algo lento», «Muy lento») y una marca vertical con lo esperado: el porcentaje del año transcurrido. En las barras grandes, la marca lleva el rótulo "esperado 85 %" (`esperadoTxt()`); en las filas de tabla, solo la marca.
- **Panel destacado y compacto** (portada): el hallazgo más urgente (dengue) en `.destacado`, que ocupa dos filas; los otros 4 en `.compacto` (cifra `--t-xl`, sin frase), en 2 x 2 y de igual alto.
- **Lista visual** (`.lista-visual`): nombre corto (salta de línea, nunca se corta con "…"), monto destacado con su porcentaje del total y una línea de metadatos con etiquetas grises (`.etiqueta`). Sin barras.
- **Barras horizontales** (`.barras-h`): una medida por categoría, ordenadas por esa medida; la categoría y el conteo como texto arriba, el monto al final de la barra. "Otras" siempre al final. Un solo color (`--acento`).
- **Barras dobles** (`barrasDobles()`): una fila por categoría con dos barras, número y monto, cada una con su propia escala (provincias de Obras).
- **Término con definición** (`g()` y `ayudas()`): subrayado punteado sutil en la primera aparición del término en cada tarjeta o párrafo. Es un botón con `aria-describedby="definicion"`: la definición se abre al pasar el cursor, con el foco o al tocar, y se cierra con Esc o al tocar fuera. Todas las definiciones están en `DEFINICIONES`.
- **Nombres legibles**: entidades con nombre completo en mayúscula inicial y siglas entre paréntesis como las usa la prensa ("Ministerio de Desarrollo e Inclusión Social (Midis)"), desde `data/nombres_entidades.json`; si falta una, `legible()` aplica la regla al nombre original. Nombres cortos de obras desde `data/nombres_cortos_obras.json` o `nombreCorto()`.
- **Mapa** (`mapaBase()`): Leaflet 1.9.4 y markercluster 1.5.3 desde cdnjs, con SRI, cargados solo al abrir la pestaña. Fondo de OpenStreetMap con su atribución, distritos de `piura_distritos.json`, puntos `--marino` agrupados, sin zoom con la rueda y, en celular, con dos dedos. Si no carga, lo dice.
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
