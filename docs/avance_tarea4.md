# Avance: la página como tablero con pestañas e IPC de Piura

Fecha: 3 de noviembre de 2026; publicado en GitHub Pages. El rediseño visual del 5 de noviembre está en la sección E.

## Cómo verla en local

```
python3 -m http.server 8000 -d docs
```

Luego abrir http://localhost:8000. Cada pestaña tiene su dirección: `#resumen`, `#dengue`, `#gasto`, `#obras`, `#salud`, `#precios`, `#fuentes` (por ejemplo, http://localhost:8000/#dengue). Para incrustar una pestaña en la web de la UDEP basta con usar esa dirección en un iframe.

## A. Estructura

- **Pestañas:** Resumen · Dengue · Gasto · Obras · Salud · Precios · Fuentes y método. En celular se deslizan de lado. Los enlaces antiguos a secciones internas (`#alertas`, `#prevencion`, `#emergencia-fen`, `#dengue-semanas`…) abren la pestaña que las contiene y, si están dentro del detalle, lo despliegan.
- **Resumen:** cinco paneles con título en forma de pregunta ("¿Cómo está el dengue?", "¿Cuánto se ha gastado?", "¿Cómo van las obras?", "¿Está preparada la salud?", "¿Cómo están los precios?"), la cifra principal, una mini-gráfica cuando aplica (serie semanal de dengue, barra de gasto con la marca del año transcurrido, barra de ocupación, serie del IPC en 12 meses), una frase y la fuente con su fecha. Al hacer clic en un panel se abre su pestaña.
- **Dos capas:** arriba, 3 a 5 paneles con cifras y gráficos; abajo, el botón "Ver detalle" (un `<details>` nativo) con las tablas completas, los filtros y las notas de método. Ninguna tabla larga se ve sin abrir el detalle (comprobado por script en las 7 pestañas). La única tabla visible es la de fuentes (11 filas), que es el contenido de esa pestaña.
- **Ayuda "?":** PIM, devengado, marco presupuestal, programas 0068 y 0017, ANIN, semana epidemiológica, confirmados y probables, dengue grave, preliminar, ocupación, camas UCI, obra paralizada, avance físico, "más pagado que construido", IPC, variación mensual y en 12 meses. Cada uno lleva un ícono que muestra una explicación de una línea (clic o teclado; Escape la cierra). Las mismas definiciones forman el glosario en "Fuentes y método".
- **Frases generadas con reglas** (escritas también en "Fuentes y método"):

| Tema | Regla |
| --- | --- |
| Dengue, semana | Casos de la última semana frente a la anterior: más, menos o igual. Avisa que son preliminares. |
| Dengue, año | Casos de 2026 hasta la última semana frente a la suma hasta esa misma semana en 2017, 2023 y 2024. Dice si es la más alta, la más baja o entre cuáles queda. |
| Gasto | Porcentaje gastado del PIM frente al porcentaje del año transcurrido a la fecha de los datos: "menor" o "mayor" si la diferencia supera 5 puntos; si no, "similar". |
| Obras | Número de paralizadas, costo y la causa registrada con más obras. |
| Salud | Ocupación promedio del último mes publicado y número de establecimientos que reportaron. |
| Precios | "Subieron" o "bajaron" según el signo de la variación mensual (0,00 % = "no variaron"). La variación en 12 meses se compara con la nacional: "mayor" o "menor" si la diferencia es de 0,1 puntos o más; si no, "similar". |

## B. Contenido por pestaña

| Pestaña | Vista simple | Detalle |
| --- | --- | --- |
| Dengue | Casos de la semana (con mini-serie), casos del año (comparados con años de brote), fallecidos. Serie semanal frente a 2017, 2023 y 2024, con meses en el eje y las 3 últimas semanas punteadas. Mapa por distrito con selector de año. | Tabla por distrito, gravedad y diagnóstico, opción "solo confirmados" para los años anteriores, notas de método y validación de la sala. |
| Gasto | Los dos puntos de vista lado a lado ("Gastado en Piura" y "Gastado por entidades con sede en Piura") para el total, prevención (0068), emergencia FEN, reconstrucción (ANIN) y dengue (0017), cada uno con su desglose por nivel de gobierno. Una línea explica por qué difieren, con montos calculados: hoy, S/ 3.533,7 millones del PIM gastado en Piura son de entidades con sede fuera, todas del gobierno nacional. | Tabla de proyectos con filtros (incluido el punto de vista), gasto FEN por entidad, notas. |
| Obras | Alertas primero: obras paralizadas (número, costo, causa principal y las 5 de mayor costo con su causa), causas de paralización en barras y "¿más pagado que construido?". Luego, las obras en ejecución: número, costo, cuántas tienen avance físico en el MEF, la nota del archivo congelado de Infobras y las 5 de mayor costo con su avance. | Tabla de paralizadas, tabla de obras con filtros, tabla de brecha, notas. |
| Salud | Camas de hospitalización y UCI, ocupación del mes, hospitalizados por dengue (con mini-serie) y vacunación: "Pedido en trámite a la DIRESA". | Camas por establecimiento, hospitalizados por establecimiento, notas. |
| Precios | Variación mensual y en 12 meses del IPC de Piura frente a la nacional, gráfico de 24 meses de la variación en 12 meses (Piura y nacional), barras de la variación mensual y el panel del SISAP como "En preparación". | Serie completa con enlace al PDF de cada mes, dato de control y resultado de la verificación. |
| Fuentes y método | Tabla de fuentes con frecuencia y fecha de cada una (ahora incluye el IPC). | Criterios, cómo se generan las frases, cómo se valida cada dato, glosario. |

### IPC de Piura (nuevo: `scripts/ipc_inei.py`)

- **Fuente:** informe técnico mensual del INEI "Variación de los Indicadores de Precios de la Economía", Cuadro 2 (variación del IPC nacional y de 26 ciudades). Lista: https://www.inei.gob.pe/biblioteca-virtual/boletines/informe-de-precios/1/
- **Validación:** el informe de febrero de 2026 dice Piura **0,48 %** mensual y **2,28 %** en 12 meses, igual que el dato de control. Además, en cada corrida se compone la serie mensual y se compara con la variación en 12 meses y la acumulada que publica el INEI: los 30 meses pasan sin avisos.
- **Serie:** 30 meses, de mayo de 2024 a octubre de 2026 (la página grafica los últimos 24). Último dato: octubre de 2026, con 0,59 % mensual y 3,39 % en 12 meses (nacional: 4,83 %).
- **Cómo se lee:** los nombres de los PDF no siguen un patrón, así que el script los toma de la lista de la biblioteca virtual (las 3 primeras páginas, 30 informes) y solo descarga los que no están en `docs/data/ipc_piura.json`. Una corrida sin informes nuevos tarda unos 20 segundos y no descarga ningún PDF.
- **Dos detalles resueltos:**
  - En la mitad de los informes el cuadro tiene una inclinación mínima, y `extract_text()` de pdfplumber mezcla sus columnas. Por eso el script arma las líneas agrupando caracteres por altura.
  - En enero y diciembre el cuadro trae solo dos columnas: en enero, mensual = acumulada; en diciembre, acumulada = 12 meses. Si aparecieran dos columnas en otro mes, el script no las adivina y no lee ese informe.
- **Actualización:** se agregó a `actualizar.yml` (diario, con `continue-on-error`). Como solo descarga cuando hay un informe nuevo, en la práctica se actualiza una vez al mes, el día 1.

## C. Diseño

- *El color y la tipografía de esta sección se reemplazaron en el rediseño (sección E); el resto sigue vigente.*
- Modo claro fijo, paleta neutra (grises) y un color de acento (azul). En el gráfico de dengue, 2026 va en azul y los años anteriores en tres grises, con rótulo al final de cada línea, leyenda y globo al pasar el cursor; antes eran naranja, verde y amarillo. El IPC usa azul para Piura y gris para el nacional.
- El énfasis lo dan el tamaño y la posición: la cifra principal es grande y la alerta de obras paralizadas lleva un borde izquierdo oscuro y ocupa todo el ancho.
- Se mantienen "Prototipo, no oficial", `noindex`, la fuente y la fecha en cada panel, y todos los cálculos validados: gasto por lugar y por sede, salas de la DIRESA, mapa, ocupación de SUSALUD, avance del MEF por CUI y estado de Infobras. Las funciones de cálculo son las mismas; solo cambió dónde se muestran.
- Los gráficos se vuelven a dibujar al cambiar de pestaña y al cambiar el tamaño de la ventana. Ya no hay que recargar al girar el celular.

## D. Verificación

- **Escritorio (1280 px):** revisé las 7 pestañas en Chrome, sin errores en la consola, también después de abrir todos los detalles y cambiar los filtros (punto de vista, año del mapa, solo confirmados).
- **375 px** (dentro de un marco de ese ancho): ninguna pestaña desborda de lado, ni con el detalle abierto. Los paneles se apilan en una columna, las pestañas se deslizan y las dos vistas del gasto caben lado a lado.
- **Direcciones:** las 7 direcciones `#pestaña` muestran solo su pestaña y marcan la activa en el menú; `#alertas` abre Obras con el detalle desplegado.
- **Ajustes después de revisar:**
  - Un rótulo del IPC se salía por la derecha.
  - Los años del eje se encimaban en celular.
  - "establecimiento(s)" ahora distingue singular y plural.
  - La alerta de obras ahora ocupa todo el ancho.
  - Al cambiar de pestaña, la página vuelve al inicio de la pestaña.
- **Workflows:** cada archivo que carga la página tiene su script:

| Archivo | Script | Workflow |
| --- | --- | --- |
| `gasto_piura.json` | `gasto_mef.py` | `actualizar.yml` |
| `inversiones_piura.json` | `inversiones_mef.py` | `actualizar.yml` |
| `fen_piura.json` | `fen_mef.py` | `actualizar.yml` |
| `infobras_piura.json` | `infobras.py` | A mano, con `scripts/actualizar_local.sh` (ver `docs/actualizacion_local.md`) |
| `camas_piura.json` | `camas_susalud.py` | A mano, con `scripts/actualizar_local.sh` |
| `ipc_piura.json` | `ipc_inei.py` (nuevo) | `actualizar.yml` |
| `dengue_2026.json` | `dengue_diresa.py` | `dengue.yml` |
| `dengue_historico.json`, `piura_distritos.json` | `dengue_historico.py`, `mapa_distritos.py` | Archivos fijos, a mano (igual que antes) |

  `historial.csv` y `historial.py` se borraron: las mini-gráficas salen de las series de cada fuente.

## E. Rediseño visual (5 de noviembre de 2026)

Solo cambia la presentación: los datos, los cálculos validados, las fuentes y las direcciones `#pestaña` son los mismos. Commits `c0fc8c7`, `f111065` y `991b5b0`, publicados en GitHub Pages.

- **Identidad de udep.edu.pe/fen, sin logo:**
  - colores: azul marino `#002856` en la cabecera y la barra, celeste en el texto sobre marino, y rojo solo para alertas y para marcar la pestaña activa;
  - tipografías: Montserrat (títulos y cifras) y Nunito Sans (texto), guardadas en `docs/fuentes/` (66 KB, licencia OFL), sin depender de Google;
  - se mantiene "Prototipo, no oficial".
- **Barra fija:**
  - al bajar quedan visibles "Actualizado al [fecha]", el botón "Compartir esta pestaña" y las pestañas (44 px de alto como mínimo, para el dedo);
  - "Actualizado al" es la fecha más reciente entre las fuentes, y cada cifra conserva la suya;
  - compartir abre el menú del sistema en celulares (WhatsApp, correo…) y copia el enlace en computadoras.
- **Portada:**
  - "¿Cómo está Piura frente a El Niño?" y un recuadro "Piden atención", que lista lo que cumple alguna regla (descritas en "Fuentes y método"): el dengue sube frente a la semana anterior, hay obras paralizadas, el gasto va más lento que el calendario o hay fuentes sin actualizar en su plazo;
  - debajo, 5 paneles del mismo tamaño, cada uno con ícono, pregunta, cifra, mini-gráfica, una frase y la fuente con su fecha;
  - el panel de obras tiene ahora una mini-gráfica: la proporción de obras activas que están paralizadas.
- **Menos texto en la vista simple:** introducciones de una línea y una frase por panel. Las explicaciones largas, como por qué difieren las dos vistas del gasto o los establecimientos con más de 100 % de ocupación, pasaron a "Ver detalle". En Obras, los nombres largos se cortan a dos líneas; el nombre completo se ve al pasar el cursor y en la tabla.
- **Distintivos comunes, siempre con ícono y texto:**
  - rojo con reloj: "Dato no actualizado desde…";
  - azul con reloj de arena: "En trámite" (vacunación);
  - gris punteado: "En preparación" (SISAP) o "Pendiente" (IPC, si no carga).
- **Navegación:** al final de cada pestaña, "Siguiente: [pestaña] →"; la última dice "Volver al resumen".
- **Dengue:** junto al mapa, los 5 distritos con más casos (las primeras filas de la tabla que ya existía).
- **Gráficos:** usan la tipografía de la página, rótulos en color de texto con un punto del color de la serie y los mismos colores de datos validados con la skill dataviz (sin colores nuevos). Se vuelven a dibujar cuando terminan de cargar las tipografías.

**Verificación:**
- `scripts/test_pagina.py` pasa. Agregué la comprobación de las pestañas de 44 px, el botón de compartir, los enlaces "Siguiente" y "Actualizado al".
- Capturas en celular (375 px) de las 7 pestañas, y de la portada y Dengue en escritorio.
- Sin errores en la consola.

**Ajustes después de la revisión de código:**
- **Dengue en la portada:** "El dengue sube" y la frase del panel comparan la semana actual y la anterior de la misma tabla, la de distritos. La cifra del panel sigue saliendo de la tabla por provincia, y ambas pueden diferir en pocos casos: en la semana 42, 1.098 frente a 1.099.
- **Reglas calculadas una vez:** dengue, obras paralizadas y ritmo del gasto se calculan una sola vez para el aviso y los paneles.
- **Colores en variables:** títulos, cifras, íconos y distintivos ya tienen versión oscura, pero la página sigue fija en modo claro (`data-theme="light"`, por la web de la UDEP).

**Decisiones del rediseño que conviene revisar:**
- En la pestaña Dengue, los tres paneles tienen el mismo tamaño (no hay panel principal), igual que en la portada.
- Los paneles de la portada no tienen enlace "Ver…"; todo el panel lleva a su pestaña.

## Decisiones que tomé y conviene revisar

1. **Selector de año del mapa:** quedó junto al mapa, en la vista simple, porque es parte del gráfico. El selector "solo confirmados" del gráfico semanal pasó al detalle.
2. **Umbral de 5 puntos** para decir que el gasto va "menor" o "mayor" que el año transcurrido, y **0,1 puntos** para comparar el IPC con el nacional. Son reglas mías; se cambian en una línea.
3. **Vacunación:** el panel dice "Pedido en trámite a la DIRESA", como pediste.
4. **SISAP:** el panel dice "En preparación" con el enlace al portal.

## Pendiente

- **El IPC no se ha corrido en GitHub Actions.** Si el sitio del INEI rechaza las conexiones desde los servidores de GitHub, el paso fallará sin detener los demás y se conservarán los datos anteriores.
