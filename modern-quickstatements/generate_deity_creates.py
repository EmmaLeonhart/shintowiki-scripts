#!/usr/bin/env python3
"""Create batches for the deity work Emma asked for on 2026-09-28.

1. deity_creates.txt: one new item per RED-LINK deity name in saijin_unresolved.json,
   i.e. a name a jawiki shrine article links to a deity page that doesn't exist.
   Emma: "All 198." Each item gets its Japanese label and P31 = kami (Q524158).
   A name that already has an item with that exact Japanese label (any class) is
   SKIPPED: create_items.py has no duplicate guard (Emma's call, 2026-08-04), so the
   check lives here and is redone every run, before create-items runs.

2. deity_role_creates.txt: the single "deified person" item that the P3831
   (object has role) qualifier on shrine -> deified-person P825 statements points to.
   Emma chose a new item over hitogami (Q11376147) or deification (Q11693234).

After creation, the red-link names match their new items by exact label in
generate_saijin_deity_research.py, so shrine -> deity P825 statements follow by
themselves, and the drip delivers them.

GENERATOR ONLY: writes the two batch files; create_items.py does the creating.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import wdqs_transport  # noqa: E402

UNRESOLVED = os.path.join(HERE, "saijin_unresolved.json")
DEITY_OUT = os.path.join(HERE, "deity_creates.txt")
ROLE_OUT = os.path.join(HERE, "deity_role_creates.txt")
KAMI = "Q524158"
HUMAN = "Q5"

ROLE_BLOCK = [
    "CREATE",
    'LAST|Len|"deified person"',
    'LAST|Lja|"神格化された人物"',
    'LAST|Den|"person venerated as a deity, e.g. enshrined as a kami"',
    f"LAST|P279|{HUMAN}",
]


def red_link_names(path=UNRESOLVED):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return list(json.load(fh).get("red_link", {}))
    except FileNotFoundError:
        return []


def usable(name):
    """A label QuickStatements can carry and that looks like a single name."""
    return bool(name) and '"' not in name and "|" not in name and len(name) <= 60


def existing_ja_labels(names):
    """Names that already are some item's exact Japanese label (any class)."""
    found = set()
    names = sorted(set(names))
    for i in range(0, len(names), 100):
        values = " ".join('"%s"@ja' % n.replace("\\", "\\\\") for n in names[i:i + 100])
        rows = wdqs_transport.query(
            "SELECT DISTINCT ?name WHERE { VALUES ?name { %s } ?item rdfs:label ?name . }" % values,
            post=True)
        found.update(r["name"]["value"] for r in rows)
    return found


def deity_blocks(names, existing):
    out = []
    for n in names:
        if n in existing or not usable(n):
            continue
        out += ["CREATE", f'LAST|Lja|"{n}"', f"LAST|P31|{KAMI}"]
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    names = red_link_names()
    existing = existing_ja_labels([n for n in names if usable(n)]) if names else set()
    blocks = deity_blocks(names, existing)
    n_items = blocks.count("CREATE")
    header = ["# One new kami item per red-link 祭神 name (Emma 2026-09-28: 'All 198').",
              "# Regenerated each run; names that already have an item are skipped.",
              "# Batch for create_items.py (gate: lockout_gate)."]
    io.open(DEITY_OUT, "w", encoding="utf-8", newline="\n").write("\n".join(header + blocks) + "\n")
    io.open(ROLE_OUT, "w", encoding="utf-8", newline="\n").write(
        "# The 'deified person' role item (Emma 2026-09-28).\n" + "\n".join(ROLE_BLOCK) + "\n")
    print(f"{len(names)} red-link names; {len(existing)} already have an item; "
          f"{n_items} to create -> {DEITY_OUT}")


if __name__ == "__main__":
    main()
