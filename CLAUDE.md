# SmartSeeds · contexto para retomar el trabajo

Archivo de traspaso. Resume lo que no se ve leyendo el código: decisiones, hallazgos
y en qué punto quedó cada cosa. Estado al sábado 14 de noviembre de 2026, 11:40.
El detalle de instalación y recursos está en `README.md` y `README_PROGRAMADOR.md`.

## El proyecto

- **NASA Space Apps Challenge 2026**, sede Sangolquí, equipo **Condor Mission**, reto **Dancing with the SARs**.
- **SmartSeeds:** el agricultor toca su terreno en un mapa y recibe los 3 cultivos que más le convienen, con las razones en lenguaje sencillo. Combina aptitud física (radar NISAR, NASADEM, NASA POWER) con un indicador de mercado (ESPAC del INEC, precios del MAG).
- **Entrega:** domingo 15 de noviembre antes de las 23:59 (meta del equipo: 21:00). Página en inglés, video de 30 s o 7 diapositivas, app publicada y repositorio público.
- **Reglas que afectan al código:** declarar el uso de IA, citar todas las referencias (incluido código abierto), usar al menos un dato de la NASA.

## Cómo trabajar con el equipo

- Responder en **español** y con explicaciones sencillas: quien programa no es programador avanzado.
- Comentarios y nombres del código en español.
- No inventar datos. Si una tabla no tiene valores reales, se deja vacía y la app dice "sin datos".
- Decir claramente qué está probado y qué no.

## Reparto del trabajo entre programadores

- **Esta computadora:** zonas de la Costa (Santo Domingo y Daule ya hechas). El trabajo sigue en esta misma máquina, solo cambia la cuenta de Claude: la carpeta, el entorno `condor` y el login de Earthdata ya están listos.
- **El otro programador:** hace lo mismo para la Sierra, provincias de **Cotopaxi y Tungurahua**. Esa es la zona de la Sierra del plan; no hay que procesarla aquí.
- Trabaja sobre **este mismo código** (confirmado el 14 nov).
- **Plan de repositorios acordado:** este repositorio es la base de la **Costa** y está publicado en https://github.com/JotaCenfe/smartseeds-costa (público, rama `main`). El otro programador prepara la parte de la Sierra por su lado. Cuando las dos partes estén listas se crea **un solo repositorio común** con la app completa; ese es el que se entrega.
- Para que la unión sea fácil, la Sierra debería partir de una copia de este repositorio (clonarlo o hacer "fork"), no de cero.
- Para unir sin conflictos: cada zona genera sus propios archivos (`celdas_ZONA.csv`, `nisar_ZONA.npz`, `humedad_ZONA.npz`), así que no chocan. Los archivos que sí comparten los dos son `src/config.py` (lista `ZONAS`) y `tablas/requisitos_cultivos.csv`: hacer `git pull` antes de tocarlos.
- No cambiar el formato de la tabla por celda ni las firmas de `aptitud()` y `mercado()` sin avisarle.

## Cómo ejecutar

En Miniforge Prompt, desde la raíz del repositorio y con el entorno `condor` activado:

```
python tests/prueba_rapida.py                 # lógica, sin internet
streamlit run app/app.py                      # app en http://localhost:8501
python -m src.clima_relieve ZONA              # NASADEM + POWER -> tabla por celda
python -m src.nisar ZONA procesar             # GCOV en remoto -> nisar_ZONA.npz
python -m src.nisar ZONA humedad              # SME2 en remoto -> humedad_ZONA.npz
python -m src.nisar ZONA capas                # llena las columnas NISAR de la tabla
```

Enlace directo a un terreno para demos: `http://localhost:8501/?lat=-0.33&lon=-79.12`.

## Arquitectura

| Archivo | Papel |
|---|---|
| `src/config.py` | Rutas, zonas (`ZONAS`), formato de la tabla por celda, rejilla. **Una zona nueva se agrega aquí.** |
| `src/clima_relieve.py` | NASA POWER (en vivo) y NASADEM → `datos/procesados/celdas_ZONA.csv` |
| `src/nisar.py` | Búsqueda en ASF, lectura remota de GCOV y SME2, capas, llenado de la tabla |
| `src/aptitud.py` | Puntaje 0–100 por cultivo y razones en texto |
| `src/mercado.py` | Regla alta / media / saturado sobre `tablas/mercado.csv` |
| `src/recomendar.py` | Une aptitud y mercado; adjunta el suelo preferido de `tablas/suelo_cultivos.csv` (solo informativo); `reparto_mejor_cultivo()` dice qué cultivo gana en cada parte de un terreno grande |
| `src/terreno.py` | Terreno dibujado: área (ha y cuadras), celdas dentro del contorno y "celda promedio" con el formato acordado. Solo numpy y pandas |
| `app/app.py` | Interfaz Streamlit; solo lee `datos/procesados/` y consulta POWER |

Contratos acordados: tabla por celda `celda, lat, lon, altura, pendiente, temp, lluvia, humedad,
encharcamiento, vegetacion` (más `humedad_confiable`); `aptitud(celda, cultivo) -> 0..100`;
`mercado(cultivo, provincia) -> alta / media / saturado / sin_datos`.

Regla de oro: **todo lo pesado se calcula antes** y la app solo lee archivos pequeños.

## Lo que ya se sabe de NISAR (no volver a descubrirlo)

- Cada archivo GCOV pesa **~7 GB**. No se descargan: se abren en remoto con `earthaccess` + `fsspec` + `h5py` y se lee solo la ventana de la zona (~15 MB, ~20 s por archivo).
- Configuración que funciona: `block_size` de 1 MB con `cache_type="blockcache"`. Con bloques de 4 MB bajaba cientos de MB por archivo.
- **La lectura se cuelga** si un mismo proceso abre más de 2 o 3 archivos seguidos. Por eso `procesar_serie` lanza un proceso aparte por fecha, con límite de tiempo y reintento, y guarda cada fecha en `datos/procesados/_nisar_tmp/`.
- Estructura confirmada: `/science/LSAR/GCOV/grids/frequencyA` (10 m) y `frequencyB` (80 m), bandas `HHHH` y `HVHV` en potencia lineal, proyección UTM. Se usa **frequencyB**: basta para celdas de ~250 m.
- **Hay que aplicar `mask`**: 0 = muestra inválida, 255 = sin dato. Las inválidas traen valores casi cero que parecen agua.
- **SME2** es la humedad de suelo de nivel 3 de NISAR: `/science/LSAR/SME2/grids/soilMoisture`, 200 m, en m³/m³, relleno −9999. El bit 0 de `retrievalQualityFlag` en 0 significa "recomendado".
- En `asf_search`, la propiedad `bytes` de NISAR es un diccionario por archivo, no un número (el ejemplo de `README_PROGRAMADOR.md` sección 5.2 falla por eso).
- No imprimir nunca el contenido de la sesión de `earthaccess`: incluye el token de Earthdata.

## Resultados en Santo Domingo de los Tsáchilas

Recuadro: lon −79.40 a −79.00, lat −0.45 a −0.05. Órbita 76 ascendente, frames 1 y 2.

- 11 fechas GCOV (19 jun – 29 oct 2026) y 10 fechas SME2 procesadas.
- El radar cubre el **76 %** de las celdas; la franja al oeste de −79,35 queda fuera de la órbita.
- HH mediana −6,0 dB, HV −11,4 dB. Índice de vegetación (RVI) entre 0,83 y 0,95: vegetación densa.
- Encharcamiento ≈ 0 % en toda la zona (época seca; a 80 m los ríos angostos no se ven).
- Humedad media 0,26 m³/m³; solo el 6 % de las celdas tiene dato "recomendado". En las demás la app muestra el valor pero no lo usa en el puntaje.
- **Consecuencia:** aquí NISAR todavía no cambia el orden de los cultivos. Cacao, banano y plátano empatan en 100.

## Resultados en Daule – Salitre – Samborondón (segunda zona, hecha el 14 nov)

Clave `daule`. Recuadro: lon −80.05 a −79.65, lat −2.05 a −1.65. Órbita 112 descendente, frames 89 y 90.

- Se eligió midiendo el agua visible (HH < −18 dB) en las tres candidatas. 21 jun: Babahoyo 1,5 %, Daule 1,5 %, Vinces 0,1 %. 31 oct: Daule 4,0 %, Babahoyo 3,0 %. Las otras dos candidatas quedan descartadas (Babahoyo `(-79.75, -2.00, -79.35, -1.60)`, Vinces `(-79.90, -1.80, -79.50, -1.40)`).
- 10 fechas GCOV (21 jun – 31 oct 2026) y 9 fechas SME2 (hasta el 19 oct). Cobertura del radar: **100 %**. Todo el proceso tarda ~15 min.
- HH mediana −8,2 dB, HV −16,8 dB. RVI entre 0,33 y 0,80 (campo abierto).
- Encharcamiento: 7,2 % de las celdas con agua en ≥ 5 % de las pasadas; 3,8 % en ≥ 10 %; 0,3 % en ≥ 30 %. El agua baja de junio a septiembre y sube a fines de octubre.
- Humedad media 0,27 m³/m³; dato "recomendado" en el 49 % de las celdas.
- **Aquí NISAR sí cambia el orden.** Terreno inundado `?lat=-1.9356&lon=-79.6511`: solo arroz (46). Terreno seco `?lat=-1.8156&lon=-79.6733`: maíz duro 100, maracuyá 92, yuca 92.
- POWER da 770 mm/año para toda la zona: el arroz pierde puntos por lluvia aunque ahí se riega. La app no sabe de riego (posible mejora: si el radar ve agua, no castigar la lluvia a los cultivos que toleran inundación; no está hecho ni acordado).
- Al ejecutar Python fuera de Miniforge Prompt, `matplotlib` falla sin mensaje (código 127) si `envs/condor/Library/bin` no está en el PATH.

## Pedidos del programador de la Sierra (14 nov) y qué falta

Analizados contra la app actual. Nada de esto está hecho todavía, salvo lo marcado.

- **Dibujar el terreno en el mapa** (polígono irregular, terrenos grandes): **hecho el 14 nov.** En la app hay dos modos: tocar un punto o dibujar el contorno (`folium.plugins.Draw` + `st_folium`). El terreno dibujado se promedia con `src/terreno.py`; las firmas de `aptitud()` y `mercado()` no cambiaron. Límite: cada celda mide ~250 m (~6 ha).
  - Probado en pantalla: dibujar dentro de Daule (promedió 1.439 celdas) y fuera de las zonas (nivel nacional). La lista "tu terreno no es igual en todas partes" se probó solo por código (353 ha junto a la zona inundada: 57 % maíz duro, 43 % arroz). El botón de corregir el dibujo y el uso en celular no se probaron.
  - Los textos en español de los botones se inyectan con un `MacroElement` agregado al mapa **antes** de `Draw`; `get_root().script.add_child(...)` no funciona con `st_folium`.
  - Streamlit no recarga los módulos de `src/` ya importados: tras cambiarlos hay que **reiniciar** `streamlit run`.
  - Si hay varios dibujos se analiza el último. El modo dibujo no tiene enlace directo (`?lat=&lon=` es solo para el punto).
- **Heladas en la Sierra:** NASA POWER entrega `T2M_MIN` (comprobado: 1,9 °C mínimo en la celda de Latacunga/Ambato, a 2.958 m de altura media; `FROST_DAYS` da 0 ahí). Faltaría ajustarlo por altura por celda y una columna `tolera_heladas` con fuente en `requisitos_cultivos.csv`.
- **Suelo del terreno:** la app no lo mide. Ya se muestra el suelo que prefiere cada cultivo (hecho). Para usarlo en el puntaje falta un mapa de suelo (SoilGrids: pH y textura; no es de la NASA).
- **Qué hay sembrado y sobreproducción:** NISAR a 80 m y sin datos de campo no distingue papa de maíz; no prometerlo. Lo viable: superficie y rendimiento por cultivo y provincia de la ESPAC en `tablas/mercado.csv` (hoy vacía), mostrar quintales por cuadra y el aviso de mercado saturado (la regla ya existe), y usar el radar solo para "hay cultivo / suelo desnudo / inundado".
- **Uso del suelo ("franja agrícola"):** no hay capa de cobertura; la app recomienda aunque el punto sea ciudad, bosque o páramo.

## Pendientes, por prioridad

1. **Segunda zona con inundación real:** hecha (Daule, ver arriba). Queda calibrar el umbral de agua y no hay fechas de época lluviosa (los datos empiezan en junio de 2026).
2. **Requisitos de cultivos:** `tablas/requisitos_cultivos.csv` tiene valores **preliminares** escritos de memoria. Verificar con FAO EcoCrop / INIAP. Los 5 cultivos de Sierra se agregaron solo para probar.
   - El equipo entregó `catalogo_cultivos_v01.json` (14 nov): 15 cultivos con **suelo** (pH, textura, drenaje, materia orgánica, salinidad) de tres fuentes con página, y 5 candidatos sin datos (rosa, clavel, aguacate, mora, uvilla). Se copió tal cual a `tablas/suelo_cultivos.csv` y la app lo muestra en la ficha del cultivo **sin usarlo en el puntaje** (el catálogo pide no tratarlo como umbral, y la app no mide el suelo del terreno).
   - El catálogo **no trae altura, temperatura ni lluvia**. Sin esos rangos no se pueden puntuar los 9 cultivos nuevos (fréjol, arveja, lenteja, chocho, trigo, cebada, amaranto, tomate, soya): pedirlos al equipo, de las mismas fuentes.
   - El "Maíz" del catálogo (libro de cultivos andinos) se asoció a `maiz_suave`; falta confirmarlo con el equipo.
3. **Mercado:** `tablas/mercado.csv` solo tiene encabezados. Falta ESPAC y SIPA.
4. **Subir a GitHub** (repositorio público) y publicar en Streamlit Community Cloud con `requirements.txt`.
5. Mejoras de la app: gráfico de la serie del radar por terreno, capa NISAR sobre el mapa, textos en inglés.
6. Integrar la zona de la Sierra (Cotopaxi y Tungurahua) que prepara el otro programador.

## Limitaciones a declarar en la entrega

- NASA POWER da un valor por celda de ~50 km: la lluvia es la misma en toda una zona.
- La temperatura por celda se ajusta por altura con un gradiente fijo de 6,5 °C por km.
- El umbral de agua (HH < −18 dB) y la escala de humedad (0,5 m³/m³ = saturado) son valores iniciales sin calibrar.
- El análisis de NISAR cubre solo la época seca de 2026.
