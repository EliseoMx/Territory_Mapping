# Territory_Mapping

Convierte una lista de coordenadas en la imagen del area que cubren: toma el
mapa de la zona, pinta el poligono encima y marca cada vertice con un pin.

![Ejemplo de salida](docs/ejemplo.png)

> Territorio de ejemplo en Zapopan, Jalisco, delimitado por Av. Moctezuma,
> Av. Nicolas Copernico, Av. El Colli y C. Paseo de los Volcanes. 15.67 ha.

---

## Que resuelve

Tienes las esquinas de un territorio en un JSON y necesitas la imagen para
imprimir, compartir o archivar. Este ejecutable la genera de un tiron, sin
abrir un navegador ni depender de ninguna cuenta.

- **No necesita API key ni cuenta.** El mapa sale de OpenStreetMap.
- **No necesita internet la segunda vez.** Las teselas quedan en cache local.
- **Un solo archivo.** `Territory_Mapping.exe`, sin instalador.

---

## Arranque rapido

### 1. Instala Python (solo para compilar)

Descarga Python 3 de <https://www.python.org/downloads/> y **marca la casilla
"Add python.exe to PATH"** durante la instalacion. Si no la marcas, `build.bat`
no va a encontrarlo.

### 2. Genera el ejecutable

Doble clic en **`build.bat`**. Crea el entorno virtual, instala Pillow y
PyInstaller, y compila. Tarda uno o dos minutos la primera vez.

El resultado queda en **`dist\Territory_Mapping.exe`**.

### 3. Pruebalo

Doble clic en **`probar.bat`**. Genera el mapa del territorio de ejemplo en
`salida\` y lo abre.

### 4. Usalo con tus coordenadas

```
dist\Territory_Mapping.exe -i mis_coordenadas.json -o salida
```

---

## Como funciona

![Diagrama de flujo](docs/diagrama-flujo.svg)

El programa proyecta las coordenadas a Web Mercator (la misma proyeccion que
usan Google Maps y OpenStreetMap), busca el **zoom mas cercano** en el que el
poligono todavia cabe en el lienzo con el margen pedido, y arma el fondo
pegando las teselas que hacen falta. Despues dibuja encima.

El contorno y los pines se dibujan en un lienzo a 4x y se reducen al final:
Pillow no tiene antialiasing, y ese es el truco para que los bordes no queden
escalonados. Los pines son geometria pura, no una imagen: escalan a cualquier
tamano sin pixelarse y el `.exe` no carga recursos externos.

### Cache de teselas

Las teselas se guardan en `%LOCALAPPDATA%\Territory_Mapping\tiles`. La primera
corrida sobre una zona descarga entre 6 y 30 imagenes; las siguientes sobre la
misma zona no piden nada a la red. Si quieres forzar la redescarga, borra esa
carpeta.

---

## Entrada

El JSON es **solo la lista de ubicaciones**, en el orden en que se recorre el
perimetro:

```json
[
  { "lat": 20.650872, "lng": -103.436386 },
  { "lat": 20.650639, "lng": -103.432531 },
  { "lat": 20.646900, "lng": -103.432741 },
  { "lat": 20.647579, "lng": -103.436573 }
]
```

| Regla | Detalle |
|---|---|
| Minimo | 3 puntos |
| Orden | El del arreglo: define el trazo del perimetro |
| Cierre | Implicito. No repitas el primer punto al final (si lo haces, se ignora) |
| Sentido | Indistinto, horario o antihorario |
| Tolerancias | Acepta `lon` y `long` ademas de `lng`, y pares `[lat, lng]` |

Detalle completo en [`docs/formato-json.md`](docs/formato-json.md).

### De donde sacar las coordenadas

En Google Maps, clic derecho sobre el punto y la primera linea del menu son las
coordenadas: se copian al portapapeles con un clic. Repite en cada esquina del
territorio y pegalas en el JSON.

---

## Parametros

```
Territory_Mapping.exe -i <json> -o <salida> [opciones]
```

| Parametro | Default | Que hace |
|---|---|---|
| `-i`, `--input` | requerido | Ruta del JSON de coordenadas |
| `-o`, `--output` | requerido | Archivo `.png`, o carpeta donde dejarlo |
| `--ancho` / `--alto` | `1280` / `1024` | Tamano de la imagen en pixeles |
| `--margen` | `8` | Porcentaje de aire alrededor del poligono |
| `--color` | `E94235` | Color del contorno, en RRGGBB |
| `--grosor` | `4` | Grosor del contorno en pixeles |
| `--opacidad` | `8` | Opacidad del relleno, 0 a 100. `0` deja solo el contorno |
| `--pin` | `34` | Alto del pin en pixeles |
| `--sin-pines` | apagado | No dibuja los marcadores |
| `--silencioso` | apagado | No imprime el avance |

Si `--output` termina en `.png`, `.jpg` o `.jpeg`, ese es el archivo. Si no, se
trata como carpeta y el archivo se llama `<nombre_del_json>_area.png`.

### Ejemplos

```bat
:: por defecto
Territory_Mapping.exe -i territorio.json -o salida

:: solo contorno, sin sombreado
Territory_Mapping.exe -i territorio.json -o salida --opacidad 0

:: para imprimir, mas grande y con pines mas visibles
Territory_Mapping.exe -i territorio.json -o mapa.png --ancho 2400 --alto 1800 --pin 52

:: en azul, sin marcadores
Territory_Mapping.exe -i territorio.json -o salida --color 1A73E8 --sin-pines
```

---

## Paleta

| Elemento | Color |
|---|---|
| Contorno y cuerpo del pin | `#E94235` |
| Circulo interior del pin | `#B20D0D` |
| Relleno del area | `#E94235` al 8% |

El relleno usa el mismo rojo que el contorno, a muy baja opacidad: el area se
lee como un solo objeto y las calles, los nombres y los parques del mapa siguen
siendo legibles por debajo.

---

## Estructura

```
Territory_Mapping/
├── src/territory_mapping.py    codigo fuente (una sola dependencia: Pillow)
├── samples/                    JSON de ejemplo
├── docs/                       formato, arquitectura, diagrama
├── build.bat                   genera dist\Territory_Mapping.exe
├── probar.bat                  corre el ejemplo y abre el resultado
└── requirements.txt
```

---

## Problemas comunes

| Sintoma | Causa y solucion |
|---|---|
| `build.bat` dice que no encuentra Python | No marcaste "Add python.exe to PATH" al instalar. Reinstala Python marcando la casilla |
| El mapa sale gris sin calles | No hubo conexion al descargar las teselas. Revisa internet y vuelve a correr: lo que ya se bajo queda en cache |
| `ERROR: se necesitan al menos 3 puntos` | El JSON tiene 2 puntos o menos, o no es un arreglo |
| `ERROR: el punto N tiene lat fuera de rango` | Invertiste `lat` y `lng`. En Mexico la latitud ronda 20 y la longitud -103 |
| El poligono sale deformado | Los puntos no estan en orden de recorrido. El orden del arreglo es el del perimetro |

---

## Estado

Funcionando: imagen del area a partir del JSON.

Pendiente del alcance original: la captura a nivel de calle de cada punto. Ver
[`docs/arquitectura.md`](docs/arquitectura.md) para la fuente elegida y por que.

---

## Creditos

Datos y teselas del mapa: **(c) OpenStreetMap contributors**, bajo
[ODbL](https://www.openstreetmap.org/copyright). La atribucion va estampada en
cada imagen que genera el programa.
