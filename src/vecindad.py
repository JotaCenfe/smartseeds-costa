"""
Los terrenos vecinos: qué vio el radar NISAR alrededor de un terreno.

Dos usos:
  1. Antes de la demo, una vez por zona (después de `nisar ZONA capas`):
         python -m src.vecindad daule
     Escribe en la tabla por celda la columna `agua_vecinos`: parte de los cuadros a menos de
     RADIO_VECINOS_M (sin contar el propio) donde el radar vio agua. El puntaje la usa: si los
     vecinos se inundan, el terreno también puede mojarse en invierno aunque el radar, que solo
     tiene pasadas de la época seca, no haya visto agua justo ahí.
  2. La app llama a `resumen_vecinos()` para contar qué hay alrededor del terreno elegido.

Solo usa numpy y pandas.
"""
from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd

from .aptitud import AGUA_VISIBLE
from .clima_relieve import cargar_celdas, ruta_celdas
from .config import ZONAS, forma_rejilla

RADIO_VECINOS_M = 1000
METROS_POR_GRADO = 111_320


def _paso_metros(clave_zona: str) -> tuple[float, float]:
    """Tamaño de una celda en metros: (norte-sur, este-oeste)."""
    lon_min, lat_min, lon_max, lat_max = ZONAS[clave_zona]["recuadro"]
    _, _, paso = forma_rejilla(ZONAS[clave_zona]["recuadro"])
    ns = paso * METROS_POR_GRADO
    return ns, ns * math.cos(math.radians((lat_min + lat_max) / 2))


def agua_en_vecinos(tabla: pd.DataFrame, clave_zona: str, radio_m: float = RADIO_VECINOS_M) -> np.ndarray:
    """Para cada celda: parte de sus vecinas (a menos de `radio_m`) donde el radar vio agua.

    "Vio agua" = encharcamiento de al menos AGUA_VISIBLE (5 % de las pasadas). Las vecinas sin
    dato de radar no cuentan. Si ninguna vecina tiene dato, el resultado queda vacío (NaN).
    """
    filas, columnas, _ = forma_rejilla(ZONAS[clave_zona]["recuadro"])
    orden = tabla["celda"].to_numpy()
    ench = np.full(filas * columnas, np.nan)
    ench[orden] = tabla["encharcamiento"].to_numpy(dtype=float)
    ench = ench.reshape(filas, columnas)
    con_dato = ~np.isnan(ench)
    con_agua = con_dato & (np.nan_to_num(ench) >= AGUA_VISIBLE)

    ns, eo = _paso_metros(clave_zona)
    alcance_f, alcance_c = int(radio_m // ns), int(radio_m // eo)
    suma_agua = np.zeros((filas, columnas))
    suma_dato = np.zeros((filas, columnas))
    for df in range(-alcance_f, alcance_f + 1):
        for dc in range(-alcance_c, alcance_c + 1):
            if (df == 0 and dc == 0) or math.hypot(df * ns, dc * eo) > radio_m:
                continue
            # la vecina (f + df, c + dc) se suma a la celda (f, c)
            destino_f = slice(max(0, -df), filas - max(0, df))
            destino_c = slice(max(0, -dc), columnas - max(0, dc))
            origen_f = slice(max(0, df), filas - max(0, -df))
            origen_c = slice(max(0, dc), columnas - max(0, -dc))
            suma_agua[destino_f, destino_c] += con_agua[origen_f, origen_c]
            suma_dato[destino_f, destino_c] += con_dato[origen_f, origen_c]
    with np.errstate(invalid="ignore", divide="ignore"):
        fraccion = np.where(suma_dato > 0, suma_agua / suma_dato, np.nan)
    return fraccion.reshape(-1)[orden]


def agregar_a_tabla(clave_zona: str) -> pd.DataFrame:
    tabla = cargar_celdas(clave_zona)
    if tabla is None:
        raise SystemExit(f"Falta la tabla de {clave_zona}: ejecuta primero python -m src.clima_relieve {clave_zona}")
    tabla["agua_vecinos"] = np.round(agua_en_vecinos(tabla, clave_zona), 3)
    tabla.to_csv(ruta_celdas(clave_zona), index=False)
    con = tabla["agua_vecinos"]
    print(f"{clave_zona}: celdas con agua en algún vecino: {(con > 0).mean():.1%}; "
          f"con agua en más del 10 % de los vecinos: {(con > 0.10).mean():.1%}; "
          f"en más del 30 %: {(con > 0.30).mean():.1%}")
    return tabla


def _distancia_m(tabla: pd.DataFrame, lat: float, lon: float) -> np.ndarray:
    ns = (tabla["lat"].to_numpy() - lat) * METROS_POR_GRADO
    eo = (tabla["lon"].to_numpy() - lon) * METROS_POR_GRADO * math.cos(math.radians(lat))
    return np.hypot(ns, eo)


def resumen_vecinos(tabla: pd.DataFrame, lat: float, lon: float, celdas_propias=None,
                    radio_m: float = RADIO_VECINOS_M) -> dict | None:
    """Qué hay alrededor de un terreno: los cuadros a menos de `radio_m` de su borde.

    `celdas_propias` son los números de celda del terreno (se excluyen de los vecinos). Para un
    punto, es la celda más cercana. Devuelve None si no hay vecinos.

    Claves: n (cuadros vecinos), radio_m, con_agua (parte con agua vista por el radar, o None),
    tipos (parte de cada tipo de terreno, {} si no hay modelo), altura_vecinos (mediana, m),
    altura_propia (m) y diferencia_altura (propia - vecinos; negativa = el terreno está más bajo).
    """
    distancia = _distancia_m(tabla, lat, lon)
    if celdas_propias is None:
        celdas_propias = [tabla["celda"].to_numpy()[int(np.argmin(distancia))]]
    propias = tabla["celda"].isin(list(celdas_propias)).to_numpy()
    # radio del terreno: distancia de su centro a su celda más lejana
    radio_terreno = float(distancia[propias].max()) if propias.any() else 0.0
    vecinas = tabla[(distancia <= radio_terreno + radio_m) & ~propias]
    if vecinas.empty:
        return None
    con_radar = vecinas["encharcamiento"].dropna()
    tipos = {}
    if "cobertura" in vecinas and vecinas["cobertura"].notna().any():
        tipos = vecinas["cobertura"].dropna().value_counts(normalize=True).to_dict()
    altura_propia = float(tabla.loc[propias, "altura"].mean()) if propias.any() else None
    altura_vecinos = float(vecinas["altura"].median())
    return {
        "n": int(len(vecinas)), "radio_m": radio_m,
        "con_agua": None if con_radar.empty else float((con_radar >= AGUA_VISIBLE).mean()),
        "tipos": tipos,
        "altura_propia": altura_propia, "altura_vecinos": altura_vecinos,
        "diferencia_altura": None if altura_propia is None else altura_propia - altura_vecinos,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ZONAS:
        raise SystemExit(f"Uso: python -m src.vecindad ZONA   (zonas: {', '.join(ZONAS)})")
    agregar_a_tabla(sys.argv[1])
