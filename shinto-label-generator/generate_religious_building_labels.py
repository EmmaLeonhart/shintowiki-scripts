"""
generate_religious_building_labels.py
=====================================
Religious buildings that are NOT Shinto shrines or Buddhist temples — churches,
cathedrals, chapels, mosques, synagogues — get an English label copied from their
Wikimedia Commons category, provided that category is in Latin script (Emma
2026-07-10: "We always copy the commons category name to the English label,
assuming that the commons category is in Latin script … for mosques and churches
and synagogues").

This is **stage 1** of the religious-building label pipeline. It produces the
English seed; the multilingual stage (English → other languages, nativised per
each language's conventions) runs FROM this English label, exactly as
`generate_multilang_quickstatements.py` uses the English shrine/temple label as
its seed. Stage 2 is `generate_religious_building_multilang.py` (to come).

Non-destructive: only items with NO English label yet are emitted. Latin-script
only — a Commons category in Cyrillic/Arabic/CJK/etc. is skipped, never guessed.

Output: quickstatements/religious_building_en.txt   (<qid>|Len|"<label>")

    python generate_religious_building_labels.py             # full run (paged)
    python generate_religious_building_labels.py --limit 500 # sample
"""
import argparse
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "quickstatements", "religious_building_en.txt")
WDQS = "https://query.wikidata.org/sparql"
UA = "ShintoWikiReligiousBuilding/1.0 (immanuelleleonhart@gmail.com)"

# Building classes to cover — churches/cathedrals/chapels, mosques, synagogues.
# Deliberately NOT Shinto shrine (Q845945) or Buddhist temple (Q5393308): those
# have their own romaji pipeline (commons_normalize + the shrine multilang gen).
CLASSES = [
    "Q16970",    # church building
    "Q2977",     # cathedral
    "Q108325",   # chapel
    "Q32815",    # mosque
    "Q34627",    # synagogue
]

_BRACKETS = re.compile(r"\s*[（(\[][^）)\]]*[）)\]]\s*$")


def is_latin_script(text):
    """True if every letter in `text` is a Latin-script letter.

    Punctuation, digits, spaces and combining marks are ignored; a single
    non-Latin letter (Cyrillic/Arabic/Greek/CJK/…) disqualifies the name — that
    is the 'assuming the commons category is in Latin script' gate.
    """
    saw_letter = False
    for ch in text:
        if ch.isalpha():
            saw_letter = True
            if not unicodedata.name(ch, "").startswith("LATIN"):
                return False
    return saw_letter


def commons_to_english(commons_name):
    """Commons category name → English label, or None if not Latin-script.

    Copies the name (Emma's rule) after stripping a leading 'Category:' and a
    trailing bracketed disambiguator; commas are kept (they are part of church
    names like 'St Mary's Church, Oxford'). Latin-script only.
    """
    name = (commons_name or "").strip()
    if name.startswith("Category:"):
        name = name[len("Category:"):].strip()
    name = _BRACKETS.sub("", name).strip()
    name = re.sub(r"\s+", " ", name)
    if not name or not is_latin_script(name):
        return None
    return name


# ─────────────────────────── network ───────────────────────────

def _wdqs(query):
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(WDQS, data=data, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)["results"]["bindings"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise SystemExit("429 from WDQS — bailing (repo policy: no retries).")
        raise


def fetch_candidates(limit=None):
    """[(qid, commons)] for buildings of CLASSES that have a Commons category but
    no English label. Paged to stay under WDQS result caps."""
    out, offset, page = [], 0, 4000
    values = " ".join("wd:" + c for c in CLASSES)
    while True:
        q = f"""SELECT ?item ?commons WHERE {{
          VALUES ?cls {{ {values} }}
          ?item wdt:P31 ?cls ; wdt:P373 ?commons .
          FILTER NOT EXISTS {{ ?item rdfs:label ?l . FILTER(LANG(?l)="en") }}
        }} ORDER BY ?item LIMIT {page} OFFSET {offset}"""
        rows = _wdqs(q)
        for b in rows:
            out.append((b["item"]["value"].rsplit("/", 1)[-1], b["commons"]["value"]))
            if limit and len(out) >= limit:
                return out[:limit]
        if len(rows) < page:
            break
        offset += page
        time.sleep(1)
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    cands = fetch_candidates(args.limit)
    print(f"{len(cands)} religious buildings with a Commons category and no English label")
    lines, skipped = [], 0
    for qid, commons in cands:
        label = commons_to_english(commons)
        if not label:
            skipped += 1
            continue
        esc = label.replace('"', '')
        lines.append(f'{qid}|Len|"{esc}"')
    lines = sorted(set(lines))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} English labels -> {OUT} "
          f"(non-Latin Commons names skipped: {skipped})")


if __name__ == "__main__":
    main()
