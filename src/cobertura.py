"""
Tipo de terreno según el radar (modelo entrenado con las pasadas de NISAR).

Idea: cada celda se describe por CÓMO se comportó el radar en todas las pasadas
(qué tan brillante se ve, cuánto cambió de una fecha a otra, cuántas veces tuvo agua).
Un modelo de agrupamiento (KMeans) junta las celdas que se comportan parecido, sin
que nadie le diga qué es cada cosa. Después cada grupo recibe un nombre con reglas
físicas del radar:

    construcciones     HH muy alto y mucho mayor que HV, sin cambios (paredes y techos)
    agua               agua en la mayoría de las pasadas (ríos, lagunas)
    inundable          agua en varias pasadas (arrozales, bajos que se encharcan)
    cultivo_activo     la señal cambia mucho entre fechas (siembra, crecimiento, cosecha)
    vegetacion_densa   HV alto y estable (árboles, cultivos permanentes, bosque)
    vegetacion_baja    HV bajo y estable (pasto, rastrojo, suelo con poca vegetación)

    python -m src.cobertura entrenar     # entrena con todas las zonas que tengan serie
                                         # y escribe la columna `cobertura` en cada tabla

Qué es y qué NO es:
  - Es aprendizaje NO supervisado: no hay datos de campo. Los nombres salen de reglas
    y solo se comprobaron contra lugares conocidos (pueblos, ríos, zona arrocera).
  - No distingue el cultivo (papa, maíz, cacao...). Solo el tipo de cobertura.
  - Con celdas de ~250 m detecta las zonas más construidas, no casas sueltas.
  - Entrenar necesita scikit-learn (entorno de desarrollo). La app NO lo necesita:
    solo lee la columna ya calculada.
"""
from __future__ import annotations

import sys
import warnings
from datetime import date

import numpy as np
import pandas as pd

from .clima_relieve import ruta_celdas
from .config import DATOS_PROCESADOS, ZONAS
from .nisar import a_db, ruta_serie

RUTA_MODELO = DATOS_PROCESADOS / "modelo_cobertura.npz"
N_GRUPOS = 8

# clave -> (nombre para mostrar, explicación sencilla, ¿se puede cultivar ahí?)
CLASES = {
    "construcciones": ("Zona construida",
                       "El radar ve paredes y techos: casas, galpones o un pueblo.", False),
    "agua": ("Agua casi permanente",
             "Hubo agua en la mayoría de las pasadas: río, laguna o estero.", False),
    "inundable": ("Terreno que se inunda",
                  "Tuvo agua en varias pasadas: arrozal o bajo que se encharca.", True),
    "cultivo_activo": ("Cultivo de ciclo corto en actividad",
                       "La señal cambió mucho entre junio y octubre: hubo siembra, "
                       "crecimiento o cosecha.", True),
    "vegetacion_densa": ("Árboles o vegetación densa",
                         "Vegetación alta que casi no cambió: árboles, cultivos permanentes "
                         "o bosque.", True),
    "vegetacion_baja": ("Vegetación baja y estable",
                        "Vegetación baja que casi no cambió: pasto, rastrojo o suelo con "
                        "poca vegetación.", True),
}

# Umbrales para nombrar cada grupo (valores iniciales, salidos de mirar los grupos de
# Daule y Santo Domingo el 14 nov; sin calibrar con datos de campo).
AGUA_PERMANENTE = 0.5        # parte de las pasadas con agua
AGUA_INUNDABLE = 0.10
HH_CONSTRUCCION_DB = -3.5    # HH promedio por encima de esto...
HH_MENOS_HV_CONSTRUCCION = 9.0   # ...y HH mucho mayor que HV = rebote en paredes
CAMBIO_HH_DB = 2.0           # variación entre fechas que indica cultivo en actividad
CAMBIO_HV_DB = 1.5
HV_DENSA_DB = -14.5          # HV promedio de vegetación alta

RASGOS = ["hh_media", "hv_media", "hh_cambio", "hv_cambio", "hh_min", "agua", "hh_menos_hv"]


def rasgos_de_serie(hh, hv, agua) -> pd.DataFrame:
    """Rasgos de cada celda a partir de la serie [fecha, fila, columna] (una fila por celda).

    hh_media, hv_media   brillo promedio en dB
    hh_cambio, hv_cambio cuánto varió entre fechas (desviación estándar, en dB)
    hh_min               la fecha más oscura (dB)
    agua                 parte de las pasadas con agua (0 a 1)
    hh_menos_hv          diferencia HH - HV (dB): alta en construcciones
    """
    with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)          # celdas sin ningún dato
        hh_db, hv_db = a_db(hh), a_db(hv)
        hh_db, hv_db = np.where(np.isnan(hh), np.nan, hh_db), np.where(np.isnan(hv), np.nan, hv_db)
        rasgos = {
            "hh_media": np.nanmean(hh_db, axis=0), "hv_media": np.nanmean(hv_db, axis=0),
            "hh_cambio": np.nanstd(hh_db, axis=0), "hv_cambio": np.nanstd(hv_db, axis=0),
            "hh_min": np.nanmin(hh_db, axis=0), "agua": np.nanmean(agua, axis=0),
            "hh_menos_hv": np.nanmean(hh_db - hv_db, axis=0),
        }
    return pd.DataFrame({nombre: valores.ravel() for nombre, valores in rasgos.items()})[RASGOS]


def rasgos_de_zona(clave_zona: str) -> pd.DataFrame:
    with np.load(ruta_serie(clave_zona)) as s:
        return rasgos_de_serie(s["hh"], s["hv"], s["agua"])


def nombrar(centro: dict) -> str:
    """Nombre de un grupo según el valor promedio de sus rasgos (reglas físicas del radar)."""
    if centro["agua"] >= AGUA_PERMANENTE:
        return "agua"
    if centro["agua"] >= AGUA_INUNDABLE:
        return "inundable"
    if centro["hh_media"] >= HH_CONSTRUCCION_DB and centro["hh_menos_hv"] >= HH_MENOS_HV_CONSTRUCCION:
        return "construcciones"
    if centro["hh_cambio"] >= CAMBIO_HH_DB or centro["hv_cambio"] >= CAMBIO_HV_DB:
        return "cultivo_activo"
    if centro["hv_media"] >= HV_DENSA_DB:
        return "vegetacion_densa"
    return "vegetacion_baja"


def clasificar(rasgos: pd.DataFrame, modelo: dict) -> np.ndarray:
    """Clase de cada celda con un modelo ya entrenado (solo numpy: busca el grupo más parecido).

    Devuelve un arreglo de textos; "" donde el radar no tiene datos.
    """
    con_dato = rasgos[RASGOS].notna().all(axis=1).to_numpy()
    x = (rasgos.loc[con_dato, RASGOS].to_numpy() - modelo["media"]) / modelo["escala"]
    distancia = ((x[:, None, :] - modelo["centros"][None, :, :]) ** 2).sum(axis=2)
    clases = np.full(len(rasgos), "", dtype=object)
    clases[con_dato] = np.asarray(modelo["nombres"], dtype=object)[distancia.argmin(axis=1)]
    return clases


def es_cultivable(clases: pd.Series) -> pd.Series:
    """True en las celdas donde se puede cultivar (o donde no se sabe el tipo de terreno)."""
    no_cultivables = [clave for clave, (_, _, cultivable) in CLASES.items() if not cultivable]
    return ~clases.isin(no_cultivables)


def composicion(celdas: pd.DataFrame) -> list[dict] | None:
    """De qué está hecho un terreno según el modelo: lista ordenada de mayor a menor.

    Cada elemento: {"clase", "nombre", "explicacion", "cultivable", "fraccion"}. Si la tabla
    trae la columna `peso`, cada celda cuenta según cuánto la ocupa el terreno.
    Devuelve None si las celdas no tienen tipo de terreno (zona sin modelo o sin radar).
    """
    if "cobertura" not in celdas:
        return None
    pesos = celdas["peso"] if "peso" in celdas else pd.Series(1.0, index=celdas.index)
    con_tipo = celdas["cobertura"].isin(list(CLASES))
    total = pesos[con_tipo].sum()
    if total <= 0:
        return None
    partes = pesos[con_tipo].groupby(celdas.loc[con_tipo, "cobertura"]).sum() / total
    return [{"clase": clase, "nombre": CLASES[clase][0], "explicacion": CLASES[clase][1],
             "cultivable": CLASES[clase][2], "fraccion": float(fraccion)}
            for clase, fraccion in partes.sort_values(ascending=False).items()]


def cargar_modelo() -> dict | None:
    if not RUTA_MODELO.exists():
        return None
    with np.load(RUTA_MODELO) as m:
        return {"media": m["media"], "escala": m["escala"], "centros": m["centros"],
                "nombres": [str(n) for n in m["nombres"]]}


def entrenar(zonas=None, n_grupos: int = N_GRUPOS, semilla: int = 0) -> dict:
    """Entrena el modelo con todas las zonas que tengan serie de radar y lo guarda.

    También escribe la columna `cobertura` en la tabla por celda de cada zona.
    Volver a ejecutarlo cuando haya pasadas nuevas o una zona nueva.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    zonas = [z for z in (zonas or ZONAS) if ruta_serie(z).exists()]
    if not zonas:
        raise RuntimeError("Ninguna zona tiene serie de radar. Ejecuta antes `python -m src.nisar ZONA procesar`.")
    por_zona = {z: rasgos_de_zona(z) for z in zonas}
    todo = pd.concat(por_zona.values(), ignore_index=True)
    con_dato = todo.notna().all(axis=1)
    escalador = StandardScaler().fit(todo[con_dato])
    kmeans = KMeans(n_clusters=n_grupos, n_init=10, random_state=semilla).fit(
        escalador.transform(todo[con_dato]))
    centros_reales = escalador.inverse_transform(kmeans.cluster_centers_)
    nombres = [nombrar(dict(zip(RASGOS, c))) for c in centros_reales]
    modelo = {"media": escalador.mean_, "escala": escalador.scale_,
              "centros": kmeans.cluster_centers_, "nombres": nombres}
    np.savez_compressed(RUTA_MODELO, media=modelo["media"], escala=modelo["escala"],
                        centros=modelo["centros"], nombres=np.array(nombres),
                        rasgos=np.array(RASGOS), zonas=np.array(zonas),
                        fecha=str(date.today()), celdas=int(con_dato.sum()))

    resumen = pd.DataFrame(centros_reales, columns=RASGOS).round(2)
    resumen.insert(0, "clase", nombres)
    resumen["celdas_%"] = (pd.Series(kmeans.labels_).value_counts(normalize=True)
                           .sort_index() * 100).round(1).to_numpy()
    print(f"Modelo entrenado con {int(con_dato.sum())} celdas de: {', '.join(zonas)}")
    print(resumen.to_string(index=False))
    for z in zonas:
        clases = clasificar(por_zona[z], modelo)
        if ruta_celdas(z).exists():
            tabla = pd.read_csv(ruta_celdas(z))
            tabla["cobertura"] = np.where(clases == "", None, clases)
            tabla.to_csv(ruta_celdas(z), index=False)
        reparto = pd.Series(clases[clases != ""]).value_counts(normalize=True).mul(100).round(1)
        print(f"\n{z}:", ", ".join(f"{c} {v} %" for c, v in reparto.items()))
    return modelo


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "entrenar":
        entrenar()
    else:
        print("Uso: python -m src.cobertura entrenar")
