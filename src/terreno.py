"""
Terreno dibujado en el mapa (un contorno irregular en vez de un solo punto).

El agricultor marca las esquinas de su terreno. Con ese contorno se calcula:
  - el área (hectáreas y cuadras),
  - qué celdas de la tabla por celda toca el terreno y CUÁNTO de cada una ocupa
    (columna `peso`, de 0 a 1): una celda que el terreno apenas roza casi no cuenta,
  - una "celda promedio" con el MISMO formato acordado, para que `aptitud()` y
    `recomendar()` funcionen igual que con un punto.

Un contorno es una lista de vértices (lon, lat) en grados, en el orden en que se dibujaron.
No usa librerías extra: solo numpy y pandas (para que la app publicada siga liviana).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .config import PASO_CELDA_SEG

MUESTRAS_POR_LADO = 6        # cada celda se revisa en 6 x 6 puntos para medir cuánto la ocupa el terreno
RADIO_TIERRA_M = 6_371_000
M2_POR_HECTAREA = 10_000
M2_POR_CUADRA = 7_056        # cuadra usada en el Ecuador: 84 m x 84 m (aproximado)

# Columnas que se promedian dentro del terreno (las que existan en la tabla)
COLUMNAS_PROMEDIO = ["altura", "pendiente", "temp", "lluvia", "humedad", "encharcamiento",
                     "vegetacion", "humedad_confiable",
                     # detalle local (src/suelo_lluvia.py y src/vecindad.py); solo si la tabla las trae
                     "ph", "arcilla", "arena", "materia_organica", "lluvia_power", "agua_vecinos",
                     "agua_invierno"]


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
    """Celdas de la tabla que el terreno toca, con la columna `peso`.

    `peso` es la parte de la celda que queda dentro del contorno (1 = toda la celda,
    0,1 = solo una esquina). Se mide revisando una rejilla de puntos dentro de cada
    celda. Así el resultado sigue la forma real del terreno y no un rectángulo.

    Si el terreno es tan pequeño que no alcanza ningún punto de la rejilla, devuelve
    la celda más cercana a su centro, con peso 1.
    """
    paso = PASO_CELDA_SEG / 3600                   # lado de la celda, en grados
    lons, lats = zip(*vertices)
    cerca = tabla[tabla["lon"].between(min(lons) - paso / 2, max(lons) + paso / 2)
                  & tabla["lat"].between(min(lats) - paso / 2, max(lats) + paso / 2)]
    if not cerca.empty:
        # Puntos repartidos dentro de cada celda: desde -paso/2 hasta +paso/2 de su centro
        saltos = ((np.arange(MUESTRAS_POR_LADO) + 0.5) / MUESTRAS_POR_LADO - 0.5) * paso
        dx, dy = np.meshgrid(saltos, saltos)
        px = cerca["lon"].to_numpy()[:, None] + dx.ravel()[None, :]
        py = cerca["lat"].to_numpy()[:, None] + dy.ravel()[None, :]
        ocupado = dentro(px.ravel(), py.ravel(), vertices).reshape(px.shape).mean(axis=1)
        sub = cerca.assign(peso=ocupado)
        sub = sub[sub["peso"] > 0]
        if not sub.empty:
            return sub
    lat, lon = centro(vertices)
    d2 = (tabla["lat"] - lat) ** 2 + (tabla["lon"] - lon) ** 2
    return tabla.loc[[d2.idxmin()]].assign(peso=1.0)


def media_con_peso(valores: pd.Series, pesos: pd.Series) -> float | None:
    """Promedio que da más importancia a las celdas que el terreno ocupa más.

    Las celdas sin dato no entran. Devuelve None si ninguna tiene dato.
    """
    con_dato = valores.notna()
    total = pesos[con_dato].sum()
    if total <= 0:
        return None
    return float((valores[con_dato].astype(float) * pesos[con_dato]).sum() / total)


def celda_promedio(celdas: pd.DataFrame, vertices) -> dict:
    """Una sola "celda" con el promedio del terreno, en el formato acordado.

    Cada celda pesa según cuánto la ocupa el terreno (columna `peso`; si no existe,
    todas pesan igual). Las celdas sin dato (por ejemplo, fuera de la franja del
    radar) no entran en el promedio. Si ninguna tiene dato, el valor queda vacío (None).
    """
    lat, lon = centro(vertices)
    celda = {"celda": None, "lat": lat, "lon": lon}
    pesos = celdas["peso"] if "peso" in celdas else pd.Series(1.0, index=celdas.index)
    for columna in COLUMNAS_PROMEDIO:
        if columna in celdas:
            celda[columna] = media_con_peso(celdas[columna], pesos)
    return celda
