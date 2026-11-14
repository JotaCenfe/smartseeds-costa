"""
Aptitud física de un terreno para cada cultivo (0 a 100) y sus razones.

Contrato:  aptitud(fila_celda, fila_cultivo) -> 0..100

Cómo se calcula (regla inicial, fácil de explicar y de ajustar):
  - Cada factor (altura, temperatura, lluvia, pendiente, encharcamiento, humedad)
    recibe una nota de 0 a 1: vale 1 dentro del rango que necesita el cultivo y
    baja en línea recta hasta 0 al alejarse (los MARGENES de abajo).
  - Puntaje = 100 x (0,6 x la peor nota + 0,4 x el promedio).
    Así manda el factor limitante: de nada sirve la lluvia perfecta si hace frío.
  - Si falta un dato (por ejemplo, NISAR fuera de las zonas detalladas), ese
    factor no cuenta y se avisa en las razones.
"""
from __future__ import annotations

import math

import pandas as pd

from .config import TABLAS

MARGEN_ALTURA_M = 300      # metros fuera del rango hasta llegar a nota 0
MARGEN_TEMP_C = 3          # grados fuera del rango
MARGEN_LLUVIA = 0.30       # 30 % por debajo del mínimo / por encima del máximo
MARGEN_PENDIENTE = 15      # grados por encima de la pendiente máxima
PESO_PEOR_FACTOR = 0.6
HUMEDAD_CONFIABLE_MIN = 0.5   # mínimo de datos "recomendados" para usar la humedad en el puntaje


def cargar_requisitos(ruta=None) -> pd.DataFrame:
    """Lee tablas/requisitos_cultivos.csv."""
    return pd.read_csv(ruta or TABLAS / "requisitos_cultivos.csv")


def _num(x):
    """Convierte a número; vacío o NaN -> None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _nota_rango(valor, minimo, maximo, margen_bajo, margen_alto):
    """1 dentro de [minimo, maximo]; baja a 0 al alejarse. None si falta el dato."""
    if valor is None or (minimo is None and maximo is None):
        return None
    if minimo is not None and valor < minimo:
        return max(0.0, 1 - (minimo - valor) / margen_bajo)
    if maximo is not None and valor > maximo:
        return max(0.0, 1 - (valor - maximo) / margen_alto)
    return 1.0


def _factor_rango(nombre, unidad, valor, minimo, maximo, margen_bajo, margen_alto,
                  bajo, alto, decimales=0):
    """Evalúa un factor con rango y redacta la razón en lenguaje sencillo."""
    if valor is None:
        return {"factor": nombre, "nota": None, "texto": f"{nombre}: sin dato para este punto"}
    nota = _nota_rango(valor, minimo, maximo, margen_bajo, margen_alto)
    if nota is None:
        return {"factor": nombre, "nota": None,
                "texto": f"{nombre}: falta el requisito del cultivo en la tabla"}
    v = f"{valor:.{decimales}f} {unidad}"
    if minimo is not None and maximo is not None:
        rango = f"{minimo:g}–{maximo:g} {unidad}"
    elif minimo is not None:
        rango = f"mínimo {minimo:g} {unidad}"
    else:
        rango = f"máximo {maximo:g} {unidad}"
    if nota >= 1:
        texto = f"{nombre} {v}: adecuada (necesita {rango})"
    elif minimo is not None and valor < minimo:
        texto = f"{nombre} {v}: {bajo} (necesita {rango})"
    else:
        texto = f"{nombre} {v}: {alto} (necesita {rango})"
    return {"factor": nombre, "nota": nota, "texto": texto}


def aptitud_detalle(celda: dict, cultivo: dict) -> dict:
    """Puntaje y explicación. Devuelve {"puntaje": 0..100 o None, "factores": [...]}."""
    alt_min, alt_max = _num(cultivo.get("altitud_min_m")), _num(cultivo.get("altitud_max_m"))
    t_min, t_max = _num(cultivo.get("temp_min_C")), _num(cultivo.get("temp_max_C"))
    ll_min, ll_max = _num(cultivo.get("lluvia_min_mm_anio")), _num(cultivo.get("lluvia_max_mm_anio"))
    pen_max = _num(cultivo.get("pendiente_max_grados"))
    tolera = str(cultivo.get("tolera_encharcamiento", "")).strip().lower()
    drenaje = str(cultivo.get("necesita_drenaje", "")).strip().lower()

    factores = [
        _factor_rango("Altura", "m", _num(celda.get("altura")), alt_min, alt_max,
                      MARGEN_ALTURA_M, MARGEN_ALTURA_M, "muy baja", "muy alta"),
        _factor_rango("Temperatura", "°C", _num(celda.get("temp")), t_min, t_max,
                      MARGEN_TEMP_C, MARGEN_TEMP_C, "muy frío", "muy caliente", decimales=1),
        _factor_rango("Lluvia", "mm/año", _num(celda.get("lluvia")), ll_min, ll_max,
                      (ll_min or 1) * MARGEN_LLUVIA, (ll_max or 1) * MARGEN_LLUVIA,
                      "llueve poco", "llueve demasiado"),
    ]

    # Pendiente: solo tiene máximo
    pendiente = _num(celda.get("pendiente"))
    if pendiente is None:
        factores.append({"factor": "Pendiente", "nota": None,
                         "texto": "Pendiente: sin dato (solo en zonas detalladas)"})
    elif pen_max is not None:
        nota = _nota_rango(pendiente, None, pen_max, 1, MARGEN_PENDIENTE)
        texto = (f"Pendiente {pendiente:.0f}°: adecuada (máximo {pen_max:g}°)" if nota >= 1 else
                 f"Pendiente {pendiente:.0f}°: terreno muy inclinado (máximo {pen_max:g}°)")
        factores.append({"factor": "Pendiente", "nota": nota, "texto": texto})

    # Encharcamiento (NISAR): fracción de fechas en que el terreno tuvo agua
    ench = _num(celda.get("encharcamiento"))
    if ench is None:
        factores.append({"factor": "Encharcamiento", "nota": None,
                         "texto": "Encharcamiento: sin dato de radar NISAR para este punto"})
    else:
        limite = {"si": None, "parcial": 0.6}.get(tolera, 0.3)   # "no" o vacío -> 0.3
        nota = 1.0 if limite is None else max(0.0, 1 - ench / limite)
        if ench < 0.005:   # menos del 0,5 %: se redondea a "nada" (en un terreno dibujado es un promedio)
            texto = "Encharcamiento: el radar no vio agua acumulada en el terreno"
        elif limite is None:
            texto = f"Encharcamiento: se inunda {ench:.0%} de las fechas, y este cultivo lo tolera"
        else:
            texto = f"Encharcamiento: el radar vio agua {ench:.0%} de las fechas; este cultivo no lo soporta bien"
        factores.append({"factor": "Encharcamiento", "nota": nota, "texto": texto})

    # Humedad del suelo (NISAR): 0 = seco, 1 = saturado
    # `humedad_confiable` = fracción de los datos que la NASA marca como recomendados.
    # En vegetación densa casi ninguno lo es: se muestra el dato pero NO cuenta en el puntaje.
    hum = _num(celda.get("humedad"))
    confiable = _num(celda.get("humedad_confiable"))
    if hum is None:
        factores.append({"factor": "Humedad", "nota": None,
                         "texto": "Humedad del suelo: sin dato de radar NISAR para este punto"})
    elif confiable is not None and confiable < HUMEDAD_CONFIABLE_MIN:
        factores.append({"factor": "Humedad", "nota": None,
                         "texto": f"Humedad del suelo según NISAR: {hum:.0%} de saturación "
                                  "(poco confiable por la vegetación densa; no cuenta en el puntaje)"})
    elif drenaje == "si":
        nota = 1.0 if hum <= 0.7 else max(0.0, 1 - (hum - 0.7) / 0.3)
        texto = ("Humedad del suelo: adecuada para un cultivo que necesita buen drenaje" if nota >= 1
                 else "Humedad del suelo: muy húmedo para un cultivo que necesita buen drenaje")
        factores.append({"factor": "Humedad", "nota": nota, "texto": texto})
    else:
        nota = 1.0 if hum >= 0.5 else max(0.0, hum / 0.5)
        texto = ("Humedad del suelo: el terreno retiene agua, bueno para este cultivo" if nota >= 1
                 else "Humedad del suelo: el terreno se seca rápido para este cultivo")
        factores.append({"factor": "Humedad", "nota": nota, "texto": texto})

    notas = [f["nota"] for f in factores if f["nota"] is not None]
    if not notas:
        return {"puntaje": None, "factores": factores}
    puntaje = 100 * (PESO_PEOR_FACTOR * min(notas) + (1 - PESO_PEOR_FACTOR) * sum(notas) / len(notas))
    return {"puntaje": round(puntaje, 1), "factores": factores}


def aptitud(fila_celda: dict, fila_cultivo: dict) -> float | None:
    """Puntaje de aptitud 0..100 (None si no hay ningún dato para calcularlo)."""
    return aptitud_detalle(fila_celda, fila_cultivo)["puntaje"]
