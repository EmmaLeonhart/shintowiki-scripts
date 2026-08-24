"""Build the kana-review page for GitHub Pages.

Emma asked for a page rather than the JSON: *"i wanted github pages for the thing lol check open
questions you made weird ass unreadable github json."* Fair — `en_label_without_kana.json` is a
machine artefact and she has to read this to make rulings on it.

Reads `en_label_without_kana.json` (written by `report_en_label_without_kana.py`) and writes
`_site/kana-review.html`, which `generate-pages.yml` copies into the published site.

What it has to show, because these are the things that actually decide a ruling:

  * whether a pair's name-mates AGREE, and how many of them there are;
  * for a disagreeing pair, the FULL vote — one dominant reading with a two-item tail is a
    different thing from a real 47/19 split, and a bare "4 distinct readings" count hides that;
  * that a reading cited to the National Tax Agency corporate registry is LEGALLY REGISTERED and
    must not be overwritten. That rule was discovered late, after three pairs had already been
    ruled "clear typo, overwrite" when they were 11-of-11 legally sourced.

No Wikidata calls; it renders what the report already measured.

Usage:
    python modern-quickstatements/generate_kana_review_page.py
"""
import html
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "en_label_without_kana.json")
OUT_DIR = os.path.join(HERE, "_site")
OUT = os.path.join(OUT_DIR, "kana-review.html")

CSS = """
:root { color-scheme: light dark; --fg:#1a1a1a; --bg:#fff; --mut:#666; --line:#ddd;
        --warn:#b45309; --ok:#15803d; --card:#f7f7f8; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e8e8e8; --bg:#16181c; --mut:#9aa0a6; --line:#333; --card:#1f2227; } }
* { box-sizing: border-box; }
body { margin:0; padding:2rem 1.25rem 4rem; background:var(--bg); color:var(--fg);
       font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",
       "Hiragino Kaku Gothic ProN","Yu Gothic",Meiryo,sans-serif; }
.wrap { max-width: 1100px; margin: 0 auto; }
h1 { font-size:1.6rem; margin:0 0 .25rem; }
h2 { font-size:1.15rem; margin:2.5rem 0 .75rem; padding-bottom:.3rem;
     border-bottom:1px solid var(--line); }
.sub { color:var(--mut); margin:0 0 2rem; }
.cards { display:flex; flex-wrap:wrap; gap:.75rem; margin:1.5rem 0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px;
        padding:.8rem 1rem; min-width:150px; flex:1; }
.card .n { font-size:1.7rem; font-weight:650; display:block; line-height:1.2; }
.card .l { color:var(--mut); font-size:.85rem; }
.note { background:var(--card); border-left:3px solid var(--warn); border-radius:0 6px 6px 0;
        padding:.9rem 1.1rem; margin:1.25rem 0; }
.note strong { color:var(--warn); }
table { border-collapse:collapse; width:100%; font-size:.93rem; }
th,td { text-align:left; padding:.45rem .6rem; border-bottom:1px solid var(--line);
        vertical-align:top; }
th { font-weight:600; color:var(--mut); font-size:.82rem; text-transform:uppercase;
     letter-spacing:.03em; position:sticky; top:0; background:var(--bg); }
td.n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.ja { font-size:1.05rem; }
.kana { font-size:1rem; }
.top { font-weight:650; }
.tail { color:var(--mut); }
.agree { color:var(--ok); font-weight:600; }
.split { color:var(--warn); font-weight:600; }
code { background:var(--card); padding:.1rem .35rem; border-radius:4px; font-size:.88em; }
footer { margin-top:3rem; color:var(--mut); font-size:.85rem;
         border-top:1px solid var(--line); padding-top:1rem; }
"""


def vote_html(readings):
    """The full vote, dominant first — the thing a 'distinct readings' count hides."""
    out = []
    for i, (kana, n) in enumerate(readings):
        cls = "top" if i == 0 else "tail"
        out.append('<span class="%s kana">%s</span><span class="tail">&times;%d</span>'
                   % (cls, html.escape(kana), n))
    return " &nbsp; ".join(out)


def main():
    with io.open(DATA, encoding="utf-8") as fh:
        d = json.load(fh)

    pairs = sorted(d["pairs"], key=lambda p: -p["support"])
    agree = [p for p in pairs if p["distinct_readings"] == 1]
    split = [p for p in pairs if p["distinct_readings"] > 1]

    rows = []
    for p in split:
        rows.append(
            "<tr><td class='ja'>%s</td><td>%s</td><td class='n'>%d</td>"
            "<td class='n'>%d</td><td>%s</td></tr>"
            % (html.escape(p["ja"]), html.escape(p["en"]), len(p["items"]),
               p["support"], vote_html(p["readings"])))
    split_rows = "\n".join(rows)

    rows = []
    for p in agree[:200]:
        rows.append(
            "<tr><td class='ja'>%s</td><td>%s</td><td class='n'>%d</td>"
            "<td class='n'>%d</td><td class='kana top'>%s</td></tr>"
            % (html.escape(p["ja"]), html.escape(p["en"]), len(p["items"]),
               p["support"], html.escape(p["kana"])))
    agree_rows = "\n".join(rows)

    doc = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kana review — shrines with an English label and no reading</title>
<style>%s</style></head><body><div class="wrap">

<h1>Kana review</h1>
<p class="sub">Shrines that have an English label but no <code>name in kana</code> (P1814),
and what their name-mates read. The unit is the <strong>(kanji, English) pair</strong>, not the
English alone.</p>

<div class="cards">
  <div class="card"><span class="n">%s</span><span class="l">items with no reading</span></div>
  <div class="card"><span class="n">%s</span><span class="l">distinct pairs</span></div>
  <div class="card"><span class="n">%s</span><span class="l">a majority could fill</span></div>
  <div class="card"><span class="n">%s</span><span class="l">name-mates unanimous</span></div>
  <div class="card"><span class="n">%s</span><span class="l">no name-mate at all</span></div>
</div>

<div class="note">
<strong>Before overwriting anything:</strong> a reading cited to
<code>houjin-bangou.nta.go.jp</code> — Japan's National Tax Agency corporate-number registry — is
the corporation's <em>legally registered</em> &#x30D5;&#x30EA;&#x30AC;&#x30CA;.
<strong>4,764 statements across 4,763 items</strong> carry that citation, and several readings that
look like obvious typos are among them
(&#x3059;&#x308F;&#x3058;&#x3093;&#x3057;&#x3083; is 11 of 11 sourced).
Cited &#8594; preserve. Uncited &#8594; fix.
</div>

<h2>Pairs where the name-mates disagree &mdash; %d</h2>
<p class="sub">The full vote, dominant reading first. Most are one reading plus a tail of typos or
Old&nbsp;Japanese katakana; a genuine split looks different and is rare.</p>
<table><thead><tr><th>kanji</th><th>English</th><th>need it</th><th>support</th>
<th>readings</th></tr></thead><tbody>
%s
</tbody></table>

<h2>Pairs where every name-mate agrees &mdash; %d</h2>
<p class="sub">The safe end. Showing the %d best-supported.</p>
<table><thead><tr><th>kanji</th><th>English</th><th>need it</th><th>support</th>
<th>reading</th></tr></thead><tbody>
%s
</tbody></table>

<footer>
Generated by <code>modern-quickstatements/generate_kana_review_page.py</code> from
<code>en_label_without_kana.json</code>. Rulings live in
<code>docs/kana_name_mate_rulings.md</code>. Nothing on this page is staged for Wikidata.
</footer>
</div></body></html>
""" % (CSS,
       "{:,}".format(d["items_missing_kana"]),
       "{:,}".format(len(pairs) + 0 or len(pairs)),
       "{:,}".format(d["covered_by_majority"]),
       "{:,}".format(d["unanimous"]),
       "{:,}".format(d["no_supported_name_mate"]),
       len(split), split_rows,
       len(agree), min(200, len(agree)), agree_rows)

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)
    print("wrote %s  (%d disagreeing pairs, %d unanimous)" % (OUT, len(split), len(agree)))


if __name__ == "__main__":
    main()
