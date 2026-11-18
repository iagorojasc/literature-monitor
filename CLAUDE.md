# Monitor bibliográfico: <TU TEMA>

## Contexto (rellena esto primero)
- Persona: <nombre, programa de doctorado, universidad>.
- Tesis: <pregunta de investigación en 3 líneas>.
- Idioma de trabajo: <idioma>. Respuestas directas, sin explicar lo básico.

## Reglas críticas
1. **Cero citas inventadas.** Autor, año, título, revista, DOI y PMID solo desde PubMed, Crossref u OpenAlex. Si no se puede verificar, decirlo.
2. **Cuartiles y métricas:** SJR solo desde el CSV de Scimago aportado; JCR solo desde `--jcr`. Sin dato, «—». Nunca inferir cuartiles.
3. Claves API solo en variables de entorno (`NCBI_API_KEY`, `NCBI_EMAIL`, `ANTHROPIC_API_KEY`); nunca en el código.
4. No cambiar términos de búsqueda sin medirlo: `python validation/recall_check.py` antes y después.

## Estructura
- `literature_monitor.py`: búsqueda PubMed por niveles (`TIERS`), barrido Crossref, dedupe, métricas de revista, salidas .docx/.csv/.json/.html.
- `dashboard_template.html`: plantilla de la web; el script inyecta los datos en `/*__DATA__*/null`.
- `monitor_server.py`: servidor local opcional (Zotero, marcas de lectura).
- `validation/key_articles.csv`: artículos que DEBEN capturarse (PMID/DOI reales).
- `ADAPTAR.md`: guía de adaptación (léela).

## Tarea inicial
Adaptar el monitor a mi tema siguiendo `ADAPTAR.md`: proponer bloques de términos y niveles con justificación (tabla de opciones),
medir recall con mis artículos clave y recortar ruido sin perder recall.

## Estado
<apunta aquí decisiones y fechas conforme avances>
