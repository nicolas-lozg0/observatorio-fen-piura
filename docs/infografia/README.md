# Infografía: precios de la última quincena

`precios_quincena.html` es el gráfico de precios de alimentos que estuvo en la pestaña Precios hasta el 25/11/2026: la
variación del precio por kg entre la 2.ª quincena del mes anterior y el mes en curso, con la raya de lo habitual en esas
mismas fechas. Se separó de la página para usarlo en infografías.

## Cómo abrirla

Desde la carpeta del repositorio, levanta un servidor local y abre la dirección:

```
cd docs
python3 -m http.server 8000
```

http://localhost:8000/infografia/precios_quincena.html

(Si la abres con doble clic, el navegador no deja leer los datos y aparece un aviso.) Publicada en GitHub Pages, la dirección
es la misma con el dominio del sitio. En la pestaña Precios hay un enlace en «Ver detalle».

## Cómo cambiar el periodo

Con los controles de arriba o con parámetros en la dirección (todos opcionales; sin ellos, los valores de la página):

| Parámetro | Qué hace | Por defecto |
| --- | --- | --- |
| `corte=aaaa-mm-dd` | último día que se toma. El periodo reciente va del 1 del mes a ese día (si ese mes tiene menos de 2 fechas con precio, se usa el mes anterior completo); la base es la 2.ª quincena del mes anterior | el último dato |
| `desde=aaaa` y `hasta=aaaa` | años de referencia para «lo habitual» (mediana de esos años, con al menos 3 con dato) | los 4 años anteriores |
| `mercado=mayorista` o `minorista` | mercado | mayorista |
| `comparar=habitual`, un año (`2025`) o vacío | qué marca la raya | habitual |
| `orden=var` o `dif` | orden de las barras | var |

Ejemplo: `precios_quincena.html?corte=2026-11-23&desde=2022&hasta=2025&mercado=minorista`. El enlace «Enlace a esta vista»
copia los parámetros de lo que se está viendo.

## Cómo exportar el PNG

Botón «Descargar PNG»: baja una imagen al doble de resolución (1920 px de ancho), con fondo blanco, título, frase, cifra
promedio, leyenda, gráfico, nota y fuente. El nombre del archivo lleva la fecha del último dato.

## Qué datos usa

Los mismos archivos que la página, que se actualizan con `scripts/precios_sisap.py`:

- `docs/data/sisap_historial.json`: precios diarios por kg de cada producto en los mercados mayorista y minorista de Piura
  (SISAP del Midagri), desde enero de 2022;
- `docs/data/precios_sisap.json`: la lista de productos, sus nombres simples, el nombre original del SISAP y el peso de cada
  uno en el promedio (subclase del IPC de Lima).

El cálculo es una copia en JavaScript de `calcular()` de `scripts/precios_sisap.py`. `scripts/test_pagina.py` comprueba que,
con los valores por defecto, la infografía dé exactamente las cifras de `precios_sisap.json`.
