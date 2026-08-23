#!/usr/bin/env python3
"""Build _site/ontology-census.html — the monthly Shinto ontology census.

Emma 2026-07-16: "Put it into a report that is an actual github page that runs
monthly with cicd on the 1st of the month."

Wired to .github/workflows/ontology-census.yml (1st of the month). Follows the
house `generate_*_page.py` convention: writes into modern-quickstatements/_site/,
which generate-pages.yml copies into the published site.

WHAT IT MEASURES, for instances of kami (Q524158) and Shinto shrine (Q845945):
  - every PROPERTY, with how many items carry it
  - every PROPERTY -> QUALIFIER pair

Pairs, never a flat qualifier list. Emma 2026-07-16: "a qualifier is utterly
contextually useless outside of the property that it qualifies." Proof it
matters: flat, P9675 MediaWiki page ID looks like kami's top qualifier (346
uses); paired, 312 of those sit on P11250 alone and it is plainly import
plumbing, not ontology.

This replaces docs/deity_qualifier_analysis_2026-07.md, which counted qualifiers
on P825 only ("almost useless ... we can just say it didn't happen") and which
nothing regenerated — it was a hand-written snapshot that expired.

Read-only against Wikidata.
"""
import html
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

_here = os.path.dirname(os.path.abspath(__file__))
_root = _here
while _root != os.path.dirname(_root) and not os.path.isdir(os.path.join(_root, "shinto_miraheze")):
    _root = os.path.dirname(_root)
if _root not in sys.path:
    sys.path.insert(0, _root)
# Imported unconditionally on purpose. This used to sit in a try/except whose handler was
#         WIKIDATA_USER_AGENT = <a non-canonical hand-built agent>
# marked `pragma: no cover`. That is a silent fail-OPEN in a system whose whole design is
# fail-closed: any import hiccup would quietly put the wrong domain on Wikidata
# requests, untested and invisible. An unimportable agent must stop the run instead.
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SPARQL = "https://query-main.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
OUT = os.path.join(_here, "_site", "ontology-census.html")

CLASSES = [("Q524158", "Kami"), ("Q845945", "Shinto shrine")]
_LBL = {}


def sparql(q, timeout=300):
    url = SPARQL + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT,
                                               "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status == 429:                 # repo policy: bail, never retry
            raise SystemExit("429 from WDQS — bailing, no retries (CLAUDE.md)")
        return json.loads(r.read().decode("utf-8"))["results"]["bindings"]


def labels(pids):
    """Property labels via the API, batched. The WDQS label service 504s at shrine scale."""
    todo = [p for p in set(pids) if p not in _LBL]
    for i in range(0, len(todo), 50):
        url = API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(todo[i:i + 50]),
            "props": "labels", "languages": "en", "format": "json"})
        req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8"))
        for pid, e in d.get("entities", {}).items():
            _LBL[pid] = e.get("labels", {}).get("en", {}).get("value", "")
        time.sleep(0.3)
    return _LBL


def collect(qid):
    n = int(sparql(f"SELECT (COUNT(DISTINCT ?i) AS ?c) WHERE {{ ?i wdt:P31/wdt:P279* wd:{qid} . }}")[0]["c"]["value"])
    time.sleep(1)
    props = [(r["p"]["value"].split("/")[-1], int(r["c"]["value"])) for r in sparql(f"""
        SELECT ?p (COUNT(DISTINCT ?i) AS ?c) WHERE {{
          ?i wdt:P31/wdt:P279* wd:{qid} . ?i ?prop ?v .
          ?p wikibase:directClaim ?prop .
        }} GROUP BY ?p ORDER BY DESC(?c)""")]
    time.sleep(1)
    pairs = [(r["p"]["value"].split("/")[-1], r["q"]["value"].split("/")[-1], int(r["c"]["value"]))
             for r in sparql(f"""
        SELECT ?p ?q (COUNT(*) AS ?c) WHERE {{
          ?i wdt:P31/wdt:P279* wd:{qid} . ?i ?pp ?st .
          ?p wikibase:claim ?pp . ?st ?pq ?qv . ?q wikibase:qualifier ?pq .
        }} GROUP BY ?p ?q ORDER BY DESC(?c)""")]
    return n, props, pairs


def esc(s):
    return html.escape(s or "")


def main():
    sections = []
    for qid, name in CLASSES:
        print(f"querying {name} ({qid})...")
        n, props, pairs = collect(qid)
        labels([p for p, _ in props] + [p for p, _, _ in pairs] + [q for _, q, _ in pairs])

        rows = "".join(
            f"<tr><td>{esc(_LBL.get(p,''))} <code>{p}</code></td>"
            f"<td class=n>{c:,}</td><td class=n>{c/n*100:.1f}%</td></tr>"
            for p, c in props)

        by_prop = {}
        for p, q, c in pairs:
            by_prop.setdefault(p, []).append((q, c))
        blocks = []
        for p in sorted(by_prop, key=lambda x: -sum(c for _, c in by_prop[x])):
            tot = sum(c for _, c in by_prop[p])
            qr = "".join(
                f"<tr><td class=ind>{esc(_LBL.get(q,''))} <code>{q}</code></td><td class=n>{c:,}</td></tr>"
                for q, c in sorted(by_prop[p], key=lambda t: -t[1]))
            blocks.append(
                f'<h4>{esc(_LBL.get(p,""))} <code>{p}</code> '
                f'<span class=tot>{tot:,} qualified statements</span></h4>'
                f"<table class=q>{qr}</table>")

        sections.append(f"""
      <h2 id="{qid}">{esc(name)} <code>{qid}</code> &mdash; {n:,} items</h2>
      <h3>Properties</h3>
      <table><tr><th>property</th><th class=n>items</th><th class=n>coverage</th></tr>{rows}</table>
      <h3>Qualifiers, by the property they qualify</h3>
      {''.join(blocks)}""")

    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shinto ontology census</title>
<style>
 body{{background:#0f1116;color:#e7e9ee;font-family:system-ui,-apple-system,sans-serif;
      margin:0;padding:32px 22px 90px;line-height:1.5;}}
 .wrap{{max-width:900px;margin:0 auto;}}
 h1{{margin:0 0 4px;font-size:1.5rem;}}
 .sub{{color:#9aa2b4;margin:0 0 26px;}}
 h2{{margin:44px 0 6px;font-size:1.2rem;border-bottom:1px solid #262b36;padding-bottom:6px;}}
 h3{{margin:26px 0 8px;font-size:.95rem;color:#9aa2b4;text-transform:uppercase;letter-spacing:.08em;}}
 h4{{margin:20px 0 4px;font-size:.95rem;font-weight:600;}}
 .tot{{color:#9aa2b4;font-weight:400;font-size:.85rem;}}
 table{{width:100%;border-collapse:collapse;margin:0 0 8px;font-size:.9rem;}}
 th,td{{text-align:left;padding:5px 8px;border-bottom:1px solid #1d212b;}}
 th{{color:#9aa2b4;font-weight:600;}}
 td.n{{text-align:right;font-variant-numeric:tabular-nums;width:90px;}}
 td.ind{{padding-left:26px;}}
 table.q{{margin-bottom:14px;}}
 code{{font-family:ui-monospace,Consolas,monospace;font-size:.82em;color:#7aa2ff;}}
 .note{{background:#171a22;border:1px solid #262b36;border-left:3px solid #7aa2ff;
        border-radius:8px;padding:14px 18px;margin:0 0 26px;color:#c9cede;font-size:.92rem;}}
</style></head><body><div class="wrap">
<h1>Shinto ontology census</h1>
<p class="sub">Every property, and every property&rarr;qualifier pair, on instances of kami and
Shinto shrine. Live from WDQS &middot; rebuilt monthly on the 1st &middot;
generated by <code>generate_ontology_census_page.py</code>, read-only.</p>
<div class="note"><strong>Qualifiers are listed under the property they qualify, never flat.</strong>
A qualifier is contextually meaningless outside its property: flat,
<code>P9675</code> looks like the top qualifier on kami at 346 uses &mdash; paired, 312 of those sit on
<code>P11250</code> alone and it is import plumbing, not ontology.</div>
{''.join(sections)}
</div></body></html>"""

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
