"""The P958 reading queue: one page, every shrine whose section can only be read off the source.

Emma asked for this shape directly (2026-08-19): "One HTML page, all 228, work at your own rate."
Nothing tracks progress, nothing chases, nothing is batched into artificial sprints.

WHY A READING QUEUE AT ALL. A shrine's P958 is the index of its 論社 block on the Kokugakuin page
(現社名など（１）（２）（３）…). For 57 items the index can be derived from a parent's P1352 ranking;
for these it cannot -- there is nothing in Wikidata to derive it from, so someone has to look at the
page. That is not a failure of tooling, it is where the data actually lives.

WHAT THE PAGE DOES. Each Kokugakuin page becomes one card showing every Wikidata item that claims
it, so the sections already taken are visible while choosing the missing one. Typing a section into
a box builds the QuickStatements line for it, live; one button copies every line entered so far.

The page emits QuickStatements TEXT. It performs no edits and needs no network. Submission is
governed by wikidata_editing_lockout.state (to 2026-09-18), which covers hand-run batches by its own
wording -- so lines can be prepared now and pasted when it lifts.

Usage:  python generate_p958_reading_queue.py
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import collections
import html
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DET = "https://jmapps.ne.jp/kokugakuin/det.html?data_id="
WD = "https://www.wikidata.org/wiki/"
AUDIT = _uos.path.join(_uar, "modern-quickstatements", "p958_candidates_audit.json")
DERIV = _uos.path.join(_uar, "modern-quickstatements", "p958_derivability.json")
OUT = _uos.path.join(_uar, "_site", "p958-reading-queue.html")

UNSET = {"0", "n/a"}


def esc(s):
    return html.escape(s) if s else "&mdash;"


def main():
    with open(DERIV, encoding="utf-8") as f:
        deriv = json.load(f)
    with open(AUDIT, encoding="utf-8") as f:
        audit = json.load(f)

    # the items that need reading: no ranking anywhere to derive from
    need = {(d["item"], d["kid"]): d.get("ja", "") for d in deriv["no_ranking"]}

    # every holder of each of those pages, so the taken sections are visible while choosing
    holders = collections.defaultdict(list)
    for cls, recs in audit.items():
        for rec in recs:
            kid = rec["kokugakuin_id"]
            for h in rec["holders"]:
                holders[kid].append((h["item"], h.get("ja") or "", h.get("section")))

    pages = collections.defaultdict(list)
    for (qid, kid), ja in need.items():
        pages[kid].append((qid, ja))

    cards = []
    for kid in sorted(pages, key=lambda k: int(k) if k.isdigit() else 0):
        rows = []
        for qid, ja, sec in sorted(holders.get(kid, []), key=lambda h: (h[2] is None, h[2] or "")):
            needs = (qid, kid) in need
            if needs:
                rows.append(
                    '<tr class="need"><td><a href="%s%s" target="_blank">%s</a></td>'
                    '<td lang="ja">%s</td><td class="cur">needs a section</td>'
                    '<td><input size="5" data-q="%s" data-k="%s" '
                    'placeholder="§" oninput="upd()"></td></tr>'
                    % (WD, qid, qid, esc(ja), qid, kid))
            else:
                cls = "unset" if sec in UNSET else ("ok" if sec else "bad")
                shown = esc(sec) if sec is not None else "<em>none</em>"
                rows.append(
                    '<tr><td><a href="%s%s" target="_blank">%s</a></td>'
                    '<td lang="ja">%s</td><td class="%s">%s</td><td></td></tr>'
                    % (WD, qid, qid, esc(ja), cls, shown))
        cards.append(
            '<div class="card"><h3><a href="%s%s" target="_blank">Kokugakuin page %s</a>'
            '<span class="n">%d item%s here, %d needing a section</span></h3>'
            '<table><thead><tr><th>item</th><th>ja</th><th>section (P958)</th>'
            '<th>set</th></tr></thead><tbody>%s</tbody></table></div>'
            % (DET, kid, esc(kid), len(holders.get(kid, [])),
               "" if len(holders.get(kid, [])) == 1 else "s", len(pages[kid]), "".join(rows)))

    style = (
        "body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1000px;margin:0 auto;"
        "padding:1.5rem;line-height:1.5;color:#222}"
        "h1{font-size:1.35rem;margin-bottom:.3rem}"
        ".intro{background:#f1f8e9;border-left:4px solid #558b2f;padding:.8rem 1rem;"
        "border-radius:0 4px 4px 0;margin:1rem 0 1.5rem}"
        ".card{border:1px solid #ddd;border-radius:6px;padding:.7rem 1rem;margin:.8rem 0}"
        ".card h3{font-size:1rem;margin:0 0 .45rem;display:flex;justify-content:space-between;"
        "align-items:baseline;gap:1rem}"
        ".n{color:#777;font-weight:400;font-size:.82rem;white-space:nowrap}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{text-align:left;padding:.25rem .5rem;border-bottom:1px solid #f0f0f0;font-size:.92rem}"
        "tr.need{background:#fffde7}.cur{color:#d32f2f;font-weight:600}"
        ".unset{color:#ef6c00}.ok{color:#2e7d32}.bad{color:#d32f2f}"
        "input{font:inherit;padding:.15rem .3rem;border:1px solid #bbb;border-radius:3px}"
        "#out{position:sticky;bottom:0;background:#263238;color:#eee;padding:.7rem 1rem;"
        "border-radius:6px 6px 0 0;margin-top:2rem}"
        "#out textarea{width:100%;height:7rem;font-family:ui-monospace,Consolas,monospace;"
        "font-size:.82rem;background:#12191c;color:#cfd8dc;border:0;border-radius:4px;padding:.5rem}"
        "#out button{font:inherit;padding:.3rem .8rem;border-radius:4px;border:0;background:#8bc34a;"
        "cursor:pointer;margin-top:.4rem}")

    script = (
        "function upd(){var out=[];"
        "document.querySelectorAll('input[data-q]').forEach(function(i){"
        "var v=i.value.trim(); if(!v) return;"
        "out.push(i.dataset.q+'|P13677|\"'+i.dataset.k+'\"|P958|\"'+v+'\"');});"
        "document.getElementById('qs').value=out.join('\\n');"
        "document.getElementById('cnt').textContent=out.length;}"
        "function cp(){var t=document.getElementById('qs');t.select();"
        "document.execCommand('copy');}")

    intro = (
        "<b>%d shrines across %d Kokugakuin pages.</b> Their P958 section is the index of their "
        "<code>現社名など（N）</code> block on the Kokugakuin page, and there is nothing in "
        "Wikidata to derive it from — so it has to be read off the source.<br><br>"
        "Each card shows <em>every</em> item on that page, so the sections already taken are visible "
        "while choosing. Type a number (or <code>n/a</code>) into a yellow row and the QuickStatements "
        "line builds at the bottom.<br><br>"
        "<b>Nothing here edits anything</b>, and nothing tracks whether you have done any of it. "
        "Submission waits on the Wikidata lockout to 2026-09-18."
        % (len(need), len(pages)))

    doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>P958 reading queue</title><style>%s</style></head><body>'
           '<h1>P958 reading queue</h1><div class="intro">%s</div>%s'
           '<div id="out"><b>QuickStatements — <span id="cnt">0</span> line(s)</b>'
           '<textarea id="qs" readonly></textarea>'
           '<button onclick="cp()">copy</button></div>'
           '<script>%s</script></body></html>' % (style, intro, "".join(cards), script))

    _uos.makedirs(_uos.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print("%d shrines needing a read, across %d pages -> %s" % (len(need), len(pages), OUT))


if __name__ == "__main__":
    main()
