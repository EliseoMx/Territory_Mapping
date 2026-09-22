# Arquitectura y fuentes de datos

Criterio: **cero costo y sin tarjeta de credito**. Ninguna de las piezas requiere
habilitar facturacion.

## Decision

| Pieza | Fuente elegida | Costo | Requiere clave |
|---|---|---|---|
| Imagen del area | Teselas raster de OpenStreetMap | Gratis | No |
| Imagenes a nivel de calle | Mapillary Graph API | Gratis | Token gratuito (sin tarjeta) |
| Validacion opcional de calles | Overpass API (OSM) | Gratis | No |
| Lenguaje / empaquetado | Python 3 + Pillow + requests -> PyInstaller | Gratis | No |

### Por que NO Google

`Static Street View` y `Maps Static API` exigen habilitar facturacion en el
proyecto de Google Cloud y enviar una API key en cada solicitud, aunque exista
un tramo mensual sin cargo. Eso implica dar de alta una tarjeta, que es justo
lo que queremos evitar.

### Por que OpenStreetMap para el mapa

Las teselas de `tile.openstreetmap.org` son abiertas y no piden clave. A cambio,
la politica de uso de la fundacion pide identificarse y no hacer descargas
masivas, asi que el programa:

- manda un `User-Agent` propio (`Territory_Mapping/<version> (<contacto>)`),
- cachea las teselas en disco (`%LOCALAPPDATA%\Territory_Mapping\tiles`), y
- descarga en serie, no en paralelo.

Un territorio tipico a zoom 16-17 son entre 6 y 20 teselas; con cache, las
corridas siguientes sobre la misma zona no vuelven a pedir nada.

### Por que Mapillary para el nivel de calle

Es imagineria a nivel de calle de origen colaborativo, con API publica y token
gratuito. Se verifico la cobertura sobre la zona del ejemplo (Av. Moctezuma,
Av. El Colli, Av. Nicolas Copernico y las calles interiores del poligono):
hay cobertura densa.

**Limitacion real:** la cobertura es colaborativa, no sistematica. Habra calles
sin fotos, y las que hay pueden tener varios anios. Por eso el programa no falla
cuando un punto no tiene imagen: lo registra y sigue.

Endpoints usados:

- `GET https://graph.mapillary.com/images?fields=id,thumb_1024_url,captured_at,compass_angle,geometry&bbox=<minLon,minLat,maxLon,maxLat>`
- descarga directa del `thumb_1024_url`

El token se lee de la variable de entorno `MAPILLARY_TOKEN` o del parametro
`--token`. Nunca se guarda en el repositorio.

## Flujo del programa

```
JSON de coordenadas
      |
      v
1. Validar poligono (>=3 puntos, rangos, cierre implicito)
      |
      +--> 2. Bounding box + zoom que encuadre el area con margen
      |          |
      |          v
      |    3. Descargar y unir teselas OSM -> lienzo
      |          |
      |          v
      |    4. Dibujar el contorno del poligono -> <nombre>_area.png
      |
      +--> 5. Generar puntos sobre el perimetro cada N metros
                 |
                 v
           6. Buscar imagen en Mapillary cerca de cada punto
                 |
                 v
           7. Descargar -> <nombre>_pXX.jpg
                 |
                 v
           8. index.html con el mapa y la galeria
```

## Atribucion obligatoria

Ambas fuentes piden credito, y el programa lo estampa en la imagen y en el
`index.html`:

- Mapa: `(c) OpenStreetMap contributors` (ODbL)
- Fotos: credito al autor de cada imagen de Mapillary

## Nota de pruebas

El entorno de desarrollo de Claude no tiene salida a `tile.openstreetmap.org`
ni a `graph.mapillary.com` (politica de egreso del sandbox). La logica de
geometria, teselado y CLI se prueba aqui con datos simulados; **las pruebas
contra la red reales se corren en la maquina Windows** con el ejecutable ya
construido.
