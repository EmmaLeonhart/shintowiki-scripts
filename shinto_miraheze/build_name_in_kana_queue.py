#!/usr/bin/env python3
"""
build_name_in_kana_queue.py
===========================
Queue item A0 — give shrines a correct MODERN HIRAGANA P1814 (name in kana),
extracted by an LLM from the jawiki lead.

WHY AN LLM STEP. The reading is present in almost every jawiki article's first
sentence, but it is not reliably regex-extractable: it appears as furigana, as a
bolded parenthetical, sometimes with the shrine's 通称 or a 旧称 in the same
parens, sometimes with okurigana splits across ruby markup. A regex that gets it
right on the easy 80% quietly gets it WRONG on the rest, and a wrong P1814
propagates straight into romaji and en labels. So the lead is handed over whole
and the reading is read out of it.

⚠ NOT the kana-QUALIFIER cleanup. `generate_kana_qualifier_add.py` /
`generate_kana_qualifier_remove.py` are Engishiki-only and undo the opposite
error — ancient-Japanese KATAKANA readings that landed in top-level P1814, which
that pair relocates onto the ojp-hani P1448 and strips from top-level. The two
touch the same property on the same items, so:

  * this builder HOLDS every item the cleanup touches — the 601 (of 2,637) that
    carry an ojp-hani P1448, derived by SPARQL — so the new writer can never
    re-introduce what the cleanup is stripping, and so the ordering question gets
    Emma's eyes before that subset runs, as she asked; and
  * the collector's hard gate is: a katakana-only reading is REJECTED. Katakana
    is the signature of exactly that ancient-reading error. P1814 wants modern
    hiragana.

Emma's instruction on gating: do NOT over-gate on confidence — producing kana is
the priority and the LLM path is high-quality. The katakana exclusion is the gate.

Target set (SPARQL, query-main): ?item wdt:P31 wd:Q845945, has a jawiki sitelink,
and has NO top-level P1814. Two buckets, recorded on each work-file:
  (a) HAS an en label — most likely to carry romanization-derived errors. Priority.
  (b) NO en label — the collector's companion step also generates the en label.

Output: one work-file per item in `name_in_kana/`, carrying the jawiki lead and an
`<!-- ANSWER: -->` marker, exactly like category_translation/ and
label_typo_review/. `collect_name_in_kana.py` turns filled answers into
QuickStatements. Read-only: Wikidata + ja.wikipedia only, no Miraheze request, so
it runs through the 403 blackout.

Usage:
    python build_name_in_kana_queue.py --limit 200        # write 200 work-files
    python build_name_in_kana_queue.py --bucket b         # only the no-en-label set
    python build_name_in_kana_queue.py --stats            # count, write nothing
"""
import argparse
import io
import os
import sys
import time
import urllib.parse

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(REPO_ROOT, "name_in_kana")

SPARQL = "https://query-main.wikidata.org/sparql"
JA_API = "https://ja.wikipedia.org/w/api.php"
UA = ("ShintoWikiLabels/1.0 "
      "(https://github.com/EmmaLeonhart/shintowiki-scripts; emma@topazcomputing.com)")
HDR = {"User-Agent": UA, "Accept": "application/sparql-results+json"}
THROTTLE = 0.4
BATCH = 20                       # titles per ja.wikipedia extracts call

TARGET_QUERY = """
SELECT ?item ?ja ?en ?art WHERE {
  ?item wdt:P31 wd:Q845945 .
  ?art schema:about ?item ; schema:isPartOf <https://ja.wikipedia.org/> .
  FILTER NOT EXISTS { ?item wdt:P1814 ?k }
  OPTIONAL { ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja") }
  OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en)="en") }
}
"""

TASK = (
    "<!-- TASK: read the LEAD above and give this shrine's reading as MODERN "
    "HIRAGANA, for Wikidata P1814 (name in kana). Fill ANSWER with exactly one of:\n"
    "  KANA: <hiragana>        the shrine's own reading, hiragana only\n"
    "  KATAKANA: <katakana>    the lead gives only an ancient/katakana reading\n"
    "  NO_KANA: <reason>       the lead carries no reading for THIS shrine\n"
    "Rules: give the reading of the SHRINE NAME itself, not a 通称 (common name), "
    "not a 旧称 (former name), and not the reading of the place it stands in. Drop "
    "interpuncts and spaces. A KATAKANA answer is recorded and NOT written to "
    "Wikidata — P1814 wants modern hiragana, and a katakana reading is the "
    "signature of the ancient-reading error a separate cleanup is undoing.\n"
    "When ANSWER is filled this file is done. -->"
)



def _utf8():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def sparql(query):
    for attempt in range(4):
        time.sleep(0.5)
        try:
            r = requests.post(SPARQL, data={"query": query, "format": "json"},
                              headers=HDR, timeout=180)
            if r.status_code == 429:
                raise SystemExit("429 from WDQS — bailing (CLAUDE.md 429 policy).")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [WDQS retry {attempt + 1}] {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("WDQS failed")


def targets():
    """[(qid, ja_label, en_label, ja_title)] — shrines with a jawiki article, no P1814."""
    out = []
    for b in sparql(TARGET_QUERY):
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        art = b["art"]["value"]
        title = urllib.parse.unquote(art.rsplit("/", 1)[-1]).replace("_", " ")
        out.append((qid, b.get("ja", {}).get("value", ""),
                    b.get("en", {}).get("value", ""), title))
    out.sort(key=lambda r: int(r[0][1:]))
    return out


def engishiki_cleanup_qids():
    """QIDs the kana-qualifier cleanup also touches. Reported, and held ONLY
    under --hold-engishiki.

    RESOLVED 2026-08-03 (Emma: "probably gating the writer per item?"). The
    collision this guarded against cannot occur, verified in the cleanup's own
    code rather than assumed:

      * generate_kana_qualifier_add.py guards BOTH its branches with
        `is_katakana(...)` and skips anything else, so a modern hiragana
        top-level P1814 can never be seeded into a カミノヤシロ qualifier.
      * generate_kana_qualifier_remove.py emits VALUE-MATCHED removals
        (`-Q135070210|P1814|"アスキ-"`), so it deletes that katakana string, not
        "the item's P1814". A hiragana value is not a target.
      * this builder's own target query requires NOT EXISTS P1814, so an item is
        queued only once it has no top-level reading at all — which for an
        Engishiki item means the cleanup's removal has already landed, and that
        removal is itself held until every ojp-hani name on the item carries its
        qualifier.

    The three together ARE the per-item gate: the two pipelines write disjoint
    values and neither can consume the other's. So the set is no longer withheld
    wholesale — that would have left 601 shrines permanently without a modern
    reading, which is the gap A0 exists to close.

    The cleanup (generate_kana_qualifier_add.py / _remove.py) works on items
    carrying an ojp-hani P1448 official name: it moves the ancient katakana
    reading onto that name as a カミノヤシロ qualifier and strips the top-level
    P1814. Both it and this builder write top-level P1814 on the same items, so
    the two must not run against the same subset unordered — Emma's instruction is
    explicitly to get her eyes on the ordering before the Engishiki subset runs.

    Derived by SPARQL, not by scraping the cleanup script: that script picks its
    targets with a query and holds no QID literals, so a source scrape would have
    matched only incidental constants (Q195793, Q845945) and excluded the wrong
    items while looking like it worked.
    """
    rows = sparql('SELECT DISTINCT ?item WHERE { ?item wdt:P31 wd:Q845945 ; '
                  'p:P1448/ps:P1448 ?nm . FILTER(LANG(?nm)="ojp-hani") }')
    return {b["item"]["value"].rsplit("/", 1)[-1] for b in rows}


def leads(titles):
    """{title -> plain-text lead} via the extracts API, BATCH titles per call."""
    out = {}
    for i in range(0, len(titles), BATCH):
        chunk = titles[i:i + BATCH]
        params = {"action": "query", "format": "json", "prop": "extracts",
                  "exintro": 1, "explaintext": 1, "redirects": 1,
                  "titles": "|".join(chunk), "formatversion": 2}
        time.sleep(THROTTLE)
        try:
            r = requests.get(JA_API, params=params,
                             headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", [])
        except Exception as e:
            print(f"  [jawiki batch {i // BATCH} failed] {e}", flush=True)
            continue
        # `redirects` rewrites titles, so map back through the normalisation the
        # API reports rather than assuming the response order matches the request.
        for p in pages:
            if "extract" in p and p.get("title"):
                out[p["title"]] = p["extract"]
        print(f"  leads {min(i + BATCH, len(titles))}/{len(titles)}", flush=True)
    return out


def write_work_file(qid, ja, en, title, lead):
    bucket = "a" if en else "b"
    path = os.path.join(OUT_DIR, f"{qid}.wiki")
    art = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<!-- ITEM: https://www.wikidata.org/wiki/{qid} -->\n"
                f"<!-- JA: {ja} | EN_LABEL: {en or '(none)'} | BUCKET: {bucket} -->\n"
                f"<!-- ARTICLE: {art} -->\n"
                f"<!-- ANSWER: -->\n"
                f"{TASK}\n\n== LEAD ==\n{lead.strip()}\n")


def main():
    _utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=200,
                    help="max work-files to write this run (default 200)")
    ap.add_argument("--bucket", choices=["a", "b"],
                    help="a = has an en label (priority); b = no en label")
    ap.add_argument("--stats", action="store_true", help="count only, write nothing")
    ap.add_argument("--hold-engishiki", action="store_true",
                    help="withhold the ojp-hani P1448 items (see engishiki_cleanup_qids; "
                         "not needed — the two pipelines write disjoint values)")
    args = ap.parse_args()

    print("querying Wikidata for shrines with a jawiki article and no P1814...",
          flush=True)
    rows = targets()
    engishiki = engishiki_cleanup_qids()
    kept = [r for r in rows if not (args.hold_engishiki and r[0] in engishiki)]
    overlap = sum(1 for r in rows if r[0] in engishiki)
    a = [r for r in kept if r[2]]
    b = [r for r in kept if not r[2]]
    print(f"{len(rows)} targets; {overlap} also carry an ojp-hani P1448 "
          + ("(HELD by --hold-engishiki)" if args.hold_engishiki
             else "(queued — the two pipelines write disjoint values)")
          + f"; bucket a (has en label) {len(a)}, bucket b {len(b)}")

    pool = a if args.bucket == "a" else b if args.bucket == "b" else a + b
    if args.stats:
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    todo = [r for r in pool
            if not os.path.exists(os.path.join(OUT_DIR, f"{r[0]}.wiki"))][:args.limit]
    if not todo:
        print("every target in this bucket already has a work-file")
        return
    print(f"downloading {len(todo)} jawiki leads...", flush=True)
    text = leads([r[3] for r in todo])

    written, noext = 0, []
    for qid, ja, en, title in todo:
        lead = text.get(title)
        if not lead:
            noext.append((qid, title))
            continue
        write_work_file(qid, ja, en, title, lead)
        written += 1
    print(f"\n{written} work-files -> {OUT_DIR}")
    if noext:
        print(f"{len(noext)} had no lead extract (redirect//disambig/empty) — skipped, "
              f"no file written so a later run retries them:")
        for qid, title in noext[:8]:
            print(f"  {qid}  {title}")


if __name__ == "__main__":
    main()
