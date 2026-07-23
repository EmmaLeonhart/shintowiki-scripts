"""
Bidirectionally link each Japanese court-rank ITEM to its ja.wikipedia RECIPIENT
CATEGORY (Emma 2026-07-23: "we should be bidirectionally linking to the categories too").

For every per-rank category Category:<rank>受位者 under [[Category:日本の位階受位者]]:
  rank item  --P1792 (category of associated people)-->  category item
  category item  --P301 (category's main topic)-->  rank item

18 of the 42 recipient categories already have a Wikidata item (bare, P31 only) —
those just get the two link statements. The other 24 have no item, so this CREATEs
them (jawiki sitelink + ja label + P31 Q4167836 Wikimedia category), mirroring the
existing convention (e.g. Q61007463 = Category:正四位受位者), then links via LAST.

Rank QIDs: base ranks from the court-rank class (WDQS), merged with the sub-rank +
外従五位 items created 2026-07-23 (hardcoded, authoritative, immune to WDQS lag).
Add-only: existing category items have no P301 and rank items have no P1792 today.

Output: modern-quickstatements/court_rank_category_links.txt  (paste-ready QS V1)
Writes only the .txt; read-only against WDQS + ja.wp.
"""

import os

import generate_court_rank_quickstatements as g

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "court_rank_category_links.txt")
CAT_CLASS = "Q4167836"      # Wikimedia category
P_TOPIC_CAT = "P1792"       # category of associated people (rank -> category)
P_CAT_TOPIC = "P301"        # category's main topic (category -> rank)

# rank items created 2026-07-23 (ja label -> QID); merged over the WDQS class map
# so every rank resolves even before WDQS indexes the new items.
NEW_RANK_QIDS = {
    "正四位上": "Q140679480", "正四位下": "Q140679481",
    "従四位上": "Q140679482", "従四位下": "Q140679483",
    "正五位上": "Q140679485", "正五位下": "Q140679486",
    "従五位上": "Q140679487", "従五位下": "Q140679488",
    "正六位上": "Q140679489", "正六位下": "Q140679491",
    "従六位上": "Q140679492", "従六位下": "Q140679493",
    "正七位上": "Q140679494", "正七位下": "Q140679495",
    "従七位上": "Q140679497", "従七位下": "Q140679498",
    "正八位上": "Q140679499", "正八位下": "Q140679500",
    "従八位上": "Q140679501", "従八位下": "Q140679502",
    "大初位上": "Q140679503", "大初位下": "Q140679505",
    "少初位上": "Q140679506", "少初位下": "Q140679507",
    "外従五位上": "Q140679508", "外従五位下": "Q140679509",
    "外従五位": "Q140679675",
}


def category_qids(cat_titles):
    """{category title -> Wikidata QID or None} via ja.wp pageprops, 40/batch."""
    out = {}
    for i in range(0, len(cat_titles), 40):
        batch = cat_titles[i:i + 40]
        d = g._ja_api({"action": "query", "prop": "pageprops",
                       "ppprop": "wikibase_item", "titles": "|".join(batch)})
        for p in d.get("query", {}).get("pages", {}).values():
            out[p["title"]] = p.get("pageprops", {}).get("wikibase_item")
    return out


def main():
    g._utf8()
    rank_map = dict(g.rank_label_to_qid())     # base ranks (+ any indexed new ones)
    rank_map.update(NEW_RANK_QIDS)             # ensure all new ones resolve

    subs = g.subcategories(g.PARENT_CAT)
    recips = [c for c in subs
              if (c.split(":", 1)[1] if ":" in c else c).endswith(g.RANK_SUFFIX)]
    cat_q = category_qids(recips)

    lines, skipped = [], []
    for cat in recips:
        name = cat.split(":", 1)[1] if ":" in cat else cat
        rank_name = name[: -len(g.RANK_SUFFIX)]
        rank_qid = rank_map.get(rank_name)
        if not rank_qid:
            skipped.append(name)
            continue
        cq = cat_q.get(cat)
        if cq:                                  # category item exists — link only
            lines.append(f"{cq}\t{P_CAT_TOPIC}\t{rank_qid}")
            lines.append(f"{rank_qid}\t{P_TOPIC_CAT}\t{cq}")
        else:                                   # create the category item, then link
            # sitelink + label use the FULL title incl. "Category:" (mirrors the
            # existing convention, e.g. Q61007463); a bare name would sitelink to a
            # mainspace article instead of the category.
            lines.append("CREATE")
            lines.append(f'LAST\tSjawiki\t"{cat}"')
            lines.append(f'LAST\tLja\t"{cat}"')
            lines.append(f"LAST\tP31\t{CAT_CLASS}")
            lines.append(f"LAST\t{P_CAT_TOPIC}\t{rank_qid}")
            lines.append(f"{rank_qid}\t{P_TOPIC_CAT}\tLAST")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    created = sum(1 for ln in lines if ln == "CREATE")
    linked_existing = sum(1 for ln in lines if ln.endswith(CAT_CLASS)) * 0  # noqa
    print(f"{len(recips)} recipient categories: created {created}, "
          f"linked {len(recips) - created - len(skipped)} existing, skipped {len(skipped)}.")
    if skipped:
        print("  skipped (no rank item):", skipped)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
