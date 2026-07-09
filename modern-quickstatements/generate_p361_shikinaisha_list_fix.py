#!/usr/bin/env python3
"""Rebuild the P361 (part of) statements on Shikinai Ronsha items from the
Shikinaisha-list ordering.

THE PROBLEM
-----------
A Shikinaisha *list entry* item (e.g. Q135039994, "entry 25 of the Mutsu list")
carries one clean `P361 → <list>` statement with `P1545` ordinal, one `P155`
(follows) and one `P156` (followed by). Its disputed real-world candidates hang
off it as `P460`. Somewhere in a partial migration those candidates each got a
*copy* of the entry's P361 statement, and where one real shrine is a candidate
for several entries the copies collapsed together — a single statement ending up
with three `P155` and three `P156` values at once.

THE FIX (Emma 2026-07-09)
-------------------------
"Remove every single part-of-the-Shikinaisha-list that is on the actual shrine
itself. Add in a new one that's just derived from the list item, with the
preceding and following taken from the data thing."

THE "DATA THING"
----------------
Each clean statement is an independent witness to its *neighbours'* ordinals: a
clean statement at ordinal N asserts that N-1 is its `P155` and N+1 is its
`P156`. Collecting those witnesses across a whole list reconstructs the true
occupant of every position — and the witnesses agree unanimously, while the
self-claims are exactly the pollution we are removing. (Verified on the Mutsu
list Q11658590: every ordinal has exactly one witnessed occupant; ordinal 25 has
five self-claimants, four of which are P460 candidates.)

So for each Ronsha item S that is part-of list L:
  * remove every `P361 → L` statement on S;
  * for each ordinal O where the witnesses say the occupant *is* S, add back one
    clean statement: `P361 = L`, `P1545 = O`, `P155 = occupant(O-1)`,
    `P156 = occupant(O+1)`, referenced to the Kokugakuin database entry and to
    the list's jawiki article.
  * A pure candidate — one the witnesses never name — keeps no P361 at all; its
    list membership belongs to the entry item it hangs off.

NOT DRIP-SAFE. This is a remove+add batch: under the daily editor's random line
order a removal could fire before its replacement and lose data. It is a
**browser batch only** — deliberately not registered in ATOMIC_FILES.

    python generate_p361_shikinaisha_list_fix.py [--limit N] [--out FILE]
"""
import argparse
import collections
import io
import json
import os
import sys
import time

import requests
from urllib.parse import unquote

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts",
    "Accept": "application/sparql-results+json",
}

RONSHA = "Q135022904"          # Shikinai Ronsha
KOKUGAKUIN_DB = "Q135159299"   # Kokugakuin University Shrine database
ENGISHIKI_JINMYOCHO = "Q11064932"  # a real Shikinaisha list is part of this
CHUNK = 100

_last = 0.0


def sparql(query):
    """Mass query with the same truncated-200 guard as the ranking generator.

    WDQS signals a mid-stream abort by gluing a Java stack trace onto an
    already-200 body, so a parse failure here means "query too heavy", not
    "bad JSON".
    """
    global _last
    for attempt in range(5):
        wait = time.time() - _last
        if wait < 3:
            time.sleep(3 - wait)
        r = requests.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"},
                         headers=HEADERS, timeout=180)
        _last = time.time()
        if r.status_code == 429:
            raise SystemExit("FATAL: 429 Too Many Requests — bailing (429 policy)")
        if r.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        try:
            return json.loads(r.text, strict=False)["results"]["bindings"]
        except (ValueError, KeyError):
            print(f"  truncated body ({len(r.text)} bytes) — retrying", flush=True)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("SPARQL kept returning truncated bodies")


def qid(uri):
    return uri.rsplit("/", 1)[-1]


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def values(var, qids):
    return "VALUES ?%s { %s }" % (var, " ".join("wd:" + q for q in qids))


def fetch_duplicate_items():
    """Ronsha items carrying more than one P361 statement."""
    rows = sparql(
        f"SELECT ?item WHERE {{ ?item wdt:P31 wd:{RONSHA} ; p:P361 ?s }} "
        "GROUP BY ?item HAVING(COUNT(?s) > 1)"
    )
    return sorted(qid(r["item"]["value"]) for r in rows)


def fetch_targets(items):
    """{item: [target qids]} — every P361 target of each duplicate item.

    NOT all of these are Shikinaisha lists — see `filter_shikinaisha_lists`.
    """
    out = collections.defaultdict(set)
    for chunk in chunks(items, CHUNK):
        for r in sparql(
            "SELECT ?item ?list WHERE { %s ?item p:P361 ?st . ?st ps:P361 ?list . }"
            % values("item", chunk)
        ):
            out[qid(r["item"]["value"])].add(qid(r["list"]["value"]))
    return out


def filter_shikinaisha_lists(targets):
    """Keep only targets that are genuinely part of the Engishiki Jinmyōchō.

    THE BUG THIS FIXES (2026-07-09, found via the contested-ordinal review).
    `P361` on a shrine means far more than "listed in a province's Shikinaisha
    list". It also means "this subshrine is part of Kamigamo Shrine", "part of the
    Twenty-Two Shrines ranking", "part of the Ninety-Nine Ōji Shrines of the
    Kumano Kodō". Of the 249 targets the first version swept up, only **47** were
    Shikinaisha lists; the other 202 were shrines and classes — Kamigamo Shrine,
    Shirayama Hime Shrine, Beppyō Shrine (a *type*), Twenty-Two Shrines.

    Rebuilding those from "neighbour witnesses" is meaningless, and the batch's
    removal lines would have deleted 425 real statements — a subshrine's
    membership of its parent shrine among them. The batch was never run.

    A real Shikinaisha list is `wdt:P361 wd:Q11064932` (part of the Engishiki
    Jinmyōchō). Nothing else is in scope.
    """
    all_targets = sorted({t for ts in targets.values() for t in ts})
    keep = set()
    for chunk in chunks(all_targets, CHUNK):
        for r in sparql(
            "SELECT ?l WHERE { %s ?l wdt:P361 wd:%s }"
            % (values("l", chunk), ENGISHIKI_JINMYOCHO)
        ):
            keep.add(qid(r["l"]["value"]))
    dropped = [t for t in all_targets if t not in keep]
    filtered = {
        item: {t for t in ts if t in keep} for item, ts in targets.items()
    }
    return {i: ts for i, ts in filtered.items() if ts}, sorted(keep), dropped


def fetch_list_statements(lists):
    """{list: [(item, ordinal, [follows], [followedBy])]} for every P361 into the list."""
    out = collections.defaultdict(lambda: collections.defaultdict(
        lambda: {"item": None, "ord": None, "f": set(), "fb": set()}))
    for chunk in chunks(lists, 40):
        rows = sparql(
            "SELECT ?list ?item ?st ?ord ?f ?fb WHERE { %s "
            "?item p:P361 ?st . ?st ps:P361 ?list . "
            "OPTIONAL { ?st pq:P1545 ?ord } OPTIONAL { ?st pq:P155 ?f } "
            "OPTIONAL { ?st pq:P156 ?fb } }" % values("list", chunk)
        )
        for r in rows:
            L = qid(r["list"]["value"])
            d = out[L][r["st"]["value"]]
            d["item"] = qid(r["item"]["value"])
            if "ord" in r:
                d["ord"] = r["ord"]["value"]
            if "f" in r:
                d["f"].add(qid(r["f"]["value"]))
            if "fb" in r:
                d["fb"].add(qid(r["fb"]["value"]))
    return {L: list(sts.values()) for L, sts in out.items()}


def build_witness_map(statements):
    """ordinal -> occupant, reconstructed from the neighbours of *clean* statements.

    A clean statement (one ordinal, one P155, one P156) at ordinal N witnesses
    that N-1 is its P155 and N+1 is its P156. Self-claims are ignored: they are
    precisely the copies being removed. An ordinal is resolved only if every
    witness agrees; a contested ordinal is left unresolved and its items are
    reported rather than edited.
    """
    votes = collections.defaultdict(set)
    for st in statements:
        if not st["ord"] or len(st["f"]) != 1 or len(st["fb"]) != 1:
            continue
        try:
            n = int(st["ord"])
        except ValueError:
            continue
        votes[n - 1].add(next(iter(st["f"])))
        votes[n + 1].add(next(iter(st["fb"])))

    resolved, contested = {}, {}
    for n, cands in votes.items():
        if len(cands) == 1:
            resolved[n] = next(iter(cands))
        else:
            contested[n] = sorted(cands)
    return resolved, contested


def fetch_kokugakuin_ids(items):
    out = collections.defaultdict(set)
    for chunk in chunks(sorted(items), CHUNK):
        for r in sparql(
            "SELECT ?item ?eid WHERE { %s ?item wdt:P13677 ?eid . }" % values("item", chunk)
        ):
            out[qid(r["item"]["value"])].add(r["eid"]["value"])
    return out


def fetch_jawiki_urls(lists):
    """Percent-decoded, to match the P4656 values already in the repo's batches."""
    out = {}
    for chunk in chunks(lists, CHUNK):
        for r in sparql(
            "SELECT ?list ?article WHERE { %s ?article schema:about ?list ; "
            "schema:isPartOf <https://ja.wikipedia.org/> . }" % values("list", chunk)
        ):
            out[qid(r["list"]["value"])] = unquote(r["article"]["value"])
    return out


def entry_id_for(ordinal, occupant, resolved, kok_ids):
    """The Kokugakuin entry id this ordinal is about.

    An item that is a candidate for several entries holds several P13677s. The
    one belonging to *this* ordinal is the one no other resolved ordinal's
    occupant also holds. If that does not single one out, cite nothing rather
    than cite wrongly.

    An occupant may legitimately hold several positions in one list (one modern
    shrine identified with two Engishiki entries). Then a single id cannot be
    attributed to a single ordinal by elimination, and we cite nothing: guessing
    would attach the wrong entry to one of the two statements.
    """
    mine = set(kok_ids.get(occupant, ()))
    if not mine:
        return None
    own_ordinals = [o for o, occ in resolved.items() if occ == occupant]
    if len(mine) == 1 and len(own_ordinals) == 1:
        return next(iter(mine))
    others = set()
    for o, occ in resolved.items():
        if occ != occupant:
            others |= set(kok_ids.get(occ, ()))
    residual = mine - others
    # Only attributable when the occupant holds exactly one position AND exactly
    # one id survives elimination.
    if len(own_ordinals) == 1 and len(residual) == 1:
        return next(iter(residual))
    return None


def qs_lines(item, L, ordinal, resolved, kok_ids, jawiki):
    """One clean replacement statement, with its two references."""
    parts = [item, "P361", L, "P1545", f'"{ordinal}"']
    if ordinal - 1 in resolved:
        parts += ["P155", resolved[ordinal - 1]]
    if ordinal + 1 in resolved:
        parts += ["P156", resolved[ordinal + 1]]

    eid = entry_id_for(ordinal, item, resolved, kok_ids)
    if eid:
        parts += ["S248", KOKUGAKUIN_DB, "S13677", f'"{eid}"']
    if L in jawiki:
        parts += ["S4656", f'"{jawiki[L]}"']
    return "|".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only emit the first N items (pilot batch)")
    ap.add_argument("--out", default=os.path.join("_site", "p361_shikinaisha_list_fix.txt"))
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("Fetching Shikinai Ronsha items with duplicate P361...", flush=True)
    items = fetch_duplicate_items()
    print(f"  {len(items)} items", flush=True)

    targets = fetch_targets(items)
    raw = sorted({L for ls in targets.values() for L in ls})
    targets, lists, dropped = filter_shikinaisha_lists(targets)
    print(f"  across {len(raw)} P361 targets", flush=True)
    print(f"  of which {len(lists)} are Shikinaisha lists (part of {ENGISHIKI_JINMYOCHO});", flush=True)
    print(f"  DROPPED {len(dropped)} non-list targets (shrines, ranking classes) — out of scope", flush=True)
    for d in dropped[:8]:
        print(f"    not a list: {d}")
    print(f"  {len(targets)} items remain in scope", flush=True)

    print("Fetching every P361 statement into those lists...", flush=True)
    per_list = fetch_list_statements(lists)
    total_st = sum(len(v) for v in per_list.values())
    print(f"  {total_st} statements", flush=True)

    witness, contested = {}, {}
    for L, sts in per_list.items():
        witness[L], contested[L] = build_witness_map(sts)

    occupants = {occ for w in witness.values() for occ in w.values()}
    print("Fetching Kokugakuin entry ids and jawiki list articles...", flush=True)
    kok_ids = fetch_kokugakuin_ids(occupants | set(items))
    jawiki = fetch_jawiki_urls(lists)
    print(f"  {len(jawiki)}/{len(lists)} lists have a jawiki article", flush=True)

    out, stats = [], collections.Counter()
    skipped = []
    for item in items:
        for L in sorted(targets[item]):
            sts = [s for s in per_list.get(L, []) if s["item"] == item]
            if not sts:
                continue
            if any(item in contested[L].get(o, []) for o in contested[L]):
                skipped.append((item, L, "contested ordinal"))
                stats["items_skipped"] += 1
                continue

            mine = sorted(o for o, occ in witness[L].items() if occ == item)
            out.append(f"# {item} in {L}: remove {len(sts)}, add {len(mine)}"
                       + (f" (ordinal{'s' if len(mine) != 1 else ''} {mine})" if mine else " (pure candidate)"))
            # Interleaved per item: the removals then this item's replacement,
            # so a batch that dies mid-run damages at most one item.
            # One '-' line per existing statement: QuickStatements' documented
            # behaviour on several identical values is unspecified, and this is
            # correct whether '-' drops one match or all of them (the surplus
            # lines simply report "not found").
            for _ in sts:
                out.append(f"-{item}|P361|{L}")
                stats["removals"] += 1
            for o in mine:
                out.append(qs_lines(item, L, o, witness[L], kok_ids, jawiki))
                stats["adds"] += 1
            stats["items"] += 1
            if not mine:
                stats["pure_candidates"] += 1
            if args.limit and stats["items"] >= args.limit:
                break
        if args.limit and stats["items"] >= args.limit:
            break

    path = args.out
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

    print("\n=== Summary ===")
    print(f"  items rewritten : {stats['items']}")
    print(f"  statements removed: {stats['removals']}")
    print(f"  statements added  : {stats['adds']}")
    print(f"  pure candidates (no P361 left): {stats['pure_candidates']}")
    print(f"  items skipped (contested ordinal): {stats['items_skipped']}")
    for it, L, why in skipped[:10]:
        print(f"    - {it} in {L}: {why}")
    print(f"\n  wrote {path}")
    print("  NOT drip-safe — browser batch only.")


if __name__ == "__main__":
    main()
