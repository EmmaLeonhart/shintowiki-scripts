"""
ONE-OFF: emit a QuickStatements CREATE batch for the Japanese court-rank ITEMS
that ja.wikipedia has recipient categories for but Wikidata is missing.

Emma creates these herself in the QuickStatements web tool (she asked for a
GitHub link to the batch), then sends the resulting QIDs back so the people
pipeline (generate_court_rank_quickstatements.py) can map every rank exactly.

Wikidata currently has only the 16 base ranks (all P31 = Q99196082 "court rank
in Japan"). Missing = the 20 upper/lower splits (正四位上/下 … 従八位上/下), the 4
初位 grades (大初位上/下, 少初位上/下), the 2 外位 (外従五位上/下) and base 従八位.

Each created item gets: ja + en label, ja + en description, P31 = Q99196082 —
mirroring the existing base rank items. Output is TAB-separated QuickStatements
V1 (paste-ready in the QS web tool). The script re-derives the missing set LIVE
from ja.wp and asserts it equals EN_LABELS, so a drift on either side errors
loudly instead of silently creating the wrong items.

Output: modern-quickstatements/court_rank_item_creates.txt
Read-only against WDQS + ja.wp; writes only the .txt (it does not edit Wikidata).
"""

import os
import sys

import generate_court_rank_quickstatements as base

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "court_rank_item_creates.txt")
COURT_RANK_CLASS = "Q99196082"  # "court rank in Japan"

# ja rank name -> en label. Keys must equal the LIVE unmatched recipient-category
# rank names (asserted below). 上 = Upper Grade, 下 = Lower Grade; 正 Senior, 従 Junior.
EN_LABELS = {
    "従八位": "Junior Eighth Rank",
    "正四位上": "Senior Fourth Rank, Upper Grade",
    "正四位下": "Senior Fourth Rank, Lower Grade",
    "従四位上": "Junior Fourth Rank, Upper Grade",
    "従四位下": "Junior Fourth Rank, Lower Grade",
    "正五位上": "Senior Fifth Rank, Upper Grade",
    "正五位下": "Senior Fifth Rank, Lower Grade",
    "従五位上": "Junior Fifth Rank, Upper Grade",
    "従五位下": "Junior Fifth Rank, Lower Grade",
    "正六位上": "Senior Sixth Rank, Upper Grade",
    "正六位下": "Senior Sixth Rank, Lower Grade",
    "従六位上": "Junior Sixth Rank, Upper Grade",
    "従六位下": "Junior Sixth Rank, Lower Grade",
    "正七位上": "Senior Seventh Rank, Upper Grade",
    "正七位下": "Senior Seventh Rank, Lower Grade",
    "従七位上": "Junior Seventh Rank, Upper Grade",
    "従七位下": "Junior Seventh Rank, Lower Grade",
    "正八位上": "Senior Eighth Rank, Upper Grade",
    "正八位下": "Senior Eighth Rank, Lower Grade",
    "従八位上": "Junior Eighth Rank, Upper Grade",
    "従八位下": "Junior Eighth Rank, Lower Grade",
    "大初位上": "Greater Initial Rank, Upper Grade",
    "大初位下": "Greater Initial Rank, Lower Grade",
    "少初位上": "Lesser Initial Rank, Upper Grade",
    "少初位下": "Lesser Initial Rank, Lower Grade",
    "外従五位上": "Outer Junior Fifth Rank, Upper Grade",
    "外従五位下": "Outer Junior Fifth Rank, Lower Grade",
}


def live_missing_rank_names():
    rank_map = base.rank_label_to_qid()
    subs = base.subcategories(base.PARENT_CAT)
    missing = []
    for c in subs:
        name = c.split(":", 1)[1] if ":" in c else c
        if not name.endswith(base.RANK_SUFFIX):
            continue
        rank = name[: -len(base.RANK_SUFFIX)]
        if rank not in rank_map:
            missing.append(rank)
    return set(missing)


def main():
    base._utf8()
    live = live_missing_rank_names()
    keys = set(EN_LABELS)
    if live != keys:
        print("MISMATCH between live ja.wp unmatched ranks and EN_LABELS:")
        print("  only live (need EN label):", sorted(live - keys))
        print("  only in map (no longer missing / typo):", sorted(keys - live))
        raise SystemExit("Refusing to write a drifted CREATE batch — reconcile EN_LABELS first.")

    lines = []
    for ja in EN_LABELS:                       # dict preserves insertion order
        en = EN_LABELS[ja]
        lines.append("CREATE")
        lines.append(f'LAST\tLja\t"{ja}"')
        lines.append(f'LAST\tLen\t"{en}"')
        lines.append('LAST\tDen\t"court rank in Japan"')
        lines.append('LAST\tDja\t"日本の位階"')
        lines.append(f"LAST\tP31\t{COURT_RANK_CLASS}")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote CREATE batch for {len(EN_LABELS)} court-rank items -> {OUT}")


if __name__ == "__main__":
    main()
