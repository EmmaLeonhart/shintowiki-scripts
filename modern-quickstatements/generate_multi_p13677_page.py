#!/usr/bin/env python3
"""Browsable table of the multiple-P13677 review set — for Emma's per-item eyes.

Emma's standing verdict (docs/kokugakuin_anomaly_review_scope_2026-07.md): the ~47
items carrying 2+ Kokugakuin entry ids are ALL ambiguous; deciding which entry backs
each parent-link needs the Kokugakuin page per item, no batch fix, heuristics
prohibited. So this does the LEGWORK and presents it — it emits no Wikidata edits.

For each (item, parent) row from `p958_manual_review.txt` it shows the parent's own
Kokugakuin entry and the item's competing entries (id → entry name, read from each
Kokugakuin page title), flagging the item-id whose entry NAME matches the parent's
entry (a strong hint, not an auto-decision). Where none matches cleanly, that is
exactly the case Emma flagged as needing eyes.

Writes `_site/kokugakuin-multi-p13677.html`. Report only.

    python generate_multi_p13677_page.py
"""
import datetime
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
REVIEW = os.path.join(HERE, "p958_manual_review.txt")
OUT = os.path.join(REPO_ROOT, "_site", "kokugakuin-multi-p13677.html")

WD_API = "https://www.wikidata.org/w/api.php"
UAW = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
UAK = "Mozilla/5.0 (compatible; EmmaBot/1.0; +https://shinto.miraheze.org/wiki/User:EmmaBot)"
DET = "https://jmapps.ne.jp/kokugakuin/det.html?data_id="
WD = "https://www.wikidata.org/wiki/"

# The parent label can itself contain parentheses ("Watatsumi Shrine (Engishiki)"),
# so match greedily up to the last ")" before the ranking field.
_ROW = re.compile(r"^(Q\d+)\t([^\t]*)\tparent=(Q\d+) \((.*)\)\tranking=([^\t]*)")
_TITLE = re.compile(r"<title>\s*［ID:\d+］\s*([^：<]+?)\s*[：<]")


def parse_rows():
    rows = []
    with io.open(REVIEW, encoding="utf-8") as fh:
        section = False
        for line in fh:
            if "MULTIPLE P13677" in line:
                section = True
                continue
            if not section:
                continue
            m = _ROW.match(line)
            if m:
                rows.append({"item": m.group(1), "item_label": m.group(2).strip(),
                             "parent": m.group(3), "parent_label": m.group(4).strip(),
                             "ranking": m.group(5).strip()})
    return rows


def wd_p13677(qids):
    """{qid: [entry ids]} for P13677, batched."""
    out = {}
    qids = sorted(set(qids))
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        url = WD_API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(chunk),
            "props": "claims", "format": "json"})
        data = json.load(urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UAW}), timeout=60))
        for q, e in data.get("entities", {}).items():
            ids = []
            for st in e.get("claims", {}).get("P13677", []):
                v = st["mainsnak"].get("datavalue", {}).get("value")
                if v:
                    ids.append(v)
            out[q] = ids
        time.sleep(0.3)
    return out


def entry_name(eid, cache):
    if eid in cache:
        return cache[eid]
    try:
        h = urllib.request.urlopen(urllib.request.Request(
            DET + eid, headers={"User-Agent": UAK}), timeout=30).read().decode("utf-8", "replace")
        m = _TITLE.search(h)
        cache[eid] = html.unescape(m.group(1).strip()) if m else "?"
    except Exception:
        cache[eid] = "?"
    time.sleep(1.0)
    return cache[eid]


def esc(s):
    return html.escape(s if s is not None else "—")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rows = parse_rows()
    print(f"{len(rows)} rows, {len({r['item'] for r in rows})} distinct items")

    p13677 = wd_p13677([r["item"] for r in rows] + [r["parent"] for r in rows])
    names = {}
    for q, ids in p13677.items():
        for eid in ids:
            entry_name(eid, names)
    print(f"resolved {len(names)} Kokugakuin entry names")

    trs = []
    for r in sorted(rows, key=lambda x: x["item"]):
        p_ids = p13677.get(r["parent"], [])
        p_names = {eid: names.get(eid, "?") for eid in p_ids}
        i_ids = p13677.get(r["item"], [])
        parent_entry_names = set(p_names.values())

        def id_cell(eid, highlight):
            nm = names.get(eid, "?")
            cls = ' class="match"' if highlight else ""
            return (f'<span{cls}><a href="{DET}{eid}" target="_blank">{esc(eid)}</a> '
                    f'{esc(nm)}</span>')

        item_cells = "<br>".join(
            id_cell(eid, names.get(eid, "?") in parent_entry_names and parent_entry_names != {"?"})
            for eid in i_ids) or "—"
        parent_cells = "<br>".join(id_cell(eid, False) for eid in p_ids) or "—"
        matched = [eid for eid in i_ids
                   if names.get(eid, "?") in parent_entry_names and parent_entry_names != {"?"}]
        verdict = ("suggest P958 = the highlighted entry" if len(matched) == 1
                   else "needs eyes — no single name match")
        trs.append(
            f'<tr><td><a href="{WD}{r["item"]}" target="_blank">{esc(r["item"])}</a><br>'
            f'{esc(r["item_label"])}</td>'
            f'<td><a href="{WD}{r["parent"]}" target="_blank">{esc(r["parent"])}</a><br>'
            f'{esc(r["parent_label"])}</td>'
            f'<td>{parent_cells}</td><td>{item_cells}</td>'
            f'<td>rank {esc(r["ranking"])}</td><td>{esc(verdict)}</td></tr>')

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    single = sum(1 for r in rows
                 if len([e for e in p13677.get(r["item"], [])
                         if names.get(e, "?") in {names.get(x, "?") for x in p13677.get(r["parent"], [])}
                         and {names.get(x, "?") for x in p13677.get(r["parent"], [])} != {"?"}]) == 1)
    body = "\n".join(trs)
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Multiple Kokugakuin ids — which entry backs each link ({len(rows)} rows)</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1150px;margin:0 auto;
  padding:1.5rem;color:#222;line-height:1.5}}
 h1{{color:#2e7d32;font-size:1.4rem}} .nav a{{color:#2e7d32}}
 .intro{{background:#fff3e0;border-left:4px solid #ff9800;padding:.75rem 1rem;border-radius:0 4px 4px 0}}
 input#f{{width:100%;padding:.5rem;margin:1rem 0;border:1px solid #ccc;border-radius:6px;box-sizing:border-box}}
 table{{border-collapse:collapse;width:100%;font-size:.85rem}}
 th,td{{border:1px solid #e0e0e0;padding:.4rem .5rem;text-align:left;vertical-align:top}}
 th{{background:#f1f8e9;position:sticky;top:0}}
 .match{{background:#e8f5e9;font-weight:600;padding:0 .2rem;border-radius:3px}}
 a{{color:#1565c0;text-decoration:none}} a:hover{{text-decoration:underline}}
 .table-wrap{{overflow-x:auto}}
 footer{{margin-top:2rem;padding-top:1rem;border-top:1px solid #e0e0e0;color:#999;font-size:.8rem}}
</style></head><body>
<p class="nav"><a href="index.html">&larr; shintowiki</a></p>
<h1>Multiple Kokugakuin ids — which entry backs each link</h1>
<p class="intro">{len(rows)} candidate-links where the shrine item carries <strong>two Kokugakuin
entry ids</strong>, so the parent-link needs a section (P958) qualifier saying WHICH entry it
concerns. Emma's rule: this is per-item, no batch fix, heuristics prohibited. This table just does
the legwork — for each link it shows the <strong>parent's</strong> own entry and the
<strong>item's</strong> two entries (id → name from the Kokugakuin page). The item entry whose name
matches the parent's entry is <span class="match">highlighted</span> as a hint. {single} rows have a
single clean name-match; the rest genuinely need eyes. <strong>Report only — no Wikidata edits.</strong></p>
<input id="f" placeholder="Filter…" oninput="document.querySelectorAll('tbody tr').forEach(t=>t.style.display=t.textContent.toLowerCase().includes(this.value.toLowerCase())?'':'none')">
<div class="table-wrap"><table>
<thead><tr><th>item (candidate)</th><th>parent (entry)</th><th>parent's Kokugakuin entry</th>
<th>item's Kokugakuin entries</th><th>rank</th><th>hint</th></tr></thead>
<tbody>
{body}
</tbody></table></div>
<footer>Generated {now} from p958_manual_review.txt + live Wikidata/Kokugakuin by
<a href="https://github.com/EmmaLeonhart/shintowiki-scripts">shintowiki-scripts</a>
(<code>generate_multi_p13677_page.py</code>). Report only.</footer>
</body></html>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
