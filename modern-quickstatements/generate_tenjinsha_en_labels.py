"""天神社 English labels, derived from the item's own reading. A deliberate special case.

Emma, 2026-08-24: *"Tenjinsha becomes Tenjin-sha and Tenjinja becomes Tenjin Shrine, a totally
valid english decision, so lets go with that thing."*

    てんじんしゃ  →  Tenjin-sha
    てんじんじゃ  →  Tenjin Shrine

**Why this is its own script and not a fix to `kana_english.label_for`.** That function matches the
longest kanji suffix first, so on 天神社 it strips 神社 and is left with the stem てん, producing
**"Ten Shrine"** — wrong. And given てんじんしゃ it has already committed to the 神社 suffix, fails to
find じんじゃ, and correctly defers rather than guessing. The real split is 天神 + 社, not 天 + 神社,
which jawiki confirms by giving the reading as てんじん-しゃ. Changing the shared suffix matcher to
handle that would alter every label the pipeline produces; this handles the one name it affects.

**Why it is SPARQL-driven and re-runs.** Her words: *"this should be a persistent part of the
pipeline… if another NTA export happens then it might legitimately change the names of some of them
due to our sparql query thing."* That is the intent, not a hazard — the English label is derived
from the reading, so a corrected reading is *supposed* to move the label with it.

**What it deliberately does NOT do:**

  * It adds **no kana**. Emma: *"We do not add kana to these ones."* The ~167 天神社 items with no
    reading get nothing here; there is no per-item evidence to derive one from, and the uniform
    "Tenjin-sha" label came from a single QuickStatements batch so it carries no information.
  * It touches **only** items whose reading is exactly てんじんしゃ or てんじんじゃ. Anything else on
    a 天神社 — あまつかむやしろ, which jawiki documents, or a truncated Old Japanese katakana — is
    left alone.
  * It emits a line only where the label would actually **change**, so a re-run on unchanged data
    produces an empty file rather than thousands of no-op edits.

Both readings are heavily backed by the National Tax Agency corporate registry (44 of 47 and 11 of
19), which is why neither is "the wrong one" — they are two real readings, and the label follows
whichever the item has.

⛔ Generates only. Nothing is delivered before the Wikidata lockout lifts on 2026-09-18.

Usage:
    python modern-quickstatements/generate_tenjinsha_en_labels.py
    python modern-quickstatements/generate_tenjinsha_en_labels.py --dry-run
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tenjinsha_en_labels.txt")
ENDPOINT = "https://query-main.wikidata.org/sparql"
WDQS_THROTTLE = 2.5

# reading -> the English label it implies. Emma's ruling, and the whole rule.
LABEL = {
    "てんじんしゃ": "Tenjin-sha",
    "てんじんじゃ": "Tenjin Shrine",
}

QUERY = """
SELECT ?item ?kana ?en WHERE {
  ?item wdt:P31 wd:Q845945 ; rdfs:label "天神社"@ja ; wdt:P1814 ?kana .
  OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en)="en") }
  FILTER(?kana = "てんじんしゃ" || ?kana = "てんじんじゃ")
}
"""


def run(query):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT, "Accept": "application/sparql-results+json"})
    for wait in (0, 15, 45, 135):
        if wait:
            print("  backing off %ds" % wait, flush=True)
            time.sleep(wait)
        time.sleep(WDQS_THROTTLE)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))["results"]["bindings"]
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print("429 from WDQS — bailing, per standing policy.")
                sys.exit(1)
            if exc.code in (503, 504):
                print("  HTTP %d from WDQS" % exc.code)
                continue
            raise
    print("WDQS kept timing out; wrote nothing.")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    rows = run(QUERY)
    lines, unchanged, by_reading = [], 0, {}
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        kana = b["kana"]["value"]
        want = LABEL[kana]
        have = b.get("en", {}).get("value")
        by_reading[kana] = by_reading.get(kana, 0) + 1
        if have == want:
            unchanged += 1
            continue
        lines.append('%s|Len|"%s"' % (qid, want))

    print("天神社 items with a ruled reading: %d" % len(rows))
    for kana, n in sorted(by_reading.items()):
        print("   %-10s -> %-14s %d" % (kana, LABEL[kana], n))
    print("labels already correct: %d" % unchanged)
    print("lines to write: %d" % len(lines))

    if args.dry_run:
        for ln in lines[:12]:
            print("   " + ln)
        return
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        if lines:
            fh.write("\n".join(lines) + "\n")
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
