"""
Indicador de mercado: ¿conviene sembrar este cultivo según la oferta y el precio?

Contrato:  mercado(cultivo, provincia) -> "alta" / "media" / "saturado"
           (o "sin_datos" mientras la tabla no tenga ese cultivo)

Lee tablas/mercado.csv. La arma `python -m src.preparar_mercado` con los datos oficiales de la
ESPAC (INEC) y los precios al productor (MAG-SIPA); ahí está explicado cómo se calcula cada fila:

    cultivo, provincia, var_superficie_pct, var_precio_pct, periodo, fuente, notas,
    rendimiento_t_ha, rendimiento_producto

  var_superficie_pct    cambio de la superficie sembrada en el periodo (%, ESPAC)
  var_precio_pct        cambio del precio al productor en el periodo (%, SIPA)
  provincia             nombre de la provincia, o "nacional" como valor general.
                        Si un cultivo no tiene fila de la provincia, se usa la nacional.
  rendimiento_t_ha      (opcional) toneladas por hectárea cosechada
  rendimiento_producto  (opcional) de qué producto son esas toneladas (por ejemplo "grano seco")

Regla inicial (cambiar los umbrales aquí cuando el equipo los acuerde):
  saturado  la superficie creció más de 10 % Y el precio bajó
  alta      el precio subió más de 5 % Y la superficie no creció más de 10 %
  media     todo lo demás
"""
from __future__ import annotations

import unicodedata

import pandas as pd

from .config import TABLAS

UMBRAL_SUPERFICIE_PCT = 10.0
UMBRAL_PRECIO_PCT = 5.0

QUINTALES_POR_TONELADA = 22.046     # quintal de 100 libras
HECTAREAS_POR_CUADRA = 0.7056       # cuadra usada en el Ecuador: 84 m x 84 m (aproximado)

ETIQUETAS = {
    "alta": "Oportunidad alta",
    "media": "Oportunidad media",
    "saturado": "Mercado saturado",
    "sin_datos": "Mercado: sin datos todavía",
}


def _comparable(texto) -> str:
    """'Los Ríos' -> 'los rios': para que una tilde o una mayúscula no impida encontrar la provincia."""
    limpio = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in limpio if unicodedata.category(c) != "Mn").lower().strip()


def cargar_mercado(ruta=None) -> pd.DataFrame:
    ruta = ruta or TABLAS / "mercado.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=["cultivo", "provincia", "var_superficie_pct",
                                     "var_precio_pct", "periodo", "fuente", "notas"])
    return pd.read_csv(ruta)


def clasificar(var_superficie_pct: float, var_precio_pct: float) -> str:
    """Aplica la regla a un par de variaciones (%)."""
    if var_superficie_pct > UMBRAL_SUPERFICIE_PCT and var_precio_pct < 0:
        return "saturado"
    if var_precio_pct > UMBRAL_PRECIO_PCT and var_superficie_pct <= UMBRAL_SUPERFICIE_PCT:
        return "alta"
    return "media"


def mercado_detalle(cultivo: str, provincia: str, tabla: pd.DataFrame | None = None) -> dict:
    """Devuelve {"nivel", "texto"} para un cultivo en una provincia."""
    tabla = cargar_mercado() if tabla is None else tabla
    filas = tabla[tabla["cultivo"].astype(str).str.lower() == str(cultivo).lower()]
    filas = filas.dropna(subset=["var_superficie_pct", "var_precio_pct"])
    de_donde = filas["provincia"].map(_comparable)
    prov = filas[de_donde == _comparable(provincia)]
    if prov.empty:   # si no hay dato de la provincia, se usa el nacional
        prov = filas[de_donde == "nacional"]
    if prov.empty:
        return {"nivel": "sin_datos", "texto": "Todavía no hay datos de mercado para este cultivo.",
                "rendimiento": None, "fuente": None}
    f = prov.iloc[0]
    sup, pre = float(f["var_superficie_pct"]), float(f["var_precio_pct"])
    nivel = clasificar(sup, pre)
    ambito = f["provincia"] if str(f["provincia"]).lower() != "nacional" else "el país"
    texto = (f"En {ambito} la superficie sembrada cambió {sup:+.0f} % y el precio al productor "
             f"{pre:+.0f} % ({f.get('periodo', '')}).")
    if nivel == "saturado":
        texto += " Se sembró más y el precio bajó: hay riesgo de que sobre producto."
    fuente = f.get("fuente")
    return {"nivel": nivel, "texto": texto, "rendimiento": rendimiento_texto(f, ambito),
            "fuente": None if pd.isna(fuente) else str(fuente)}


def rendimiento_texto(fila, ambito: str = "el país") -> str | None:
    """Cuánto rinde el cultivo en promedio, en toneladas por hectárea y quintales por cuadra."""
    rendimiento = pd.to_numeric(fila.get("rendimiento_t_ha"), errors="coerce")
    if pd.isna(rendimiento):
        return None
    por_cuadra = rendimiento * QUINTALES_POR_TONELADA * HECTAREAS_POR_CUADRA
    producto = fila.get("rendimiento_producto")
    de_que = "" if pd.isna(producto) else f" de {producto}"
    return (f"En {ambito} rinde en promedio unas {rendimiento:.1f} toneladas{de_que} por hectárea "
            f"(cerca de {por_cuadra:.0f} quintales por cuadra).")


def mercado(cultivo: str, provincia: str) -> str:
    return mercado_detalle(cultivo, provincia)["nivel"]


# ---------------------------------------------------------------------------
# Lo que se siembra en la provincia (tablas/siembra_provincias.csv, de la ESPAC)
# ---------------------------------------------------------------------------
HECTAREAS_CON_EXPERIENCIA = 500   # desde aquí se considera que el cultivo "se siembra" en la provincia

ETIQUETAS_EVIDENCIA = {
    "fuerte": "Se siembra en tu provincia y rinde bien",
    "presente": "Se siembra en tu provincia, pero rinde menos que en el país",
    "poca": "Casi no se siembra en tu provincia",
    "sin_datos": "Sin datos de siembra en tu provincia",
}


def cargar_siembra(ruta=None) -> pd.DataFrame:
    ruta = ruta or TABLAS / "siembra_provincias.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=["cultivo_espac", "cultivo", "provincia", "anio", "superficie_ha",
                                     "var_superficie_pct", "rendimiento_t_ha", "rendimiento_pais_t_ha",
                                     "rendimiento_producto"])
    return pd.read_csv(ruta)


def _miles(numero) -> str:
    return f"{numero:,.0f}".replace(",", ".")


def evidencia_local(cultivo: str, provincia: str, tabla: pd.DataFrame | None = None) -> dict:
    """¿Se siembra este cultivo en la provincia y cómo le va? Devuelve {"nivel", "texto"}.

    Es lo más cercano que hay a "cómo les ha ido a los vecinos": la ESPAC del INEC no baja de la
    provincia. Niveles: fuerte (se siembra y rinde igual o más que el país), presente (se siembra
    pero rinde menos), poca (menos de HECTAREAS_CON_EXPERIENCIA hectáreas), sin_datos.
    """
    tabla = cargar_siembra() if tabla is None else tabla
    if tabla.empty or not (tabla["cultivo"].astype(str) == str(cultivo)).any():
        return {"nivel": "sin_datos", "texto": "La ESPAC no publica datos de siembra de este cultivo."}
    filas = tabla[(tabla["cultivo"].astype(str) == str(cultivo))
                  & (tabla["provincia"].map(_comparable) == _comparable(provincia))]
    if filas.empty or float(filas.iloc[0]["superficie_ha"]) < HECTAREAS_CON_EXPERIENCIA:
        cuanto = "no registra siembras" if filas.empty else f"registra solo {_miles(filas.iloc[0]['superficie_ha'])} ha"
        return {"nivel": "poca", "texto": f"En {provincia} la ESPAC {cuanto} de este cultivo: "
                                          "hay poca experiencia cerca de ti."}
    f = filas.iloc[0]
    texto = f"En {f['provincia']} hay {_miles(f['superficie_ha'])} ha sembradas ({int(f['anio'])})"
    rinde, pais = pd.to_numeric(f["rendimiento_t_ha"], errors="coerce"), pd.to_numeric(f["rendimiento_pais_t_ha"], errors="coerce")
    if pd.isna(rinde) or pd.isna(pais) or pais <= 0:
        return {"nivel": "presente", "texto": texto + "."}
    diferencia = 100 * (rinde / pais - 1)
    if diferencia >= 0:
        return {"nivel": "fuerte", "texto": f"{texto} y rinde {diferencia:.0f} % más que el promedio del país."}
    return {"nivel": "presente", "texto": f"{texto}, pero rinde {-diferencia:.0f} % menos que el promedio del país."}


def mas_sembrados(provincia: str, n: int = 5, tabla: pd.DataFrame | None = None) -> list[dict]:
    """Los n cultivos con más hectáreas en la provincia, según la ESPAC (lista vacía si no hay datos)."""
    tabla = cargar_siembra() if tabla is None else tabla
    filas = tabla[tabla["provincia"].map(_comparable) == _comparable(provincia)]
    filas = filas.sort_values("superficie_ha", ascending=False).head(n)
    return [{"nombre": f["cultivo_espac"], "cultivo": f["cultivo"] if isinstance(f["cultivo"], str) else "",
             "superficie_ha": float(f["superficie_ha"]), "anio": int(f["anio"])}
            for _, f in filas.iterrows()]
