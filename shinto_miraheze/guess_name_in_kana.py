#!/usr/bin/env python3
"""Guess a modern hiragana reading for a shrine name when the jawiki article gives none.

Emma, 2026-08-23, choosing the full build of kana-from-jawiki over the bounded one:
pull the kana from the article, feed the naming pipeline, **and guess where no kana can
be found**. She was shown her own 2026-08-18 objection — that it extends the programme's
runtime, cutting against the finite ending — and chose the full build anyway.

This module is the "guess where no kana can be found" half. It exists separately from
`collect_name_in_kana.py` because a guessed reading is **not the same kind of fact** as
one extracted from the article, and the difference has to survive all the way to Wikidata:

  * an extracted reading is referenced to the jawiki article (`S143`/`S4656`) because the
    article states it;
  * a guessed reading has NO such source. Attaching that reference to a guess would put a
    false claim of provenance on Wikidata, which is worse than having no reading at all.

WHY A NAIVE CONVERTER IS NOT ENOUGH
-----------------------------------
`pykakasi` alone gets shrine names wrong at exactly the suffix that every shrine name has:

    三芳野神社  ->  みよしのがみしゃ      (segments 野神 / 社)
    correct     ->  みよしのじんじゃ

It reads the stem fine — 三芳野 -> みよしの — and mangles the suffix. So the suffix is
handled from a table and only the stem goes to the converter. Longest suffix wins, because
神宮 must not be matched as 宮 and 大神宮 must not be matched as 神宮.

The stem remains a guess and can still be wrong: shrine names carry irregular, local and
archaic readings that no general converter knows. That is what `measure` is for — run it
against the readings already collected from articles and look at the real accuracy before
trusting anything here.
"""
import io
import os
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

# Longest first — 大神宮 before 神宮 before 宮, 大社 before 社.
SUFFIXES = [
    ("大神宮", "だいじんぐう"),
    ("神宮", "じんぐう"),
    ("大社", "たいしゃ"),
    ("神社", "じんじゃ"),
    ("八幡宮", "はちまんぐう"),
    ("天満宮", "てんまんぐう"),
    ("東照宮", "とうしょうぐう"),
    ("神明宮", "しんめいぐう"),
    ("稲荷", "いなり"),
]

HIRAGANA = set(chr(c) for c in range(0x3041, 0x3097)) | {"ー"}


def split_suffix(name):
    """(stem, suffix_kana) — or (name, "") when nothing matches."""
    for suf, kana in SUFFIXES:
        if name.endswith(suf) and len(name) > len(suf):
            return name[: -len(suf)], kana
    for suf, kana in SUFFIXES:
        if name == suf:
            return "", kana
    return name, ""


def _converter():
    import pykakasi
    return pykakasi.kakasi()


def guess(name, kks=None):
    """A hiragana guess for `name`, or None if nothing usable came out.

    Returns None rather than a partial reading: a reading with a stray kanji in it is not
    a reading, and P1814 wants a clean modern one.
    """
    if not name:
        return None
    kks = kks or _converter()
    stem, suffix = split_suffix(name)
    stem_kana = "".join(i["hira"] for i in kks.convert(stem)) if stem else ""
    out = stem_kana + suffix
    if not out:
        return None
    if not all(ch in HIRAGANA for ch in out):
        return None
    return out


def measure(pairs):
    """pairs: [(name, true_reading)] -> (exact, close, wrong, misses).

    `close` means the guess matches once long-vowel and small-kana spelling differences
    are flattened — worth counting separately because those are a different kind of error
    from reading the wrong word.
    """
    kks = _converter()
    exact = close = wrong = 0
    misses = []
    for name, truth in pairs:
        g = guess(name, kks)
        if g is None:
            wrong += 1
            misses.append((name, truth, None))
        elif g == truth:
            exact += 1
        elif _flat(g) == _flat(truth):
            close += 1
        else:
            wrong += 1
            misses.append((name, truth, g))
    return exact, close, wrong, misses


def _flat(s):
    out = s.replace("ー", "").replace("っ", "つ")
    for a, b in (("ゃ", "や"), ("ゅ", "ゆ"), ("ょ", "よ")):
        out = out.replace(a, b)
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "--measure":
        import json
        import time
        import urllib.parse
        import urllib.request
        from shinto_miraheze.ua_for import ua_for

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log = os.path.join(root, "name_in_kana", "_resolved.log")
        truth = {}
        for line in io.open(log, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and parts[1] == "KANA":
                truth[parts[0]] = parts[2]
        print(f"{len(truth)} article-sourced readings available as ground truth")

        names = {}
        qids = sorted(truth)
        for i in range(0, len(qids), 50):
            chunk = qids[i:i + 50]
            url = ("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
                "action": "wbgetentities", "ids": "|".join(chunk),
                "props": "labels", "languages": "ja", "format": "json"}))
            req = urllib.request.Request(url, headers={"User-Agent": ua_for("www.wikidata.org")})
            with urllib.request.urlopen(req, timeout=60) as fh:
                d = json.load(fh)
            for q, e in d.get("entities", {}).items():
                lab = e.get("labels", {}).get("ja", {}).get("value")
                if lab:
                    names[q] = lab
            time.sleep(1.0)

        pairs = [(names[q], truth[q]) for q in qids if q in names]
        print(f"{len(pairs)} of them have a ja label to guess from")
        exact, close, wrong, misses = measure(pairs)
        total = len(pairs) or 1
        print(f"\nexact  {exact:4d}  {exact/total:6.1%}")
        print(f"close  {close:4d}  {close/total:6.1%}   (long-vowel / small-kana only)")
        print(f"wrong  {wrong:4d}  {wrong/total:6.1%}")
        print("\nfirst misses (name / true / guessed):")
        for name, t, g in misses[:15]:
            print(f"  {name}\t{t}\t{g}")
        return
    for name in sys.argv[1:]:
        print(name, "->", guess(name))


if __name__ == "__main__":
    main()
