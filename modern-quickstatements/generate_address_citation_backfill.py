#!/usr/bin/env python3
"""
generate_address_citation_backfill.py
======================================
Citation backfill for the non-同上 imported addresses (queue.md 同上 rung).

The original Shikinaisha import copied 所在地 cells from the jawiki
per-district 式内社一覧 templates without any reference. The 同上 cells
are being corrected by the doujou pipeline; the rows that carried a REAL
address are correct on Wikidata but still uncited. This script emits the
same reference pair Emma specified for the doujou re-adds —
S143 = Q177837 (imported from: Japanese Wikipedia) +
S4656 = the list-article URL — onto those existing claims.

Method (bounded, no guessing):
 1. Parse every per-district table template of the list article
    (reusing resolve_doujou_addresses' fetch/parse), collecting every
    row that carries a real address (prefecture-prefixed cell), with
    rowspan name carry-down.
 2. SPARQL for P6375@ja statements that (a) have NO reference at all and
    (b) whose value is one of those row addresses — the VALUES join IS
    the row-address == claim-address gate.
 3. Only emit when the item's ja label matches a name cell of a row
    carrying exactly that address (label_matches_names, same matcher the
    resolver uses). Non-matching bindings are printed, never guessed.

Each line re-states the existing claim with references:
    Qxxx|P6375|ja:"島根県..."|S143|Q177837|S4656|"https://ja.wikipedia.org/wiki/..."
direct_daily_edits.py finds the existing claim by value and attaches the
reference group (wbsetreference; identical references are hash-deduped
by Wikibase, so a re-applied line is a no-op). Once the statement has a
reference it drops out of the SPARQL and the item converges — same
re-derive-from-live-state design as generate_doujou_address_fixes.py.

Deliberately slow via the daily drip; multi-year convergence is fine.
"""

import io
import re
import sys

import requests

from resolve_doujou_addresses import (
    JA_API, LIST_ARTICLE, PREF_RE, SPARQL, UA,
    fetch_wikitext, label_matches_names, parse_rows,
)

OUTPUT_FILE = "address_citation_backfill.txt"
JAWIKI_ITEM = "Q177837"  # Japanese Wikipedia

NAME_RE = re.compile(r"神社|大社|神宮|社$")


def collect_address_rows(template_titles, fetch=fetch_wikitext):
    """Every row of every district table that carries a real address:
    [{"names": [...], "address": str, "template": str}]. Rows whose name
    cell is a rowspan continuation inherit the previous row's names."""
    rows = []
    for title in template_titles:
        text = fetch(title)
        last_names: list = []
        for cells in parse_rows(text):
            names = [c for c in cells if NAME_RE.search(c)]
            addr = next((c for c in cells if PREF_RE.match(c)), None)
            if addr:
                rows.append({"names": names or last_names,
                             "address": addr,
                             "template": title})
            if names:
                last_names = names
    return rows


def build_lines(bindings, addr_rows, url):
    """(lines, skipped) from SPARQL bindings [(qid, ja_label, addr)].
    A line is emitted only when the label matches a name cell of a row
    carrying that exact address; everything else lands in skipped."""
    lines, skipped, seen = [], [], set()
    for qid, label, addr in bindings:
        key = (qid, addr)
        if key in seen:
            continue
        seen.add(key)
        rows = addr_rows.get(addr, [])
        if any(label_matches_names(label, r["names"]) for r in rows):
            lines.append(
                f'{qid}|P6375|ja:"{addr}"|S143|{JAWIKI_ITEM}|S4656|"{url}"')
        else:
            skipped.append((qid, label, addr))
    return lines, skipped


def fetch_unreferenced(addresses):
    """[(qid, ja_label, addr)] for P6375@ja statements with no reference
    whose value is one of `addresses`. None on rate-limit."""
    values = " ".join(f'"{a}"@ja' for a in sorted(addresses))
    q = f"""SELECT ?item ?jaLabel ?addr WHERE {{
  VALUES ?addr {{ {values} }}
  ?item p:P6375 ?st .
  ?st ps:P6375 ?addr .
  FILTER NOT EXISTS {{ ?st prov:wasDerivedFrom ?ref }}
  ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja")
}}"""
    r = requests.post(SPARQL, data={"query": q, "format": "json"},
                      headers=UA, timeout=120)
    if r.status_code == 429:
        return None
    r.raise_for_status()
    return [(b["item"]["value"].rsplit("/", 1)[-1],
             b["jaLabel"]["value"],
             b["addr"]["value"])
            for b in r.json()["results"]["bindings"]]


def main():
    import urllib.parse
    # In main, not at import: tests import this module under pytest capture.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    list_text = fetch_wikitext(LIST_ARTICLE)
    templates = re.findall(r"\{\{(出雲国[^{}]*?の式内社一覧)\}\}", list_text)
    print(f"District templates: {len(templates)}")

    rows = collect_address_rows([f"Template:{t}" for t in templates])
    addr_rows = {}
    for row in rows:
        addr_rows.setdefault(row["address"], []).append(row)
    print(f"Rows with real addresses: {len(rows)} ({len(addr_rows)} distinct addresses)")

    bindings = fetch_unreferenced(addr_rows.keys())
    if bindings is None:
        print("WARNING: Wikidata 429 — aborting; writing no lines this run")
        open(OUTPUT_FILE, "w", encoding="utf-8").close()
        return
    print(f"Unreferenced P6375@ja statements matching a row address: {len(bindings)}")

    url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(LIST_ARTICLE)
    lines, skipped = build_lines(bindings, addr_rows, url)

    # Sorted at the writer, per DEVLOG 2026-08-21: WDQS row order is not stable, so
    # emitting in result order rewrote all 76 lines of this file every build.
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in sorted(set(lines)):
            f.write(line + "\n")
    print(f"Wrote {len(lines)} reference-backfill lines -> {OUTPUT_FILE}")
    for qid, label, addr in skipped:
        print(f"  skipped (label≠row names for this address): {qid} {label} {addr}")


if __name__ == "__main__":
    main()
