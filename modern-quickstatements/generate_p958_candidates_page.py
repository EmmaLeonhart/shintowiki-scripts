"""Candidates report: Kokugakuin pages whose P958 sections look wrong.

REPORT ONLY. Emits no edits and no QuickStatements. The correct section for an entry can
only be read off the Kokugakuin page itself -- that is how Emma established 1 / 0 / n/a for
page 181621 -- so this narrows WHERE to look and never guesses WHAT the value should be.

Why it exists: three real errors turned up on page 181621, the one page Emma happened to
open. Three errors on one page is not evidence the page is unusual, and the queue said so.
Generalised 2026-08-19 across every Kokugakuin id held by more than one item:

    900   ids held by more than one item
    619   fine -- distinct real sections
    197   a holder has NO section while its siblings do   <- 181621's shape
     66   no holder on the page has any section
     18   every holder carries 0 or n/a, so none is distinguished
      0   collisions -- nowhere do two items claim the same (id, real section)

The zero is worth as much as the rest: the failure mode here is UNDER-specification, not
two shrines fighting over one entry.

Identity is (P13677 + P958). Neither section `0` nor `n/a` carries uniqueness -- Emma,
2026-08-19 -- so an item whose only section is one of those is not distinguished from its
siblings by the section at all.

Usage:  python generate_p958_candidates_page.py
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import collections
import csv
import html
import io
import json
import sys
import urllib.parse
import urllib.request

from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SPARQL = "https://query-main.wikidata.org/sparql"
DET = "https://jmapps.ne.jp/kokugakuin/det.html?data_id="
WD = "https://www.wikidata.org/wiki/"
OUT = _uos.path.join(_uar, "_site", "p958-candidates.html")
JSON_OUT = _uos.path.join(_uar, "modern-quickstatements", "p958_candidates_audit.json")

# Section values that establish nothing (Emma, 2026-08-19).
UNSET = {"0", "n/a"}

CLASSES = [
    ("COLLISION", "Two items claim the same (id, section)",
     "The only class that is a genuine conflict. Currently empty -- recorded so that stays visible."),
    ("MISSING-SOME", "A holder has no section while its siblings do",
     "Page 181621's shape, and the largest class. One item on the page never received a section."),
    ("MISSING-ALL", "No holder on the page has any section",
     "Nobody on the page was ever sectioned, so the entries are indistinguishable."),
    ("ALL-UNSET", "Every holder carries 0 or n/a",
     "Sectioned, but with values carrying no uniqueness -- so still not distinguished."),
]


def fetch():
    wd_pace(SPARQL_INTERVAL)
    q = ("SELECT ?item ?ja ?kid ?sec WHERE { ?item p:P13677 ?st . ?st ps:P13677 ?kid . "
         'OPTIONAL { ?st pq:P958 ?sec } OPTIONAL { ?item rdfs:label ?ja FILTER(lang(?ja)="ja") } }')
    req = urllib.request.Request(SPARQL + "?" + urllib.parse.urlencode({"query": q}),
                                 headers={"User-Agent": WIKIDATA_USER_AGENT, "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def classify(holders):
    """-> class name, or None when the page is fine."""
    secs = [s for _, _, s in holders]
    real = [s for s in secs if s and s not in UNSET]
    if any(real.count(s) > 1 for s in set(real)):
        return "COLLISION"
    missing = [h for h in holders if h[2] is None]
    if missing and any(s for _, _, s in holders if s):
        return "MISSING-SOME"
    if missing:
        return "MISSING-ALL"
    if secs and all(s in UNSET for s in secs if s):
        return "ALL-UNSET"
    return None


def esc(s):
    return html.escape(s) if s else "&mdash;"


def build_cards(items):
    cards = []
    for kid, holders in items:
        hrows = []
        for i, j, s in holders:
            cls = "bad" if s is None else ("unset" if s in UNSET else "ok")
            shown = "<em>no section</em>" if s is None else esc(s)
            hrows.append('<tr><td><a href="%s%s" target="_blank">%s</a></td>'
                         '<td lang="ja">%s</td><td class="%s">%s</td></tr>'
                         % (WD, i, i, esc(j), cls, shown))
        cards.append('<div class="card"><h3><a href="%s%s" target="_blank">page %s</a> '
                     '<span class="n">%d holders</span></h3>'
                     '<table><thead><tr><th>item</th><th>ja</th><th>section (P958)</th></tr>'
                     '</thead><tbody>%s</tbody></table></div>'
                     % (DET, kid, esc(kid), len(holders), "".join(hrows)))
    return "".join(cards) or "<p><em>none</em></p>"


def main():
    rows = fetch()
    byid = collections.defaultdict(list)
    for x in rows:
        byid[x["kid"]].append((x["item"].rsplit("/", 1)[-1], x["ja"],
                               (x["sec"] or "").strip() or None))
    multi = {k: v for k, v in byid.items() if len({i for i, _, _ in v}) > 1}

    buckets = collections.defaultdict(list)
    for kid, holders in multi.items():
        c = classify(holders)
        if c:
            buckets[c].append((kid, sorted(holders)))

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump({c: [{"kokugakuin_id": k,
                        "holders": [{"item": i, "ja": j, "section": s} for i, j, s in h]}
                       for k, h in sorted(v)] for c, v in buckets.items()},
                  f, ensure_ascii=False, indent=1)

    parts = []
    for key, title, note in CLASSES:
        items = sorted(buckets.get(key, []),
                       key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0)
        parts.append('<section><h2>%s <span class="count">%d</span></h2>'
                     '<p class="note">%s</p>%s</section>'
                     % (esc(title), len(items), esc(note), build_cards(items)))

    flagged = sum(len(v) for v in buckets.values())
    style = (
        "body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1000px;"
        "margin:0 auto;padding:1.5rem;line-height:1.5;color:#222}"
        "h1{font-size:1.4rem;margin-bottom:.3rem}"
        ".intro{background:#e8f4fd;border-left:4px solid #1976d2;padding:.8rem 1rem;"
        "border-radius:0 4px 4px 0;margin:1rem 0 2rem}"
        "h2{font-size:1.15rem;margin-top:2rem;border-bottom:2px solid #eee;padding-bottom:.3rem}"
        ".count{background:#1976d2;color:#fff;border-radius:10px;padding:.05rem .5rem;font-size:.85rem}"
        ".note{color:#555;font-size:.92rem;margin:.3rem 0 1rem}"
        ".card{border:1px solid #ddd;border-radius:6px;padding:.7rem 1rem;margin:.7rem 0}"
        ".card h3{font-size:1rem;margin:0 0 .4rem}"
        ".n{color:#777;font-weight:400;font-size:.85rem}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{text-align:left;padding:.25rem .5rem;border-bottom:1px solid #f0f0f0;font-size:.92rem}"
        ".bad{color:#d32f2f;font-weight:600}.unset{color:#ef6c00}.ok{color:#2e7d32}")
    intro = (
        "<b>Report only &mdash; no edits, no QuickStatements.</b> The correct section can only be "
        "read off the Kokugakuin page itself, which is how page 181621's values were established. "
        "This narrows <em>where</em> to look; it never guesses <em>what</em> the value should be."
        "<br><br>Identity is <b>(P13677 + section P958)</b>. Neither <code>0</code> nor "
        "<code>n/a</code> carries uniqueness, so a holder whose only section is one of those is not "
        "distinguished from its siblings.<br><br><b>%d</b> Kokugakuin ids are held by more than one "
        "item, and <b>%d</b> of them are fine. <b>Nothing collides</b> &mdash; nowhere do two items "
        "claim the same (id, real section). The failure mode is under-specification, not two shrines "
        "fighting over one entry." % (len(multi), len(multi) - flagged))
    doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>P958 section candidates</title><style>%s</style></head><body>'
           '<h1>Kokugakuin pages whose P958 sections look wrong</h1>'
           '<div class="intro">%s</div>%s</body></html>' % (style, intro, "".join(parts)))

    _uos.makedirs(_uos.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print("%d multi-holder ids; %d candidate page(s) -> %s" % (len(multi), flagged, OUT))
    for key, _, _ in CLASSES:
        print("   %4d  %s" % (len(buckets.get(key, [])), key))


if __name__ == "__main__":
    main()
