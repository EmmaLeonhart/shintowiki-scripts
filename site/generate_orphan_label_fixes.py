"""Build a page of generated labels that would FIX an orphan description.

Emma, 2026-09-06: *"a specific github pages page with all the Ukrainian labels we made for
shrines that have Ukrainian descriptions but no label. I guess really for any of our labels
that we made which would be applied to a shrine that has no label but has a description in
the language"* — so Ukrainian is the motivating case but the page is per-language.

WHAT THIS IS, AND WHY IT IS THE OTHER HALF OF AN EXISTING JOB
------------------------------------------------------------
`modern-quickstatements/audit_orphan_descriptions.py` already finds descriptions sitting on
items with no label in that language, and its answer is to REMOVE the description — correct,
because Wikidata's uniqueness constraint is on the (label, description) PAIR, so a
description with no label stakes the half that matters least and can get the eventual LABEL
edit rejected. A description with no label costs a label.

But removal is only the right answer when there is no label to be had. Where
`shinto-label-generator/` has ALREADY GENERATED a label for that exact item in that exact
language, the better move is step 2 of Emma's four-step path (`docs/description_label_policy.md`):
supply the missing label and keep the description. This page is that intersection — the
orphans we can fix rather than clear.

So the two scripts partition the same population and must not be confused:

    audit_orphan_descriptions.py  ->  orphans with NO generated label  ->  remove description
    this script                   ->  orphans WITH a generated label   ->  add the label

NETWORK: exactly ONE SPARQL request, and that is deliberate. `CLAUDE.md` names per-language
query fan-out as the thing that drew repeated 503/504 and got the pacing rule written; the
audit script solved it the same way, with one grouped query instead of a hundred. This asks
for (item, lang, description) in a single pass and does every join locally against the label
files already in the repo.

Read-only. It never edits Wikidata and never stages anything into the atomic files — it
renders a page and, per language, a paste-ready QuickStatements block. Delivery stays on the
one road: the daily drip.

Usage:
    python site/generate_orphan_label_fixes.py
    python site/generate_orphan_label_fixes.py --out _site/orphan-label-fixes.html
    python site/generate_orphan_label_fixes.py --cache _orphans.json   # reuse a prior query
"""
import argparse
import collections
import datetime
import glob
import html
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
SHRINE = "Q845945"
WDQS_THROTTLE = 2.5
LABEL_DIR = os.path.join(REPO_ROOT, "shinto-label-generator", "quickstatements")
SITE_DIR = os.path.join(REPO_ROOT, "_site")
PAGES_URL = "https://emmaleonhart.github.io/shintowiki-scripts"

# One request. Same shape as audit_orphan_descriptions.ALL_QUERY, plus the description text
# so the page can show what is actually sitting on the item — the whole point is judging
# whether our label belongs next to that description, which cannot be done from a QID.
ORPHAN_QUERY = """
SELECT ?item ?lang ?desc WHERE {
  ?item wdt:P31 wd:%s .
  ?item schema:description ?desc .
  BIND(LANG(?desc) AS ?lang)
  FILTER NOT EXISTS {
    ?item rdfs:label ?label .
    FILTER(LANG(?label) = LANG(?desc))
  }
}
""" % SHRINE


def sparql(query):
    url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode(
        {"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT,
        "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=600) as fh:
        data = json.load(fh)
    time.sleep(WDQS_THROTTLE)
    return data["results"]["bindings"]


def fetch_orphans():
    """[(qid, lang, description)] for every shrine description with no label in that lang."""
    out = []
    for row in sparql(ORPHAN_QUERY):
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        out.append((qid, row["lang"]["value"], row["desc"]["value"]))
    return out


def load_labels(langs):
    """{(qid, lang): label} from the generated QuickStatements files.

    Format is TAB-separated `Qxxx<TAB>L<lang><TAB>"text"`, with `# Source: ...` comment
    lines interleaved. The language is read from the FIELD, not from the filename: several
    files carry more than one language tag (the zh family especially), so trusting the
    filename would silently mis-attribute those rows.
    """
    want = set(langs)
    labels = {}
    for path in sorted(glob.glob(os.path.join(LABEL_DIR, "*.txt"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            qid, field, value = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if not qid.startswith("Q") or not field.startswith("L"):
                continue
            lang = field[1:]
            if lang not in want:
                continue
            labels[(qid, lang)] = value.strip('"')
    return labels


def esc(s):
    return html.escape(s or "", quote=True)


def render(rows_by_lang, orphan_counts, generated_at):
    total_fix = sum(len(v) for v in rows_by_lang.values())
    total_orphan = sum(orphan_counts.values())
    langs = sorted(rows_by_lang, key=lambda l: -len(rows_by_lang[l]))

    parts = []
    parts.append("""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Orphan descriptions we can fix with a label</title>
<style>
 :root{--fg:#222;--muted:#666;--line:#e0e0e0;--accent:#2e7d32;--warn:#b26a00;}
 body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--fg);
      margin:0 auto;padding:1rem;max-width:1100px;line-height:1.5;}
 h1{border-bottom:2px solid var(--accent);padding-bottom:.4rem;}
 h2{margin-top:2.2rem;border-bottom:1px solid var(--line);padding-bottom:.3rem;}
 .lede{background:#f6f6f6;border-left:4px solid var(--accent);padding:.8rem 1rem;
       border-radius:3px;}
 table{border-collapse:collapse;width:100%;font-size:.92rem;}
 th,td{border-bottom:1px solid var(--line);padding:.35rem .5rem;text-align:left;
       vertical-align:top;}
 th{background:#fafafa;position:sticky;top:0;}
 td.q{white-space:nowrap;font-family:ui-monospace,Consolas,monospace;}
 td.lab{font-weight:600;}
 .muted{color:var(--muted);}
 .counts{display:flex;flex-wrap:wrap;gap:.4rem;margin:1rem 0;}
 .chip{background:#eef4ee;border:1px solid #cfe0cf;border-radius:12px;
       padding:.15rem .6rem;font-size:.85rem;white-space:nowrap;}
 textarea{width:100%;height:9rem;font-family:ui-monospace,Consolas,monospace;
          font-size:.8rem;border:1px solid #ccc;border-radius:4px;padding:.5rem;}
 details{margin:.6rem 0;}
 summary{cursor:pointer;font-weight:600;}
 .wrap{overflow-x:auto;}
</style>
""")
    parts.append("<h1>Orphan descriptions we can fix with a label</h1>")
    parts.append(
        '<p class="lede">These are shrine items carrying a <b>description</b> in a language '
        'with <b>no label</b> in that language — and for which '
        '<code>shinto-label-generator/</code> has <b>already generated</b> the missing '
        'label.<br><br>'
        'On Wikidata the uniqueness constraint is on the <b>(label, description) pair</b>, so '
        'a description with no label stakes the half that matters least and can get the '
        'eventual label edit rejected: <b>a description with no label costs a label</b>. '
        '<code>audit_orphan_descriptions.py</code> therefore <i>removes</i> such '
        'descriptions. That is right only where no label exists. Every row below is an orphan '
        'we can <b>fix instead of clear</b> — step 2 of the four-step path in '
        '<code>docs/description_label_policy.md</code>.</p>')
    parts.append(
        '<p><b>{:,}</b> fixable rows across <b>{}</b> languages, out of <b>{:,}</b> orphan '
        'descriptions total. Generated {} — read-only, one SPARQL request.</p>'.format(
            total_fix, len(langs), total_orphan, esc(generated_at)))

    parts.append('<div class="counts">')
    for lang in langs:
        have = len(rows_by_lang[lang])
        tot = orphan_counts.get(lang, 0)
        pct = (100.0 * have / tot) if tot else 0.0
        parts.append(
            '<span class="chip"><a href="#{0}">{0}</a> {1:,} / {2:,} ({3:.0f}%)</span>'.format(
                esc(lang), have, tot, pct))
    parts.append('</div>')

    for lang in langs:
        rows = sorted(rows_by_lang[lang])
        tot = orphan_counts.get(lang, 0)
        parts.append('<h2 id="{0}">{0} — {1:,} fixable'.format(esc(lang), len(rows)))
        if tot:
            parts.append(' <span class="muted">of {:,} orphans</span>'.format(tot))
        parts.append('</h2>')

        qs = "\n".join('{}\tL{}\t"{}"'.format(q, lang, lab.replace('"', "'"))
                       for q, lab, _ in rows)
        parts.append(
            '<details><summary>QuickStatements for all {:,} ({} labels)</summary>'
            '<textarea readonly onclick="this.select()">{}</textarea>'
            '<p class="muted">Paste-ready. Delivery still goes through the daily drip — '
            'this box is for looking, not a second road to Wikidata.</p></details>'.format(
                len(rows), esc(lang), esc(qs)))

        parts.append('<div class="wrap"><table><thead><tr>'
                     '<th>item</th><th>our label</th><th>existing description</th>'
                     '</tr></thead><tbody>')
        for qid, label, desc in rows:
            parts.append(
                '<tr><td class="q"><a href="https://www.wikidata.org/wiki/{0}">{0}</a></td>'
                '<td class="lab">{1}</td><td class="muted">{2}</td></tr>'.format(
                    esc(qid), esc(label), esc(desc)))
        parts.append('</tbody></table></div>')

    parts.append('<p class="muted" style="margin-top:2rem">'
                 'Built by <code>site/generate_orphan_label_fixes.py</code>. '
                 '<a href="{}/index.html">shintowiki dashboards</a></p>'.format(PAGES_URL))
    return "\n".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(SITE_DIR, "orphan-label-fixes.html"))
    ap.add_argument("--cache", help="JSON file of a previous query; read if present, else written")
    ap.add_argument("--lang", help="restrict the page to one language (e.g. uk)")
    args = ap.parse_args(argv)

    orphans = None
    if args.cache and os.path.exists(args.cache):
        orphans = [tuple(r) for r in json.load(io.open(args.cache, encoding="utf-8"))]
        print("orphans from cache: {:,}".format(len(orphans)))
    if orphans is None:
        print("querying WDQS (one request)...")
        orphans = fetch_orphans()
        print("orphan (item, lang) pairs: {:,}".format(len(orphans)))
        if args.cache:
            io.open(args.cache, "w", encoding="utf-8", newline="\n").write(
                json.dumps(orphans, ensure_ascii=False))

    if args.lang:
        orphans = [o for o in orphans if o[1] == args.lang]

    orphan_counts = collections.Counter(lang for _, lang, _ in orphans)
    labels = load_labels(set(orphan_counts))
    print("generated labels loaded for those languages: {:,}".format(len(labels)))

    rows_by_lang = collections.defaultdict(list)
    for qid, lang, desc in orphans:
        lab = labels.get((qid, lang))
        if lab:
            rows_by_lang[lang].append((qid, lab, desc))

    total = sum(len(v) for v in rows_by_lang.values())
    print("fixable rows: {:,} across {} languages".format(total, len(rows_by_lang)))
    for lang, rows in sorted(rows_by_lang.items(), key=lambda kv: -len(kv[1]))[:12]:
        print("   {:<8} {:>6,} of {:>6,}".format(lang, len(rows), orphan_counts[lang]))

    if not rows_by_lang:
        print("nothing to render — no orphan had a generated label")
        return 1

    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC")
    doc = render(rows_by_lang, orphan_counts, generated_at)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    io.open(args.out, "w", encoding="utf-8", newline="\n").write(doc)
    print("wrote {} ({:,} bytes)".format(args.out, len(doc.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
