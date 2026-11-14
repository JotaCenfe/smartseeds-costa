"""
Une aptitud física + mercado y devuelve la recomendación.

Contrato:  recomendar(celda, provincia) -> lista de cultivos ordenada por puntaje,
           cada uno con puntaje, razones en texto y nivel de mercado.

Empates: muchos cultivos pueden sacar el mismo puntaje (por ejemplo, varios con 100).
Para que el orden no dependa de la posición en la tabla, los empatados se ordenan así:
  1. mejor mercado primero (alta, media, sin datos, saturado);
  2. lo que el agricultor prefiera: "pronto" = primero el que da cosecha más rápido;
     "largo" = primero los cultivos permanentes (producen muchos años).
El puntaje NO cambia con la preferencia: solo decide el orden entre empatados.
"""
from __future__ import annotations

import math

import pandas as pd

from .aptitud import _num, aptitud_detalle, cargar_requisitos
from .config import TABLAS
from .mercado import cargar_mercado, mercado_detalle

PUNTAJE_MINIMO = 40   # por debajo de esto no se recomienda el cultivo

ORDEN_MERCADO = {"alta": 0, "media": 1, "sin_datos": 2, "saturado": 3}
ORDEN_TIPO_LARGO = {"permanente": 0, "semipermanente": 1, "ciclo_corto": 2}
TEXTO_TIPO = {
    "ciclo_corto": "de ciclo corto: se vuelve a sembrar después de cada cosecha",
    "semipermanente": "semipermanente: una siembra produce varios años",
    "permanente": "permanente: produce muchos años, pero suele pedir más inversión "
                  "al inicio y más espera",
}

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


def tiempo_texto(cultivo: dict) -> str | None:
    """Cuánto tarda la primera cosecha y qué tipo de cultivo es, en palabras.

    Sale de las columnas `ciclo_meses` y `tipo` de requisitos_cultivos.csv.
    Devuelve None si la tabla no tiene ninguno de los dos datos.
    """
    meses = _num(cultivo.get("ciclo_meses"))
    tipo = TEXTO_TIPO.get(str(cultivo.get("tipo", "")).strip().lower())
    partes = []
    if meses is not None:
        espera = f"{meses:g} meses" if meses < 24 else f"{meses / 12:g} años"
        partes.append(f"Primera cosecha: unos {espera}")
    if tipo:
        partes.append(f"Cultivo {tipo}")
    return ". ".join(partes) + "." if partes else None


def _clave_preferencia(cultivo: dict, preferencia: str) -> tuple:
    """Orden entre cultivos empatados, según lo que prefiere el agricultor."""
    meses = _num(cultivo.get("ciclo_meses"))
    meses = 9999 if meses is None else meses           # sin dato de tiempo: al final
    if preferencia == "largo":
        tipo = str(cultivo.get("tipo", "")).strip().lower()
        return (ORDEN_TIPO_LARGO.get(tipo, 3), meses)
    return (meses,)


def empatados(todos: list[dict], n: int = 3) -> list[dict]:
    """Cultivos que quedaron fuera de los n primeros pero tienen su mismo puntaje (redondeado)."""
    if len(todos) <= n or todos[n - 1]["puntaje"] < PUNTAJE_MINIMO:
        return []
    corte = round(todos[n - 1]["puntaje"])
    return [c for c in todos[n:] if round(c["puntaje"]) == corte]


def evaluar_todos(celda: dict, provincia: str, requisitos: pd.DataFrame | None = None,
                  tabla_mercado: pd.DataFrame | None = None,
                  tabla_suelo: pd.DataFrame | None = None,
                  preferencia: str = "pronto") -> list[dict]:
    """Evalúa todos los cultivos de la tabla para un terreno. Ordenados de mejor a peor.

    `preferencia` ("pronto" o "largo") solo ordena a los que empatan en puntaje.
    Si el agricultor tiene riego, se indica en la celda: celda["riego"] = True.
    """
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
            "rendimiento_texto": m.get("rendimiento"),       # None si no hay dato de rendimiento
            "mercado_fuente": m.get("fuente"),
            "meses": _num(cultivo.get("ciclo_meses")),       # meses hasta la primera cosecha
            "tiempo_texto": tiempo_texto(cultivo.to_dict()),
            "_desempate": _clave_preferencia(cultivo.to_dict(), preferencia),
            # Suelo que prefiere el cultivo (referencia; None si el catálogo no lo tiene)
            "suelo": suelo_detalle(cultivo["cultivo"], tabla_suelo),
        })
    # Puntaje redondeado (así se muestra); luego mercado; luego la preferencia del agricultor
    return sorted(salida, key=lambda c: (-round(c["puntaje"]), ORDEN_MERCADO.get(c["mercado"], 2),
                                         c["_desempate"]))


def reparto_mejor_cultivo(celdas: pd.DataFrame, requisitos: pd.DataFrame | None = None,
                          max_celdas: int = 300, riego: bool = False,
                          preferencia: str = "pronto") -> list[dict]:
    """En un terreno grande: qué parte del terreno tiene a cada cultivo como mejor opción.

    Evalúa cada celda del terreno por separado (hasta `max_celdas`, repartidas por todo
    el terreno) y cuenta cuál cultivo gana en cada una. Si la tabla trae la columna
    `peso` (parte de la celda que ocupa el terreno), cada celda cuenta según ese peso.
    Devuelve una lista ordenada de
    {"cultivo", "nombre", "fraccion"}; "ninguno" = ningún cultivo llega al puntaje mínimo.
    Los empates se resuelven con la misma preferencia que en la lista principal (aquí
    no se mira el mercado).
    """
    requisitos = cargar_requisitos() if requisitos is None else requisitos
    cultivos = sorted((c.to_dict() for _, c in requisitos.iterrows()),
                      key=lambda c: _clave_preferencia(c, preferencia))
    if len(celdas) > max_celdas:
        celdas = celdas.iloc[:: math.ceil(len(celdas) / max_celdas)]
    cuenta: dict[str, float] = {}
    for fila in celdas.to_dict("records"):
        fila["riego"] = riego
        peso = fila.get("peso", 1.0)
        mejor, mejor_puntaje = "ninguno", None
        for cultivo in cultivos:
            puntaje = aptitud_detalle(fila, cultivo)["puntaje"]
            if puntaje is None or puntaje < PUNTAJE_MINIMO:
                continue
            # en un empate (mismo puntaje redondeado) gana el primero según la preferencia
            if mejor_puntaje is None or round(puntaje) > round(mejor_puntaje):
                mejor, mejor_puntaje = cultivo["cultivo"], puntaje
        cuenta[mejor] = cuenta.get(mejor, 0) + peso
    total = sum(cuenta.values())
    return [{"cultivo": c,
             "nombre": NOMBRES.get(c, c.replace("_", " ").capitalize()),
             "fraccion": n / total}
            for c, n in sorted(cuenta.items(), key=lambda par: -par[1])]


def recomendar(celda: dict, provincia: str, n: int = 3, **kw) -> list[dict]:
    """Los n mejores cultivos para el terreno (solo los que superan el puntaje mínimo)."""
    return [c for c in evaluar_todos(celda, provincia, **kw) if c["puntaje"] >= PUNTAJE_MINIMO][:n]
