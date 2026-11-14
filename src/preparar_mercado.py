"""
Arma tablas/mercado.csv con los datos oficiales de superficie y de precios.

Se ejecuta una sola vez (no necesita internet) después de guardar en datos/crudos/mercado/ estos
dos archivos del Sistema de Información Pública Agropecuaria (SIPA) del MAG:

  superficie-produccion.xlsx        superficie, producción y provincia de 38 cultivos, 2002-2025.
                                    Son los resultados de la ESPAC del INEC.
        https://sipa.agricultura.gob.ec/descargas/base-estadistica/modulo_productivo/superficie-produccion.xlsx
  precios-productor-ponderado.xlsx  precio mensual al productor por provincia, 2016-2026.
        https://sipa.agricultura.gob.ec/descargas/base-estadistica/modulo_economico/precios-productor-ponderado.xlsx

Uso:
    python -m src.preparar_mercado            # escribe tablas/mercado.csv
    python -m src.preparar_mercado ver        # solo muestra el resultado, no escribe nada

Cómo se calcula cada fila (un cultivo en el país o en una provincia):
  var_superficie_pct  cambio de la superficie plantada o sembrada entre 2024 y 2025 (ESPAC).
  var_precio_pct      cambio del precio promedio entre 2024 y 2025. Solo se comparan los meses (y
                      las provincias) que tienen precio en LOS DOS años, para no mezclar épocas.
  rendimiento_t_ha    producción de 2025 entre superficie cosechada de 2025.

Si faltan datos, la fila NO se escribe y la app dice "sin datos" (no se inventa nada):
  - menos de MESES_MINIMOS meses con precio en los dos años;
  - en una provincia, menos de HECTAREAS_MINIMAS hectáreas en alguno de los dos años (la ESPAC
    es una encuesta por muestreo: con pocas hectáreas el dato de una provincia salta demasiado).
Una provincia sin fila propia usa la fila "nacional" (eso lo hace src/mercado.py).
"""
from __future__ import annotations

import sys
import unicodedata

import pandas as pd

from .config import CAPITALES, DATOS_CRUDOS, TABLAS
from .mercado import clasificar

CARPETA = DATOS_CRUDOS / "mercado"
ARCHIVO_SUPERFICIE = "superficie-produccion.xlsx"
ARCHIVO_PRECIOS = "precios-productor-ponderado.xlsx"

ANIO_ANTES, ANIO_AHORA = 2024, 2025
MESES_MINIMOS = 6         # meses con precio en los dos años (valor elegido por el equipo)
HECTAREAS_MINIMAS = 500   # superficie mínima en una provincia (valor elegido por el equipo)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

# cultivo de la app -> (cultivo en la ESPAC, producto en los precios del SIPA, qué se pesa en el
# rendimiento, aclaración para la columna `notas`). Producto None = el SIPA no publica su precio.
CULTIVOS = {
    "cacao": ("Cacao (Almendra Seca)", "Cacao Ccn51 Almendra Seca", "almendra seca", ""),
    "banano": ("Banano (Fruta Fresca)", "Banano Cavendish Spot", "fruta fresca",
               "Precio 'spot' (fuera de contrato)."),
    "platano": ("Plátano (Fruta Fresca)", "Plátano Barraganete", "fruta fresca", ""),
    "palma_aceitera": ("Palma Africana (Fruta Fresca)", "Palma De Aceite", "fruta fresca", ""),
    "cafe_robusta": ("Café (Grano Oro)", "Café Robusta Cereza", "grano oro",
                     "La ESPAC no separa café robusta de arábigo: la superficie y el rendimiento son de todo el café."),
    "maracuya": ("Maracuyá (Fruta Fresca)", "Maracuyá", "fruta fresca", ""),
    "maiz_duro": ("Maíz Duro Seco (Grano Seco)", "Maíz Duro Seco Húmedo y Sucio", "grano seco", ""),
    "arroz": ("Arroz (En Cáscara)", "Arroz Cáscara Grano Largo", "arroz en cáscara", ""),
    "yuca": ("Yuca (Raíz Fresca)", "Yuca", "raíz fresca", ""),
    "pina": ("Piña (Fruta Fresca)", "Piña Md-2", "fruta fresca", ""),
    "papa": ("Papa (Tubérculo Fresco)", "Papa Superchola", "tubérculo fresco", ""),
    "maiz_suave": ("Maíz Suave Seco (Grano Seco)", "Maíz Suave Seco", "grano seco",
                   "Solo maíz suave seco (el choclo va aparte en la ESPAC)."),
    "haba": ("Haba Tierna (En Vaina)", "Haba Tierna En Vaina", "haba tierna en vaina",
             "Solo haba tierna (la seca va aparte en la ESPAC)."),
    "quinua": ("Quinua (Grano Seco)", None, "grano seco", ""),
    "tomate_de_arbol": ("Tomate De Árbol (Fruta Fresca)", "Tomate De Árbol", "fruta fresca", ""),
}

FUENTE = ("INEC, ESPAC 2024 y 2025, superficie y producción por provincia (base histórica publicada por el "
          "MAG-SIPA: sipa.agricultura.gob.ec/descargas/base-estadistica/modulo_productivo/superficie-produccion.xlsx); "
          "MAG-SIPA, precios mensuales al productor por provincia "
          "(sipa.agricultura.gob.ec/descargas/base-estadistica/modulo_economico/precios-productor-ponderado.xlsx)")

COLUMNAS = ["cultivo", "provincia", "var_superficie_pct", "var_precio_pct", "periodo", "fuente", "notas",
            "rendimiento_t_ha", "rendimiento_producto"]


def sin_tildes(texto) -> str:
    """'Los Ríos' -> 'LOS RIOS': para comparar nombres escritos de distinta forma."""
    limpio = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in limpio if unicodedata.category(c) != "Mn").upper().strip()


PROVINCIAS = {sin_tildes(p): p for p in CAPITALES}   # nombre sin tildes -> nombre bien escrito


def _leer_hoja(archivo: str, hoja: str, n_columnas: int) -> pd.DataFrame:
    """Lee una hoja de Excel desde la fila que empieza con 'Año' (lo anterior son títulos)."""
    import openpyxl   # solo hace falta para preparar la tabla, no para la app

    ruta = CARPETA / archivo
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta}. Las direcciones de descarga están al inicio de src/preparar_mercado.py")
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    filas, encabezado = [], None
    for fila in libro[hoja].iter_rows(values_only=True, max_col=n_columnas):
        if encabezado is None:
            if fila[0] == "Año":
                encabezado = [str(c).strip() for c in fila]
            continue
        if fila[0] is not None:
            filas.append(fila)
    libro.close()
    return pd.DataFrame(filas, columns=encabezado)


def leer_superficie() -> pd.DataFrame:
    """Una fila por año, cultivo y provincia: hectáreas plantadas, cosechadas y toneladas."""
    t = _leer_hoja(ARCHIVO_SUPERFICIE, "Superficie y Producción", 7)
    t = t.rename(columns={"Año": "anio", "Cultivo": "cultivo", "Provincia": "provincia",
                          "Superficie Plantada (ha)": "plantada", "Superficie Cosechada (ha)": "cosechada",
                          "Producción (toneladas)": "produccion"})
    for c in ["anio", "plantada", "cosechada", "produccion"]:
        t[c] = pd.to_numeric(t[c], errors="coerce")      # "." y "*" (dato oculto) quedan vacíos
    t["cultivo"] = t["cultivo"].astype(str).str.strip()
    t["prov"] = t["provincia"].map(sin_tildes)
    # se suman las filas "Solo", "Asociado" e "Invernadero": así sale el total que publica el INEC
    return t.groupby(["anio", "cultivo", "prov"], as_index=False)[["plantada", "cosechada", "produccion"]].sum(min_count=1)


def leer_precios() -> pd.DataFrame:
    """Una fila por año, mes, provincia y producto: precio promedio en dólares por kilo."""
    t = _leer_hoja(ARCHIVO_PRECIOS, "Nacional", 9)
    t = t.rename(columns={"Año": "anio", "Precio Promedio (USD/KG)": "usd_kg"})
    t["anio"] = pd.to_numeric(t["anio"], errors="coerce")
    t["usd_kg"] = pd.to_numeric(t["usd_kg"], errors="coerce")
    t["mes"] = t["Mes"].astype(str).str.lower().str.strip().map({m: i + 1 for i, m in enumerate(MESES)})
    t["producto"] = t["Producto"].astype(str).str.lower().str.strip()
    t["prov"] = t["Provincia"].map(sin_tildes)
    t = t.dropna(subset=["anio", "mes", "usd_kg"])
    return t.groupby(["anio", "mes", "prov", "producto"], as_index=False)["usd_kg"].mean()


def variacion_precio(precios: pd.DataFrame, producto: str, prov: str | None = None) -> dict | None:
    """Cambio del precio entre los dos años, usando solo los pares provincia-mes que están en los dos."""
    p = precios[(precios["producto"] == producto.lower()) & precios["anio"].isin([ANIO_ANTES, ANIO_AHORA])]
    if prov is not None:
        p = p[p["prov"] == prov]
    if p.empty:
        return None
    pares = p.pivot_table(index=["prov", "mes"], columns="anio", values="usd_kg").reindex(
        columns=[ANIO_ANTES, ANIO_AHORA]).dropna()
    meses = pares.index.get_level_values("mes").nunique()
    if meses < MESES_MINIMOS:
        return None
    antes, ahora = float(pares[ANIO_ANTES].mean()), float(pares[ANIO_AHORA].mean())
    return {"var": 100 * (ahora / antes - 1), "antes": antes, "ahora": ahora, "meses": meses,
            "provincias": pares.index.get_level_values("prov").nunique()}


def _superficie(sup: pd.DataFrame, cultivo: str, prov: str | None = None) -> dict | None:
    s = sup[sup["cultivo"] == cultivo]
    if prov is not None:
        s = s[s["prov"] == prov]
    por_anio = s.groupby("anio")[["plantada", "cosechada", "produccion"]].sum(min_count=1)
    if ANIO_ANTES not in por_anio.index or ANIO_AHORA not in por_anio.index:
        return None
    antes, ahora = por_anio.loc[ANIO_ANTES], por_anio.loc[ANIO_AHORA]
    if pd.isna(antes["plantada"]) or pd.isna(ahora["plantada"]) or antes["plantada"] <= 0:
        return None
    rendimiento = None
    if pd.notna(ahora["produccion"]) and pd.notna(ahora["cosechada"]) and ahora["cosechada"] > 0:
        rendimiento = float(ahora["produccion"] / ahora["cosechada"])
    return {"var": 100 * (ahora["plantada"] / antes["plantada"] - 1), "antes": float(antes["plantada"]),
            "ahora": float(ahora["plantada"]), "produccion": ahora["produccion"], "cosechada": ahora["cosechada"],
            "rendimiento": rendimiento}


def _miles(numero) -> str:
    return f"{numero:,.0f}".replace(",", ".")


def _por_kilo(precio) -> str:
    return f"{precio:.3f}".replace(".", ",") + " USD por kilo"


def _fila(clave: str, ambito: str, s: dict, p: dict) -> dict:
    _, producto, pesa, aclaracion = CULTIVOS[clave]
    donde = "en el país" if ambito == "nacional" else f"en {ambito}"
    de_donde = (f"promedio de {p['provincias']} provincias" if ambito == "nacional" and p["provincias"] > 1
                else "promedio")
    notas = (f"Superficie plantada o sembrada {donde}: {_miles(s['antes'])} ha ({ANIO_ANTES}) y "
             f"{_miles(s['ahora'])} ha ({ANIO_AHORA}). Precio de {producto.lower()}, {de_donde} de los "
             f"{p['meses']} meses con dato en los dos años: {_por_kilo(p['antes'])} ({ANIO_ANTES}) y "
             f"{_por_kilo(p['ahora'])} ({ANIO_AHORA}).")
    if s["rendimiento"] is not None:
        notas += (f" Rendimiento = producción {ANIO_AHORA} ({_miles(s['produccion'])} t) entre superficie "
                  f"cosechada {ANIO_AHORA} ({_miles(s['cosechada'])} ha).")
    notas += " Variaciones calculadas por el equipo."
    if aclaracion:
        notas += " " + aclaracion
    return {"cultivo": clave, "provincia": ambito, "var_superficie_pct": round(s["var"], 1),
            "var_precio_pct": round(p["var"], 1), "periodo": f"{ANIO_ANTES}-{ANIO_AHORA}", "fuente": FUENTE,
            "notas": notas, "rendimiento_t_ha": None if s["rendimiento"] is None else round(s["rendimiento"], 2),
            "rendimiento_producto": pesa}


def armar_tabla(sup: pd.DataFrame | None = None, precios: pd.DataFrame | None = None) -> pd.DataFrame:
    """Devuelve la tabla de mercado: una fila nacional por cultivo y una por provincia con datos."""
    sup = leer_superficie() if sup is None else sup
    precios = leer_precios() if precios is None else precios
    filas = []
    for clave, (cultivo, producto, _, _) in CULTIVOS.items():
        if producto is None:
            continue
        s, p = _superficie(sup, cultivo), variacion_precio(precios, producto)
        if s is not None and p is not None:
            filas.append(_fila(clave, "nacional", s, p))
        for prov, nombre in PROVINCIAS.items():
            s = _superficie(sup, cultivo, prov)
            if s is None or min(s["antes"], s["ahora"]) < HECTAREAS_MINIMAS:
                continue
            p = variacion_precio(precios, producto, prov)
            if p is not None:
                filas.append(_fila(clave, nombre, s, p))
    return pd.DataFrame(filas, columns=COLUMNAS)


def principal(argumentos: list[str]) -> None:
    tabla = armar_tabla()
    ver = tabla[["cultivo", "provincia", "var_superficie_pct", "var_precio_pct", "rendimiento_t_ha"]].copy()
    ver["resultado"] = [clasificar(a, b) for a, b in zip(tabla["var_superficie_pct"], tabla["var_precio_pct"])]
    print(ver.to_string(index=False))
    sin_fila = [c for c in CULTIVOS if c not in set(tabla["cultivo"])]
    print(f"\n{len(tabla)} filas. Cultivos sin datos suficientes: {', '.join(sin_fila) or 'ninguno'}")
    if argumentos[:1] == ["ver"]:
        print("(solo se mostró: no se escribió nada)")
        return
    tabla.to_csv(TABLAS / "mercado.csv", index=False, encoding="utf-8", lineterminator="\n")
    print("Escrito:", TABLAS / "mercado.csv")


if __name__ == "__main__":
    principal(sys.argv[1:])
