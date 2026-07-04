"""
COMPREHENSIVE categorization of bfs/miscellaneous.tsv — every one of the 1269
items assigned to its actual Wikidata P31 type(s). No crude keyword buckets, no
"OTHER" catch-all: a full type census so we can decide, per real type, what to do
(translate / transliterate / skip).

Offline. Writes miscellaneous_categorized.md (full type census + items grouped by
exact type-signature).
"""

import os
import sys
import io
import csv
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "miscellaneous.tsv")
OUT = os.path.join(HERE, "miscellaneous_categorized.md")


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _utf8()
    rows = []
    with open(SRC, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rows.append(row)

    # Individual-type census: every P31 type across all items, counted.
    type_count = Counter()
    type_items = defaultdict(list)
    for r in rows:
        for t in [x.strip() for x in r["p31_types"].split(",") if x.strip()]:
            type_count[t] += 1
            type_items[t].append(r)

    # Exact type-signature groups (every item lands in exactly one).
    sig_count = Counter(r["p31_types"] for r in rows)

    lines = ["# Miscellaneous residual — COMPLETE categorization", "",
             f"All **{len(rows)}** items in bfs/miscellaneous.tsv, categorized by actual "
             f"Wikidata type (P31). {len(type_count)} distinct types; "
             f"{len(sig_count)} distinct type-signatures. Nothing is in a catch-all.", ""]

    lines += ["## Every P31 type, by item count", "", "| Count | Type |", "|---:|---|"]
    for t, n in type_count.most_common():
        lines.append(f"| {n} | {t} |")

    lines += ["", "## Items grouped by exact type-signature", ""]
    for sig, n in sig_count.most_common():
        lines.append(f"### {sig}  ({n})")
        for r in sorted((x for x in rows if x["p31_types"] == sig),
                        key=lambda x: (x["en"] or x["ja"])):
            lines.append(f"- {r['qid']} — {r['en'] or '(no en)'} / {r['ja'] or '(no ja)'}")
        lines.append("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"{len(rows)} items · {len(type_count)} distinct types · {len(sig_count)} signatures")
    print(f"-> {OUT}\n\nTop 30 types:")
    for t, n in type_count.most_common(30):
        print(f"  {n:4d}  {t}")


if __name__ == "__main__":
    main()
