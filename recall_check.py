#!/usr/bin/env python3
"""Prueba de regresión del monitor (regla 4 de CLAUDE.md): ejecútala ANTES y DESPUÉS de tocar términos de búsqueda o criterios.

1. RECALL: cada artículo de key_articles.csv indexado en PubMed debe ser capturado por algún nivel activo por defecto
   (A y B). Los que no están en PubMed (solo DOI) deben pasar el cribado local de Crossref.
2. CRIBADO: ningún artículo clave puede figurar como «descartar» en la caché de veredictos, y los de must_discard.csv
   (ejemplos tuyos) deben estar entre los descartados de algún mes.
Uso:  python validation/recall_check.py        (devuelve código 1 si algo falla)
"""
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import literature_monitor as m  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
DEFAULT_TIERS = [k for k in m.TIERS if k[0] in "AB"]  # niveles activos por defecto (--tiers A,B,S)
SPORT_JOURNALS = ("sports science & coaching", "strength & conditioning")


def main():
    rows = m.load_key_articles(os.path.join(HERE, "key_articles.csv"))
    pm = [r["pmid"] for r in rows if r.get("pmid")]
    fail = []
    if not rows:
        print("AVISO: validation/key_articles.csv está vacío; rellénalo (PMID/DOI reales) para medir el recall.")
    idq = " OR ".join(f"{p}[uid]" for p in pm)
    hits = {p: [] for p in pm}
    for k in (DEFAULT_TIERS if pm else []):
        r = m.eutils("esearch.fcgi", dict(db="pubmed", term=f"({m.TIERS[k]['query']}) AND ({idq})", retmode="json",
                                           retmax=500), post=True).json()["esearchresult"]
        for p in r["idlist"]:
            hits.setdefault(p, []).append(k)
    print(f"RECALL · {len(pm)} claves en PubMed vs niveles {', '.join(DEFAULT_TIERS)}")
    for p in pm:
        flag = "OK " if hits[p] else "FALLA"
        print(f"  {flag} PMID {p}: {','.join(hits[p]) or '— no capturado por ningún nivel'}")
        if not hits[p]:
            fail.append(f"recall PMID {p}")
    for r in [r for r in rows if not r.get("pmid") and r.get("doi")]:
        it = m.crossref_work(r["doi"])
        if not it:
            print(f"  ? DOI {r['doi']}: no encontrado en Crossref")
            fail.append(f"crossref DOI {r['doi']}")
            continue
        a = m.crossref_to_article(it)
        sport = any(s in a["journal"].lower() for s in SPORT_JOURNALS)
        ok = m.crossref_screen(f"{a['title']} {a['abstract']}", sport)
        print(f"  {'OK ' if ok else 'FALLA'} DOI {r['doi']}: cribado Crossref ({'deportiva' if sport else 'multidisciplinar'})")
        if not ok:
            fail.append(f"crossref screen {r['doi']}")

    print("CRIBADO")
    cache_path = os.path.join(OUT, "screening_cache.json")
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    key_ids = {x.lower() for r in rows for x in (r.get("pmid"), r.get("doi")) if x}
    bad = [k for k, v in cache.items() if v["verdict"] == "descartar" and any(i.lower() in key_ids for i in v.get("ids", []))]
    print(f"  {'OK ' if not bad else 'FALLA'} ninguna clave descartada en la caché ({len(cache)} veredictos)")
    fail += [f"clave descartada {b}" for b in bad]
    out_ids = set()
    for f in glob.glob(os.path.join(OUT, "Monitor_*_data.json")):
        for a in json.load(open(f, encoding="utf-8")).get("screened_out", []):
            out_ids |= {x.lower() for x in (a.get("pmid"), a.get("doi")) if x}
    for r in csv.DictReader(open(os.path.join(HERE, "must_discard.csv"), encoding="utf-8")):
        ident = (r["pmid"] or r["doi"]).lower()
        ok = ident in out_ids
        print(f"  {'OK ' if ok else 'FALLA'} descartado: {r['nota']}")
        if not ok:
            fail.append(f"no descartado: {ident}")
    print("\nRESULTADO:", "TODO OK" if not fail else f"{len(fail)} FALLO(S): {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
