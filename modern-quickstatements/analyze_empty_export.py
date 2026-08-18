#!/usr/bin/env python3
"""Analyse a Special:Export full-history XML dump of the 'empty items' — what each
item LOST, so restoration candidates surface.

Emma 2026-07-11: Special:Export (one bulk XML with full revision history) is the
right tool, not thousands of per-item API calls. For each item this diffs the PEAK
revision (the one with the most statements — the item at its fullest) against the
CURRENT (last) revision: every property/value present at peak but gone now is
recoverable. P31 (instance of) is called out, since it's usually the first thing
stripped. Also lists the editors and the edit count.

    python analyze_empty_export.py [path-to-export.xml]

Default path is the newest Wikidata-*.xml in the user's Downloads. Writes
_site/empty-items.html. Report only.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import datetime
import glob
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
OUT = os.path.join(REPO_ROOT, "_site", "empty-items.html")
WD = "https://www.wikidata.org/wiki/"
API = "https://www.wikidata.org/w/api.php"
EXPORT = "https://www.wikidata.org/w/index.php?title=Special:Export&action=submit"
UA = WIKIDATA_USER_AGENT
SOURCE_PAGE = "User:MisterSynergy/sysop/empty_items"


def fetch_qids_from_page():
    url = API + "?" + urllib.parse.urlencode({
        "action": "parse", "page": SOURCE_PAGE, "prop": "wikitext", "format": "json"})
    wt = json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60)
    )["parse"]["wikitext"]["*"]
    out, seen = [], set()
    for m in re.finditer(r"^\|\s*\[\[(Q\d+)(?:\|[^\]]*)?\]\]\s*$", wt, re.M):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


def fetch_export(qids, batch=250, out_path=None):
    """Special:Export the items in batches (full history), combined into ONE valid XML.

    Each batch returns its own `<mediawiki>` document; concatenating them gives an
    invalid multi-root file, so we keep only the `<page>…</page>` blocks and wrap
    them once. `<text>` content is XML-escaped, so `</page>` never occurs inside.
    """
    out_path = out_path or os.path.join(REPO_ROOT, "_site", "empty-items-export.xml")
    _page = re.compile(r"<page>.*?</page>", re.S)
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("<mediawiki>\n")
        for i in range(0, len(qids), batch):
            chunk = qids[i:i + batch]
            data = urllib.parse.urlencode({"pages": "\n".join(chunk), "history": "1"}).encode()
            req = urllib.request.Request(EXPORT, data=data, headers={"User-Agent": UA})
            xml = urllib.request.urlopen(req, timeout=300).read().decode("utf-8", "replace")
            for pg in _page.findall(xml):
                fh.write(pg)
                fh.write("\n")
            print(f"  exported {min(i+batch,len(qids))}/{len(qids)}", flush=True)
            time.sleep(1.0)
        fh.write("</mediawiki>\n")
    return out_path


def default_xml():
    downloads = os.path.expanduser("~/Downloads")
    cands = sorted(glob.glob(os.path.join(downloads, "Wikidata-*.xml")),
                   key=os.path.getmtime, reverse=True)
    return cands[0] if cands else None


def claim_values(claims):
    """{prop: [rendered value strings]} from a Wikibase entity's claims JSON."""
    out = {}
    for prop, statements in (claims or {}).items():
        vals = []
        for st in statements if isinstance(statements, list) else []:
            snak = st.get("mainsnak", st) if isinstance(st, dict) else {}
            if snak.get("snaktype") and snak.get("snaktype") != "value":
                vals.append(snak["snaktype"])
                continue
            dv = snak.get("datavalue", {})
            v = dv.get("value")
            if isinstance(v, dict):
                if "id" in v:
                    vals.append(v["id"])
                elif "text" in v:
                    vals.append(v["text"])
                elif "time" in v:
                    vals.append(v["time"].lstrip("+")[:10])
                elif "amount" in v:
                    vals.append(v["amount"].lstrip("+"))
                elif "latitude" in v:
                    vals.append(f"{v['latitude']:.4f},{v['longitude']:.4f}")
                else:
                    vals.append(json.dumps(v, ensure_ascii=False)[:40])
            elif v is not None:
                vals.append(str(v)[:60])
        if vals:
            out[prop] = vals
    return out


def iter_pages(path):
    """(title, [(timestamp, user, comment, content_json_str)]) per page, streaming."""
    ns = None
    revs = []
    title = None
    for event, elem in ET.iterparse(path, events=("start", "end")):
        tag = elem.tag.split("}")[-1]
        if event == "end" and tag == "title":
            title = elem.text
        elif event == "end" and tag == "revision":
            ts = elem.findtext("{*}timestamp") or ""
            c = elem.find("{*}contributor")
            user = None
            if c is not None:
                user = c.findtext("{*}username") or c.findtext("{*}ip") or "?"
            comment = elem.findtext("{*}comment") or ""
            text = elem.findtext("{*}text") or ""
            revs.append((ts, user or "?", comment, text))
            elem.clear()
        elif event == "end" and tag == "page":
            if title and title.startswith("Q"):
                yield title, revs
            revs = []
            title = None
            elem.clear()


def analyse(path):
    rows = []
    for qid, revs in iter_pages(path):
        if not revs:
            continue
        revs.sort(key=lambda r: r[0])   # oldest -> newest by timestamp
        editors = {}
        parsed = []
        for ts, user, comment, content in revs:
            editors[user] = editors.get(user, 0) + 1
            try:
                data = json.loads(content) if content.strip().startswith("{") else {}
            except Exception:
                data = {}
            parsed.append((ts, data))
        # peak = revision with the most statements; current = last revision
        def nclaims(d):
            return sum(len(v) for v in (d.get("claims") or {}).values()
                       if isinstance(v, list))
        peak_ts, peak = max(parsed, key=lambda p: nclaims(p[1]))
        cur_ts, cur = parsed[-1]
        peak_c = claim_values(peak.get("claims"))
        cur_c = claim_values(cur.get("claims"))
        removed = {}
        for prop, vals in peak_c.items():
            gone = [v for v in vals if v not in cur_c.get(prop, [])]
            if gone:
                removed[prop] = gone
        labels = {l: v["value"] for l, v in (cur.get("labels") or {}).items()}
        rows.append({
            "qid": qid,
            "labels": labels,
            "removed": removed,
            "lost": sum(len(v) for v in removed.values()),
            "peak_n": nclaims(peak), "cur_n": nclaims(cur),
            "editors": [u for u, _ in sorted(editors.items(), key=lambda kv: -kv[1])],
            "edits": len(revs),
        })
    return rows


def esc(s):
    return html.escape(str(s) if s is not None else "")


def render(rows):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows.sort(key=lambda r: (-r["lost"], -len(r["removed"]), -r["edits"]))
    p31 = sum(1 for r in rows if "P31" in r["removed"])
    strong = sum(1 for r in rows if r["lost"] >= 3)

    def qlink(v):
        return (f'<a href="{WD}{esc(v)}" target="_blank">{esc(v)}</a>'
                if re.fullmatch(r"Q\d+", str(v)) else esc(v))

    trs = []
    for r in rows:
        if not r["removed"]:
            continue
        labels = " · ".join(f'{esc(v)} <small>({esc(l)})</small>'
                            for l, v in sorted(r["labels"].items())) or "<em>none</em>"
        rem = "<br>".join(
            f'{"<strong>" if p=="P31" else ""}'
            f'<a href="{WD}Property:{p}" target="_blank">{p}</a>'
            f'{"</strong>" if p=="P31" else ""} → {", ".join(qlink(v) for v in vs)}'
            for p, vs in sorted(r["removed"].items(), key=lambda kv: (kv[0] != "P31", kv[0])))
        editors = ", ".join(esc(u) for u in r["editors"][:10])
        if len(r["editors"]) > 10:
            editors += f' <small>+{len(r["editors"])-10}</small>'
        trs.append(
            f'<tr class="{"has-p31" if "P31" in r["removed"] else ""}" '
            f'data-search="{esc(r["qid"]+" "+" ".join(r["labels"].values())).lower()}">'
            f'<td><a href="{WD}{r["qid"]}" target="_blank">{r["qid"]}</a></td>'
            f'<td style="text-align:center;font-weight:700;color:{"#c62828" if r["lost"]>=3 else "#888"}">{r["lost"]}</td>'
            f'<td>{labels}</td><td>{rem}</td>'
            f'<td>{len(r["editors"])} users / {r["edits"]} edits<br><small>{editors}</small></td></tr>')
    body = "\n".join(trs)
    shown = len(trs)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Empty items — restoration candidates ({shown})</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1200px;margin:0 auto;padding:1.5rem;color:#222;line-height:1.5}}
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
<h1>Empty items — restoration candidates</h1>
<p class="intro">From a Special:Export full-history dump of
<a href="{WD}User:MisterSynergy/sysop/empty_items" target="_blank">User:MisterSynergy/sysop/empty_items</a>.
For each item the <strong>peak</strong> revision (most statements) is diffed against the
<strong>current</strong> one — everything present then and gone now is <strong>recoverable</strong>.
Sorted by how much was lost, most first; <strong>P31</strong> removals are bold. Report only.</p>
<div class="counts">
 <div class="card"><div class="n">{shown}</div><div class="l">items that lost something</div></div>
 <div class="card"><div class="n">{strong}</div><div class="l">lost &ge;3 statements</div></div>
 <div class="card"><div class="n">{p31}</div><div class="l">lost their P31</div></div>
 <div class="card"><div class="n">{len(rows)}</div><div class="l">items in the dump</div></div>
</div>
<input id="f" placeholder="Filter by QID or label…" oninput="document.querySelectorAll('tbody tr').forEach(t=>t.style.display=t.dataset.search.includes(this.value.toLowerCase())?'':'none')">
<div class="table-wrap"><table>
<thead><tr><th>item</th><th>lost</th><th>surviving labels</th><th>removed properties (P31 bold)</th><th>editors / edits</th></tr></thead>
<tbody>
{body}
</tbody></table></div>
<footer>Generated {now} from the Special:Export dump by
<a href="https://github.com/EmmaLeonhart/shintowiki-scripts">shintowiki-scripts</a>
(<code>analyze_empty_export.py</code>). Report only.</footer>
</body></html>"""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    args = sys.argv[1:]
    if "--fetch" in args:
        # Self-contained (CI): pull the QIDs off the page, Special:Export them all.
        qids = fetch_qids_from_page()
        print(f"{len(qids)} QIDs; exporting full history…", flush=True)
        path = fetch_export(qids)
    else:
        path = args[0] if args else default_xml()
    if not path or not os.path.exists(path):
        print(f"no export XML found (looked for {path})")
        return 1
    print(f"parsing {path} ({os.path.getsize(path)//1024} KB)", flush=True)
    rows = analyse(path)
    lost = [r for r in rows if r["removed"]]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(render(rows))
    # the plain list, straight from the parsed dump (no extra API calls)
    listp = os.path.join(REPO_ROOT, "_site", "empty-items-list.txt")
    with io.open(listp, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# {len(rows)} empty items (Special:Export dump). QID\tlost\tlabel\turl\n")
        for r in sorted(rows, key=lambda r: -r["lost"]):
            lab = r["labels"].get("en") or (next(iter(r["labels"].values())) if r["labels"] else "")
            f.write(f'{r["qid"]}\t{r["lost"]}\t{lab}\t{WD}{r["qid"]}\n')
    p31 = sum(1 for r in rows if "P31" in r["removed"])
    print(f"{len(rows)} items, {len(lost)} lost something, {p31} lost P31 -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
