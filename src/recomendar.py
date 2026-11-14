"""
Une aptitud física + mercado y devuelve la recomendación.

Contrato:  recomendar(celda, provincia) -> lista de cultivos ordenada por puntaje,
           cada uno con puntaje, razones en texto y nivel de mercado.
"""
from __future__ import annotations

import math

import pandas as pd

from .aptitud import aptitud_detalle, cargar_requisitos
from .config import TABLAS
from .mercado import cargar_mercado, mercado_detalle

PUNTAJE_MINIMO = 40   # por debajo de esto no se recomienda el cultivo

# Nombres para mostrar (con tildes). Si un cultivo no está aquí, se usa su clave.
NOMBRES = {"platano": "Plátano", "cafe_robusta": "Café robusta", "maracuya": "Maracuyá",
           "maiz_duro": "Maíz duro", "maiz_suave": "Maíz suave", "pina": "Piña",
           "tomate_de_arbol": "Tomate de árbol"}


COLUMNAS_SUELO = ["cultivo", "nombre_catalogo", "ph_min", "ph_max", "textura", "drenaje",
                  "materia_organica", "salinidad", "fuente", "pagina", "notas"]


def cargar_suelo(ruta=None) -> pd.DataFrame:
    """Lee tablas/suelo_cultivos.csv: el suelo que prefiere cada cultivo según manuales.

    Sale del catálogo del equipo (catalogo_cultivos_v01, 14 nov). Son rangos REPORTADOS
    por cada fuente, no límites absolutos, y la app todavía no mide el suelo del terreno:
    por eso se muestran como referencia y NO entran en el puntaje.
    """
    ruta = ruta or TABLAS / "suelo_cultivos.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS_SUELO)
    return pd.read_csv(ruta)


def suelo_detalle(cultivo: str, tabla_suelo: pd.DataFrame | None = None) -> dict | None:
    """{"texto", "fuente"} con el suelo que prefiere el cultivo, o None si no hay dato."""
    tabla_suelo = cargar_suelo() if tabla_suelo is None else tabla_suelo
    filas = tabla_suelo[tabla_suelo["cultivo"].astype(str).str.lower() == str(cultivo).lower()]
    if filas.empty:
        return None
    f = filas.iloc[0]

    def dato(columna):
        v = f.get(columna)
        return None if pd.isna(v) or str(v).strip() == "" else v

    partes = []
    if dato("ph_min") is not None and dato("ph_max") is not None:
        partes.append(f"pH entre {float(f['ph_min']):g} y {float(f['ph_max']):g}")
    for columna, etiqueta in (("textura", "textura"), ("drenaje", "drenaje"),
                              ("materia_organica", "materia orgánica"),
                              ("salinidad", "salinidad")):
        if dato(columna) is not None:
            v = str(f[columna])
            partes.append(f"{etiqueta}: {v[0].lower()}{v[1:]}")
    if not partes:
        return None
    fuente = str(dato("fuente") or "")
    if dato("pagina") is not None:
        fuente += f" p. {int(float(f['pagina']))}."
    return {"texto": " · ".join(partes), "fuente": fuente}


def evaluar_todos(celda: dict, provincia: str, requisitos: pd.DataFrame | None = None,
                  tabla_mercado: pd.DataFrame | None = None,
                  tabla_suelo: pd.DataFrame | None = None) -> list[dict]:
    """Evalúa todos los cultivos de la tabla para un terreno. Ordenados de mejor a peor."""
    requisitos = cargar_requisitos() if requisitos is None else requisitos
    tabla_mercado = cargar_mercado() if tabla_mercado is None else tabla_mercado
    tabla_suelo = cargar_suelo() if tabla_suelo is None else tabla_suelo
    salida = []
    for _, cultivo in requisitos.iterrows():
        det = aptitud_detalle(celda, cultivo.to_dict())
        if det["puntaje"] is None:
            continue
        m = mercado_detalle(cultivo["cultivo"], provincia, tabla_mercado)
        salida.append({
            "cultivo": cultivo["cultivo"],
            "nombre": NOMBRES.get(cultivo["cultivo"],
                                  str(cultivo["cultivo"]).replace("_", " ").capitalize()),
            "nombre_cientifico": cultivo.get("nombre_cientifico", ""),
            "tipo": cultivo.get("tipo", ""),
            "puntaje": det["puntaje"],
            "factores": det["factores"],
            "mercado": m["nivel"],
            "mercado_texto": m["texto"],
            # Suelo que prefiere el cultivo (referencia; None si el catálogo no lo tiene)
            "suelo": suelo_detalle(cultivo["cultivo"], tabla_suelo),
        })
    return sorted(salida, key=lambda c: -c["puntaje"])


def reparto_mejor_cultivo(celdas: pd.DataFrame, requisitos: pd.DataFrame | None = None,
                          max_celdas: int = 300) -> list[dict]:
    """En un terreno grande: qué parte del terreno tiene a cada cultivo como mejor opción.

    Evalúa cada celda del terreno por separado (hasta `max_celdas`, repartidas por todo
    el terreno) y cuenta cuál cultivo gana en cada una. Devuelve una lista ordenada de
    {"cultivo", "nombre", "fraccion"}; "ninguno" = ningún cultivo llega al puntaje mínimo.
    """
    requisitos = cargar_requisitos() if requisitos is None else requisitos
    cultivos = [c.to_dict() for _, c in requisitos.iterrows()]
    if len(celdas) > max_celdas:
        celdas = celdas.iloc[:: math.ceil(len(celdas) / max_celdas)]
    cuenta: dict[str, int] = {}
    for fila in celdas.to_dict("records"):
        mejor, mejor_puntaje = "ninguno", None
        for cultivo in cultivos:
            puntaje = aptitud_detalle(fila, cultivo)["puntaje"]
            if puntaje is None or puntaje < PUNTAJE_MINIMO:
                continue
            if mejor_puntaje is None or puntaje > mejor_puntaje:  # en un empate gana el primero de la tabla
                mejor, mejor_puntaje = cultivo["cultivo"], puntaje
        cuenta[mejor] = cuenta.get(mejor, 0) + 1
    total = sum(cuenta.values())
    return [{"cultivo": c,
             "nombre": NOMBRES.get(c, c.replace("_", " ").capitalize()),
             "fraccion": n / total}
            for c, n in sorted(cuenta.items(), key=lambda par: -par[1])]


def recomendar(celda: dict, provincia: str, n: int = 3, **kw) -> list[dict]:
    """Los n mejores cultivos para el terreno (solo los que superan el puntaje mínimo)."""
    return [c for c in evaluar_todos(celda, provincia, **kw) if c["puntaje"] >= PUNTAJE_MINIMO][:n]
