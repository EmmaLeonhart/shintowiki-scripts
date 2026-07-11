#!/usr/bin/env python3
"""Browsable GitHub Pages table of the residual Shikinaisha missing a P13677 id.

Emma asked (Open questions, 2026-07): *"You could definitely make a GitHub Pages page
that shows me the actual stuff here and link it as a response."* This renders
`kokugakuin_id_report.txt` — the per-item output of `match_kokugakuin_ids.py`, the
18 entries whose Kokugakuin University Digital Museum entry id (P13677) the strict
matcher could not safely fill — as a filterable HTML table with the why for each,
plus links to the candidate ids and the items already holding them.

Report only. Parses the committed report file (no scraping, no SPARQL) so it is cheap
to run in CI. Re-run `match_kokugakuin_ids.py` first if the report has gone stale.
Writes `_site/kokugakuin-missing-ids.html`.

    python generate_kokugakuin_id_page.py
"""
import datetime
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
REPORT = os.path.join(HERE, "kokugakuin_id_report.txt")
OUT = os.path.join(REPO_ROOT, "_site", "kokugakuin-missing-ids.html")

WD = "https://www.wikidata.org/wiki/"
DET = "https://jmapps.ne.jp/kokugakuin/det.html?data_id="

# What each status means, for the page's legend. Keyed by a stable prefix.
LEGEND = [
    ("NO-ANCHOR",
     "No known Kokugakuin id anywhere in this shrine's district, so there is no "
     "range to scan — the matcher had no anchor to search from."),
    ("NO-MATCH",
     "The district range was scanned but no entry title exactly equals this "
     "shrine's Japanese name."),
    ("AMBIGUOUS",
     "Another target in the same district shares this exact label, so a name match "
     "cannot tell them apart (e.g. two 野蚊神社 in 河北郡)."),
    ("ENTRY-TAKEN",
     "A name-matching entry id exists but is already held by other item(s) — minting "
     "it here would duplicate an id. These are the ones needing per-item human eyes."),
]

_ID_HOLDERS = re.compile(r"id (\d+) held by ([Q0-9,]+)")


def status_kind(status):
    for pref, _desc in LEGEND:
        if status.startswith(pref):
            return pref
    return "OTHER"


def esc(s):
    return html.escape(s if s is not None else "—")


def wd_link(q):
    return f'<a href="{WD}{q}" target="_blank">{esc(q)}</a>'


def render_status(status):
    """ENTRY-TAKEN carries ids + holder QIDs — turn them into links."""
    m = _ID_HOLDERS.findall(status)
    if not m:
        return esc(status)
    parts = []
    for id_, holders in m:
        hl = ", ".join(wd_link(h) for h in holders.split(","))
        parts.append(
            f'<a href="{DET}{id_}" target="_blank">id {esc(id_)}</a> '
            f'held by {hl}')
    return "ENTRY-TAKEN &mdash; " + "; ".join(parts)


def parse_report():
    rows = []
    with io.open(REPORT, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 4:
                continue
            q, ja, district, status = parts[0], parts[1], parts[2], "|".join(parts[3:]).strip()
            rows.append({"q": q, "ja": ja, "district": district,
                         "status": status, "kind": status_kind(status)})
    return rows


def render(rows):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    import collections
    counts = collections.Counter(r["kind"] for r in rows)

    legend_html = "\n".join(
        f'<li><code>{esc(p)}</code> ({counts.get(p, 0)}) — {esc(d)}</li>'
        for p, d in LEGEND)

    def row_html(r):
        search = esc(f'{r["q"]} {r["ja"]} {r["district"]} {r["status"]}').lower()
        return (f'<tr data-search="{search}">'
                f'<td>{wd_link(r["q"])}</td>'
                f'<td lang="ja">{esc(r["ja"])}</td>'
                f'<td lang="ja">{esc(r["district"]) or "&mdash;"}</td>'
                f'<td><span class="kind kind-{r["kind"]}">{esc(r["kind"])}</span></td>'
                f'<td>{render_status(r["status"])}</td></tr>')

    body_rows = "\n".join(row_html(r) for r in rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shikinaisha missing a Kokugakuin id — {len(rows)} entries</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 1100px;
    margin: 0 auto; padding: 1.5rem; color: #222; line-height: 1.5; }}
  h1 {{ color: #2e7d32; font-size: 1.5rem; }}
  .nav a {{ color: #2e7d32; }}
  .intro {{ background: #fff3e0; border-left: 4px solid #ff9800;
    padding: 0.75rem 1rem; border-radius: 0 4px 4px 0; }}
  ul.legend {{ list-style: none; padding: 0; font-size: 0.9rem; }}
  ul.legend li {{ padding: 0.25rem 0; }}
  input#filter {{ width: 100%; padding: 0.6rem; font-size: 1rem; margin: 1rem 0;
    border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.88rem; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 0.4rem 0.55rem; text-align: left;
    vertical-align: top; }}
  th {{ background: #f1f8e9; position: sticky; top: 0; }}
  .kind {{ font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 4px;
    white-space: nowrap; }}
  .kind-ENTRY-TAKEN {{ background: #ffebee; color: #c62828; }}
  .kind-AMBIGUOUS {{ background: #fff8e1; color: #ef6c00; }}
  .kind-NO-MATCH {{ background: #e3f2fd; color: #1565c0; }}
  .kind-NO-ANCHOR {{ background: #f3e5f5; color: #6a1b9a; }}
  a {{ color: #1565c0; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;
    color: #999; font-size: 0.8rem; }}
  .table-wrap {{ overflow-x: auto; }}
</style>
</head>
<body>
<p class="nav"><a href="index.html">&larr; shintowiki</a></p>
<h1>Shikinaisha still missing a Kokugakuin entry id</h1>
<p class="intro">Every real 927 register entry has an id in the Kokugakuin University
Digital Museum shrine database (P13677); some entry items are missing it. The strict
matcher (<code>match_kokugakuin_ids.py</code>) matches a shrine's Japanese name against
the database's entry titles, but name-matching alone isn't safe — two adjacent entries
can describe the same shrine — so it cut the missing-id set from 94 to these
<strong>{len(rows)}</strong> and found <strong>zero</strong> safe to add on its own.
Your call: is name-matching good enough, or do these need per-item eyes? Nothing runs
until you say. Report only — no Wikidata edits.</p>

<h3>What the statuses mean</h3>
<ul class="legend">
{legend_html}
</ul>

<input id="filter" type="text" placeholder="Filter by QID, name, district, or status…"
  oninput="filt()">

<div class="table-wrap"><table>
<thead><tr><th>item</th><th>ja</th><th>district</th><th>status</th><th>detail</th></tr></thead>
<tbody>
{body_rows}
</tbody></table></div>

<script>
function filt() {{
  var q = document.getElementById('filter').value.toLowerCase();
  document.querySelectorAll('tbody tr').forEach(function(tr) {{
    tr.style.display = tr.dataset.search.indexOf(q) > -1 ? '' : 'none';
  }});
}}
</script>
<footer>Generated {now} from <code>kokugakuin_id_report.txt</code> by
<a href="https://github.com/EmmaLeonhart/shintowiki-scripts">shintowiki-scripts</a>
(<code>generate_kokugakuin_id_page.py</code>). Report only; no Wikidata edits.</footer>
</body>
</html>"""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rows = parse_report()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(render(rows))
    import collections
    counts = collections.Counter(r["kind"] for r in rows)
    print(f"{len(rows)} entries -> {OUT}")
    for k, n in counts.most_common():
        print(f"  {n:3d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
