# -*- coding: utf-8 -*-
"""
Salidas para ver el territorio en la web.

- KML: el formato que importa Google My Maps (y Google Earth). Lleva el
  poligono con la paleta del programa y un pin por vertice.
- Liga instantanea: geojson.io con el territorio embebido en la propia URL.
  No necesita cuenta ni servidor; la liga ES el mapa.
"""

import json
from urllib.parse import quote
from xml.sax.saxutils import escape

GEOJSON_IO = "https://geojson.io/#data=data:application/json,"


def _kml_color(rgb_hex, alpha):
    """RRGGBB + alpha 0-255 -> aabbggrr, el orden que usa KML."""
    t = rgb_hex.strip().lstrip("#")
    return ("%02x%s%s%s" % (alpha, t[4:6], t[2:4], t[0:2])).lower()


def descripcion(ha, per):
    return "%.2f ha | perimetro %.0f m" % (ha, per)


def to_kml(points, nombre, ha, per, color="E94235", opacidad=8.0):
    """Documento KML con el poligono y un pin por vertice."""
    fill_alpha = max(0, min(255, int(round(255 * opacidad / 100.0))))
    anillo = " ".join("%.7f,%.7f,0" % (lo, la) for la, lo in points + [points[0]])
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "<Document>",
        "  <name>%s</name>" % escape(nombre),
        "  <description>%s</description>" % escape(descripcion(ha, per)),
        '  <Style id="area">',
        "    <LineStyle><color>%s</color><width>4</width></LineStyle>" % _kml_color(color, 255),
        "    <PolyStyle><color>%s</color><fill>%d</fill><outline>1</outline></PolyStyle>"
        % (_kml_color(color, fill_alpha), 1 if fill_alpha else 0),
        "  </Style>",
        '  <Style id="pin">',
        "    <IconStyle><color>%s</color><scale>1.0</scale>" % _kml_color(color, 255),
        "      <Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon>",
        "    </IconStyle>",
        "  </Style>",
        "  <Placemark>",
        "    <name>%s</name>" % escape(nombre),
        "    <description>%s</description>" % escape(descripcion(ha, per)),
        "    <styleUrl>#area</styleUrl>",
        "    <Polygon><outerBoundaryIs><LinearRing><coordinates>%s</coordinates>"
        "</LinearRing></outerBoundaryIs></Polygon>" % anillo,
        "  </Placemark>",
    ]
    for i, (la, lo) in enumerate(points, 1):
        out += [
            "  <Placemark>",
            "    <name>Punto %d</name>" % i,
            "    <description>%.6f, %.6f</description>" % (la, lo),
            "    <styleUrl>#pin</styleUrl>",
            "    <Point><coordinates>%.7f,%.7f,0</coordinates></Point>" % (lo, la),
            "  </Placemark>",
        ]
    out += ["</Document>", "</kml>", ""]
    return "\n".join(out)


def instant_link(points, nombre, ha, per, color="E94235", opacidad=8.0):
    """Liga de geojson.io con el territorio dentro de la URL."""
    c = "#" + color.strip().lstrip("#").upper()
    feats = [{
        "type": "Feature",
        "properties": {
            "name": nombre, "info": descripcion(ha, per),
            "stroke": c, "stroke-width": 4,
            "fill": c, "fill-opacity": round(opacidad / 100.0, 3),
        },
        "geometry": {"type": "Polygon", "coordinates": [
            [[round(lo, 7), round(la, 7)] for la, lo in points + [points[0]]]]},
    }]
    for i, (la, lo) in enumerate(points, 1):
        feats.append({
            "type": "Feature",
            "properties": {"name": "Punto %d" % i, "marker-color": c},
            "geometry": {"type": "Point", "coordinates": [round(lo, 7), round(la, 7)]},
        })
    gj = {"type": "FeatureCollection", "features": feats}
    texto = json.dumps(gj, separators=(",", ":"), ensure_ascii=False)
    # geojson.io parte la liga en cada '#' y '&' (separan sus parametros),
    # aun codificados. Como escapes de JSON significan lo mismo y no rompen
    # la liga.
    texto = texto.replace("#", "\\u0023").replace("&", "\\u0026")
    return GEOJSON_IO + quote(texto, safe="")
