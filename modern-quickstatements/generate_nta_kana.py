#!/usr/bin/env python3
"""
generate_nta_kana.py
====================
Give a shrine or temple its **P1814 name in kana** from the National Tax Agency
corporate-number registry, so the deterministic English-label stage can then name it.

## Why this exists

The English-label residual is ~18,065 items, and the reason the deterministic stages
cannot name them is not the romanization rule — it is that **the item carries no kana**.
``generate_kana_en_labels.py`` turns kana into a label with no judgement at all; it just
has nothing to turn. So the bottleneck is readings, and readings are what this supplies.

Emma, 2026-09-18, reversing the deliberate-slowness rule for this work on purpose:
*"I do want to accelerate it ... get this to as close to zero as possible through local
agentic work and then after we will let the cloud operations clean up the residuals"*,
on the view that cloud operations may not be resilient as long-term things.

## Why the NTA and not research

Measured the same day over the 400 staged ``en_label/`` work-files:

  * 23 of 400 have a jawiki article, whose lead gives the reading as furigana. Those
    were answered by reading them — 39 labels, 0 rejected.
  * Of 50 sampled from the rest, **39 carry no source of any kind**.
  * Web search returns the *search engine's* inference, not a source. Two were checked
    against their claimed sources and were in neither: ``わせんじ`` for 和泉寺 (cited
    jawiki page does not exist) and ``なかはらじ`` for 中原寺 (tesshow.jp lists it in
    kanji only). The work-files forbid exactly this: *"Do not invent a reading you
    cannot source."*

A 宗教法人's フリガナ is the one it registered with the state, and this repo already
treats that as authoritative — 4,764 P1814 statements cite houjin-bangou.nta.go.jp, and
Emma's 2026-08-24 ruling is that an NTA-cited reading is PRESERVED even when it looks
like a typo. ``shinto_miraheze/fetch_nta_religious_readings.py`` builds the index:
**34,050 readings**, each with its 13-digit corporate number.

## What it emits, and the two rules that shape it

``Q…|P1814|"<hiragana>"|S854|"<registry page for this corporation>"``

  * **Hiragana, converted from the registry's katakana.** P1814 wants modern hiragana
    and ``collect_name_in_kana.py`` REJECTS katakana outright — rightly, because katakana
    is the signature of the ancient-Engishiki-reading error the kana-qualifier cleanup
    exists to undo. The conversion is mechanical; the provenance is the registry.
  * **The reference travels with the value, always.** An uncited reading is one the next
    pass is entitled to "correct" — ``generate_lost_shrine_creates.py`` records that near
    miss on 近殿神社's legally registered ちかどのじんしゃ. So a match with no corporate
    number is not emitted.

## Matching requires municipality, and completion refuses to guess

``遠妙寺`` exists in 中央市 and in 笛吹市; ``長谷寺`` in 徳島市 reads チョウコクジ, not
はせでら. So the key is (municipality, name) and a name that matches in a DIFFERENT
municipality is rejected, not used. Measured over the target population: 401 unique
matches, **zero ambiguous**.

The registry's furigana is sometimes the STEM ONLY — 淺間神社 → センゲン, 三ッ宮神社 →
ミツミヤ. Where the missing tail has exactly one reading it is completed (神社 → ジンジャ);
where it has more than one it is **skipped rather than guessed**: 寺 is じ or でら, 宮 is
ぐう or みや, and picking one is inventing a reading. That is the same line the web-search
rejection above draws, applied to our own output.

Read-only against Wikidata and the local index. REPORT + GENERATE ONLY.

Usage:
    python generate_nta_kana.py [--out nta_kana.txt] [--dry-run]
"""
import argparse
import collections
import io
import json
import os
import re
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import wdqs_transport  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(_uar, "shinto_miraheze", "nta_religious_readings.json")
OUT = os.path.join(HERE, "nta_kana.txt")
ENDPOINT = "https://query-main.wikidata.org/sparql"
REGISTRY = "https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=%s"

# Targets: a shrine or temple with NO English label (so it is not already "done" under
# Emma's 2026-08-24 rule), NO top-level P1814 (so nothing is overwritten), a ja label to
# match on and a P131 to disambiguate by.
QUERY = """
SELECT ?item ?ja ?cityja WHERE {
  { ?item wdt:P31 wd:Q845945 } UNION { ?item wdt:P31 wd:Q5393308 }
  ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja")
  FILTER NOT EXISTS { ?item rdfs:label ?en . FILTER(LANG(?en)="en") }
  FILTER NOT EXISTS { ?item wdt:P1814 ?k }
  ?item wdt:P131 ?city . ?city rdfs:label ?cityja . FILTER(LANG(?cityja)="ja")
}"""

# A name tail whose reading is unambiguous, so a stem-only furigana can be completed.
# Anything NOT here is skipped when the tail is missing -- 寺 (じ/でら), 宮 (ぐう/みや),
# 院 in rare compounds. One reading or no completion.
COMPLETABLE = [
    ("神社", "ジンジャ"),
    ("神宮", "ジングウ"),
    ("八幡宮", "ハチマングウ"),
    ("大社", "タイシャ"),
]


def to_hiragana(text):
    """Katakana -> hiragana. The long vowel mark and the nakaguro are left alone."""
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def city_keys(city):
    """NTA writes a town as 郡+町 and a ward as 市+区; Wikidata labels the bare unit.

    Without this, 上板町 / 鋸南町 / 大山崎町 and every 区 miss entirely -- 87 of 350
    misses in the first measurement were this and nothing else.
    """
    out = {city}
    m = re.match(r"^.+?郡(.+[町村])$", city)
    if m:
        out.add(m.group(1))
    m = re.match(r"^.+?市(.+区)$", city)
    if m:
        out.add(m.group(1))
    return out


def load_index(path=None):
    """{(city, name): [(kana, houjin)]} over every municipality spelling."""
    with io.open(path or INDEX, encoding="utf-8") as fh:
        raw = json.load(fh)
    by = collections.defaultdict(list)
    for key, rec in raw.items():
        _pref, city, name = key.split("|", 2)
        for ck in city_keys(city):
            by[(ck, name)].append((rec["kana"], rec["houjin"]))
    return by


def complete(name, kana):
    """(kana, None) with the name's tail restored, or (None, why) when it cannot be.

    The registry often files the stem alone. Completing it is only safe where the tail
    has exactly one reading; where it has two, guessing is the thing this file refuses
    to do anywhere else.
    """
    for tail, reading in COMPLETABLE:
        if name.endswith(tail):
            return (kana if kana.endswith(reading) else kana + reading), None
    if name.endswith(("寺", "宮", "院", "庵", "坊", "堂")):
        # Ambiguous tails: 寺 is じ or でら, 宮 is ぐう or みや. Only accept a furigana
        # that already carries its own tail.
        for reading in ("ジ", "デラ", "テラ", "グウ", "ミヤ", "イン", "アン", "ボウ", "ドウ"):
            if kana.endswith(reading):
                return kana, None
        return None, "stem-only furigana %r on an ambiguous tail" % kana
    return kana, None


def build(rows, index):
    """(lines, stats) — one QuickStatement per confidently matched item."""
    lines = []
    stats = collections.Counter()
    for qid, ja, city in rows:
        cands = index.get((city, ja), [])
        if not cands:
            stats["no match in the registry"] += 1
            continue
        if len(cands) > 1:
            stats["same name twice in one municipality"] += 1
            continue
        kana, houjin = cands[0]
        if not houjin:
            stats["no corporate number — would be uncited"] += 1
            continue
        full, why = complete(ja, kana)
        if full is None:
            stats["ambiguous tail, skipped"] += 1
            continue
        hira = to_hiragana(full)
        if re.search(r"[ァ-ヶ]", hira):
            stats["still katakana after conversion"] += 1
            continue
        lines.append('%s|P1814|"%s"|S854|"%s"' % (qid, hira, REGISTRY % houjin))
        stats["emitted"] += 1
    return lines, stats


def fetch_population():
    rows = wdqs_transport.query_csv(QUERY, endpoint=ENDPOINT, timeout=300, post=True)
    out = []
    for r in rows:
        v = {k: (r[k]["value"] if isinstance(r[k], dict) else r[k]) for k in r}
        out.append((v.get("item", "").rsplit("/", 1)[-1], v.get("ja", ""), v.get("cityja", "")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    index = load_index()
    rows = fetch_population()
    print("registry: %d (municipality, name) keys" % len(index))
    print("targets:  %d shrines/temples with no en label, no P1814, and a P131" % len(rows))

    lines, stats = build(rows, index)
    for reason, n in stats.most_common():
        print("  %-42s %5d" % (reason, n))

    if args.dry_run:
        for ln in lines[:15]:
            print("   %s" % ln)
        return 0
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if lines else ""))
    print("\n%d QuickStatements -> %s" % (len(lines), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
