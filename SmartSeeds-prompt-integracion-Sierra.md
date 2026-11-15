# Prompt para la sesión que está uniendo SmartSeeds

Copia el texto de abajo en la sesión del programador que está uniendo Costa y Sierra. Mantén abierta esa misma sesión para que conserve el contexto de sus cambios.

---

Estamos integrando SmartSeeds para NASA Space Apps Challenge, equipo Condor Mission. Continúa en la carpeta y rama donde ya estás uniendo Costa y Sierra. Responde en español, con explicaciones sencillas. El objetivo es incorporar el trabajo de Costa y extender la ficha del MAG y la validación de campo a las zonas que ya configuramos para Cotopaxi y Tungurahua.

## Antes de editar

1. Confirma la carpeta, la rama actual, sus remotos y su estado con `git status --short --branch`, `git remote -v` y `git log -5 --oneline`. Si hay cambios de otra persona o un merge en curso, identifícalos y consúltame antes de cambiar la rama o iniciar otra integración.
2. Lee `CLAUDE.md` y la [guía de traspaso](https://github.com/JotaCenfe/smartseeds-costa/blob/traspaso-sierra/SmartSeeds-traspaso-Sierra.md). La [rama traspaso-sierra](https://github.com/JotaCenfe/smartseeds-costa/tree/traspaso-sierra) contiene el código de validación preparado sobre la versión de Costa.
3. Trae la rama de traspaso para inspeccionarla. Este comando actualiza `FETCH_HEAD` sin cambiar la rama actual.

```bash
git fetch https://github.com/JotaCenfe/smartseeds-costa.git refs/heads/traspaso-sierra
git log -4 --oneline FETCH_HEAD
git show --stat FETCH_HEAD
```

## Integración

1. Verifica si la rama unida ya tiene la integración MAG de Costa (`ceea044`) y las notas del piloto (`62b6351`). Si faltan, incorpora primero esa base siguiendo el flujo de unión del equipo. Si llegaron por squash o se copiaron manualmente, comprueba el contenido de los archivos antes de aplicar commits otra vez.
2. Revisa el cambio de validación en `src/validar_campo.py` y `src/identificar_cultivo.py`. Si la base de Costa ya está integrada, toma el commit superior de la rama de traspaso con `git cherry-pick <SHA del traspaso>`. Si esos archivos ya fueron editados en Sierra, resuelve el conflicto conservando lo que requiera la rama unida. Publica únicamente en la rama de integración acordada; deja el merge a la rama principal al equipo.
3. Usa los identificadores y las cuadrículas definitivas de Cotopaxi y Tungurahua de `src/config.py`. Para cada zona ejecuta `python -m src.validar_campo ZONA descargar` y `python -m src.validar_campo ZONA medir`. Revisa los puntos evaluables, las etiquetas no reconocidas y el top 3 por cultivo. Conserva «maíz» genérico como ambiguo. Los puntos SIGTIERRAS de 2014–2015 sirven para contraste histórico.
4. Confirma qué capas vectoriales del MAG están disponibles para esas cuadrículas y comprueba el año, los atributos y los términos de reutilización. El módulo existente consulta seis capas, principalmente de Costa. Con las capas verificadas ejecuta `python -m src.cultivos_mapeados ZONA descargar` y `python -m src.cultivos_mapeados ZONA tabla`. Si añades especies, incorpora sus nombres, colores y años en la app. Un registro de campo o una zonificación de aptitud no proporciona un porcentaje sembrado.
5. Prueba en la app un punto y un polígono de cada zona. Comprueba la ficha y capa «Cultivo mapeado (MAG)», el año, el caso sin datos y que se mantenga el flujo de Daule y Santo Domingo. Ejecuta `python tests/prueba_rapida.py`.

## Resultados y decisiones pendientes

- La propuesta de orden con el MAG se ensayó en Costa y todavía requiere decisión de equipo. Consiste en adelantar un cultivo con al menos 50 % de cobertura histórica si está a 10 puntos o menos de la mejor opción apta. Conserva el puntaje y el mínimo de aptitud. El agricultor confirma el riego. Antes de activarla en la Sierra, compara el orden actual y el propuesto por zona y registra el tamaño de la muestra.
- HLS y VH quedan como pilotos. Para comprobar si ayudan en la Sierra, selecciona escenas por cobertura despejada dentro de cada zona y compara los modelos en las mismas celdas y bloques, con máscara de calidad. Los GeoTIFF experimentales de Costa quedaron fuera de GitHub. Confirma tamaño y fuente antes de iniciar nuevas descargas satelitales.
- Actualiza `CLAUDE.md` con los commits incorporados, las fuentes, los resultados por zona y las pruebas realizadas. Indica qué quedó pendiente, en especial si faltan cartografía vectorial reutilizable, datos de radar o verificación en el navegador.
