#!/usr/bin/env python3
"""Remove uncited Japanese street addresses (P6375) from Shikinai Ronsha items
that also carry a *cited* Japanese address.

Emma 2026-07-09:

    "If there are Japanese language addresses that are uncited, they should be
    removed if there is a cited Japanese address on the shrine. Simple as that!"

A citation is the signal she has been using to pick the true address all along
("if any one of them has a citation, that's a really good sign"). Where exactly
that signal is available — at least one sourced Japanese address, at least one
unsourced one — the unsourced ones are the import noise and go.

SCOPE
-----
* Japanese addresses only (`LANG(?addr) = "ja"`). The romanised (`en`) values are
  the same address written twice and are handled as exceptions on the review
  page, not here.
* Only items that have BOTH a cited and an uncited Japanese address. An item
  whose addresses are all uncited keeps them — there is no signal to choose by.
* Hand-reviewed exceptions are skipped: Emma confirmed those addresses correct.

THE HAZARD THIS GUARDS
----------------------
QuickStatements removes a statement by matching its **value**, not its GUID. If
an uncited address had the same text as a cited one, `-Q1|P6375|ja:"x"` could
delete the cited statement instead. Any item where an uncited value equals one of
its cited values is therefore refused and reported, never emitted. (Checked
against live data 2026-07-09: zero such items — but the check stays, because the
day it stops being zero is the day it silently destroys a sourced address.)

REMOVE-ONLY, therefore drip-safe. It is also small enough to run as a browser
batch, which is what `--print-url` is for.

    python generate_uncited_address_removals.py [--out FILE] [--print-url]
"""
import argparse
import collections
import io
import json
import os
import shutil
import sys
import time
import urllib.parse

import requests

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts",
    "Accept": "application/sparql-results+json",
}

RONSHA = "Q135022904"
OUTPUT_FILE = "uncited_address_removals.txt"
QS_URL = "https://quickstatements.toolforge.org/#/v1="

# Emma reviewed these personally: their several addresses are correct as they
# stand, so they are not a cited-vs-uncited choice at all.
EXCEPTIONS = {
    "Q10885171",   # Izawa-no-miya
    "Q10896675",   # Izumo-daijingū
    "Q11379325",   # Izawa Shrine
    "Q11457393",   # Samugawa Shrine
    "Q114593121",  # Baba Tsutsukowake Shrine
}

_last = 0.0


def sparql(query):
    global _last
    for attempt in range(5):
        gap = time.time() - _last
        if gap < 3:
            time.sleep(3 - gap)
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


def build_query():
    """One row per Japanese P6375 statement, with how many references it carries."""
    return f"""
    SELECT ?item ?st ?addr (COUNT(DISTINCT ?ref) AS ?nrefs) WHERE {{
      ?item wdt:P31 wd:{RONSHA} ; p:P6375 ?st .
      ?st ps:P6375 ?addr .
      FILTER(LANG(?addr) = "ja")
      OPTIONAL {{ ?st prov:wasDerivedFrom ?ref }}
    }} GROUP BY ?item ?st ?addr
    """


def plan_removals(by_item):
    """{item: [addr, ...]} to remove, plus the items refused for a value collision.

    `by_item` maps qid -> [(address_text, n_references), ...].
    """
    removals, collisions = {}, {}
    for qid, statements in sorted(by_item.items()):
        if qid in EXCEPTIONS:
            continue
        cited = [a for a, n in statements if n > 0]
        uncited = [a for a, n in statements if n == 0]
        if not cited or not uncited:
            continue
        clash = set(uncited) & set(cited)
        if clash:
            # Value-matched removal cannot distinguish the two statements.
            collisions[qid] = sorted(clash)
            continue
        removals[qid] = uncited
    return removals, collisions


def is_quotable(text):
    """An embedded double quote leaves QS's splitter inside-out. A pipe is safe."""
    return '"' not in text


def qs_removal(qid, addr):
    return f'-{qid}|P6375|ja:"{addr}"'


def qs_batch_url(lines):
    """QuickStatements v1 URL form: `|` separates fields, `||` separates commands."""
    return QS_URL + urllib.parse.quote("||".join(lines), safe="")


def publish_to_site(path):
    """Mirror the batch into _site/ so the dashboard can link it."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser()
    # direct_daily_edits reads ATOMIC_FILES by BARE NAME from this directory and
    # silently `continue`s past a missing path, so a batch written only under
    # _site/ never reaches Wikidata. Write where the editor looks; copy to _site.
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--print-url", action="store_true",
                    help="print a QuickStatements batch URL for the whole file")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("Querying Japanese P6375 addresses on Shikinai Ronsha...", flush=True)
    rows = sparql(build_query())

    by_item = collections.defaultdict(list)
    for r in rows:
        by_item[r["item"]["value"].rsplit("/", 1)[-1]].append(
            (r["addr"]["value"], int(r["nrefs"]["value"]))
        )
    print(f"  {len(by_item)} items carry at least one Japanese address")

    removals, collisions = plan_removals(by_item)

    lines = []
    for qid, addrs in removals.items():
        for addr in addrs:
            if not is_quotable(addr):
                print(f"  skipping unquotable address on {qid}: {addr!r}")
                continue
            lines.append(qs_removal(qid, addr))

    path = args.out
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    publish_to_site(path)

    print(f"\n  {len(lines)} uncited addresses removed across {len(removals)} items")
    if collisions:
        print(f"  REFUSED {len(collisions)} item(s): an uncited value equals a cited value,")
        print("    so a value-matched removal could delete the sourced statement:")
        for qid, clash in collisions.items():
            print(f"      {qid}: {clash}")
    print(f"  wrote {path}")

    if args.print_url and lines:
        print("\nQuickStatements batch URL:")
        print(qs_batch_url(lines))


if __name__ == "__main__":
    main()
