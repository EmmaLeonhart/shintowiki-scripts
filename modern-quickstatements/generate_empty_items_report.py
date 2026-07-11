#!/usr/bin/env python3
"""Report on the Wikidata 'empty items' (User:MisterSynergy/sysop/empty_items).

Emma 2026-07-11: these items now have 0 sitelinks + 0 statements, but many were
emptied — she wants the HISTORY of each, "particularly the P31 history: there's
often something that was removed from P31." So for every item on the maintenance
list this builds a table with:

  * a link to the item;
  * its surviving labels across languages (often the only thing left);
  * the properties that were REMOVED over its history — especially P31 — read
    from the Wikidata auto-comments on each revision (`wbremoveclaims-remove …
    [[Property:P31]]: [[Qxxx]]`), so no full-content diffing is needed;
  * the list of users who edited it, and the edit count;
  * its backlinks (what still links to it).

Writes `_site/empty-items.html`. Report only — no Wikidata edits.

    python generate_empty_items_report.py [--limit N]
"""
import argparse
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
OUT = os.path.join(REPO_ROOT, "_site", "empty-items.html")

API = "https://www.wikidata.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SOURCE_PAGE = "User:MisterSynergy/sysop/empty_items"
WD = "https://www.wikidata.org/wiki/"

THROTTLE = 0.15

# Wikidata removal auto-comment: "/* wbremoveclaims-remove:1| */ [[Property:P31]]: [[Q5]]"
_REMOVED = re.compile(r"wbremoveclaims-remove[^*]*\*/\s*\[\[Property:(P\d+)\]\]:\s*(.*)")
_QID_IN = re.compile(r"\[\[Q\d+(?:\|[^\]]*)?\]\]|Q\d+")


def api_get(params):
    params = dict(params, format="json")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2)


def fetch_item_qids(limit=None):
    """The ordered list of item QIDs from the maintenance page's table."""
    wt = api_get({"action": "parse", "page": SOURCE_PAGE,
                  "prop": "wikitext"})["parse"]["wikitext"]["*"]
    qids, seen = [], set()
    # each row's item column is `| [[Qxxx|label]]` then `| [[Qxxx|Qxxx]]`.
    for m in re.finditer(r"^\|\s*\[\[(Q\d+)(?:\|([^\]]*))?\]\]\s*$", wt, re.M):
        q = m.group(1)
        if q not in seen:
            seen.add(q)
            qids.append(q)
            if limit and len(qids) >= limit:
                break
    return qids


def fetch_labels(qids):
    """{qid: {lang: value}} for surviving labels, batched."""
    out = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        data = api_get({"action": "wbgetentities", "ids": "|".join(chunk),
                        "props": "labels"})
        for q, e in data.get("entities", {}).items():
            out[q] = {lang: v["value"] for lang, v in e.get("labels", {}).items()}
        time.sleep(THROTTLE)
    return out


def fetch_history(qid):
    """(editors[list], edit_count, removed_props{prop: [values]}) from revision comments."""
    editors, count = {}, 0
    removed = {}
    cont = {}
    while True:
        data = api_get({"action": "query", "prop": "revisions", "titles": qid,
                        "rvprop": "user|comment|timestamp", "rvlimit": "500",
                        "rvdir": "newer", **cont})
        pages = data.get("query", {}).get("pages", {})
        for p in pages.values():
            for rev in p.get("revisions", []):
                count += 1
                u = rev.get("user", "?")
                editors[u] = editors.get(u, 0) + 1
                c = rev.get("comment", "")
                m = _REMOVED.search(c)
                if m:
                    prop, tail = m.group(1), m.group(2)
                    vals = _QID_IN.findall(tail) or [tail.strip()[:40]]
                    removed.setdefault(prop, [])
                    for v in vals:
                        vv = re.sub(r"\[\[|\]\]", "", v).split("|")[0]
                        if vv and vv not in removed[prop]:
                            removed[prop].append(vv)
        if "continue" in data:
            cont = {"rvcontinue": data["continue"]["rvcontinue"]}
            time.sleep(THROTTLE)
        else:
            break
    ordered = sorted(editors.items(), key=lambda kv: -kv[1])
    return [u for u, _ in ordered], count, removed


def fetch_backlinks(qid):
    """Titles of pages that link to the item (main namespace), capped."""
    data = api_get({"action": "query", "list": "backlinks", "bltitle": qid,
                    "blnamespace": "0", "bllimit": "20"})
    return [b["title"] for b in data.get("query", {}).get("backlinks", [])]


def esc(s):
    return html.escape(str(s) if s is not None else "")


def render(rows, total):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with_p31 = sum(1 for r in rows if "P31" in r["removed"])

    def wd_prop(p):
        return f'<a href="{WD}Property:{p}" target="_blank">{p}</a>'

    def qlink(v):
        return (f'<a href="{WD}{v}" target="_blank">{esc(v)}</a>'
                if re.fullmatch(r"Q\d+", v) else esc(v))

    trs = []
    for r in rows:
        labels = " · ".join(f'<span lang="{esc(l)}">{esc(v)}</span> <small>({esc(l)})</small>'
                            for l, v in sorted(r["labels"].items())) or "<em>no labels</em>"
        rem = "<br>".join(
            f'{"<strong>" if p == "P31" else ""}{wd_prop(p)}{"</strong>" if p == "P31" else ""}'
            f' → {", ".join(qlink(v) for v in vs)}'
            for p, vs in sorted(r["removed"].items(),
                                key=lambda kv: (kv[0] != "P31", kv[0]))) or "—"
        editors = ", ".join(f'<a href="{WD.replace("/wiki/","/wiki/User:")}{urllib.parse.quote(u)}" '
                            f'target="_blank">{esc(u)}</a>' for u in r["editors"][:12])
        if len(r["editors"]) > 12:
            editors += f' <small>+{len(r["editors"]) - 12} more</small>'
        bl = ", ".join(f'<a href="{WD}{esc(b)}" target="_blank">{esc(b)}</a>'
                       for b in r["backlinks"]) or "—"
        lost = r.get("lost", sum(len(vs) for vs in r["removed"].values()))
        trs.append(
            f'<tr class="{"has-p31" if "P31" in r["removed"] else ""}" '
            f'data-search="{esc(r["qid"]+" "+" ".join(r["labels"].values())).lower()}">'
            f'<td><a href="{WD}{r["qid"]}" target="_blank">{r["qid"]}</a></td>'
            f'<td style="text-align:center;font-weight:700;'
            f'color:{"#c62828" if lost>=3 else "#888"}">{lost}</td>'
            f'<td>{labels}</td><td>{rem}</td>'
            f'<td>{esc(len(r["editors"]))} users / {esc(r["edits"])} edits<br>'
            f'<small>{editors}</small></td>'
            f'<td>{bl}</td></tr>')
    body = "\n".join(trs)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wikidata empty items — history &amp; removed P31 ({len(rows)})</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1300px;margin:0 auto;
  padding:1.5rem;color:#222;line-height:1.5}}
 h1{{color:#2e7d32;font-size:1.4rem}} .nav a{{color:#2e7d32}}
 .intro{{background:#fff3e0;border-left:4px solid #ff9800;padding:.75rem 1rem;border-radius:0 4px 4px 0}}
 .counts{{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}}
 .card{{background:#e8f5e9;border:1px solid #c8e6c9;border-radius:8px;padding:.6rem 1.1rem;text-align:center}}
 .card .n{{font-size:1.5rem;font-weight:700;color:#2e7d32}} .card .l{{font-size:.78rem;color:#555}}
 input#f{{width:100%;padding:.55rem;margin:1rem 0;border:1px solid #ccc;border-radius:6px;box-sizing:border-box}}
 table{{border-collapse:collapse;width:100%;font-size:.83rem}}
 th,td{{border:1px solid #e0e0e0;padding:.4rem .5rem;text-align:left;vertical-align:top}}
 th{{background:#f1f8e9;position:sticky;top:0}}
 tr.has-p31 td:first-child{{border-left:3px solid #c62828}}
 a{{color:#1565c0;text-decoration:none}} a:hover{{text-decoration:underline}}
 .table-wrap{{overflow-x:auto}}
 footer{{margin-top:2rem;padding-top:1rem;border-top:1px solid #e0e0e0;color:#999;font-size:.8rem}}
</style></head><body>
<p class="nav"><a href="index.html">&larr; shintowiki</a></p>
<h1>Wikidata empty items — history &amp; removed P31</h1>
<p class="intro">From <a href="{WD}{urllib.parse.quote(SOURCE_PAGE)}" target="_blank">User:MisterSynergy/sysop/empty_items</a>
(items with 0 sitelinks + 0 statements). Many were <em>emptied</em> and could be
<strong>restored</strong>. Sorted by how much was lost — the "lost" column counts the
(property, value) pairs removed over the item's history (read from the edit-summary
auto-comments), <strong>especially P31 (instance of)</strong>, which is usually the first thing
to go. Rows are the restoration candidates, most-recoverable first. Report only — no edits.</p>
<div class="counts">
 <div class="card"><div class="n">{len(rows)}</div><div class="l">items processed{f" of {total}" if total>len(rows) else ""}</div></div>
 <div class="card"><div class="n">{sum(1 for r in rows if r.get("lost",0)>=3)}</div><div class="l">lost &ge;3 statements (recover)</div></div>
 <div class="card"><div class="n">{with_p31}</div><div class="l">had a P31 removed</div></div>
</div>
<input id="f" placeholder="Filter by QID or label…" oninput="document.querySelectorAll('tbody tr').forEach(t=>t.style.display=t.dataset.search.includes(this.value.toLowerCase())?'':'none')">
<div class="table-wrap"><table>
<thead><tr><th>item</th><th>lost</th><th>surviving labels</th><th>removed properties (P31 bold)</th>
<th>editors / edits</th><th>backlinks</th></tr></thead>
<tbody>
{body}
</tbody></table></div>
<footer>Generated {now} from live Wikidata by
<a href="https://github.com/EmmaLeonhart/shintowiki-scripts">shintowiki-scripts</a>
(<code>generate_empty_items_report.py</code>). Report only.</footer>
</body></html>"""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    qids = fetch_item_qids(args.limit)
    total_all = len(fetch_item_qids()) if args.limit else len(qids)
    print(f"{len(qids)} items to process (list has {total_all})")
    labels = fetch_labels(qids)
    rows = []
    for i, q in enumerate(qids, 1):
        editors, edits, removed = fetch_history(q)
        backlinks = fetch_backlinks(q)
        rows.append({"qid": q, "labels": labels.get(q, {}), "editors": editors,
                     "edits": edits, "removed": removed, "backlinks": backlinks})
        if i % 25 == 0:
            print(f"  {i}/{len(qids)}")
        time.sleep(THROTTLE)
    # Restoration candidates first: the more (property, value) pairs a now-empty
    # item lost, the more there is to recover.
    for r in rows:
        r["lost"] = sum(len(vs) for vs in r["removed"].values())
    rows.sort(key=lambda r: (-r["lost"], -len(r["removed"]), -r["edits"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(render(rows, total_all))
    p31 = sum(1 for r in rows if "P31" in r["removed"])
    recov = sum(1 for r in rows if r["lost"] >= 3)
    print(f"-> {OUT} ({len(rows)} rows, {p31} with a removed P31, "
          f"{recov} strong restoration candidates >=3 lost)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
