# Observatorio FEN Piura: contexto para Claude Code

Este archivo da el contexto del proyecto. Léelo completo antes de empezar.

## Quién y para qué

- Rodrigo Lozano Galecio, asistente de investigación del Prof. Germán Vega (Facultad de Ciencias Económicas y Empresariales, Universidad de Piura).
- La UDEP está formando un comité de comunicación sobre el Fenómeno El Niño (FEN) 2026-2027. A Germán le corresponde la parte económica y social.
- Objetivo: una página web que reúna, en un solo lugar, 10 a 20 indicadores clave para saber "cómo está hoy Piura frente a El Niño", y que se actualice sola. No se generan datos nuevos: solo se recolectan de fuentes públicas.
- Por ahora la página es independiente. Más adelante se integrará a la página oficial de la UDEP sobre El Niño (https://www.udep.edu.pe/fen/, hecha en WordPress con Elementor y administrada por DIRCOM). Por eso todo debe poder incrustarse luego como bloque HTML o iframe.

## Decisiones ya tomadas por Germán

- Alojamiento: GitHub Pages.
- Primer entregable: identificar la información disponible y luego ir viendo cómo se sube a la web. Primero el inventario, después la página.
- Obras y gasto: empezar con prevención y reconstrucción, pero la idea es poder ver todo lo que se gasta en Piura. Avance financiero y físico, todos los niveles de gobierno, con filtros parametrizables.
- Dengue: nivel distrito, a la frecuencia más desagregada disponible (semana epidemiológica). Incluir casos graves, fallecidos, camas disponibles y vacunación.
- Posible más adelante: precios en mercados (SISAP del MIDAGRI).
- Ámbito geográfico: región (departamento) Piura.

## Fuentes identificadas

| Indicador | Fuente | Estado |
| --- | --- | --- |
| Gasto público (PIA, PIM, devengado) por proyecto, nivel de gobierno, programa | MEF, Presupuesto y Ejecución de Gasto: https://www.datosabiertos.gob.pe/dataset/presupuesto-y-ejecuci%C3%B3n-de-gasto | CSV. 2026 diario: https://fs.datosabiertos.mef.gob.pe/datastorefiles/2026-Gasto-Diario.csv ; mensual: .../2026-Gasto-Mensual.csv ; diccionario: .../Gastos_Diccionario.csv. Archivos muy grandes: leer por partes (chunks) y filtrar Piura. Confirmar columnas con el diccionario |
| Gasto en prevención | Mismo CSV, programa presupuestal 0068 (reducción de vulnerabilidad y atención de emergencias por desastres) | Confirmar el nombre exacto de la columna y del código |
| Reconstrucción / ANIN | Mismo CSV, por pliego o ejecutora | Identificar los códigos |
| Avance físico de obras | Infobras (Contraloría): https://apps.contraloria.gob.pe/infobras/ | Verificar si permite descarga masiva |
| Avance físico de inversiones | MEF, Seguimiento de la Ejecución de Inversiones (Formato 12-B), por código único de inversión | Consulta por código; unir con el CSV del MEF |
| Dengue histórico por distrito y semana | CDC-Minsa: https://datosabiertos.gob.pe/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue | Cubre 2000-2024. El portal bloquea descargas que no vienen de un navegador (error 418): puede requerir descarga manual |
| Dengue 2025-2026 | CDC (teleconferencias semanales en PDF, dge.gob.pe) y salas situacionales de la DIRESA Piura (PDF en gob.pe) | Evaluar extracción de tablas desde PDF |
| Camas hospitalarias | SUSALUD, formato F500.2, datos.susalud.gob.pe | Verificar si sigue actualizándose después de marzo de 2021 |
| Vacunación contra el dengue | Minsa (REUNIS) | Fuente por confirmar. Piura es región priorizada (10 a 20 años) |
| Precios en mercados | SISAP MIDAGRI: http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/ | Verificar si incluye Piura y si se puede descargar |

## Tarea 1: verificar fuentes

Antes de construir nada:

1. Descarga el diccionario del CSV de gasto del MEF y confirma qué columnas trae: ubicación (departamento, provincia, distrito), nivel de gobierno, pliego, ejecutora, programa presupuestal, producto o proyecto, código único de inversión, PIA, PIM, devengado, fecha.
2. Prueba la descarga del CSV 2026 (diario o mensual) y mide su tamaño. Filtra Piura leyendo por partes.
3. Revisa si Infobras, SUSALUD (camas) y SISAP permiten descarga automática.
4. Escribe los hallazgos en `docs/inventario.md`: por fuente, qué variables trae, nivel geográfico, frecuencia, formato, URL exacta y si se puede automatizar.

Detente y muéstrame el inventario antes de pasar a la tarea 2.

## Tarea 2: prototipo con gasto público

1. Script en Python (`scripts/gasto_mef.py`) que:
   - descargue el CSV del MEF del año en curso;
   - filtre el departamento de Piura (por ubicación del gasto, según el diccionario);
   - calcule PIM, devengado y porcentaje de avance;
   - permita filtrar por nivel de gobierno, programa presupuestal (incluido el 0068), pliego y proyecto;
   - guarde un resultado liviano en `data/gasto_piura.json` o `.csv` (nunca el CSV completo del MEF en el repositorio).
2. Página estática en `docs/` (o la carpeta que use GitHub Pages) que muestre:
   - avance total de Piura;
   - avance por nivel de gobierno;
   - avance del programa 0068 (prevención);
   - una tabla filtrable por proyecto.
3. GitHub Actions que corra el script una vez al día, actualice los datos y publique la página.

## Reglas de trabajo

- Idioma: español, en la página, en los comentarios del código y en la documentación.
- No inventes datos ni columnas. Si algo no se puede verificar, dilo y déjalo marcado como pendiente.
- Cada número de la página debe indicar su fuente y la fecha de actualización.
- No subas al repositorio archivos grandes ni datos personales.
- Código simple y que corra de principio a fin. Antes de dar algo por terminado, córrelo y revisa el resultado.
- Diseño sobrio y legible en celular; nada que dependa de un servidor (GitHub Pages es solo estático).
- No hagas push ni crees el repositorio público sin preguntarme antes.

## Estructura sugerida del repositorio

```
observatorio-fen-piura/
  CLAUDE.md
  README.md
  docs/            página web (GitHub Pages) e inventario
  scripts/         descarga y procesamiento
  data/            resultados livianos (json o csv)
  .github/workflows/actualizar.yml
```

## Contexto adicional (no es tarea ahora)

- Se pidió al INEI, por transparencia, el Censo 2025 por manzana de toda la región Piura y la cartografía de manzanas. Si llega, servirá para cruzar vulnerabilidad social con zonas bajas o inundables. Esa parte se hará después.
- Mientras tanto se pueden usar los datos del Censo 2017 por manzana, que son públicos.
