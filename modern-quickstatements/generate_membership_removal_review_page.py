"""A readable page for the 816 membership removals, so Emma can see them before they deliver.

Emma, 2026-08-25, asked to see one batch before it goes out. This is the one worth showing: it is
the largest, and it is the only staged batch that **removes** statements — 829 lines against 816
items. A `.txt` full of `-Q135038751|P361|Q11467693` is not something anyone can judge.

**What the batch does, in words.** Each line removes a `part of` statement from a MODERN shrine
pointing into a 神名帳 list. List membership belongs to the **register entry**, not to the modern
shrine identified with it; the shrine expresses that identification as `P460 → entry`. A shrine
holding both is import damage, and the repo has a documented test for it.

**Why 816 and not the 2,151 already staged.** `list_membership_removals.txt` implements the same
rule but its population was selected AS RONSHA, so it has always been narrower than the rule it
implements. 2,788 items meet the rule; 2,008 were already staged; these are the rest.

**The removal is value-matched, and that is intended.** Emma: *"every single membership thing on
those items should be removed unless the membership of the Shikinaisha list is 100% accurate and is
100% what we want. We remove it and then we add it again."* So an affected item loses ALL of its
`part of` into that list, not only the statement that tripped the test. **The page shows exactly how
many statements each removal actually takes**, since that is the part a line of QuickStatements
hides.

Reads labels through the Wikidata API in batches (not SPARQL — this is lookup, not a sweep), paced
by the shared `wd_pace`. Writes `_site/membership-removals.html`.

Usage:
    python modern-quickstatements/generate_membership_removal_review_page.py
"""
import collections
import html
import io
import json
import os
import sys
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.wd_pace import wd_pace, READ_INTERVAL

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BATCH = os.path.join(HERE, "orphan_membership_removals.txt")
OUT_DIR = os.path.join(REPO, "_site")
OUT = os.path.join(OUT_DIR, "membership-removals.html")
API = "https://www.wikidata.org/w/api.php"

CSS = """
:root { color-scheme: light dark; --fg:#1a1a1a; --bg:#fff; --mut:#666; --line:#ddd;
        --warn:#b45309; --bad:#b91c1c; --card:#f7f7f8; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e8e8e8; --bg:#16181c; --mut:#9aa0a6; --line:#333; --card:#1f2227; } }
* { box-sizing: border-box; }
body { margin:0; padding:2rem 1.25rem 4rem; background:var(--bg); color:var(--fg);
       font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
       "Hiragino Kaku Gothic ProN","Yu Gothic",Meiryo,sans-serif; }
.wrap { max-width:1100px; margin:0 auto; }
h1 { font-size:1.6rem; margin:0 0 .25rem; }
h2 { font-size:1.1rem; margin:2.2rem 0 .6rem; padding-bottom:.3rem;
     border-bottom:1px solid var(--line); }
.sub { color:var(--mut); margin:0 0 1.5rem; }
.cards { display:flex; flex-wrap:wrap; gap:.75rem; margin:1.5rem 0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px;
        padding:.8rem 1rem; min-width:150px; flex:1; }
.card .n { font-size:1.7rem; font-weight:650; display:block; line-height:1.2; }
.card .l { color:var(--mut); font-size:.85rem; }
.note { background:var(--card); border-left:3px solid var(--warn); border-radius:0 6px 6px 0;
        padding:.9rem 1.1rem; margin:1.25rem 0; }
.note strong { color:var(--warn); }
table { border-collapse:collapse; width:100%; font-size:.93rem; }
th,td { text-align:left; padding:.4rem .6rem; border-bottom:1px solid var(--line);
        vertical-align:top; }
th { font-weight:600; color:var(--mut); font-size:.8rem; text-transform:uppercase;
     letter-spacing:.03em; }
td.n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
a { color:inherit; }
.multi { color:var(--bad); font-weight:650; }
details { margin:.5rem 0 1.4rem; }
summary { cursor:pointer; font-weight:600; padding:.35rem 0; }
code { background:var(--card); padding:.1rem .35rem; border-radius:4px; font-size:.88em; }
footer { margin-top:3rem; color:var(--mut); font-size:.85rem;
         border-top:1px solid var(--line); padding-top:1rem; }
"""


def api(params):
    params = dict(params, format="json", formatversion="2")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    wd_pace(READ_INTERVAL)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def entities(qids, props):
    out = {}
    for i in range(0, len(qids), 50):
        out.update(api({"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
                        "props": props, "languages": "ja|en"})["entities"])
    return out


def label(ent):
    labs = (ent or {}).get("labels", {})
    return labs.get("ja", {}).get("value") or labs.get("en", {}).get("value") or ""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    pairs = []
    for line in io.open(BATCH, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.lstrip("-").split("|")
        if len(parts) >= 3:
            pairs.append((parts[0], parts[2]))

    items = sorted({i for i, _ in pairs})
    lists = sorted({l for _, l in pairs})
    print("removal pairs: %d  items: %d  lists: %d" % (len(pairs), len(items), len(lists)))

    print("fetching item claims + labels...")
    ents = entities(items, "labels|claims")
    print("fetching list labels...")
    list_ents = entities(lists, "labels")
    list_name = {q: label(e) for q, e in list_ents.items()}

    # How many statements each value-matched removal ACTUALLY takes, and what the
    # item's P460 says — the two things the QuickStatements line does not show.
    rows = []
    for item, lst in pairs:
        e = ents.get(item, {})
        claims = e.get("claims", {})
        n_taken = sum(
            1 for st in claims.get("P361", [])
            if (st["mainsnak"].get("datavalue") or {}).get("value", {}).get("id") == lst)
        entry = None
        for st in claims.get("P460", []):
            dv = st["mainsnak"].get("datavalue")
            if dv:
                entry = dv["value"]["id"]
                break
        rows.append({"item": item, "ja": label(e), "list": lst, "taken": n_taken, "entry": entry})

    by_list = collections.defaultdict(list)
    for r in rows:
        by_list[r["list"]].append(r)

    multi = [r for r in rows if r["taken"] > 1]
    no_entry = [r for r in rows if not r["entry"]]
    total_statements = sum(r["taken"] for r in rows)

    def esc(x):
        return html.escape(x or "")

    sections = []
    for lst in sorted(by_list, key=lambda l: -len(by_list[l])):
        rs = sorted(by_list[lst], key=lambda r: r["ja"] or r["item"])
        trs = []
        for r in rs:
            taken = ('<span class="multi">%d</span>' % r["taken"]) if r["taken"] > 1 else str(r["taken"])
            entry = ('<a href="https://www.wikidata.org/wiki/%s">%s</a>' % (r["entry"], r["entry"])
                     if r["entry"] else '<span class="multi">none</span>')
            trs.append(
                '<tr><td><a href="https://www.wikidata.org/wiki/%s">%s</a></td>'
                '<td>%s</td><td class="n">%s</td><td>%s</td></tr>'
                % (r["item"], r["item"], esc(r["ja"]), taken, entry))
        sections.append(
            '<details><summary>%s &mdash; %s &nbsp;<span style="font-weight:400;color:var(--mut)">'
            '%d shrines</span></summary>'
            '<table><thead><tr><th>item</th><th>name</th><th>statements removed</th>'
            '<th>P460 &rarr; entry</th></tr></thead><tbody>%s</tbody></table></details>'
            % (esc(list_name.get(lst, lst)),
               '<a href="https://www.wikidata.org/wiki/%s">%s</a>' % (lst, lst),
               len(rs), "\n".join(trs)))

    doc = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Membership removals &mdash; review before delivery</title>
<style>%s</style></head><body><div class="wrap">

<h1>Membership removals</h1>
<p class="sub">The staged batch <code>orphan_membership_removals.txt</code>, rendered so it can be
judged before it delivers. Nothing here has been sent to Wikidata; the lockout runs to
<strong>2026-09-18</strong>.</p>

<div class="cards">
  <div class="card"><span class="n">%s</span><span class="l">shrines affected</span></div>
  <div class="card"><span class="n">%s</span><span class="l">statements actually removed</span></div>
  <div class="card"><span class="n">%s</span><span class="l">lists involved</span></div>
  <div class="card"><span class="n">%s</span><span class="l">lose more than one statement</span></div>
  <div class="card"><span class="n">%s</span><span class="l">have no P460 entry</span></div>
</div>

<div class="note">
<strong>What each line does.</strong> It removes a <code>part of</code> statement from a
<em>modern shrine</em> pointing into a 神名帳 list. Membership belongs to the <em>register
entry</em>; the modern shrine says <code>P460 &rarr; entry</code> instead. An item holding both is
import damage.
<br><br>
<strong>The removal is value-matched, so it takes every matching statement on that item</strong> —
which is intended: <em>"every single membership thing on those items should be removed unless the
membership of the Shikinaisha list is 100%% accurate and is 100%% what we want. We remove it and
then we add it again."</em> The <em>statements removed</em> column is that count, and it is the
thing a QuickStatements line hides. Re-adding correct membership is the separate later job.
<br><br>
<strong>Rows with no P460</strong> are the ones worth a second look: without it, the claim that the
item is a modern shrine rather than a register entry rests on the list correspondence alone.
</div>

%s

<footer>
Generated by <code>modern-quickstatements/generate_membership_removal_review_page.py</code> from
<code>orphan_membership_removals.txt</code>. Generator:
<code>generate_orphan_membership_removals.py</code>. Nothing on this page has been delivered.
</footer>
</div></body></html>
""" % (CSS,
       "{:,}".format(len(items)),
       "{:,}".format(total_statements),
       "{:,}".format(len(lists)),
       "{:,}".format(len(multi)),
       "{:,}".format(len(no_entry)),
       "\n".join(sections))

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(doc)
    print("\nwrote %s" % OUT)
    print("  %d shrines, %d statements actually removed, %d lists"
          % (len(items), total_statements, len(lists)))
    print("  %d lose more than one statement; %d have no P460" % (len(multi), len(no_entry)))


if __name__ == "__main__":
    main()
