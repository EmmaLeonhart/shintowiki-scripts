#!/usr/bin/env python3
"""Browsable explainer of the Awa Province entry-3 defect + the by-hand delete.

Emma asked (Open questions, 2026-07): *"oh god fucking link this."* This is the page
for the Awa list defect written up in `docs/engishiki_list_defects_2026-07.md §1`:
the 927 register's Awa entry #3 is 天神社 (Tenjinsha), but the jawiki list wrote it as
a piped link to a *different* shrine, 下立松原神社 (Shimotachimatsubara), and the import
followed the link — so Wikidata now says Awa entry #3 IS Shimotachimatsubara. The add
that puts 天神社 back at ordinal 3 is queued; the leftover is a by-hand delete of the
wrong statement, which can't be a QuickStatement because 下立松原神社 sits on the list
twice (ordinals 3 and 5) with the same value.

Static content (no SPARQL) — the facts are pinned in the source articles and the doc.
Writes `_site/awa-entry-3.html`.

    python generate_awa_entry3_page.py
"""
import datetime
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
OUT = os.path.join(REPO_ROOT, "_site", "awa-entry-3.html")

WD = "https://www.wikidata.org/wiki/"
DET = "https://jmapps.ne.jp/kokugakuin/det.html?data_id="

AWA_LIST = "Q11450714"        # List of Shikinaisha in Awa Province
TENJIN = "Q137041912"         # 天神社 — the real entry 3, currently list-less
SHIMO = "Q11361262"           # 下立松原神社 — really entry 5, wrongly also at 3

# The 927 Awa sequence: (ordinal, ja, QID, kokugakuin id, note)
SEQUENCE = [
    ("1", "安房坐神社", None, None, ""),
    ("2", "后神天比理乃咩命神社", None, "181733", ""),
    ("3", "天神社", TENJIN, "181734", "correct entry — currently holds NO list membership"),
    ("4", "莫越山神社", None, "181735", ""),
    ("5", "下立松原神社", SHIMO, "181736", "correctly here at 5"),
    ("6", "高家神社", None, "181737", ""),
]


def wd(q, label=None):
    import html
    return f'<a href="{WD}{q}" target="_blank">{html.escape(label or q)}</a>' if q else "&mdash;"


def render():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    import html

    seq_rows = []
    for ordn, ja, q, kid, note in SEQUENCE:
        wrong = ordn == "3"
        koku = f'<a href="{DET}{kid}" target="_blank">{kid}</a>' if kid else "&mdash;"
        cls = ' class="wrong"' if wrong else ""
        cur = (f'<td class="bad">{wd(SHIMO, "下立松原神社")} '
               f'<span class="tag">(piped-link import)</span></td>') if wrong \
            else f'<td>{wd(q, ja) if q else html.escape(ja)}</td>'
        should = (f'<td class="good">{wd(TENJIN, "天神社")}</td>') if wrong \
            else f'<td>{wd(q, ja) if q else html.escape(ja)}</td>'
        seq_rows.append(
            f'<tr{cls}><td>{ordn}</td><td lang="ja">{html.escape(ja)}</td>'
            f'<td>{koku}</td>{cur}{should}</tr>')
    seq_html = "\n".join(seq_rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Awa Province entry 3 — a piped link stole 天神社</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 960px;
    margin: 0 auto; padding: 1.5rem; color: #222; line-height: 1.6; }}
  h1 {{ color: #2e7d32; font-size: 1.5rem; }}
  h2 {{ color: #2e7d32; border-bottom: 2px solid #c8e6c9; padding-bottom: 0.3rem;
    margin-top: 2rem; }}
  .nav a {{ color: #2e7d32; }}
  .intro {{ background: #fff3e0; border-left: 4px solid #ff9800;
    padding: 0.75rem 1rem; border-radius: 0 4px 4px 0; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; margin: 1rem 0; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 0.45rem 0.6rem; text-align: left; }}
  th {{ background: #f1f8e9; }}
  tr.wrong td {{ background: #fff8e1; }}
  td.bad {{ color: #c62828; }}
  td.good {{ color: #2e7d32; font-weight: 600; }}
  .tag {{ font-size: 0.75rem; color: #888; }}
  code, pre {{ font-family: Consolas, Monaco, monospace; }}
  pre {{ background: #263238; color: #eceff1; padding: 0.85rem 1rem; border-radius: 6px;
    overflow-x: auto; font-size: 0.85rem; }}
  pre .del {{ color: #ff8a80; }}
  pre .add {{ color: #b9f6ca; }}
  .box {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem 1.25rem;
    margin: 1rem 0; }}
  .box.add {{ background: #e8f5e9; border-color: #c8e6c9; }}
  .box.del {{ background: #ffebee; border-color: #ffcdd2; }}
  a {{ color: #1565c0; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;
    color: #999; font-size: 0.8rem; }}
</style>
</head>
<body>
<p class="nav"><a href="index.html">&larr; shintowiki</a></p>
<h1>Awa Province, entry 3: a piped link stole 天神社</h1>
<p class="intro">The 927 register's Awa entry <strong>#3</strong> is a shrine called
<strong>天神社 (Tenjinsha)</strong>. On the jawiki list article that entry's link was
written as a <em>piped link</em> pointing at a different shrine —
<code>[[下立松原神社#白浜町の下立松原神社|下立松原神社]]</code> — and the import followed the
link instead of the entry name. So Wikidata now says Awa entry #3 <em>is</em>
Shimotachimatsubara (which is really entry #5, correctly there too). The
<strong>add</strong> putting Tenjinsha back at #3 is already queued; the leftover is a
by-hand <strong>delete</strong> of the wrong statement.</p>

<h2>The Awa sequence — Kokugakuin ids prove the swap</h2>
<p>The ids run contiguously; <strong>181734 is missing entirely</strong> from the list
and is held by {wd(TENJIN, "天神社")}, a complete entry item that carries
<strong>no list membership at all</strong>. Its slot was taken by the piped link.</p>
<table>
<thead><tr><th>ordinal</th><th>register entry</th><th>Kokugakuin id</th>
<th>what Wikidata says now</th><th>what it should say</th></tr></thead>
<tbody>
{seq_html}
</tbody></table>

<h2>The fix, in two halves</h2>
<div class="box add">
<p><strong>1. The add — already queued</strong> in <code>miscellaneous_edits.txt</code>,
behind the drip's conflict gate. It puts 天神社 back at ordinal 3:</p>
<pre><span class="add">{AWA_LIST}\tP527\t{TENJIN}\tP1545\t"3"</span></pre>
</div>
<div class="box del">
<p><strong>2. The delete — by hand.</strong> Remove the list's <code>has part</code> →
{wd(SHIMO, "下立松原神社")} statement <em>carrying ordinal 3</em> (keep the correct one at
ordinal 5). <strong>This cannot be a QuickStatement:</strong> two <code>has part</code>
statements on {wd(AWA_LIST)} share the value {wd(SHIMO)}, so a value-matched removal is
as likely to take the correct #5 as the wrong #3. It needs a by-hand delete of that one
specific statement — or the forthcoming sequential-misc mechanism, which runs
remove-then-add pairs safely.</p>
<pre><span class="del">- {AWA_LIST}  has part  {SHIMO}  (series ordinal 3)   &larr; delete this one</span>
  {AWA_LIST}  has part  {SHIMO}  (series ordinal 5)   &larr; keep</pre>
</div>

<p>Detail: <code>docs/engishiki_list_defects_2026-07.md §1</code>. Report only — the
delete is not automated; the add sits behind the conflict gate.</p>
<footer>Generated {now} by
<a href="https://github.com/EmmaLeonhart/shintowiki-scripts">shintowiki-scripts</a>
(<code>generate_awa_entry3_page.py</code>).</footer>
</body>
</html>"""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(render())
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
