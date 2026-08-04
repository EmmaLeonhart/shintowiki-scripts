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

MEMBERSHIP COMES FROM THE JAWIKI CATEGORY, NOT FROM WIKIDATA (Emma 2026-08-03:
"Are you seriously trying to get the Beppyo shrines from Wikidata? Don't! Get
them from the Japanese Wikipedia category for them!"). `Category:別表神社` lists
346 ns-0 articles and costs ONE paginated API call. Each article's QID comes back
from the same API via `prop=pageprops` → `wikibase_item`, so this script issues no
SPARQL at all — see the "DO NOT HAMMER WIKIDATA" rule in CLAUDE.md.

(The earlier version queried `?i wdt:P13723 wd:Q10898274`. That route is real —
P31 returns zero, the ranking property returns 350 — but querying Wikidata to
build a worklist is exactly the habit that rule forbids.)

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

JA_API = "https://ja.wikipedia.org/w/api.php"
UA = ("ShintoWikiBeppyo/1.0 "
      "(https://github.com/EmmaLeonhart/shintowiki-scripts; emma@topazcomputing.com)")
THROTTLE = 0.4
BATCH = 1                        # whole-article extracts are 1-per-request (see articles())
MAX_CHARS = 20000                # per-article cap in the work-file

AUTOCHTHONOUS = "Q135508874"

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


CATEGORY = "Category:別表神社"


def _api(params):
    p = {"action": "query", "format": "json", "formatversion": 2}
    p.update(params)
    time.sleep(THROTTLE)
    r = requests.get(JA_API, params=p, headers={"User-Agent": UA}, timeout=90)
    r.raise_for_status()
    return r.json()


def category_members():
    """Every ns-0 article in Category:別表神社. One paginated API call."""
    titles, cont = [], {}
    while True:
        d = _api(dict({"list": "categorymembers", "cmtitle": CATEGORY,
                       "cmlimit": 500, "cmnamespace": 0}, **cont))
        titles += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d:
            return titles
        cont = d["continue"]


def targets():
    """[(qid, ja_title, langlinks)] for the category's articles, biggest first.

    The QID arrives with the article listing (pageprops.wikibase_item) and the
    langlink count stands in for "large shrine" — no Wikidata query is made.
    """
    titles = [t for t in category_members() if t != "別表神社"]
    out = []
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        d = _api({"titles": "|".join(chunk), "prop": "pageprops|langlinks",
                  "lllimit": 500})
        for p in d.get("query", {}).get("pages", []):
            qid = (p.get("pageprops") or {}).get("wikibase_item")
            if not qid:
                continue
            out.append((qid, p["title"], len(p.get("langlinks", []))))
        print(f"  ids {min(i + 50, len(titles))}/{len(titles)}", flush=True)
    out.sort(key=lambda r: -r[2])
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

    print(f"listing {CATEGORY} from ja.wikipedia (no Wikidata query)...", flush=True)
    rows = targets()
    print(f"{len(rows)} Beppyo articles with a QID "
          f"(largest first: {', '.join(r[1] for r in rows[:5])})")
    if args.stats:
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    todo = [r for r in rows
            if not os.path.exists(os.path.join(OUT_DIR, f"{r[0]}.wiki"))][:args.limit]
    if not todo:
        print("every target already has a work-file")
        return
    print(f"downloading {len(todo)} jawiki articles...", flush=True)
    text = articles([r[1] for r in todo])

    written, missing = 0, []
    for qid, title, links in todo:
        body = text.get(title)
        if not body:
            missing.append((qid, title))
            continue
        write_work_file(qid, title, "", title, links, body)
        written += 1
    print(f"\n{written} work-files -> {OUT_DIR}")
    if missing:
        print(f"{len(missing)} had no article extract — skipped, retried next run:")
        for qid, title in missing[:8]:
            print(f"  {qid}  {title}")


if __name__ == "__main__":
    main()
