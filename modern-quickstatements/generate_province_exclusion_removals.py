#!/usr/bin/env python3
"""Script 2 of 2: remove the two P3113 exclusions that sit on the wrong province's list.

Pair with `generate_province_exclusions.py`, which is script 1 and ADDS ONLY.
CLAUDE.md, "Add-first, remove-later via SPARQL (two scripts, never one)":

    script 1 only ADDS … script 2 only REMOVES, and only acts on items where a
    fresh SPARQL query *confirms the add already landed*. Never add+remove in one
    action — under the random run order the remove could fire before the add,
    losing data.

So this script emits nothing until Wikidata itself says the correct statement
exists. Run it AFTER the script-1 batch has been executed.

WHY ONLY TWO
------------
Six shrines were found excluded on a different province's list than their
coordinates indicate. Four of them are NOT errors, and removing them would have
destroyed correct data:

* `Osaka Gokoku Shrine` — the boundary dataset is demonstrably wrong here.
  Sumiyoshi Taisha, the *ichinomiya of Settsu*, also falls inside the 河内
  polygon. Kawachi over-extends across southern Osaka. The existing Settsu
  statement is right and the polygon is wrong.
* `Munakata Shrine` — its other list is the Imperial Palace / Heian-kyō list,
  which Emma ruled out of scope ("Just don't do it. That one is solved").
* `Kasuga Shrine (Kitakyushu)` (1.1 km) and `Oi Shrine (Shimada)` (5.8 km) sit
  close enough to a province boundary that the data cannot adjudicate them.

The two below are not border cases. Himure Hachimangū is 21 km from any other
province, and Shibi Shrine's coordinates are in Satsuma while its list is Izumi
Province, roughly 600 km away. Emma 2026-07-09: "Remove only the 2 unambiguous
errors."

    python generate_province_exclusion_removals.py [--out FILE] [--print-url]
"""
import argparse
import io
import os
import sys
import urllib.parse

from generate_province_exclusions import P_EXCLUDES, QS_URL, sparql

OUTPUT_FILE = "province_exclusion_removals.txt"

# (shrine, wrong list to remove from, correct list the add must have landed on)
CORRECTIONS = [
    # Himure Hachimangū: in Ōmi (21 km from the nearest other province), listed on Etchū.
    ("Q11509681", "Q11636380", "Q11638477"),
    # Shibi Shrine: coordinates in Satsuma, listed on Izumi Province (~600 km away).
    ("Q11605711", "Q11417778", "Q11622280"),
]


def add_landed(shrine, correct_list):
    """Does the corrected statement exist on Wikidata right now?

    This is the whole safety interlock: if the add has not landed, the removal
    is not emitted, so the shrine is never left off both lists.
    """
    rows = sparql("SELECT (COUNT(*) AS ?n) WHERE {{ wd:{} wdt:{} wd:{} }}".format(
        correct_list, P_EXCLUDES, shrine))
    return int(rows[0]["n"]["value"]) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--print-url", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    lines, blocked = [], []
    for shrine, wrong_list, correct_list in CORRECTIONS:
        if add_landed(shrine, correct_list):
            lines.append("-{}|{}|{}".format(wrong_list, P_EXCLUDES, shrine))
            print("  add landed: {} is on {} — safe to remove from {}".format(
                shrine, correct_list, wrong_list))
        else:
            blocked.append((shrine, wrong_list, correct_list))
            print("  HOLDING {}: the corrected statement on {} has not landed yet".format(
                shrine, correct_list))

    path = args.out
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")

    print("\n  {} removal(s) emitted, {} held back".format(len(lines), len(blocked)))
    print("  wrote {}".format(path))
    if not lines:
        print("\n  Nothing to do. Run the script-1 batch first, then re-run this.")
        return

    if args.print_url:
        print("\nQuickStatements batch URL:")
        print(QS_URL + urllib.parse.quote("||".join(lines), safe=""))


if __name__ == "__main__":
    main()
