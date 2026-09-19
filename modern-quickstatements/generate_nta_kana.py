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
SELECT ?item ?ja ?cityja ?prefja WHERE {
  { ?item wdt:P31 wd:Q845945 } UNION { ?item wdt:P31 wd:Q5393308 }
  ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja")
  FILTER NOT EXISTS { ?item rdfs:label ?en . FILTER(LANG(?en)="en") }
  FILTER NOT EXISTS { ?item wdt:P1814 ?k }
  ?item wdt:P131 ?city . ?city rdfs:label ?cityja . FILTER(LANG(?cityja)="ja")
  OPTIONAL {
    ?item wdt:P131+ ?pref . ?pref wdt:P31 wd:Q50337 .
    ?pref rdfs:label ?prefja . FILTER(LANG(?prefja)="ja")
  }
}"""

# Municipality names that are NOT unique nationally -- 北区, 中央区, 伊達市, 南部町. Derived
# from the index itself rather than listed, so it tracks the registry.
#
# ⚠ THIS IS A CORRECTNESS GATE, not a tidy-up. The first version keyed on (municipality,
# name) with no prefecture, and 106 of 1,433 emitted matches sat on one of these names --
# a 北区 temple on Wikidata could take the reading of a 北区 corporation in a different
# prefecture entirely, and nothing in the output would look wrong. Where Wikidata gives a
# prefecture the candidates are filtered by it; where it does not, an ambiguous
# municipality is REFUSED rather than guessed.

# A name tail whose reading is unambiguous, so a stem-only furigana can be completed.
# Anything NOT here is skipped when the tail is missing -- 寺 (じ/でら), 宮 (ぐう/みや),
# 院 in rare compounds. One reading or no completion.
COMPLETABLE = [
    ("神社", "ジンジャ"),
    ("神宮", "ジングウ"),
    ("八幡宮", "ハチマングウ"),
    ("大社", "タイシャ"),
]


# Old-form (旧字体) -> modern (新字体), applied to the NAME on BOTH sides of the match.
#
# The registry records the LEGALLY REGISTERED name, which for a corporation founded before
# the 1949 reform is usually the old form: 淨嚴寺, 圓行寺, 寳藏院. Wikidata labels the same
# building in modern kanji. Measured over the 34,050-entry index, the old forms are not a
# tail — 藏 appears 292 times, 淨 240, 寳 224, 嚴 165, 國 155, 眞 154, 廣 153, 壽 149.
#
# Normalising creates collisions on purpose: 龍源寺 and 竜源寺 in one municipality collapse
# to one key and are then REFUSED as ambiguous, which is the correct outcome — two
# corporations, one name, no way to tell which the item is.
#
# The small-kana variants are here for the same reason: 三ッ宮神社 and 三ツ宮神社 are one name
# spelled two ways, and the registry and Wikidata do not agree on which.
_OLD_TO_NEW = {
    "藏": "蔵", "淨": "浄", "寳": "宝", "寶": "宝", "嚴": "厳", "國": "国", "眞": "真",
    "廣": "広", "壽": "寿", "德": "徳", "樂": "楽", "應": "応", "萬": "万", "澤": "沢",
    "瀧": "滝", "榮": "栄", "彌": "弥", "禪": "禅", "惠": "恵", "觀": "観", "圓": "円",
    "學": "学", "藝": "芸", "齋": "斎", "齊": "斉", "淺": "浅", "濱": "浜", "邊": "辺",
    "邉": "辺", "會": "会", "亞": "亜", "拜": "拝", "縣": "県", "舊": "旧", "假": "仮",
    "靈": "霊", "豐": "豊", "辨": "弁", "辯": "弁", "瓣": "弁", "攝": "摂", "續": "続",
    "團": "団", "對": "対", "醫": "医", "兒": "児", "髙": "高", "﨑": "崎", "櫻": "桜",
    "靜": "静", "當": "当", "歸": "帰", "來": "来", "體": "体", "變": "変", "辭": "辞",
    "殘": "残", "燈": "灯", "爐": "炉", "龍": "竜", "圀": "国", "傳": "伝", "淸": "清",
    "峯": "峰", "嶋": "島", "曉": "暁", "濟": "済", "檜": "桧", "寫": "写", "從": "従",
    "ヶ": "ケ", "ヵ": "カ", "ッ": "ツ", "ヂ": "ジ", "ヅ": "ズ",
}


def fold_name(name):
    """The form both sides of the match are compared in. Never emitted, only compared."""
    return "".join(_OLD_TO_NEW.get(c, c) for c in name)


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
    """({(city, folded name): [(kana, houjin, prefecture)]}, {ambiguous municipality names})."""
    with io.open(path or INDEX, encoding="utf-8") as fh:
        raw = json.load(fh)
    by = collections.defaultdict(list)
    prefs = collections.defaultdict(set)
    for key, rec in raw.items():
        pref, city, name = key.split("|", 2)
        for ck in city_keys(city):
            by[(ck, fold_name(name))].append((rec["kana"], rec["houjin"], pref))
            prefs[ck].add(pref)
    return by, {c for c, p in prefs.items() if len(p) > 1}


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


def build(rows, index, ambiguous_cities=frozenset()):
    """(lines, stats) — one QuickStatement per confidently matched item."""
    lines = []
    stats = collections.Counter()
    for row in rows:
        qid, ja, city = row[0], row[1], row[2]
        pref = row[3] if len(row) > 3 else ""
        cands = index.get((city, fold_name(ja)), [])
        if cands and city in ambiguous_cities:
            if not pref:
                stats["municipality name not unique, no prefecture to settle it"] += 1
                continue
            cands = [c for c in cands if c[2] == pref]
            if not cands:
                stats["municipality name not unique, prefecture disagrees"] += 1
                continue
        if not cands:
            stats["no match in the registry"] += 1
            continue
        if len(cands) > 1:
            stats["same name twice in one municipality"] += 1
            continue
        kana, houjin, _pref = cands[0]
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
        # An OPTIONAL that did not bind comes back as a present key holding None, so
        # `.get(k, "")` returns None rather than the default -- which is how projecting
        # ?prefja turned every row's ja label into None on the first run.
        v = {k: ((r[k].get("value") if isinstance(r[k], dict) else r[k]) or "") for k in r}
        out.append((v.get("item", "").rsplit("/", 1)[-1], v.get("ja", ""),
                    v.get("cityja", ""), v.get("prefja", "")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    index, ambiguous = load_index()
    rows = fetch_population()
    print("registry: %d (municipality, name) keys; %d municipality names are not unique "
          "nationally" % (len(index), len(ambiguous)))
    print("targets:  %d shrines/temples with no en label, no P1814, and a P131" % len(rows))

    lines, stats = build(rows, index, ambiguous)
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
