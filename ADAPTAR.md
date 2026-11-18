# Cómo adaptarlo a tu tema

Abre esta carpeta con Claude Code (`claude`), rellena `CLAUDE.md` y pídele que siga esta guía. Orden recomendado.

## 0. Antes de nada
1. `pip install -r requirements.txt` (mejor en un entorno virtual).
2. Opcional: `NCBI_EMAIL` y `NCBI_API_KEY` como variables de entorno. Ninguna clave va en el código.
3. Mientras queden marcadores `EDITAR` en los bloques de términos, `literature_monitor.py` se niega a buscar y te dice cuáles faltan.

## 1. Qué hay que rellenar (todo en `literature_monitor.py` salvo indicación)
| Qué | Dónde | Notas |
|---|---|---|
| Bloques de términos | sección 1: `TEMA_CORE`, `TEMA_AMBIG`, `CONTEXTO`, `CONCEPTO_B`, `CONCEPTO_C` | Cada lista es un bloque OR en título/abstract. `TEMA_CORE`: términos específicos de tu tema. `TEMA_AMBIG`: términos con otros sentidos, que exigen `CONTEXTO`. `CONCEPTO_B/C`: los dos conceptos del núcleo de tu tesis. Añade los bloques que necesites. |
| Niveles de búsqueda | diccionario `TIERS` | Cada nivel combina bloques con `allof(anyof(...), ...)`. `priority` menor = más relevante. Los de prefijo B son el núcleo de la tesis; los A, el tema general. |
| Etiquetas de prioridad | `PRIORITY_LABELS` | Lo que ve el lector. |
| Autores seguidos | nivel `S1` (comentado) en `TIERS` | Nombre completo `"Apellido, Nombre"[FAU]`; sus artículos nunca se descartan. |
| Revistas «core» | `CORE_JOURNALS` | Solo marca visual (★), no filtra. |
| Revistas sin PubMed | `CROSSREF_ONLY` | Barrido por ISSN; verifica los ISSN contra Crossref antes de añadir. |
| Criterio de cribado | `SCREEN_SYSTEM` | Describe tu tema y qué es relevante, dudoso y descartable. Sube `SCREEN_VERSION` al cambiarlo para invalidar la caché. |
| Marca ⚑ «cercano a tu tesis» | `THESIS_RULES` y la lista `topics` de `summaries/article_notes.json` | Reglas sobre etiquetas de tema. |
| Texto de la web y del Word | `dashboard_template.html` (`EDITAR: tu tema`) y `doc.add_heading` en el script | Título y etiquetas. |
| Artículos clave | `validation/key_articles.csv` | PMID o DOI **reales**. Son la prueba de recall, la semilla del chasing y nunca se descartan. |
| Ejemplos de ruido | `validation/must_discard.csv` | Artículos que el cribado debe descartar. |

## 2. Reglas que conviene conservar
1. Cero citas inventadas: autor, año, título, revista, DOI y PMID solo desde PubMed, Crossref u OpenAlex.
2. Cuartiles solo desde datos que tú aportes (Scimago público; JCR con acceso de tu universidad). Sin dato, «—». La citación a 2 años de OpenAlex no es el JIF.
3. No cambies términos sin medirlo: `python validation/recall_check.py` antes y después.
4. Toda cifra de un resumen mensual debe aparecer en el abstract del artículo.

## 3. Primera vuelta
1. Rellena `validation/key_articles.csv` con 10–30 artículos que DEBEN aparecer.
2. Rellena bloques y `TIERS`; ejecuta un mes de prueba (`--screen none --no-chasing`); mira cuántas claves se capturan por nivel.
3. Ajusta hasta que el recall de claves sea alto; después recorta ruido revisando muestras por nivel y registra el recorte en `LEGACY_QUERIES`.
4. Reescribe `SCREEN_SYSTEM` y criba.

## 4. Cribado, sin pagar API
- Con `ANTHROPIC_API_KEY` (o llavero de macOS, servicio `literature-monitor-anthropic`) el script criba solo (`--screen api`, coste por token).
- Sin clave: `--screen cache`. En Claude Code, en esta carpeta, pide «criba <mes>»: lee el `_data.json`, escribe veredictos en `out/screening_cache.json` (`by`: `claude-session`), anotaciones en `summaries/article_notes.json` y el resumen en `summaries/monthly_summaries.json`; luego regenera el mes.

## 5. Datos de revistas (opcionales, con licencia: no se incluyen)
- Scimago: scimagojr.com > Journal Rankings > Download data → `data/scimago/scimagojr_AAAA.csv` y `--scimago <ruta>`.
- JCR: exportaciones por categoría desde tu acceso institucional (tope de 600 filas por export; activa JIF Rank y JIF Percentile) → `data/jcr/*.csv` y `--jcr data/jcr`.
- No redistribuyas esos ficheros ni los subas a un repositorio público (`data/` ya está en `.gitignore`).

## 6. Automatización mensual (solo macOS)
`--auto` genera el mes anterior si falta su `_data.json`. Se programa con un LaunchAgent diario a las 09:00 con `RunAtLoad`:
- Proyecto **fuera de Escritorio, Documentos e iCloud** y sin espacios en la ruta (si no, launchd falla con EX_CONFIG).
- `ProgramArguments`: ruta absoluta de `python3` (`which python3`) + ruta absoluta de `literature_monitor.py` + `--auto`.
- `WorkingDirectory`, `StandardOutPath`, `StandardErrorPath`: rutas absolutas dentro del proyecto (`out/monthly_run.log`).
- Cargar: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<plist>`; comprobar: `launchctl print gui/$(id -u)/<label>`.
En Linux, un cron diario con el mismo comando.

## 7. Servidor local opcional (`monitor_server.py`)
Sirve el dashboard en `127.0.0.1:47651` y guarda en Zotero (conector local, puerto 23119, colección «Monitor», ajustable con `MONITOR_ZOTERO_COLLECTION`) y las marcas de lectura. Sin él, la web funciona igual y descarga `.ris`.
