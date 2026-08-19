"""
Add English labels to the court-rank RECIPIENT CATEGORY items (Emma 2026-07-24:
"the categories need english labels ... lacking them is a bother").

For each of the 42 ja.wp recipient categories under [[Category:日本の位階受位者]] that
has a Wikidata item, set:
    Len = "Category:Recipients of <english rank label>"
e.g. Category:正四位上受位者 (Q140685601) -> "Category:Recipients of Senior Fourth
Rank, Upper Grade". The English rank label is read live from the rank item, so it
tracks whatever the rank items actually say.

Add-only: skips any category that already has an en label. Rank QIDs come from the
court-rank class (WDQS) merged with the 2026-07-23/24 sub-rank + 外従五位 items
(hardcoded, immune to WDQS lag); en labels are read from the Wikidata API (current,
no query-service lag).

Output: modern-quickstatements/court_rank_category_en_labels.txt  (paste-ready QS V1)
Writes only the .txt.
"""

import os
import requests

import generate_court_rank_quickstatements as g
from generate_court_rank_category_links import NEW_RANK_QIDS
from shinto_miraheze.ua_contact import contact
from shinto_miraheze.wd_pace import wd_pace

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "court_rank_category_en_labels.txt")
WD_API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": "ShintoWikiCourtRank/1.0 ({contact('wikidata')})"}


def _wb(ids_or_titles, by="ids"):
    """wbgetentities helper; returns the entities dict. 50 per call."""
    out = {}
    items = list(ids_or_titles)
    for i in range(0, len(items), 50):
        batch = items[i:i + 50]
        params = {"action": "wbgetentities", "props": "labels", "format": "json"}
        if by == "ids":
            params["ids"] = "|".join(batch)
        else:
            params["sites"] = "jawiki"
            params["titles"] = "|".join(batch)
        wd_pace()
        r = requests.get(WD_API, params=params, headers=UA, timeout=60)
        r.raise_for_status()
        out.update(r.json().get("entities", {}))
    return out


def main():
    g._utf8()
    rank_map = dict(g.rank_label_to_qid())
    rank_map.update(NEW_RANK_QIDS)

    # english label per rank QID (API = current, avoids WDQS lag on new items)
    rank_ents = _wb(sorted(set(rank_map.values())), by="ids")
    en_by_qid = {q: e.get("labels", {}).get("en", {}).get("value")
                 for q, e in rank_ents.items()}

    subs = g.subcategories(g.PARENT_CAT)
    recips = [c for c in subs
              if (c.split(":", 1)[1] if ":" in c else c).endswith(g.RANK_SUFFIX)]

    cat_ents = _wb(recips, by="titles")
    # map jawiki title -> (qid, existing en label)
    title_to = {}
    for qid, e in cat_ents.items():
        if qid.startswith("-"):
            continue
        # find which requested title this entity is (via its ja label = the title)
        ja = e.get("labels", {}).get("ja", {}).get("value")
        if ja:
            title_to[ja] = (qid, e.get("labels", {}).get("en", {}).get("value"))

    lines, skipped = [], []
    for cat in recips:
        name = cat.split(":", 1)[1] if ":" in cat else cat
        rank_name = name[: -len(g.RANK_SUFFIX)]
        rank_qid = rank_map.get(rank_name)
        en_rank = en_by_qid.get(rank_qid) if rank_qid else None
        info = title_to.get(cat)          # cat items are labelled with the full "Category:..." title
        if not info or not en_rank:
            skipped.append((cat, bool(info), en_rank))
            continue
        cat_qid, existing_en = info
        if existing_en:                    # add-only
            continue
        label = f"Category:Recipients of {en_rank}"
        esc = label.replace('"', '""')
        lines.append(f'{cat_qid}\tLen\t"{esc}"')

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(recips)} categories: {len(lines)} en labels to add, {len(skipped)} skipped.")
    for s in skipped:
        print("  skip:", s)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
