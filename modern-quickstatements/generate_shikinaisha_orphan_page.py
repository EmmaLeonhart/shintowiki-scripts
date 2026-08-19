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

from report_orphan_shikinaisha import gather, normalise, dup_key

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
OUT = os.path.join(REPO_ROOT, "_site", "shikinaisha-orphans.html")

WD = "https://www.wikidata.org/wiki/"


def twins_of(q, claimed_lists, parts_of, ja_label, kok_keys, ids_of_named):
    """The named entry QIDs this orphan is a twin of, with the match reason.

    Mirrors report_orphan_shikinaisha.classify but RETURNS the matching entries
    rather than a one-line label, so the page can link the pair.

    Matches on the COMPOSITE key (P13677 + section P958) -- see dup_key. It used to
    match on the bare id, which is not an identity: one Kokugakuin page carries many
    entries, and section 0 is exempt from uniqueness entirely."""
    out = {}  # qid -> reason
    # Kokugakuin twins: a named entry sharing an (id, section) key that can prove identity.
    for kk in kok_keys.get(q, ()):
        dk = dup_key(*kk)
        if not dk:
            continue
        for e in ids_of_named.get(dk, []):
            if e != q:
                out.setdefault(e, "same Kokugakuin id + section")
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
     list_label, parts_of, dup_ids, kok_keys) = gather()

    ids_of_named = collections.defaultdict(list)
    for q, keys in kok_keys.items():
        if q in parts:
            for kk in keys:
                dk = dup_key(*kk)
                if dk:
                    ids_of_named[dk].append(q)
    # Every confirmed Shikinaisha carrying each Kokugakuin id (named entries AND
    # living-shrine items) — so we can spot an id that several shrines claim.
    holders_of_id = collections.defaultdict(list)
    for q, keys in kok_keys.items():
        if q in confirmed:
            for k, sec in keys:
                holders_of_id[k].append((q, sec))

    orphans = sorted(confirmed - parts)
    rows = []
    for q in orphans:
        cl = claims.get(q, [])
        tw = twins_of(q, cl, parts_of, ja_label, kok_keys, ids_of_named)
        mine = ja_label.get(q, "")
        # A twin found by (normalised) NAME means the two items are the same shrine
        # under one name — a clean living/entry duplicate.
        name_twins = {e: r for e, r in tw.items()
                      if r in ("same ja label", "same normalised ja label")}
        # A twin found ONLY by shared Kokugakuin id, whose name differs, is the
        # jawiki<->Kokugakuin-DB *disagreement*: the list names one shrine for that
        # entry, the DB id is carried by a different-named (or several) shrine(s).
        id_twins = {e: r for e, r in tw.items() if r == "same Kokugakuin id + section"}
        for e in list(id_twins):
            if mine and normalise(ja_label.get(e, "")) == normalise(mine):
                name_twins[e] = "same Kokugakuin id + section + same name"
                del id_twins[e]
        # Competing claimants: for each shared id that names an entry, every
        # confirmed Shikinaisha that also holds it (the "who else claims this" set).
        # This one IS legitimately id-level: "how many shrines point at this Kokugakuin
        # page" is a question about the page, not about an entry on it. The section is
        # carried through so a shared page with DIFFERENT sections is visibly not a
        # conflict -- which, per the 2026-08-19 check, is what most of them are.
        claimants = {}
        for k in kokugakuin.get(q, []):
            holders = holders_of_id.get(k, [])
            if len(holders) > 1:
                claimants[k] = [(h, h in parts, sec) for h, sec in holders]
        if name_twins:
            diag = "duplicate"
        elif id_twins:
            diag = "disputed"
        elif tw:
            diag = "duplicate"
        else:
            diag = "notwin"
        rows.append({
            "q": q,
            "ja": mine,
            "en": en_label.get(q, ""),
            "koku": kokugakuin.get(q, []),
            "claims": [list_label.get(l, l) for l in cl],
            "twins": tw,
            "name_twins": name_twins,
            "id_twins": id_twins,
            "claimants": claimants,
            "diag": diag,
        })
    return rows, ja_label


def _koku_link(k):
    return (f'<a href="https://jmapps.ne.jp/kokugakuin/det.html?data_id={k}" '
            f'target="_blank">{esc(k)}</a>')


def render(rows, ja_label):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    dup = [r for r in rows if r["diag"] == "duplicate"]
    dis = [r for r in rows if r["diag"] == "disputed"]
    notwin = [r for r in rows if r["diag"] == "notwin"]

    def koku_cell(r):
        return ", ".join(_koku_link(k) for k in r["koku"]) or "—"

    def claims_cell(r):
        return esc(", ".join(r["claims"])) if r["claims"] else "<em>claims no list</em>"

    def search_attr(r):
        return esc(f'{r["q"]} {r["ja"]} {r["en"]} {" ".join(r["claims"])}').lower()

    def dup_row(r):
        twins = "<br>".join(
            f'{wd_link(e, ja_label.get(e) or e)} <span class="reason">({esc(reason)})</span>'
            for e, reason in r["twins"].items()) or "—"
        return (f'<tr class="dup" data-search="{search_attr(r)}">'
                f'<td>{wd_link(r["q"])}</td><td lang="ja">{esc(r["ja"])}</td>'
                f'<td>{esc(r["en"])}</td><td>{koku_cell(r)}</td>'
                f'<td>{claims_cell(r)}</td><td>{twins}</td></tr>')

    def dis_row(r):
        # the differently-named entry(ies) the list uses for this id
        entry = "<br>".join(
            f'{wd_link(e, ja_label.get(e) or e)}' for e in r["id_twins"]) or "—"
        # everyone (confirmed) who claims a shared id → the size of the dispute
        claim_bits = []
        for k, holders in r["claimants"].items():
            names = ", ".join(
                wd_link(h, ja_label.get(h) or h)
                + f' <span class="reason">§{esc(sec or "no section")}</span>'
                + (" <span class=\"reason\">‹named entry›</span>" if is_named else "")
                for h, is_named, sec in holders if h != r["q"])
            claim_bits.append(f'{_koku_link(k)}: <strong>{len(holders)}</strong> claim it — {names}')
        claim_html = "<br>".join(claim_bits) or "—"
        return (f'<tr class="dis" data-search="{search_attr(r)}">'
                f'<td>{wd_link(r["q"])}</td><td lang="ja">{esc(r["ja"])}</td>'
                f'<td>{esc(r["en"])}</td><td>{koku_cell(r)}</td>'
                f'<td>{claims_cell(r)}</td><td>{entry}</td>'
                f'<td>{claim_html}</td></tr>')

    def notwin_row(r):
        return (f'<tr class="orphan" data-search="{search_attr(r)}">'
                f'<td>{wd_link(r["q"])}</td><td lang="ja">{esc(r["ja"])}</td>'
                f'<td>{esc(r["en"])}</td><td>{koku_cell(r)}</td>'
                f'<td>{claims_cell(r)}</td></tr>')

    dup_rows = "\n".join(dup_row(r) for r in dup)
    dis_rows = "\n".join(dis_row(r) for r in dis)
    notwin_rows = "\n".join(notwin_row(r) for r in notwin)

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
  .card.warn .n {{ color: #e65100; }}
  .card .l {{ font-size: 0.8rem; color: #555; }}
  input#filter {{ width: 100%; padding: 0.6rem; font-size: 1rem; margin: 1rem 0;
    border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 0.4rem 0.55rem; text-align: left;
    vertical-align: top; }}
  th {{ background: #f1f8e9; position: sticky; top: 0; }}
  tr.dup td:first-child {{ border-left: 3px solid #4caf50; }}
  tr.dis td:first-child {{ border-left: 3px solid #d32f2f; }}
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
the 927 register entries (unlike a <em>Ronsha</em>, a disputed candidate). {len(rows)} carry the
confirmed class yet appear on no list. They fall into three kinds, diagnosed below:
<br>&bull; <strong>{len(dup)} living/entry duplicates</strong> — a separate item, already named by a
list, is the <em>same shrine</em> under the same name (matched by name, or by Kokugakuin id + same
name). The living item only <em>looks</em> unnamed because the list names its entry twin. → link or merge.
<br>&bull; <strong style="color:#d32f2f">{len(dis)} Kokugakuin-id disagreements</strong> — the item
shares a Kokugakuin database id with a <em>differently-named</em> entry, and/or that id is claimed by
<em>several</em> shrines. This is jawiki and the Kokugakuin database <em>disagreeing on which modern
shrine is the 927 entry</em> — <strong>do NOT blind-merge these</strong>; they need an identification call.
<br>&bull; <strong>{len(notwin)} no twin</strong> — no entry shares its id or name: a mis-tagged modern
shrine, or a genuine entry the lists are missing.
<br>Report only — nothing here is edited on Wikidata.</p>

<div class="counts">
  <div class="card"><div class="n">{len(rows)}</div><div class="l">total unnamed</div></div>
  <div class="card"><div class="n">{len(dup)}</div><div class="l">living/entry duplicate (link/merge)</div></div>
  <div class="card warn"><div class="n">{len(dis)}</div><div class="l">Kokugakuin-id disagreement (identify)</div></div>
  <div class="card"><div class="n">{len(notwin)}</div><div class="l">no twin (mis-tag or missing)</div></div>
</div>

<input id="filter" type="text" placeholder="Filter by QID, Japanese/English name, or list…"
  oninput="filt()">

<h2 style="color:#d32f2f;border-color:#ffcdd2">{len(dis)} Kokugakuin-id disagreements — jawiki vs the Kokugakuin database</h2>
<p>The list names one shrine as the entry; the same Kokugakuin id is carried by a
<em>different-named</em> shrine (this item), or by several shrines at once. The last column shows
everyone who claims each shared id — the size of the dispute. These are identification calls, not
merges.</p>
<div class="table-wrap"><table>
<thead><tr><th>this item (living)</th><th>ja</th><th>en</th><th>Kokugakuin id</th>
<th>claims list</th><th>list names this entry</th><th>who claims the shared id</th></tr></thead>
<tbody>
{dis_rows}
</tbody></table></div>

<h2>{len(dup)} living/entry duplicates — link or merge each pair</h2>
<div class="table-wrap"><table>
<thead><tr><th>item</th><th>ja</th><th>en</th><th>Kokugakuin id</th><th>claims list</th>
<th>twin (already named)</th></tr></thead>
<tbody>
{dup_rows}
</tbody></table></div>

<h2>{len(notwin)} with no twin — mis-tagged shrine, or entry the list is missing</h2>
<div class="table-wrap"><table>
<thead><tr><th>item</th><th>ja</th><th>en</th><th>Kokugakuin id</th><th>claims list</th></tr></thead>
<tbody>
{notwin_rows}
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
    import collections
    c = collections.Counter(r["diag"] for r in rows)
    print(f"{len(rows)} orphans: {c['duplicate']} duplicate / {c['disputed']} "
          f"Kokugakuin-id disagreement / {c['notwin']} no-twin -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
