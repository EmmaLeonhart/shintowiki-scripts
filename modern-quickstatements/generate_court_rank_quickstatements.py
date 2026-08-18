"""
Generate P14005 (Japanese court rank) QuickStatements for PEOPLE, from the
ja.wikipedia rank-recipient category tree under
[[Category:日本の位階受位者]] (Japanese court-rank recipients).

Pipeline
--------
1. Enumerate the subcategories of the parent category on ja.wikipedia. Each
   per-rank subcategory is named "<rank>受位者" (e.g. 正一位受位者, 従四位上受位者).
2. Resolve <rank> -> the Wikidata rank ITEM QID by matching the rank's ja label
   against the items already used as P14005 values (WDQS). No hardcoded QID
   table to drift. This match is ALSO the exclusion filter: the special
   subcategories (失位・返上を命じられた者, 位階を持たない者, etc.) do not name a
   court-rank item, so they resolve to nothing and are skipped automatically.
3. For each rank subcategory, recursively collect its ns=0 member pages (all
   descendants of a rank category still hold that rank), resolve each page to
   its Wikidata QID (ja.wp pageprops wikibase_item), and emit
       QID|P14005|<rank-item-QID>
4. Add-only / non-destructive: a person who ALREADY has P14005 = that rank is
   skipped (existing person->rank pairs preloaded from WDQS). Nothing is ever
   removed here — consistent with the repo's add-first, two-scripts rule.

Output (atomic): modern-quickstatements/court_rank_people.txt
Like every generator here, this ONLY writes the .txt. Wikidata is edited solely
by the daily QuickStatements submitter (submit_daily_batch.py) — no bespoke
direct-API editing, no edit summaries (see CLAUDE.md "Wikidata editing").

Flags
-----
--highest-only   emit only each person's single highest rank instead of every
                 rank they ever held (default: every rank held).
--max N          cap emitted lines (smoke tests).
--dry-run        print a summary, do not write the .txt.

429 from WDQS => bail immediately (repo rule). Read-only against both wikis.

STATUS 2026-07-28 — WIRED IN. The 26 sub-rank items exist (created by Emma,
Q140679480…Q140679509) and WDQS has indexed them: the live rerun this day reported
"42 rank categories resolved", which was the wire-in condition. The rank map is by
primary ja label under the court-rank class; 无位 is skipped; recursion no longer
double-tags a coarser parent rank; every rank a person held is emitted. The step now
runs in generate-quickstatements.yml and court_rank_people.txt is registered in
direct_daily_edits.ATOMIC_FILES (uncapped — ~10% of the daily draw, the same share
as its size peers). Current output: 12,326 people -> 12,605 statements.

Nothing edits yet: a week-long Wikidata freeze runs to 2026-08-04
(FREEZE_WIKIDATA_UNTIL in cleanup-loop.yml's window-gate forces
wikidata-daily-fire=false), so the first court-rank lines can land no earlier than
that. Confirmed still in force by Emma on 2026-07-28.
"""

import os
import re
import sys
import time
import argparse
import requests
from shinto_miraheze.ua_contact import contact

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "court_rank_people.txt")

JA_API = "https://ja.wikipedia.org/w/api.php"
SPARQL = "https://query-main.wikidata.org/sparql"
PARENT_CAT = "Category:日本の位階受位者"
RANK_SUFFIX = "受位者"

UA = {"User-Agent": "ShintoWikiCourtRankPeople/1.0 ({contact('wikidata')})"}
SPARQL_HDR = dict(UA, **{"Accept": "application/sparql-results+json"})


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _sparql(query):
    for attempt in range(4):
        time.sleep(0.5)
        try:
            r = requests.post(SPARQL, data={"query": query, "format": "json"},
                              headers=SPARQL_HDR, timeout=120)
            if r.status_code == 429:
                raise SystemExit("429 from WDQS — bailing (repo rule).")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [WDQS retry {attempt+1}] {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("WDQS failed after retries")


def _ja_api(params):
    params = dict(params, format="json")
    for attempt in range(4):
        time.sleep(0.3)
        try:
            r = requests.get(JA_API, params=params, headers=UA, timeout=60)
            if r.status_code == 429:
                raise SystemExit("429 from ja.wikipedia — bailing.")
            r.raise_for_status()
            return r.json()
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [ja.wp retry {attempt+1}] {e}", flush=True)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("ja.wikipedia API failed after retries")


COURT_RANK_CLASS = "Q99196082"  # "court rank in Japan"
# "no rank" — a member of the class but NOT a rank to tag people with; skip it.
NO_RANK_QID = "Q11504610"       # 无位


def rank_label_to_qid():
    """{primary ja label of a court-rank item -> QID}, for every item under the
    court-rank class. This is broader than "items used as P14005 values" (which
    misses ranks not yet used) and now covers the sub-rank items created
    2026-07-23, so every ja.wp per-rank recipient category resolves. 无位 (no
    rank) is excluded."""
    rows = _sparql(
        'SELECT ?item ?lab WHERE { '
        '?item (wdt:P31|wdt:P279)/wdt:P279* wd:%s . '
        '?item rdfs:label ?lab . FILTER(LANG(?lab)="ja") }' % COURT_RANK_CLASS
    )
    m = {}
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[1]
        if qid == NO_RANK_QID:
            continue
        m[b["lab"]["value"]] = qid
    return m


def existing_pairs():
    """Set of (person_qid, rank_qid) already stated, so we never re-add."""
    rows = _sparql("SELECT ?p ?r WHERE { ?p wdt:P14005 ?r }")
    out = set()
    for b in rows:
        out.add((b["p"]["value"].rsplit("/", 1)[1],
                 b["r"]["value"].rsplit("/", 1)[1]))
    return out


def subcategories(cat):
    """Direct subcategory titles (ns=14) of a category on ja.wikipedia."""
    subs, cont = [], {}
    while True:
        data = _ja_api({"action": "query", "list": "categorymembers",
                        "cmtitle": cat, "cmtype": "subcat", "cmlimit": "500", **cont})
        subs += [m["title"] for m in data["query"]["categorymembers"]]
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return subs


def category_pages(cat, seen_cats):
    """All ns=0 page titles under a category, recursing into NON-rank
    subcategories only. A subcategory that is itself a rank-recipient category
    (name ends in 受位者) is a DIRECT child of the parent tree and is crawled on
    its own top-level pass; recursing into it here would tag its people with the
    coarser parent rank too (e.g. 従八位上受位者's members also getting 従八位).
    Other subcats (by-era groupings etc.) share this category's rank, so recurse."""
    if cat in seen_cats:
        return []
    seen_cats.add(cat)
    titles, cont = [], {}
    while True:
        data = _ja_api({"action": "query", "list": "categorymembers",
                        "cmtitle": cat, "cmnamespace": "0|14", "cmlimit": "500", **cont})
        for m in data["query"]["categorymembers"]:
            if m["ns"] == 0:
                titles.append(m["title"])
            elif m["ns"] == 14:
                name = m["title"].split(":", 1)[1] if ":" in m["title"] else m["title"]
                if not name.endswith(RANK_SUFFIX):
                    titles += category_pages(m["title"], seen_cats)
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return titles


def titles_to_qids(titles):
    """{ja.wp title -> Wikidata QID} via pageprops wikibase_item, 50/batch."""
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = _ja_api({"action": "query", "prop": "pageprops",
                        "ppprop": "wikibase_item", "titles": "|".join(batch),
                        "redirects": "1"})
        pages = data.get("query", {}).get("pages", {})
        # map any redirect-normalised titles back is unnecessary; we key by the
        # returned page title, and only need the QID set per rank anyway.
        for p in pages.values():
            qid = p.get("pageprops", {}).get("wikibase_item")
            if qid:
                out[p["title"]] = qid
    return out


def main():
    _utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--highest-only", action="store_true",
                    help="emit only each person's highest rank (default: every rank held)")
    ap.add_argument("--max", type=int, default=0, help="cap emitted lines")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"Rank label->QID map (P14005 values)...", flush=True)
    rank_map = rank_label_to_qid()
    print(f"  {len(rank_map)} court-rank items.", flush=True)

    print("Existing person->rank pairs (skip re-adds)...", flush=True)
    have = existing_pairs()
    print(f"  {len(have)} existing P14005 statements.", flush=True)

    print(f"Subcategories of {PARENT_CAT}...", flush=True)
    subs = subcategories(PARENT_CAT)
    # keep only per-rank recipient categories that resolve to a rank item;
    # this drops the 失位/返上/no-rank specials automatically.
    rank_cats = []
    for c in subs:
        name = c.split(":", 1)[1] if ":" in c else c
        if not name.endswith(RANK_SUFFIX):
            continue
        rank_name = name[: -len(RANK_SUFFIX)]
        qid = rank_map.get(rank_name)
        if qid:
            rank_cats.append((c, rank_name, qid))
        else:
            print(f"  [skip] {name}: no P14005 item matches '{rank_name}'", flush=True)
    print(f"  {len(rank_cats)} rank categories resolved.", flush=True)

    # person_qid -> list of (rank_qid, rank_name), ordered as discovered
    person_ranks = {}
    # rank "strength" for --highest-only: senior(正)>junior(従), then lower N first.
    def strength(rank_name):
        grade = 0 if rank_name.startswith("正") else 1  # 正 senior beats 従 junior
        mnum = re.search(r"[一二三四五六七八九十]", rank_name)
        order = "一二三四五六七八九十"
        n = order.index(mnum.group()) if mnum else 99
        upper = 0 if rank_name.endswith("上") else 1  # 上 upper beats 下
        return (n, grade, upper)  # smaller = higher rank

    for cat, rank_name, rank_qid in rank_cats:
        titles = category_pages(cat, set())
        qmap = titles_to_qids(titles)
        print(f"  {rank_name}: {len(titles)} pages, {len(qmap)} with QIDs", flush=True)
        for title, pq in qmap.items():
            person_ranks.setdefault(pq, []).append((rank_qid, rank_name))

    lines = []
    for pq, ranks in person_ranks.items():
        chosen = ranks
        if args.highest_only:
            chosen = [min(ranks, key=lambda rr: strength(rr[1]))]
        for rank_qid, rank_name in chosen:
            if (pq, rank_qid) in have:
                continue
            lines.append(f"{pq}|P14005|{rank_qid}")

    # de-dup lines while preserving order
    seen, uniq = set(), []
    for ln in lines:
        if ln not in seen:
            seen.add(ln); uniq.append(ln)
    if args.max:
        uniq = uniq[: args.max]

    print(f"{len(person_ranks)} people -> {len(uniq)} new P14005 statements.", flush=True)
    if args.dry_run:
        for ln in uniq[:20]:
            print("   ", ln)
        return
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for ln in uniq:
            f.write(ln + "\n")
    print(f"Wrote {len(uniq)} lines -> {OUT}")


if __name__ == "__main__":
    main()
