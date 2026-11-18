# Literature Monitor · monthly PubMed alerts for your thesis

**Stop re-running the same PubMed searches by hand.** Define your topic once; get a monthly report with only the new
papers, screened, annotated and ready for Zotero. Built by a PhD student for PhD students, with one hard rule:
**no invented citations**. Every author, year, title, journal, DOI and PMID comes from PubMed, Crossref or OpenAlex.

*(Spanish summary at the bottom · Resumen en español al final)*

## What you get every month
- **Word report, CSV (Zotero-ready), JSON and an HTML dashboard** with one page per month (arrows or ← → keys to move between months).
- **Layered Boolean search** in PubMed with AND/OR term blocks and priority tiers, with full pagination and a check that
  retrieved == reported. Exact queries are logged (`query_log`), in the spirit of PRISMA-S.
- **Crossref sweep** for journals PubMed does not index, with a local screen; items without an abstract are listed for
  manual review instead of being dropped silently.
- **Citation chasing** (OpenAlex): new papers that cite your key articles. OpenAlex only discovers; metadata are verified in PubMed/Crossref.
- **Screening** (relevant / doubtful / discard, with a reason) using Claude: by API key or **for free inside a Claude Code
  session** (`criba <month>`). Your key articles and followed authors are never discarded.
- **Per-article one-line conclusions and a monthly summary** that only use what the abstracts say.
- **Journal metrics from your own files**: SJR (Scimago) and JCR quartile/decile. No data, no number: the dashboard shows «—».
- **Open-access links**, study-type labels, no repeats across months, a **regression test** (`recall_check.py`) that
  checks your must-find papers are still captured after you tweak a search, and an optional **local server** that saves to Zotero and keeps reading marks.
- **Hands-off scheduling** on macOS (LaunchAgent) or cron.

## Why it is different from a saved PubMed search
| Saved search / e-mail alert | Literature Monitor |
|---|---|
| One query, everything that matches | Tiers by priority, noise trimming with a "trimmed" list to catch false negatives |
| No way to know what you are missing | Recall test against your key articles, and citation chasing |
| Duplicates across months | Each paper shown once, in the first month it appeared |
| Manual triage | Triage with reasons and one-line conclusions |

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export NCBI_EMAIL="you@example.org"      # optional; NCBI_API_KEY too (free)
python literature_monitor.py 2026-09-01 2026-09-30
```
This is a **template**: the term blocks, tiers and screening prompt carry `EDITAR` ("edit") placeholders and the script
refuses to search until you fill them. Open the folder with [Claude Code](https://claude.com/claude-code), fill `CLAUDE.md`
and follow **[ADAPTAR.md](ADAPTAR.md)** (adaptation guide, in Spanish): it walks through blocks, tiers, key articles, screening and scheduling.

## Rules baked in
1. Zero invented citations. 2. No inferred quartiles. 3. API keys only in environment variables. 4. Do not change search terms without measuring recall before and after.

## Not included
Scimago and Clarivate JCR data are licensed: bring your own (instructions in ADAPTAR.md). No API key is needed to run it.

## Resumen en español
Monitor bibliográfico mensual para tesis: búsquedas por niveles en PubMed, Crossref y citation chasing con OpenAlex,
cribado con razón, resúmenes y exportación a Word, CSV (Zotero) y un HTML acumulado. Plantilla vacía: rellena tus términos
siguiendo `ADAPTAR.md`. Cero citas inventadas y cuartiles solo desde tus propios datos.

## License
MIT. Contributions and issues are welcome.
