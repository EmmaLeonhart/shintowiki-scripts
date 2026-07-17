#!/usr/bin/env python3
"""TEST Emma's hypothesis, empirically.

Emma 2026-07-16:

    "I am thoroughly convinced it is almost certain that you're going to be able to
    get an honorific out of every single Kami that has an honorific on Wikidata from
    the English language label. I'm pretty much certain about that, and you should
    actually test it! Make a programmatic thing, see what makes it happen and things
    like that."

So: of the kami whose JAPANESE label carries an honorific, for how many can the same
honorific be recovered from the ENGLISH label alone? Prints the misses and why, so
the failure modes are visible rather than assumed.

Sarutahiko is excluded — Emma 2026-07-16: "Sarutahiko is a special case just ignore
him... he just has a weird name."

Read-only. Run: python test_honorific_from_english.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "modern-quickstatements"))
import generate_shinto_honorifics as g   # noqa: E402



SARUTAHIKO = {"Q3090037"}   # Emma: special case, ignore


def main():
    honorifics = g.load_honorifics()
    kami = g.load_kami()

    forms = sorted(
        ((f, hq, efs) for hq, jas, efs in honorifics for f in jas),
        key=lambda t: len(t[0]), reverse=True,
    )
    all_en_forms = sorted({e for _, _, efs in forms for e in efs}, key=len, reverse=True)
    en_form_index = {e.lower(): hq for _, hq, efs in forms for e in efs}

    def ja_match(text):
        for f, hq, _ in forms:
            if text.endswith(f) and len(text) > len(f):
                return hq, f
        return None, None

    agree = disagree = en_only_missing = no_en = 0
    romaji_ok = 0
    misses, conflicts = [], []

    for qid, k in sorted(kami.items()):
        if qid in SARUTAHIKO:
            continue
        ja_hq, ja_form = ja_match(k["ja"])
        if not ja_hq:
            continue                                  # no honorific in ja => not in scope

        en_hq, romaji = g.derive_from_english(k["en"], en_form_index, all_en_forms)
        if not k["en"]:
            no_en += 1
            continue
        if romaji:
            romaji_ok += 1
        if en_hq is None:
            en_only_missing += 1
            misses.append((qid, k["ja"], k["en"], ja_form))
        elif en_hq == ja_hq:
            agree += 1
        else:
            disagree += 1
            conflicts.append((qid, k["ja"], k["en"], ja_form))

    total = agree + disagree + en_only_missing + no_en
    print("=" * 78)
    print("HYPOTHESIS: the honorific is recoverable from the ENGLISH label alone")
    print("=" * 78)
    print(f"  kami whose JA label carries an honorific : {total}")
    print(f"    EN gives the SAME honorific            : {agree}    ({agree/total*100:.0f}%)")
    print(f"    EN gives a DIFFERENT honorific         : {disagree}")
    print(f"    EN has NO recoverable honorific        : {en_only_missing}")
    print(f"    no EN label at all                     : {no_en}")
    print(f"  romaji confidently derived (P2440)       : {romaji_ok}")

    print("\n--- EN label carries NO honorific (hypothesis misses) ---")
    for qid, ja, en, f in misses[:25]:
        print(f"  {qid:12} ja={ja:16} en={en:34} (ja honorific: {f})")
    if len(misses) > 25:
        print(f"  ... +{len(misses) - 25} more")

    if conflicts:
        print("\n--- EN and JA disagree on WHICH honorific ---")
        for qid, ja, en, f in conflicts[:20]:
            print(f"  {qid:12} ja={ja:16} en={en:34} (ja honorific: {f})")

    print("\nVERDICT:", "hypothesis HOLDS" if en_only_missing == 0 and disagree == 0
          else f"hypothesis does NOT fully hold — {en_only_missing} misses, {disagree} conflicts")


if __name__ == "__main__":
    main()
