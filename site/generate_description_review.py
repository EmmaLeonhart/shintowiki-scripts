"""Build a browsable page for the 63 undescribed Engishiki items, for Emma to look at.

Emma, 2026-08-21, asked which description shape these should get and answered:
*"Use command line to force open all of them so I can look at them. I am still unsure where
they are or what they are."*

So this answers "where" and "what" directly, on one page rather than 63 browser tabs:

  WHAT   -- class, the historical P1448 name, the Jinmyōchō list it belongs to, its
            Kokugakuin id, and every SIBLING in its group WITH that sibling's existing
            description. The siblings are the real answer to "what are these": they are the
            same class of thing, already described, and 11 of 13 use the register position.
  WHERE  -- the ancient province/district from P131, AND the actual coordinates where the
            item has them, linked to OpenStreetMap. Half of these carry real coordinates, so
            "where" has a concrete answer for them rather than only an ancient district name.

Each card shows the two candidate descriptions side by side, built from that item's own data,
so the choice is made against real strings rather than a description of the choice.

Read-only, offline: it consumes `description_enrichment_en/_evidence.json` (written by
`shinto_miraheze/fetch_description_evidence.py`) plus the work-files themselves. No network.

Usage:
    python site/generate_description_review.py [--out _site/description-review.html]
"""
import argparse
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVIDENCE = os.path.join(ROOT, "description_enrichment_en", "_evidence.json")
WORKDIR = os.path.join(ROOT, "description_enrichment_en")
DEFAULT_OUT = os.path.join(ROOT, "_site", "description-review.html")

MEMBER_RE = re.compile(
    r"^\*\s*\[\[d:(Q\d+)\]\]\s*—\s*(.*?)$", re.M)
DESC_RE = re.compile(r"EXISTING en desc: '(.*?)'")


def group_members(work_file):
    """-> [(qid, raw_line, existing_desc_or_None)] for every member of the group."""
    body = io.open(os.path.join(WORKDIR, work_file), encoding="utf-8").read()
    out = []
    for qid, rest in MEMBER_RE.findall(body):
        m = DESC_RE.search(rest)
        out.append((qid, rest.strip(), m.group(1) if m else None))
    return out


def location_phrase(row):
    """The ancient-geography string, exactly as the location option would produce it."""
    parts = [p for p in row.get("P131_in", []) if p]
    # P131 comes back province-first; a description reads smallest-first.
    parts = list(reversed(parts))
    country = (row.get("P17_country") or ["Japan"])[0]
    if parts:
        return "Shinto shrine in %s, %s" % (", ".join(parts), country)
    return "Shinto shrine in %s" % country


def coords_of(row):
    return row.get("_coords")


def card(row, members):
    qid = row["qid"]
    en = row.get("en_label") or ""
    ja = row.get("ja_label") or ""
    sibs = [(q, line, d) for q, line, d in members if q != qid]

    sib_html = ""
    if sibs:
        rows_ = []
        for q, line, d in sibs:
            desc = ('<span class="have">%s</span>' % html.escape(d)) if d else \
                   '<span class="none">(no description)</span>'
            rows_.append(
                '<tr><td><a href="https://www.wikidata.org/wiki/%s" target="_blank">%s</a></td>'
                '<td>%s</td></tr>' % (q, q, desc))
        sib_html = ('<div class="sibs"><div class="lbl">Siblings sharing this label — how '
                    'they are already described</div><table>%s</table></div>'
                    % "".join(rows_))

    where_bits = []
    prov = ", ".join(reversed([p for p in row.get("P131_in", []) if p]))
    if prov:
        where_bits.append('<b>P131 (ancient):</b> %s' % html.escape(prov))
    c = coords_of(row)
    if c:
        where_bits.append(
            '<b>coordinates:</b> <a href="https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=15/%s/%s"'
            ' target="_blank">%.5f, %.5f — open map</a>' % (c[0], c[1], c[0], c[1], c[0], c[1]))
    else:
        where_bits.append('<span class="none">no coordinates on the item</span>')
    for site, title in sorted((row.get("sitelinks") or {}).items()):
        if site.endswith("wiki") and len(site) <= 8:
            where_bits.append('<b>%s:</b> <a href="https://%s.wikipedia.org/wiki/%s" '
                              'target="_blank">%s</a>'
                              % (site, site[:-4], html.escape(title.replace(" ", "_")),
                                 html.escape(title)))

    what_bits = []
    if row.get("P31_class"):
        what_bits.append('<b>class:</b> %s' % html.escape(", ".join(row["P31_class"])))
    if row.get("_p1448"):
        what_bits.append('<b>historical name (P1448):</b> %s' % html.escape(row["_p1448"]))
    if row.get("_list"):
        what_bits.append('<b>listed in:</b> %s' % html.escape(row["_list"]))
    if row.get("_kokugakuin"):
        what_bits.append('<b>Kokugakuin id:</b> <a href="https://d-museum.kokugakuin.ac.jp/eos/'
                         'detail/?id=%s" target="_blank">%s</a>'
                         % (row["_kokugakuin"], row["_kokugakuin"]))
    if row.get("P825_deity"):
        what_bits.append('<b>deity:</b> %s' % html.escape(", ".join(row["P825_deity"])))

    return """
<div class="card">
  <h2><a href="https://www.wikidata.org/wiki/{qid}" target="_blank">{qid}</a>
      <span class="en">{en}</span> <span class="ja">{ja}</span></h2>
  <div class="col"><div class="lbl">WHAT it is</div>{what}</div>
  <div class="col"><div class="lbl">WHERE it is</div>{where}</div>
  {sibs}
  <div class="opts">
    <div class="opt"><div class="tag">A — ancient-province location</div>
      <code>{loc}</code></div>
    <div class="opt"><div class="tag">B — register position</div>
      <code class="unk">Ronsha N of &lt;parent&gt; — <em>N not on this item</em></code></div>
  </div>
</div>""".format(
        qid=qid, en=html.escape(en), ja=html.escape(ja),
        what="<br>".join(what_bits) or "&mdash;",
        where="<br>".join(where_bits),
        sibs=sib_html,
        loc=html.escape(location_phrase(row)))


CSS = """
:root{--bg:#fbfaf7;--fg:#1b1a17;--mut:#6b6660;--line:#e0dbd2;--card:#fff;--acc:#8a5a2b}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#14130f;--fg:#ece7dd;--mut:#9a938a;--line:#2e2b25;--card:#1c1a16;--acc:#d3a15f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;padding:2rem 1.2rem}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .3rem}
.intro{color:var(--mut);margin:0 0 1.6rem;max-width:70ch}
.intro b{color:var(--fg)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:1rem 1.1rem;margin:0 0 1rem}
.card h2{font-size:1.02rem;margin:0 0 .7rem;font-weight:600}
.card h2 a{color:var(--acc);text-decoration:none;font-family:ui-monospace,monospace;font-size:.9rem}
.en{margin-left:.5rem}
.ja{margin-left:.4rem;color:var(--mut);font-weight:400}
.col{margin:0 0 .6rem;font-size:.88rem}
.lbl{color:var(--mut);font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;margin-bottom:.25rem}
.sibs{margin:.7rem 0;padding-top:.6rem;border-top:1px solid var(--line)}
.sibs table{border-collapse:collapse;font-size:.85rem;width:100%}
.sibs td{padding:.18rem .5rem .18rem 0;vertical-align:top}
.sibs a{color:var(--acc)}
.have{color:var(--fg)}
.none{color:var(--mut);font-style:italic}
.opts{display:grid;grid-template-columns:1fr 1fr;gap:.7rem;margin-top:.8rem;
padding-top:.7rem;border-top:1px solid var(--line)}
@media(max-width:700px){.opts{grid-template-columns:1fr}}
.tag{font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mut);margin-bottom:.25rem}
code{display:block;background:var(--bg);border:1px solid var(--line);border-radius:6px;
padding:.45rem .6rem;font-family:ui-monospace,monospace;font-size:.82rem;overflow-x:auto}
code.unk{color:var(--mut)}
"""


def main(argv=None):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rows = json.load(io.open(EVIDENCE, encoding="utf-8"))
    cards = []
    for row in rows:
        members = group_members(row["work_file"]) if row.get("work_file") else []
        cards.append(card(row, members))

    n_coords = sum(1 for r in rows if r.get("_coords"))
    intro = ("<b>%d Engishiki items with no English description.</b> Each card shows what the "
             "item is, where it is (ancient province from P131, plus real coordinates where "
             "the item has them &mdash; %d of %d do), the siblings that share its label "
             "<i>with their existing descriptions</i>, and the two candidate description "
             "shapes built from that item's own data. The siblings are the useful part: they "
             "are the same class of thing and already described, and most use the register "
             "position rather than a location."
             % (len(rows), n_coords, len(rows)))

    doc = ("<!doctype html><html><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           "<title>Undescribed Engishiki items</title><style>%s</style></head><body>"
           "<div class='wrap'><h1>Undescribed Engishiki items</h1>"
           "<p class='intro'>%s</p>%s</div></body></html>"
           % (CSS, intro, "".join(cards)))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    io.open(args.out, "w", encoding="utf-8", newline="\n").write(doc)
    print("wrote %s (%d cards, %d with coordinates)"
          % (os.path.relpath(args.out, ROOT), len(rows), n_coords))
    return 0


if __name__ == "__main__":
    sys.exit(main())
