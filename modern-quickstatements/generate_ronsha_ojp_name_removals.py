#!/usr/bin/env python3
"""Remove Old Japanese official names (P1448) from Shikinai Ronsha items.

Emma 2026-07-09:

    "Instances of Shikinai Ronsha (Q135022904) should not even have Old Japanese
    official names. Because these official names are not actually real official
    names. For a Ronsha, the official name will either be in modern Japanese or
    maybe middle Japanese. You should be just removing the old Japanese ones,
    because the old Japanese ones are referring to the Engishiki shrine, and
    Ronshas are not Engishiki shrines. They're said to be the same as, and linked
    to, an Engishiki shrine, but they are not an Engishiki shrine... The
    candidates' official names do not come from the Engishiki, even if they
    identify themselves as being the one in the Engishiki."

So: an `ojp-*` P1448 on a *candidate* is a name copied off the Engishiki entry it
merely claims to be, and has to go.

THE GUARD THAT MATTERS
----------------------
`P31` is not exclusive. 15 items are typed BOTH Q135022904 (Ronsha) and
Q135038714 (Disputed Shikinaisha/Shikigeisha) — those are Engishiki *entries*
that happen to also carry the Ronsha class, and their Old Japanese official name
is genuine. This script edits only **pure** Ronsha: typed Ronsha and neither
Q134917286 (Shikinaisha) nor Q135038714. (Q134917286 currently overlaps zero
Ronsha, but a separate cleanup is draining that class off Ronsha items, so the
guard covers it rather than assuming today's count holds.)

REMOVE-ONLY, therefore DRIP-SAFE
--------------------------------
No paired add, so there is no order in which a removal can fire before its
replacement. `direct_daily_edits.execute_removal` matches monolingual text on
text *and* language and removes exactly ONE claim per line, so an item holding
the same Old Japanese name twice needs two lines. A surplus line simply reports
"Claim not found for removal".

    python generate_ronsha_ojp_name_removals.py [--out FILE]
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import collections
import io
import json
import os
import shutil
import sys

import wdqs_transport
import time

import requests


RONSHA = "Q135022904"          # Shikinai Ronsha — the candidate class
SHIKINAISHA = "Q134917286"     # Shikinaisha — a real Engishiki shrine
DISPUTED_ENTRY = "Q135038714"  # Disputed Shikinaisha or Shikigeisha — an entry

OUTPUT_FILE = "ronsha_ojp_name_removals.txt"



def sparql(query):
    """One WDQS query, through the shared transport.

    ⚠ `throttle=3` is not a copied constant, it is this file's own figure. It
    paced itself at 3s, above the 2.5s floor, by its author's choice; the transport
    would otherwise have run it at 2.5 and made it LESS polite than it was. The
    floor is a floor, so the parameter can only slow a caller down.

    What it gains: the repo's 15/45/135 backoff in place of 10/20/30/40 — fewer
    attempts (4 rather than 5) but a far harder escalation, 195s of waiting against
    100s, which is the right direction for a service asking us to ease off.

    It keeps what mattered: `strict=False`, now in `_parse_bindings`. Until
    2026-09-17 the shared module parsed strictly, and migrating this file would
    have been a downgrade — a raw newline in a literal would have been retried
    three times and then raised.
    """
    return wdqs_transport.query(query, timeout=180, throttle=3)


def build_query():
    """One row per statement (bag semantics — an item holding the same name twice
    yields two rows, and each needs its own removal line).

    The FILTER NOT EXISTS is the guard: items typed both Ronsha and one of the
    Engishiki-entry classes are entries, and their Old Japanese name is real.
    """
    return f"""
    SELECT ?item ?name WHERE {{
      ?item wdt:P31 wd:{RONSHA} .
      ?item p:P1448 ?st . ?st ps:P1448 ?name .
      FILTER(STRSTARTS(LANG(?name), "ojp"))
      FILTER NOT EXISTS {{
        ?item wdt:P31 ?cls .
        VALUES ?cls {{ wd:{SHIKINAISHA} wd:{DISPUTED_ENTRY} }}
      }}
    }}
    """


def fetch_rows():
    """Pure-Ronsha items with an Old Japanese P1448, one row per statement."""
    return sparql(build_query())


def is_quotable(text):
    """Can this value be embedded in a QS v1 line without changing its meaning?

    Only a double quote is dangerous. `split_qs_parts` toggles `in_quotes` on
    every `"`, so an embedded quote leaves the splitter inside-out and any field
    after the value gets swallowed into it. A `|` is safe — the splitter honours
    quoting, so a pipe inside the quoted value never splits (checked against
    `direct_daily_edits.split_qs_parts`, including with a trailing qualifier).

    A removal line ends at the value, so today an embedded quote would happen to
    round-trip; screen it anyway rather than depend on the line never growing.
    """
    return '"' not in text


def qs_removal(qid, text, lang):
    # QuickStatements v1 monolingual text: lang:"text"
    return f'-{qid}|P1448|{lang}:"{text}"'


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
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("Querying pure-Ronsha items with Old Japanese official names...", flush=True)
    rows = fetch_rows()

    lines, langs, items = [], collections.Counter(), set()
    for r in rows:
        qid = r["item"]["value"].rsplit("/", 1)[-1]
        name = r["name"]["value"]
        lang = r["name"].get("xml:lang")
        if not lang or not lang.startswith("ojp"):
            continue
        if not is_quotable(name):
            print(f"  skipping unquotable value on {qid}: {name!r}")
            continue
        lines.append(qs_removal(qid, name, lang))
        langs[lang] += 1
        items.add(qid)

    path = args.out
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    # Sorted at the writer, per DEVLOG 2026-08-21: WDQS row order is not stable, so
    # emitting in result order rewrote all 1,739 lines of this file every build.
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(sorted(set(lines))) + "\n")
    publish_to_site(path)

    print(f"\n  {len(lines)} removals across {len(items)} items")
    for lang, n in langs.most_common():
        print(f"    {lang}: {n}")
    print(f"  wrote {path}")


if __name__ == "__main__":
    main()
