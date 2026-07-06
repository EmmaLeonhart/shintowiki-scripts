#!/usr/bin/env python3
"""Add P17 (country) = Japan (Q17) to each recreation candidate whose type makes
country authoritative — physical/cultural things located in Japan: Shinto shrine,
festival, Buddhist temple, kofun. Emma 2026-07-06: "a bit more data to really run"
(beyond P31+labels — P17=Japan for shrines/festivals/temples).

Country is NOT applied to types where P17 is wrong or ill-defined for a bare item:
  * kami (Q524158)   — a deity is not "located in a country" (would need P27-style
    modelling that we cannot assert from the name alone) → skip.
  * human (Q5)       — people take P27 citizenship, not P17 → skip (left for the
    genealogy pass / human review).
  * book (Q571)      — a text's country of origin is a separate claim we don't have
    authoritatively from the name → skip.
  * null P31         — untyped → skip.

Every deleted item in this dataset is a Shinto/Japanese sub-topic recovered from
shinto.fandom.com, so P17=Japan for the four place/physical types is definitional,
not a guess. Q17 (Japan) verified against live Wikidata 2026-07-06.

Runs AFTER enrich_p31.py (reads `enrichment.p31_label`). Pure local transform; no
network. Writes `enrichment.p17` / `p17_label` / `p17_property` into each
candidate's JSON + `items/_country_summary.md`. Re-run enrich_p31 first if
build_item_json.py has regenerated the items (it drops enrichment).
"""
import io
import os
import sys
import glob
import json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(HERE, "items")

# P31 type-label → country is authoritative (physical/cultural thing IN Japan).
COUNTRY_TYPES = frozenset({"Shinto shrine", "festival", "Buddhist temple", "kofun",
                           "kofun group"})
JAPAN_QID = "Q17"


def country_for(p31_label):
    """Return (p17_qid, p17_label) if country is authoritative for this type, else
    (None, None). Pure — no network. Japan only, and only for place/physical types."""
    if p31_label in COUNTRY_TYPES:
        return JAPAN_QID, "Japan"
    return None, None


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    files = sorted(glob.glob(os.path.join(ITEMS_DIR, "Q*.json")))
    rows, assigned = [], 0
    by_type = Counter()
    for f in files:
        rec = json.load(open(f, encoding="utf-8"))
        if not rec.get("recreation_candidate"):
            continue
        enr = rec.setdefault("enrichment", {})
        p31_label = enr.get("p31_label")
        qid, lab = country_for(p31_label)
        enr["p17"] = qid
        enr["p17_label"] = lab
        enr["p17_property"] = "P17" if qid else None
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2, sort_keys=True)
        assigned += bool(qid)
        by_type[p31_label or "(untyped)"] += bool(qid)
        if qid:
            rows.append((rec["qid"], rec.get("recovered_label") or "", p31_label))

    lines = ["# Recreation-candidate P17 (country) — Japan for place/physical types\n",
             f"- Candidates given P17=Japan (Q17): **{assigned}**",
             f"- Applicable types: {', '.join(sorted(COUNTRY_TYPES))}\n",
             "P17=Japan is authoritative for these Shinto/Japanese place types (not a "
             "guess); kami/human/book/untyped are skipped (P17 wrong or unknown). See "
             "`enrich_country.py`.\n", "## By type\n"]
    for t, n in by_type.most_common():
        if n:
            lines.append(f"- {t}: {n}")
    lines += ["\n## Per-candidate\n", "| QID | en | P31 | P17 |", "|---|---|---|---|"]
    for qid, en, p31_label in sorted(rows, key=lambda r: (r[2], r[0])):
        lines.append(f"| {qid} | {en} | {p31_label} | Japan (Q17) |")
    with open(os.path.join(ITEMS_DIR, "_country_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Assigned P17=Japan to {assigned} candidates "
          f"({', '.join(sorted(COUNTRY_TYPES))}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
