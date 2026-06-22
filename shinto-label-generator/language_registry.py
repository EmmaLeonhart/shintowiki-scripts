"""
language_registry.py — B3: the single source of truth for shrine-label
generator coverage across every language in query.csv.

`COVERED` maps each language we already generate to (generator script, method).
`split_coverage` partitions the query.csv language list into the covered set and
the uncovered "long tail" (todo), sorted by label count so the next generators
to build are obvious. Source/pipeline languages (ja, en) and the special `mul`
bucket are not counted as todo.

Run `python language_registry.py` to print/refresh the coverage report
(also written to ../docs/language_coverage.md by report_coverage.py).
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Languages already generated, with the script and transliteration method.
COVERED = {
    # 15-language non-CJK multilang generator (en-primary, id-fallback)
    "tr": ("generate_multilang_quickstatements.py", "affix"),
    "de": ("generate_multilang_quickstatements.py", "affix"),
    "nl": ("generate_multilang_quickstatements.py", "affix"),
    "es": ("generate_multilang_quickstatements.py", "affix"),
    "it": ("generate_multilang_quickstatements.py", "affix"),
    "eu": ("generate_multilang_quickstatements.py", "affix"),
    "lt": ("generate_multilang_quickstatements.py", "declension"),
    "ru": ("generate_multilang_quickstatements.py", "cyrillic+declension"),
    "uk": ("generate_multilang_quickstatements.py", "cyrillic+declension"),
    "fa": ("generate_multilang_quickstatements.py", "perso-arabic"),
    "ar": ("generate_multilang_quickstatements.py", "arabic"),
    "arz": ("generate_multilang_quickstatements.py", "arabic"),
    "hi": ("generate_multilang_quickstatements.py", "devanagari"),
    "fr": ("generate_multilang_quickstatements.py", "affix"),
    "pt": ("generate_multilang_quickstatements.py", "affix"),
    "vi": ("generate_multilang_quickstatements.py", "affix"),
    "bn": ("generate_multilang_quickstatements.py", "bengali-abugida"),
    "ca": ("generate_multilang_quickstatements.py", "affix"),
    "gl": ("generate_multilang_quickstatements.py", "affix"),
    "sv": ("generate_multilang_quickstatements.py", "affix-suffix"),
    "nb": ("generate_multilang_quickstatements.py", "affix-suffix"),
    "da": ("generate_multilang_quickstatements.py", "affix-suffix"),
    "hu": ("generate_multilang_quickstatements.py", "affix-suffix"),
    "la": ("generate_multilang_quickstatements.py", "affix"),
    "ast": ("generate_multilang_quickstatements.py", "affix"),
    "sh": ("generate_multilang_quickstatements.py", "affix"),
    "hr": ("generate_multilang_quickstatements.py", "affix"),
    "el": ("generate_multilang_quickstatements.py", "greek"),
    "az": ("generate_multilang_quickstatements.py", "affix"),
    "tl": ("generate_multilang_quickstatements.py", "affix"),
    "war": ("generate_multilang_quickstatements.py", "affix"),
    "min": ("generate_multilang_quickstatements.py", "affix"),
    "eo": ("generate_multilang_quickstatements.py", "affix"),
    "jv": ("generate_multilang_quickstatements.py", "affix"),
    # CJK + special cases
    "zh": ("generate_chinese_quickstatements.py", "cjk-manyogana"),
    "zh-hant": ("generate_chinese_quickstatements.py", "opencc-s2t"),
    "zh-tw": ("generate_chinese_quickstatements.py", "opencc-s2tw"),
    "zh-hk": ("generate_chinese_quickstatements.py", "opencc-s2hk"),
    "zh-hans": ("generate_chinese_quickstatements.py", "simplified-base"),
    "zh-cn": ("generate_chinese_quickstatements.py", "simplified-base"),
    "zh-sg": ("generate_chinese_quickstatements.py", "simplified-base"),
    "ko": ("generate_korean_quickstatements.py", "hangul/hanja"),
    "tok": ("fetch_shrines_tokiponize.py", "tokiponize"),
    "id": ("generate_indonesian_proposals.py", "romaji"),
}

# Not "todo": ja is the source label; en is produced by the English-label
# pipeline (Stages 0/1/2/4); mul is Wikidata's "multiple languages" bucket.
SOURCE_OR_SPECIAL = {"ja", "en", "mul"}


def load_query_csv(path=None):
    """Return [(lang, count), ...] from query.csv."""
    path = path or os.path.join(HERE, os.pardir, "query.csv")
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append((row["lang"], int(row["count"])))
    return rows


def split_coverage(rows):
    """Partition [(lang, count)] into (covered, todo). Each entry is a dict
    {lang, count, generator?, method?}. todo excludes source/special langs and
    is sorted by count descending (highest-coverage gaps first)."""
    covered, todo = [], []
    for lang, count in rows:
        if lang in COVERED:
            script, method = COVERED[lang]
            covered.append({"lang": lang, "count": count, "generator": script, "method": method})
        elif lang in SOURCE_OR_SPECIAL:
            continue
        else:
            todo.append({"lang": lang, "count": count})
    todo.sort(key=lambda d: d["count"], reverse=True)
    return covered, todo


def main():
    rows = load_query_csv()
    covered, todo = split_coverage(rows)
    print(f"Languages in query.csv: {len(rows)}")
    print(f"Covered by a generator: {len(covered)}")
    print(f"Uncovered (todo):       {len(todo)}")
    print("\nTop 25 uncovered by label count:")
    for d in todo[:25]:
        print(f"  {d['lang']:8s} {d['count']:5d}")


if __name__ == "__main__":
    main()
