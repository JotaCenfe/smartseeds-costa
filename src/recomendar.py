"""
Une aptitud física + mercado y devuelve la recomendación.

Contrato:  recomendar(celda, provincia) -> lista de cultivos ordenada por puntaje,
           cada uno con puntaje, razones en texto y nivel de mercado.
"""
from __future__ import annotations

import pandas as pd

from .aptitud import aptitud_detalle, cargar_requisitos
from .mercado import cargar_mercado, mercado_detalle

PUNTAJE_MINIMO = 40   # por debajo de esto no se recomienda el cultivo

# Nombres para mostrar (con tildes). Si un cultivo no está aquí, se usa su clave.
NOMBRES = {"platano": "Plátano", "cafe_robusta": "Café robusta", "maracuya": "Maracuyá",
           "maiz_duro": "Maíz duro", "maiz_suave": "Maíz suave", "pina": "Piña",
           "tomate_de_arbol": "Tomate de árbol"}


def evaluar_todos(celda: dict, provincia: str, requisitos: pd.DataFrame | None = None,
                  tabla_mercado: pd.DataFrame | None = None) -> list[dict]:
    """Evalúa todos los cultivos de la tabla para un terreno. Ordenados de mejor a peor."""
    requisitos = cargar_requisitos() if requisitos is None else requisitos
    tabla_mercado = cargar_mercado() if tabla_mercado is None else tabla_mercado
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
        })
    return sorted(salida, key=lambda c: -c["puntaje"])


def recomendar(celda: dict, provincia: str, n: int = 3, **kw) -> list[dict]:
    """Los n mejores cultivos para el terreno (solo los que superan el puntaje mínimo)."""
    return [c for c in evaluar_todos(celda, provincia, **kw) if c["puntaje"] >= PUNTAJE_MINIMO][:n]
