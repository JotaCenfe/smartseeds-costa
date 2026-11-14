"""
Terreno dibujado en el mapa (un contorno irregular en vez de un solo punto).

El agricultor marca las esquinas de su terreno. Con ese contorno se calcula:
  - el área (hectáreas y cuadras),
  - qué celdas de la tabla por celda caen dentro,
  - una "celda promedio" con el MISMO formato acordado, para que `aptitud()` y
    `recomendar()` funcionen igual que con un punto.

Un contorno es una lista de vértices (lon, lat) en grados, en el orden en que se dibujaron.
No usa librerías extra: solo numpy y pandas (para que la app publicada siga liviana).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

RADIO_TIERRA_M = 6_371_000
M2_POR_HECTAREA = 10_000
M2_POR_CUADRA = 7_056        # cuadra usada en el Ecuador: 84 m x 84 m (aproximado)

# Columnas que se promedian dentro del terreno (las que existan en la tabla)
COLUMNAS_PROMEDIO = ["altura", "pendiente", "temp", "lluvia", "humedad", "encharcamiento",
                     "vegetacion", "humedad_confiable"]


def vertices_de_geojson(dibujo: dict) -> list[tuple[float, float]] | None:
    """Vértices (lon, lat) del contorno exterior de un dibujo del mapa (GeoJSON).

    Sirve para polígonos y rectángulos. Devuelve None si el dibujo no es un área.
    """
    geometria = (dibujo or {}).get("geometry") or {}
    if geometria.get("type") != "Polygon" or not geometria.get("coordinates"):
        return None
    anillo = [(float(p[0]), float(p[1])) for p in geometria["coordinates"][0]]
    if len(anillo) > 1 and anillo[0] == anillo[-1]:
        anillo = anillo[:-1]                      # GeoJSON repite el primer vértice al final
    return anillo if len(anillo) >= 3 else None


def centro(vertices) -> tuple[float, float]:
    """(lat, lon) del centro del terreno: promedio de sus vértices."""
    lons, lats = zip(*vertices)
    return sum(lats) / len(lats), sum(lons) / len(lons)


def area_m2(vertices) -> float:
    """Área del contorno en metros cuadrados.

    Pasa los grados a metros alrededor del centro del terreno (válido para terrenos
    de hasta decenas de kilómetros) y aplica la fórmula del área de un polígono.
    """
    lat0, lon0 = centro(vertices)
    x = [math.radians(lon - lon0) * RADIO_TIERRA_M * math.cos(math.radians(lat0))
         for lon, _ in vertices]
    y = [math.radians(lat - lat0) * RADIO_TIERRA_M for _, lat in vertices]
    n = len(vertices)
    suma = sum(x[i] * y[(i + 1) % n] - x[(i + 1) % n] * y[i] for i in range(n))
    return abs(suma) / 2


def area_texto(vertices) -> str:
    """Área en palabras: metros cuadrados si es pequeña; si no, hectáreas y cuadras."""
    m2 = area_m2(vertices)
    if m2 < 1_000:
        return f"{m2:.0f} m²"
    hectareas, cuadras = m2 / M2_POR_HECTAREA, m2 / M2_POR_CUADRA
    decimales = 1 if hectareas < 100 else 0       # en terrenos grandes sobran los decimales
    return f"{hectareas:.{decimales}f} ha (≈ {cuadras:.{decimales}f} cuadras)"


def dentro(lons, lats, vertices) -> np.ndarray:
    """Para cada punto (lon, lat): True si cae dentro del contorno.

    Método del rayo: se cuenta cuántos lados del contorno cruza una línea horizontal
    que sale del punto; si el número es impar, el punto está dentro.
    """
    lons, lats = np.asarray(lons, dtype="float64"), np.asarray(lats, dtype="float64")
    adentro = np.zeros(lons.shape, dtype=bool)
    n = len(vertices)
    for i in range(n):
        (x1, y1), (x2, y2) = vertices[i], vertices[(i + 1) % n]
        if y1 == y2:
            continue                              # un lado horizontal no cruza el rayo
        cruza = (y1 > lats) != (y2 > lats)
        x_cruce = x1 + (lats - y1) * (x2 - x1) / (y2 - y1)
        adentro ^= cruza & (lons < x_cruce)
    return adentro


def celdas_del_terreno(tabla: pd.DataFrame, vertices) -> pd.DataFrame:
    """Filas de la tabla por celda cuyo centro cae dentro del contorno.

    Si el terreno es más pequeño que una celda (~250 m) y no contiene ningún centro,
    devuelve la celda más cercana al centro del terreno.
    """
    sub = tabla[dentro(tabla["lon"].to_numpy(), tabla["lat"].to_numpy(), vertices)]
    if not sub.empty:
        return sub
    lat, lon = centro(vertices)
    d2 = (tabla["lat"] - lat) ** 2 + (tabla["lon"] - lon) ** 2
    return tabla.loc[[d2.idxmin()]]


def celda_promedio(celdas: pd.DataFrame, vertices) -> dict:
    """Una sola "celda" con el promedio del terreno, en el formato acordado.

    Las celdas sin dato (por ejemplo, fuera de la franja del radar) no entran en el
    promedio. Si ninguna tiene dato, el valor queda vacío (None).
    """
    lat, lon = centro(vertices)
    celda = {"celda": None, "lat": lat, "lon": lon}
    for columna in COLUMNAS_PROMEDIO:
        if columna in celdas:
            valor = celdas[columna].mean()        # .mean() ignora los vacíos
            celda[columna] = None if pd.isna(valor) else float(valor)
    return celda
