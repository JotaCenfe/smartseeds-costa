# SmartSeeds · integración del MAG para Cotopaxi y Tungurahua

La [rama de traspaso](https://github.com/JotaCenfe/smartseeds-costa/tree/traspaso-sierra) contiene los cambios de validación y parte de `smartseeds-costa/main` en `62b6351`. El [prompt para la sesión de integración](https://github.com/JotaCenfe/smartseeds-costa/blob/traspaso-sierra/SmartSeeds-prompt-integracion-Sierra.md) describe cómo traer el commit y comprobar ambas zonas. Utilizar las cuadrículas incorporadas por el programador de la Sierra.

Si trabajan con el parche compartido como archivo, pueden revisarlo con `git apply --check smartseeds-validacion-sierra.patch` y aplicarlo con `git apply smartseeds-validacion-sierra.patch`. Ejecutar ambos comandos desde la raíz del repositorio unido, con el parche en esa carpeta. Usar el parche o el commit de traspaso una sola vez. Si los archivos cambiaron durante la unión, revisar el diff con el programador.

## Qué aporta el parche

- Reconoce los nombres explícitos de papa, maíz suave, haba, quinua y tomate de árbol en los puntos SIGTIERRAS. «Maíz» a secas queda entre las etiquetas por revisar. El informe indica cuántos puntos se recibieron, quedaron fuera, carecen de equivalencia o quedaron sin puntaje. El top 3 cuenta únicamente los cultivos que alcanzan el mínimo de aptitud y representa el escenario sin riego confirmado.
- El experimento de reconocimiento devuelve «datos insuficientes» cuando queda una sola clase o faltan bloques espaciales. Esto evita presentar un acierto artificial de 100 % al predecir solo «otro».

## Procesamiento después de la unión

1. Tomar los identificadores y límites de `src/config.py` y revisar que cada tabla `celdas_ZONA.csv` corresponda a esa cuadrícula.
2. Ejecutar `python -m src.validar_campo ZONA descargar` y `python -m src.validar_campo ZONA medir` con cada zona. Revisar el número de puntos por cultivo, las etiquetas descartadas y el top 3 por separado.
3. Revisar qué polígonos de cultivo cubren cada cuadrícula. `cultivos_mapeados` consulta seis cultivos, principalmente de Costa. Añadir capas andinas cuando se confirme el acceso al archivo vectorial, el año, sus atributos y la licencia. Con las fuentes disponibles ejecutar `python -m src.cultivos_mapeados ZONA descargar` y `python -m src.cultivos_mapeados ZONA tabla`. La ficha y la capa del mapa ya leen un CSV por zona; las nuevas especies requerirán incorporarse a los nombres, colores y años de la app.
4. Comprobar en cada zona un punto y un polígono, con fechas visibles y un caso sin dato del MAG. Si un cultivo mapeado queda fuera del top 3, mostrar su aptitud y el factor limitante. Validar la propuesta de orden con y sin riego antes de incorporarla a la recomendación. Comparar el rendimiento del clasificador con y sin VH en las mismas celdas y bloques. Para HLS, seleccionar escenas según el área despejada dentro de la zona.

El compendio del MAG incluye papa y maíz suave. Aún falta verificar un archivo vectorial de esa cartografía que permita calcular proporciones por parcela. La zonificación de papa en época seca aporta una referencia de aptitud. Los puntos SIGTIERRAS aportan observaciones históricas en ubicaciones concretas. [Compendio MAG 2024–2025](https://sipa.agricultura.gob.ec/index.php/mapa-cobertura-uso-tierra-renagro) · [Zonificación de papa](https://www.datosabiertos.gob.ec/dataset/mapa-de-zonificacion-agroecologica-del-cultivo-de-papa-en-epoca-seca-escala-1-25-000-ano-2025)

## Verificación local

El parche aplica sobre la versión de Costa y sus dos módulos compilan. Las pruebas simuladas de Cotopaxi y Tungurahua comprobaron las equivalencias, el corte de aptitud y los casos sin datos o fuera de la cuadrícula. La prueba con una sola clase devolvió «datos insuficientes». También se verificó el cálculo con puntos SIGTIERRAS reales de Daule y Santo Domingo. Quedan pendientes los datos y la verificación visual de ambas zonas de la Sierra.
