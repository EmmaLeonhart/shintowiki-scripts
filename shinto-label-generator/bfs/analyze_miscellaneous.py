"""
Comprehensive analysis of bfs/miscellaneous.tsv — the thorny residual — grouped
into coarse buckets so we can decide what to do with each. Highlights TEXTS (the
group Emma flagged as easily translatable into all languages).

Offline: reads miscellaneous.tsv (qid, en, ja, p31_types). Writes
miscellaneous_analysis.md + a texts.tsv of the priority translatable set.
"""

import os
import sys
import io
import csv
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "miscellaneous.tsv")

# Ordered keyword -> bucket. First match on the item's p31_types string wins.
BUCKETS = [
    ("TEXT", ["literary work", "written work", "religious text", "book", "encyclopedia",
              "chapter", "volume", "edition", "dictionary", "text", "article", "manuscript",
              "romanization", "orthograph", "writing system", "script", "treatise", "poem",
              "anthology", "database", "periodical", "codex", "law", "legal"]),
    ("RITUAL/PRACTICE", ["festival", "ritual", "ceremony", "matsuri", "rite", "holiday",
                          "observance", "practice", "custom", "prayer", "dance"]),
    ("OBJECT/ARCHITECTURE", ["architectural", "architecture", "building", "structure",
                             "object", "artifact", "artefact", "instrument", "sword",
                             "mirror", "regalia", "treasure", "style", "gate"]),
    ("OFFICE/RANK/TITLE", ["rank", "office", "title", "position", "court", "official"]),
    ("TIME/CALENDAR", ["era", "period", "calendar", "day", "tense", "time", "year", "month",
                       "season"]),
    ("ORG/GROUP/CLAN", ["organization", "organisation", "clan", "family", "dynasty",
                        "group", "sect", "school", "company", "institution", "party"]),
    ("RELIGION/BELIEF", ["religion", "belief", "deity type", "mytholog", "spirit", "faith",
                         "cosmolog"]),
    ("INFRA/DRIFT", ["Wikimedia", "WikiProject", "Wikipedia", "template", "disambiguation",
                     "category", "metaclass", "reason for", "Wikibase", "language edition",
                     "natural language", "modern language", "dialect", "languoid", "taxon",
                     "bilateral", "embassy", "consulate", "license", "Braille", "census",
                     "Archive of Our Own", "exonym", "class", "property", "identifier"]),
]


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def bucket_of(types_str):
    low = types_str.lower()
    for name, kws in BUCKETS:
        for kw in kws:
            if kw.lower() in low:
                return name
    return "OTHER"


def main():
    _utf8()
    rows = []
    with open(SRC, encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            rows.append(row)

    by_bucket = defaultdict(list)
    for row in rows:
        by_bucket[bucket_of(row["p31_types"])].append(row)

    order = [b[0] for b in BUCKETS] + ["OTHER"]
    # write texts.tsv (whole TEXT bucket)
    texts = by_bucket.get("TEXT", [])
    with open(os.path.join(HERE, "texts.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("qid\ten\tja\tp31_types\n")
        for row in sorted(texts, key=lambda x: x["p31_types"]):
            f.write(f"{row['qid']}\t{row['en']}\t{row['ja']}\t{row['p31_types']}\n")

    # Refined: REAL Japanese texts worth translating — has a ja label, is an
    # actual work, and is NOT a covered Shikinaisha list or generic drift
    # (foreign encyclopedias, databases, Wikipedia editions, romanization systems).
    WORK = ["literary work", "written work", "religious text", "diary", "treatise",
            "poem", "anthology", "manuscript", "classic", "chronicle", "scripture"]
    DROP = ["chapter", "list", "encyclopedia", "database", "wikipedia", "wikimedia",
            "wikiproject", "romanization", "authority", "newsletter", "magazine",
            "newspaper", "periodical", "software", "website", "front end", "edition",
            "identifier", "knowledge base"]
    jp_texts = []
    for row in texts:
        low = row["p31_types"].lower()
        if row["ja"] and any(w in low for w in WORK) and not any(d in low for d in DROP):
            jp_texts.append(row)
    with open(os.path.join(HERE, "japanese_texts.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("qid\ten\tja\tp31_types\n")
        for row in sorted(jp_texts, key=lambda x: x["en"] or x["ja"]):
            f.write(f"{row['qid']}\t{row['en']}\t{row['ja']}\t{row['p31_types']}\n")

    # write analysis md
    lines = ["# Miscellaneous residual — comprehensive analysis", "",
             f"Total: **{len(rows)}** items (bfs/miscellaneous.tsv). Coarse buckets by P31:",
             "", "| Bucket | Count |", "|---|---:|"]
    for b in order:
        lines.append(f"| {b} | {len(by_bucket.get(b, []))} |")
    lines += ["", "## TEXTS (priority — easily translatable)",
              f"{len(texts)} items → `texts.tsv`. Top type-signatures:", ""]
    for sig, n in Counter(t["p31_types"] for t in texts).most_common(15):
        lines.append(f"- {n}× {sig}")
    lines += ["", "### Sample texts"]
    for row in sorted(texts, key=lambda x: x["en"])[:40]:
        lines.append(f"- {row['qid']} — {row['en'] or row['ja']}  ({row['p31_types']})")
    # brief per-bucket sample for the others
    for b in order:
        if b in ("TEXT",):
            continue
        items = by_bucket.get(b, [])
        if not items:
            continue
        lines += ["", f"## {b} ({len(items)})"]
        for row in items[:12]:
            lines.append(f"- {row['qid']} — {row['en'] or row['ja']}  ({row['p31_types']})")
    with open(os.path.join(HERE, "miscellaneous_analysis.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"{len(rows)} misc items. Buckets:")
    for b in order:
        print(f"  {b:22s} {len(by_bucket.get(b, []))}")
    print(f"\nTEXTS -> texts.tsv ({len(texts)}); full breakdown -> miscellaneous_analysis.md")


if __name__ == "__main__":
    main()
