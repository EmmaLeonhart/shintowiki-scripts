#!/usr/bin/env python3
"""
build_beppyo_p612_queue.py
==========================
Queue item A0b — the Beppyo-shrine mother-house (P612) pass.

WHY AN LLM, AND WHY OPUS. The mother house is COMMON in jawiki prose — a shrine's
由緒 routinely says it was a 勧請 from some 総本社, or names the shrine it was
分霊'd from — but it is essentially never in structured data: no infobox field
carries it. Ubiquitous in prose, absent from the infobox, is precisely the shape
a regex cannot take and a reader can. Emma is confident an LLM can do it and
specified an Opus pass, expecting some results to need correction.

THE ROUTE WAS CONFIRMED, NOT GUESSED (Emma's instruction). Beppyo membership is
NOT modelled with P31: `?i wdt:P31 wd:Q10898274` returns ZERO. It is carried by
the shrine-ranking property — `?i wdt:P13723 wd:Q10898274` — which returns
exactly 350, matching the real-world count of 別表神社. 344 have a jawiki
article; 13 already carry P612 (only 6 of those with the P1013 qualifier).

ORDERING. "Large shrines first, then move down" — ordered by sitelink count,
which puts Itsukushima, Meiji Jingū, Izumo Taisha, Heian Jingū, Kamigamo at the
front. `--limit` walks down that order.

OUTPUT MODEL (docs/wikidata_shrine_festival_model.md, and it is an invariant):

    <shrine>|P612|<head shrine | Q135508874>|P1013|Q195793|S854|"<article url>"

ONE P612 statement, the P1013=Q195793 criterion qualifier in the SAME statement,
never a bare P612. Q135508874 (autochthonous shrine) is the correct answer for a
shrine of indigenous origin — that is a real finding, not a null result, so the
work-file asks for it explicitly rather than letting those become NO_MOTHER.

Writes one work-file per shrine into `beppyo_p612/` with the jawiki article text
and an `<!-- ANSWER: -->` marker; `collect_beppyo_p612.py` turns filled answers
into QuickStatements. Wikidata + ja.wikipedia only — no Miraheze request, so it
runs through the 403 blackout.

Usage:
    python build_beppyo_p612_queue.py --stats
    python build_beppyo_p612_queue.py --limit 40
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
OUT_DIR = os.path.join(REPO_ROOT, "beppyo_p612")

SPARQL = "https://query-main.wikidata.org/sparql"
JA_API = "https://ja.wikipedia.org/w/api.php"
UA = ("ShintoWikiBeppyo/1.0 "
      "(https://github.com/EmmaLeonhart/shintowiki-scripts; emma@topazcomputing.com)")
HDR = {"User-Agent": UA, "Accept": "application/sparql-results+json"}
THROTTLE = 0.4
BATCH = 1                        # whole-article extracts are 1-per-request (see articles())
MAX_CHARS = 20000                # per-article cap in the work-file

BEPPYO = "Q10898274"             # 別表神社 — reached via P13723, NOT P31
AUTOCHTHONOUS = "Q135508874"

TARGET_QUERY = """
SELECT ?item ?ja ?en ?art (COUNT(?any) AS ?links) WHERE {
  ?item wdt:P13723 wd:%s .
  ?art schema:about ?item ; schema:isPartOf <https://ja.wikipedia.org/> .
  ?any schema:about ?item .
  OPTIONAL { ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja") }
  OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en)="en") }
  FILTER NOT EXISTS { ?item wdt:P612 ?m }
}
GROUP BY ?item ?ja ?en ?art
ORDER BY DESC(?links)
""" % BEPPYO

TASK = (
    "<!-- TASK: read the ARTICLE below and identify this shrine's MOTHER HOUSE — "
    "the shrine it was branched from (勧請元 / 分霊元 / 総本社 / 本社). This is "
    "normally stated in the 由緒 or 歴史 prose, not in the infobox. Fill ANSWER "
    "with exactly one of:\n"
    "  MOTHER: <Qid> # <shrine name>   the mother house, as a Wikidata Q-id\n"
    "  AUTOCHTHONOUS:                  the article says the shrine is of "
    "indigenous/local origin (地主神, 国津神 of the place, founded in situ) with no "
    "parent shrine — this is a REAL finding, use Q135508874\n"
    "  UNCLEAR: <what the article says>  the article does not settle it\n\n"
    "Rules:\n"
    "  * The mother house is the shrine this one was BRANCHED FROM. Do not "
    "confuse it with: a shrine merged INTO this one (合祀), a 摂社/末社 inside "
    "this one's grounds, or a shrine this one is the head OF (that is the "
    "reverse direction).\n"
    "  * 総本社/総本宮 of the network is the right answer when the article says "
    "this shrine is a 分社 of it. If the article names a nearer, more specific "
    "parent (e.g. branched from a regional shrine which is itself a branch), "
    "prefer the NEARER one — the accurate individual layer is the whole point of "
    "this pass.\n"
    "  * Give a Q-id you have actually verified names that shrine. Do NOT guess a "
    "Q-id from a name; if you cannot confirm the item, answer UNCLEAR with the "
    "shrine name in the text.\n"
    "  * Founding by a person/clan, or 分霊 from a deity rather than a named "
    "shrine, is not a mother house — UNCLEAR.\n"
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
    """[(qid, ja, en, ja_title, sitelinks)] — Beppyo shrines with no P612, big first."""
    out = []
    for b in sparql(TARGET_QUERY):
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        title = urllib.parse.unquote(
            b["art"]["value"].rsplit("/", 1)[-1]).replace("_", " ")
        out.append((qid, b.get("ja", {}).get("value", ""),
                    b.get("en", {}).get("value", ""), title,
                    int(b["links"]["value"])))
    return out


def articles(titles):
    """{title -> plain-text article} — the WHOLE article, not just the lead: the
    mother house lives in 由緒/歴史, which exintro would cut off.

    ONE title per request, deliberately. `prop=extracts` silently lowers exlimit
    to 1 for whole-article extracts ("exlimit was too large for a whole article
    extracts request, lowered to 1") — a multi-title batch returns the first
    article and an EMPTY string for every other page, which reads exactly like
    "article missing" rather than like an error. Batching here loses 7 of every 8.
    """
    out = {}
    for n, title in enumerate(titles, 1):
        params = {"action": "query", "format": "json", "prop": "extracts",
                  "explaintext": 1, "redirects": 1, "titles": title,
                  "formatversion": 2}
        time.sleep(THROTTLE)
        try:
            r = requests.get(JA_API, params=params,
                             headers={"User-Agent": UA}, timeout=90)
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", [])
        except Exception as e:
            print(f"  [jawiki {title} failed] {e}", flush=True)
            continue
        for p in pages:
            if p.get("extract") and p.get("title"):
                out[p["title"]] = p["extract"]
        if n % 10 == 0 or n == len(titles):
            print(f"  articles {n}/{len(titles)}", flush=True)
    return out


def write_work_file(qid, ja, en, title, links, text):
    path = os.path.join(OUT_DIR, f"{qid}.wiki")
    url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    body = text.strip()
    truncated = len(body) > MAX_CHARS
    if truncated:
        body = body[:MAX_CHARS]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<!-- ITEM: https://www.wikidata.org/wiki/{qid} -->\n"
                f"<!-- JA: {ja} | EN: {en or '(none)'} | SITELINKS: {links} -->\n"
                f"<!-- ARTICLE: {url} -->\n"
                f"<!-- ANSWER: -->\n"
                f"{TASK}\n\n== ARTICLE ==\n{body}\n")
        if truncated:
            f.write(f"\n<!-- TRUNCATED at {MAX_CHARS} chars — read the full "
                    f"article at {url} if the answer is not settled above -->\n")


def main():
    _utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=40,
                    help="max work-files to write this run (default 40)")
    ap.add_argument("--stats", action="store_true", help="count only, write nothing")
    args = ap.parse_args()

    print(f"querying the {BEPPYO} (別表神社) set via P13723...", flush=True)
    rows = targets()
    print(f"{len(rows)} Beppyo shrines with a jawiki article and no P612 "
          f"(largest first: {', '.join(r[1] or r[0] for r in rows[:5])})")
    if args.stats:
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    todo = [r for r in rows
            if not os.path.exists(os.path.join(OUT_DIR, f"{r[0]}.wiki"))][:args.limit]
    if not todo:
        print("every target already has a work-file")
        return
    print(f"downloading {len(todo)} jawiki articles...", flush=True)
    text = articles([r[3] for r in todo])

    written, missing = 0, []
    for qid, ja, en, title, links in todo:
        body = text.get(title)
        if not body:
            missing.append((qid, title))
            continue
        write_work_file(qid, ja, en, title, links, body)
        written += 1
    print(f"\n{written} work-files -> {OUT_DIR}")
    if missing:
        print(f"{len(missing)} had no article extract — skipped, retried next run:")
        for qid, title in missing[:8]:
            print(f"  {qid}  {title}")


if __name__ == "__main__":
    main()
