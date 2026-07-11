#!/usr/bin/env python3
"""Browsable GitHub Pages table of the 150 confirmed Shikinaisha no list names.

Emma asked (Open questions, 2026-07): *"Yes, please respond to this thing with a
link to the GitHub Pages thing, browsable table."* This is that page — the same
data as `report_orphan_shikinaisha.py` writes to `docs/orphan_shikinaisha_2026-07.md`,
but rendered as a filterable HTML table with the **twin entry QID surfaced** so the
84 twin pairs can be eyeballed side by side.

REPORT ONLY. Emits no Wikidata edits. Reuses the report's SPARQL `gather()` so the
two never drift. Writes `_site/shikinaisha-orphans.html` (committed + deployed by
`generate-pages.yml`; SPARQL reads work locally against query-main).

    python generate_shikinaisha_orphan_page.py
"""
import datetime
import html
import io
import os
import sys

from report_orphan_shikinaisha import gather, normalise

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
OUT = os.path.join(REPO_ROOT, "_site", "shikinaisha-orphans.html")

WD = "https://www.wikidata.org/wiki/"


def twins_of(q, claimed_lists, parts_of, ja_label, kokugakuin, ids_of_named):
    """The named entry QIDs this orphan is a twin of, with the match reason.

    Mirrors report_orphan_shikinaisha.classify but RETURNS the matching entries
    rather than a one-line label, so the page can link the pair."""
    out = {}  # qid -> reason
    # Kokugakuin-id twins: any named entry sharing one of this item's ids.
    for k in kokugakuin.get(q, []):
        for e in ids_of_named.get(k, []):
            if e != q:
                out.setdefault(e, "same Kokugakuin id")
    # Label twins: named entries in a list this item claims, same (normalised) ja.
    mine = ja_label.get(q)
    twins = [e for l in claimed_lists for e in parts_of.get(l, ()) if e != q]
    if mine:
        for e in twins:
            if ja_label.get(e) == mine:
                out.setdefault(e, "same ja label")
        for e in twins:
            if normalise(ja_label.get(e, "")) == normalise(mine):
                out.setdefault(e, "same normalised ja label")
    return out


def esc(s):
    return html.escape(str(s) if s is not None else "—")


def wd_link(q, label=None):
    return f'<a href="{WD}{q}" target="_blank">{esc(label or q)}</a>'


def build_rows():
    import collections
    (parts, confirmed, claims, kokugakuin, ja_label, en_label,
     list_label, parts_of, dup_ids) = gather()

    ids_of_named = collections.defaultdict(list)
    for q, ks in kokugakuin.items():
        if q in parts:
            for k in ks:
                ids_of_named[k].append(q)

    orphans = sorted(confirmed - parts)
    rows = []
    for q in orphans:
        cl = claims.get(q, [])
        tw = twins_of(q, cl, parts_of, ja_label, kokugakuin, ids_of_named)
        has_twin = bool(tw)
        rows.append({
            "q": q,
            "ja": ja_label.get(q, ""),
            "en": en_label.get(q, ""),
            "koku": kokugakuin.get(q, []),
            "claims": [list_label.get(l, l) for l in cl],
            "twins": tw,
            "bucket": "twin" if has_twin else "orphan",
        })
    return rows, ja_label


def render(rows, ja_label):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    twins = [r for r in rows if r["bucket"] == "twin"]
    orphs = [r for r in rows if r["bucket"] == "orphan"]

    def row_html(r):
        koku = ", ".join(
            f'<a href="https://jmapps.ne.jp/kokugakuin/det.html?data_id={k}" target="_blank">{esc(k)}</a>'
            for k in r["koku"]) or "—"
        claims = esc(", ".join(r["claims"])) if r["claims"] else "<em>claims no list</em>"
        twins = "<br>".join(
            f'{wd_link(e, ja_label.get(e) or e)} <span class="reason">({esc(reason)})</span>'
            for e, reason in r["twins"].items()) or "—"
        cls = "twin" if r["bucket"] == "twin" else "orphan"
        search = esc(f'{r["q"]} {r["ja"]} {r["en"]} {" ".join(r["claims"])}')
        return (f'<tr class="{cls}" data-search="{search.lower()}">'
                f'<td>{wd_link(r["q"])}</td>'
                f'<td lang="ja">{esc(r["ja"])}</td>'
                f'<td>{esc(r["en"])}</td>'
                f'<td>{koku}</td>'
                f'<td>{claims}</td>'
                f'<td>{twins}</td></tr>')

    twin_rows = "\n".join(row_html(r) for r in twins)
    orph_rows = "\n".join(row_html(r) for r in orphs)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Confirmed Shikinaisha the lists don't name — {len(rows)} items</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 1200px;
    margin: 0 auto; padding: 1.5rem; color: #222; line-height: 1.5; }}
  h1 {{ color: #2e7d32; font-size: 1.5rem; }}
  h2 {{ color: #2e7d32; border-bottom: 2px solid #c8e6c9; padding-bottom: 0.3rem;
    margin-top: 2rem; }}
  .nav a {{ color: #2e7d32; }}
  .intro {{ background: #fff3e0; border-left: 4px solid #ff9800;
    padding: 0.75rem 1rem; border-radius: 0 4px 4px 0; }}
  .counts {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }}
  .card {{ background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 8px;
    padding: 0.75rem 1.25rem; text-align: center; }}
  .card .n {{ font-size: 1.6rem; font-weight: 700; color: #2e7d32; }}
  .card .l {{ font-size: 0.8rem; color: #555; }}
  input#filter {{ width: 100%; padding: 0.6rem; font-size: 1rem; margin: 1rem 0;
    border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 0.4rem 0.55rem; text-align: left;
    vertical-align: top; }}
  th {{ background: #f1f8e9; position: sticky; top: 0; }}
  tr.twin td:first-child {{ border-left: 3px solid #4caf50; }}
  tr.orphan td:first-child {{ border-left: 3px solid #ff9800; }}
  .reason {{ color: #888; font-size: 0.78rem; }}
  a {{ color: #1565c0; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;
    color: #999; font-size: 0.8rem; }}
  .table-wrap {{ overflow-x: auto; }}
</style>
</head>
<body>
<p class="nav"><a href="index.html">&larr; shintowiki</a></p>
<h1>Confirmed Shikinaisha that no Engishiki list names</h1>
<p class="intro">A <strong>confirmed Shikinaisha</strong> is a shrine confidently identified as one of
the 927 register entries (unlike a <em>Ronsha</em>, a disputed candidate).
{len(rows) + 0} carry the confirmed class yet appear on no list.
<strong>{len(twins)} have a twin</strong> — a separate item, already named by a list, that
is the same shrine (matched by shared Kokugakuin id, identical Japanese name, or old-vs-new
kanji). Your call: <em>link</em> each pair (&ldquo;these two are the same shrine&rdquo;) or
<em>merge</em> them. <strong>{len(orphs)} have no twin</strong> — either modern shrines
mis-tagged as register entries, or genuine entries the lists are missing. Your call: which.
Report only — nothing here is edited on Wikidata.</p>

<div class="counts">
  <div class="card"><div class="n">{len(rows)}</div><div class="l">total unnamed</div></div>
  <div class="card"><div class="n">{len(twins)}</div><div class="l">have a twin (link or merge)</div></div>
  <div class="card"><div class="n">{len(orphs)}</div><div class="l">no twin (mis-tag or missing entry)</div></div>
</div>

<input id="filter" type="text" placeholder="Filter by QID, Japanese/English name, or list…"
  oninput="filt()">

<h2>{len(twins)} with a twin entry — link or merge each pair</h2>
<div class="table-wrap"><table>
<thead><tr><th>item</th><th>ja</th><th>en</th><th>Kokugakuin id</th><th>claims list</th>
<th>twin (already named)</th></tr></thead>
<tbody>
{twin_rows}
</tbody></table></div>

<h2>{len(orphs)} with no twin — decide: mis-tagged shrine, or entry the list is missing</h2>
<div class="table-wrap"><table>
<thead><tr><th>item</th><th>ja</th><th>en</th><th>Kokugakuin id</th><th>claims list</th>
<th>twin</th></tr></thead>
<tbody>
{orph_rows}
</tbody></table></div>

<script>
function filt() {{
  var q = document.getElementById('filter').value.toLowerCase();
  document.querySelectorAll('tbody tr').forEach(function(tr) {{
    tr.style.display = tr.dataset.search.indexOf(q) > -1 ? '' : 'none';
  }});
}}
</script>
<footer>Generated {now} from live Wikidata SPARQL by
<a href="https://github.com/EmmaLeonhart/shintowiki-scripts">shintowiki-scripts</a>
(<code>generate_shikinaisha_orphan_page.py</code>). Report only; no Wikidata edits.</footer>
</body>
</html>"""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rows, ja_label = build_rows()
    html_out = render(rows, ja_label)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(html_out)
    twins = sum(1 for r in rows if r["bucket"] == "twin")
    print(f"{len(rows)} orphans ({twins} twin / {len(rows)-twins} no-twin) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
