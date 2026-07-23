"""
ONE-OFF: emit a QuickStatements CREATE batch for the Japanese court-rank SUB-RANK
items that ja.wikipedia categorises people under but Wikidata has no OWN item for.

Context (verified live 2026-07-23 against the class Q99196082 "court rank in Japan"):
the base ranks all already exist as items (正一位…従八位, 大初位, 少初位, 外位, …).
The finer grades (正四位上/下, 大初位上/下, 外従五位上/下, …) currently exist ONLY as
skos aliases on their base item — NOT as their own items — so people can't be tagged
at that granularity via P14005. 従六位上/下 don't exist even as aliases.

So this batch CREATES only the sub-ranks that lack their own item, and links each to
its parent base rank (Emma 2026-07-23: "sub-ranks like Junior Eighth Rank, Lower Grade
should link to the higher ones like Junior Eighth Rank"). It NEVER recreates a rank
that already has its own item — the existence test is the item's PRIMARY ja label
under Q99196082, built live, so nothing existing is duplicated.

Each created sub-rank gets: ja+en label, ja+en description, P31 = Q99196082 (so the
P14005 value constraint is satisfied on its own), and LINK_PROP -> parent base rank.

LINK_PROP is P279 (subclass of) by default — PENDING Emma's confirmation (P279
subclass-of vs P361 part-of). Nothing should be run until she confirms.

Output: modern-quickstatements/court_rank_item_creates.txt  (paste-ready QS V1, TAB)
Read-only against WDQS + ja.wp; writes only the .txt.
"""

import os
import sys

import generate_court_rank_quickstatements as base

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "court_rank_item_creates.txt")
COURT_RANK_CLASS = "Q99196082"          # "court rank in Japan"
LINK_PROP = "P279"                      # subclass of — PENDING Emma confirm (vs P361 part of)

# en label per sub-rank ja name (base 従八位 removed — it already exists).
EN_LABELS = {
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

# Parent base rank for names whose "strip the 上/下" base has no own item.
# 外従五位 (outer junior fifth) has no base item; its alias lives on 外位 (Q11430321).
SPECIAL_PARENT = {"外従五位": "Q11430321"}   # 外位 — FLAG for Emma to confirm vs 従五位 Q11071125


def existing_by_primary_label():
    """{primary ja label -> QID} for every item under the court-rank class."""
    rows = base._sparql(
        'SELECT ?item ?ja WHERE { '
        '?item (wdt:P31|wdt:P279)/wdt:P279* wd:%s . '
        '?item rdfs:label ?ja . FILTER(LANG(?ja)="ja") }' % COURT_RANK_CLASS
    )
    return {b["ja"]["value"]: b["item"]["value"].rsplit("/", 1)[1] for b in rows}


def needed_rank_names():
    """ja.wp recipient-category rank names that have NO own item yet."""
    existing = existing_by_primary_label()
    subs = base.subcategories(base.PARENT_CAT)
    need = []
    for c in subs:
        name = c.split(":", 1)[1] if ":" in c else c
        if not name.endswith(base.RANK_SUFFIX):
            continue
        rank = name[: -len(base.RANK_SUFFIX)]
        if rank not in existing:            # no OWN item (alias-only or absent)
            need.append(rank)
    return need, existing


def parent_qid(rank, existing):
    base_name = rank[:-1] if rank[-1] in "上下" else rank
    if base_name in existing:
        return existing[base_name]
    return SPECIAL_PARENT.get(base_name)


def main():
    base._utf8()
    need, existing = needed_rank_names()
    need_set, keys = set(need), set(EN_LABELS)
    if need_set != keys:
        print("MISMATCH between live need-to-create set and EN_LABELS:")
        print("  live-needs, no EN label:", sorted(need_set - keys))
        print("  in map but not needed (already has own item now):", sorted(keys - need_set))
        raise SystemExit("Reconcile EN_LABELS before writing (something changed on Wikidata).")

    lines, unresolved = [], []
    for rank in EN_LABELS:                   # stable order
        pq = parent_qid(rank, existing)
        if not pq:
            unresolved.append(rank)
            continue
        en = EN_LABELS[rank]
        lines.append("CREATE")
        lines.append(f'LAST\tLja\t"{rank}"')
        lines.append(f'LAST\tLen\t"{en}"')
        lines.append('LAST\tDen\t"court rank in Japan"')
        lines.append('LAST\tDja\t"日本の位階"')
        lines.append(f"LAST\tP31\t{COURT_RANK_CLASS}")
        lines.append(f"LAST\t{LINK_PROP}\t{pq}")

    if unresolved:
        raise SystemExit(f"No parent QID for: {unresolved} — fix SPECIAL_PARENT.")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote CREATE batch for {len(EN_LABELS)} sub-rank items "
          f"(link={LINK_PROP}) -> {OUT}")


if __name__ == "__main__":
    main()
