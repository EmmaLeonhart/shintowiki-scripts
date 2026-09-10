"""
generate_derived_name_in_kana.py
================================
The GENERAL case of the derived reading. Emma, 2026-09-09: *"Realistically, all
of the shrines should have proper Kana names derived from the Japanese put in
them."*

GENERATOR ONLY — writes QuickStatements lines into an atomic .txt file that the
single daily submitter runs. It never edits Wikidata and the lines carry no edit
summaries (CLAUDE.md "Wikidata editing — ONE path only").

## What this is, next to the two things it is not

`build_name_in_kana_queue.py` hands a jawiki lead to an LLM and has the reading
READ out of the article. Its target set excludes every item with an English
label, because CLAUDE.md says such an item is finished:

    "Once something has an English label, it's graduated past the point that we
    care about its KANA reading. It is done. There's no KANA reading because the
    English label IS the KANA reading!"

That exclusion is about *reading an article*, not about *deriving from the
label*, and the same rule says what to do when a kana value is wanted anyway:

    "If a kana value is ever wanted on such an item it is DERIVED mechanically
    from the English label plus the shrine suffix taken from the Japanese."

`generate_katakana_reading_add.py` is that derivation pointed at four items — the
residue of the katakana cleanup. This script is the same derivation, through the
same `english_to_kana`, pointed at the general population: every shrine that has
both labels and no `P1814` at all. 16,753 of them on 2026-09-10.

## Add-only, so it can never overwrite a ruling

The target query requires `NOT EXISTS { ?item wdt:P1814 ?any }`, so nothing here
can touch a name-mate ruling, an NTA-registered reading
(`docs/kana_name_mate_rulings.md`: 4,764 statements are cited to the corporate
registry and are legally registered, not our errors), or a katakana value the
カミノヤシロ pipeline is still relocating. That is true by construction rather
than by a filter someone has to keep in step.

## THE THREE TIERS — measured, not assumed

There is a held-out set for this: the 5,781 shrines that carry BOTH an English
label and a real `P1814`. Deriving those and comparing against the reading they
already have says exactly how often the derivation is right, and splitting the
result by whether the item's NAME-MATES agree separates it sharply
(measured 2026-09-10, after the macron fix):

| tier | test | n (held-out) | precision |
|---|---|---|---|
| 1 | derived == the dominant reading on items with the identical ja label | 3,190 | **97.74%** |
| 2 | the ja label has no name-mate carrying any reading — nothing to check | 2,117 | **93.86%** |
| 3 | a name-mate reading exists and CONTRADICTS the derivation | 474 | **64.35%** |

Tier 1 is two independent sources agreeing: the English label (Emma's rule that
it IS the reading) and Emma's own name-mate rule (`docs/kana_name_mate_rulings.md`:
*"the dominant hiragana reading wins and is applied to every blank on that
pair"*). Several of the tier-1 "errors" are cases where the EXISTING value is the
known-wrong one — じんしゃ for じんじゃ, a truncated はちまん — so the real precision
is above the measured figure.

**Emma's call, 2026-09-10: ship tiers 1 and 2, hold tier 3.** On the live target
set that is 7,596 + 2,992 = 10,588 lines, with 1,348 held back as tier 3.

Tier 3 is not dropped: `build_kana_disagreement_queue.py` turns it into
`name_in_kana/` work-files carrying BOTH candidate readings, so the existing
cloud routine reads the jawiki lead and picks. This script writes the tier-3 list
to `derived_name_in_kana_disagreements.json` for it. (Emma chose this over
leaving them or filing a report.) It is the one place where an en-labelled item
legitimately goes back to an article — because two mechanical sources disagree,
which is not a case CLAUDE.md's rule contemplates.

## What it refuses outright

`kana_for` returns None unless it is confident, and on a population this size the
refusals are most of the work — 4,810 of the 16,753:

  * **no known shrine-type suffix on the ja label** (1,492) — 大社 reads たいしゃ on
    some shrines and おおやしろ on others, 神宮 has an ambiguous stem boundary, and
    a 〜神 item has no shrine suffix at all. All three are absent from the suffix
    table on purpose.
  * **the en label does not end in the expected shrine word** (2,202) — a gloss, a
    romanized whole name, an un-stripped disambiguator.
  * **a multi-word stem** (525) — a stem that is two or more words is a gloss, not
    a single romanized name.
  * **a stem that will not romanize** (416) — an English word in the stem position.
  * **the shrine word alone** (175) — nothing left to romanize.

## ⛔ 天神社 + "Tenjin Shrine" is held

`english_to_kana._SUFFIXES` carries that entry with a warning against exactly
this job: both てんじんじゃ and てんじんしゃ are attested per item, the English labels
came from one bulk batch and carry no per-item information, and
`docs/kana_name_mate_rulings.md` settles the pair from jawiki as てんじんしゃ, with
てんじんじゃ correct only where the National Tax Agency registered it that way. An
item with no reading gives no way to know which it is. Seven items. The
"Tenjin-sha"/"Tenjinsha" labels are NOT held: jawiki backs てんじんしゃ and the
label agrees with it.

Output: derived_name_in_kana.txt, derived_name_in_kana_disagreements.json
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

import argparse
import collections
import io
import json
import os
import shutil
import sys
import time
import urllib.parse

import requests

_usys.path.insert(0, _uos.path.dirname(_uos.path.abspath(__file__)))
from english_to_kana import derive  # noqa: E402

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
OUTPUT_FILE = "derived_name_in_kana.txt"
DISAGREEMENT_FILE = "derived_name_in_kana_disagreements.json"
SHRINE = "Q845945"

# (kanji suffix, English phrase) pairs a BULK job must not derive through. A
# documented open question, not a hunch — see the module docstring.
HELD_ENTRIES = {("天神社", "Tenjin Shrine")}

# Emma's call, 2026-09-10. Tier 3 is routed to the LLM queue instead of shipped.
SHIP_TIERS = {1, 2}

TARGET_QUERY = f"""
SELECT ?item ?ja ?en ?art WHERE {{
  ?item wdt:P31 wd:{SHRINE} .
  ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja")
  ?item rdfs:label ?en . FILTER(LANG(?en) = "en")
  FILTER NOT EXISTS {{ ?item wdt:P1814 ?any }}
  # OPTIONAL, and only used for the tier-3 items that go back to an article.
  # Nothing that ships depends on it.
  OPTIONAL {{ ?art schema:about ?item ; schema:isPartOf <https://ja.wikipedia.org/> }}
}}
"""

# Every reading already on a shrine, with its ja label — the name-mate evidence.
# Deliberately NOT restricted to items with an English label: a name-mate's vote
# is about the Japanese name, and half the readings sit on items with no en label.
MATE_QUERY = f"""
SELECT ?item ?ja ?kana WHERE {{
  ?item wdt:P31 wd:{SHRINE} .
  ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja")
  ?item wdt:P1814 ?kana .
}}
"""


class RateLimitError(Exception):
    """Raised on HTTP 429 — bail, no retries (CLAUDE.md 429 policy)."""


_last = 0.0


def fetch_sparql(query, retries=3):
    """One POSTed query, spaced at least 5s from the last. Returns None on a
    timeout that survives the retries, so the caller can leave the existing file
    alone rather than truncating it to zero lines."""
    global _last
    for attempt in range(1, retries + 1):
        elapsed = time.time() - _last
        if elapsed < 5:
            time.sleep(5 - elapsed)
        try:
            r = requests.post(
                SPARQL_ENDPOINT,
                data={"query": query, "format": "json"},
                headers={"User-Agent": UA,
                         "Accept": "application/sparql-results+json"},
                timeout=300,
            )
        except requests.exceptions.ReadTimeout:
            _last = time.time()
            if attempt < retries:
                time.sleep(10 * attempt)
                continue
            print("SPARQL timed out after retries — exiting gracefully")
            return None
        _last = time.time()
        if r.status_code == 429:
            print("FATAL: 429 Too Many Requests from SPARQL endpoint — bailing")
            raise RateLimitError("429")
        r.raise_for_status()
        return r.json()["results"]["bindings"]


def qid(uri):
    return uri.rsplit("/", 1)[-1]


def s(text):
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def is_katakana(value):
    """A katakana-only reading. The same test the kana-qualifier pipeline uses.
    Such a value is an ancient reading being relocated elsewhere, so it must not
    vote as a name-mate for a modern hiragana reading."""
    has_hira = any("぀" <= ch <= "ゟ" for ch in value)
    has_kata = any("゠" <= ch <= "ヿ" for ch in value)
    return has_kata and not has_hira


def collect_targets(rows):
    """[(qid, ja, en, ja_title)] sorted by QID number. A duplicate QID means the
    item carries the shrine class twice, not two labels — rdfs:label returns one
    per language — so dedupe on the QID. ``ja_title`` is "" when the item has no
    jawiki article."""
    seen = {}
    for r in rows:
        q = qid(r["item"]["value"])
        art = r.get("art", {}).get("value", "")
        title = (urllib.parse.unquote(art.rsplit("/", 1)[-1]).replace("_", " ")
                 if art else "")
        seen.setdefault(q, (q, r["ja"]["value"], r["en"]["value"], title))
    return [seen[q] for q in sorted(seen, key=lambda x: int(x[1:]))]


def collect_mates(rows):
    """{ja label -> Counter of hiragana readings}, ONE VOTE PER ITEM.

    Counting rows would let a single item with two values outvote two items, and
    would count an item once per shrine class it carries. Spaces are stripped
    because `くまの じんじゃ` is the same reading as `くまのじんじゃ` with a typo
    (`docs/kana_name_mate_rulings.md`), and katakana values are dropped: they are
    the ancient readings a different pipeline is relocating.
    """
    per_item = collections.defaultdict(lambda: {"ja": None, "vals": set()})
    for r in rows:
        q = qid(r["item"]["value"])
        per_item[q]["ja"] = r["ja"]["value"]
        per_item[q]["vals"].add(r["kana"]["value"].replace(" ", ""))
    mates = collections.defaultdict(collections.Counter)
    for rec in per_item.values():
        for v in rec["vals"]:
            if not is_katakana(v):
                mates[rec["ja"]][v] += 1
    return mates


def dominant(mates, ja):
    """The reading most items with this exact ja label carry, or None.

    Ties are broken by the reading itself so the output is stable across runs —
    WDQS row order is not, and an unstable tiebreak would rewrite the whole file
    every build."""
    c = mates.get(ja)
    if not c:
        return None
    return min(c.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def classify(items, mates):
    """(rows, reasons). One row per derivable item:
    (qid, ja, en, derived, mate, tier, ja_title). Tier 1 = the name-mates agree, 2 = there
    are none, 3 = they contradict. Refusals go into ``reasons`` only."""
    rows, reasons = [], collections.Counter()
    for q, ja, en, title in items:
        d = derive(ja, en)
        if d.kana and (d.kanji_suffix, d.en_phrase) in HELD_ENTRIES:
            reasons["held: undecided reading for this ja/en pair"] += 1
            continue
        if not d.kana:
            reasons[d.reason] += 1
            continue
        mate = dominant(mates, ja)
        tier = 2 if mate is None else (1 if mate == d.kana else 3)
        reasons[f"tier {tier}"] += 1
        rows.append((q, ja, en, d.kana, mate, tier, title))
    return rows, reasons


def build_lines(rows):
    return [f"{q}|P1814|{s(kana)}" for q, ja, en, kana, mate, tier, title in rows
            if tier in SHIP_TIERS]


def publish_to_site(path):
    """Copy the batch into _site/ for the GitHub Pages browser. The file the
    daily editor reads is the bare-name one in this directory; this is only the
    published copy."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def here(name):
    return name if os.path.dirname(name) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--stats", action="store_true",
                    help="report the population and the tier/refusal breakdown, "
                         "write nothing")
    args = ap.parse_args()

    print("=== Derived hiragana P1814 for shrines with an English label "
          "and no reading ===\n")
    target_rows = fetch_sparql(TARGET_QUERY)
    if target_rows is None:
        print("No SPARQL result — leaving the existing files untouched.")
        return
    mate_rows = fetch_sparql(MATE_QUERY)
    if mate_rows is None:
        print("No name-mate result — leaving the existing files untouched. "
              "Without the mates every item would fall to tier 2 and the "
              "tier-1 gate would silently stop existing.")
        return

    items = collect_targets(target_rows)
    mates = collect_mates(mate_rows)
    rows, reasons = classify(items, mates)
    lines = build_lines(rows)
    tier3 = [r for r in rows if r[5] == 3]

    print(f"{len(items)} shrines with both labels and no P1814")
    print(f"{len(mates)} distinct ja labels carry a hiragana reading somewhere\n")
    for reason, n in reasons.most_common():
        print(f"  {n:>6}  {reason}")
    print(f"\n  shipping tiers {sorted(SHIP_TIERS)}: {len(lines)} lines")
    print(f"  tier 3 to the LLM queue: {len(tier3)}")
    for q, ja, en, kana, mate, _, _title in tier3[:10]:
        print(f"    {q:<12} {ja:<16} {en:<32} derived={kana:<20} mate={mate}")

    if args.stats:
        print("\n--stats: nothing written")
        return

    path = here(args.out)
    with open(path, "w", encoding="utf-8") as f:
        # Sorted at the writer, per DEVLOG 2026-08-21: WDQS row order is not
        # stable, so emitting in result order rewrites the whole file every build.
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    publish_to_site(path)

    dis = here(DISAGREEMENT_FILE)
    with open(dis, "w", encoding="utf-8", newline="\n") as f:
        json.dump([{"qid": q, "ja": ja, "en": en, "derived": kana, "mate": mate,
                    "ja_title": title}
                   for q, ja, en, kana, mate, _, title in tier3],
                  f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print(f"\nWrote {len(lines)} lines to {path}")
    print(f"Wrote {len(tier3)} disagreements to {dis}")


if __name__ == "__main__":
    # Rebound here rather than at import time: at module level it replaces the
    # caller's stdout, which breaks pytest's capture.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
