"""Tests for the Japanese→Toki Pona engine (tokiponizer.py) and a phonotactic
invariant over EVERY committed tok label.

Regression origin (2026-07-04): the YOON_MAP palatal glides rya/ryu/ryo and nyu
were mis-spelled with the Latin letter 'y' (liya/liyu/liyo/niyu) — but 'y' is NOT
in the toki pona alphabet (the /j/ glide is written 'j', cf. the correct siblings
mya→mija, pyu→piju). 731 committed tok labels carried the illegal letter. Fixed to
lija/liju/lijo/niju; these tests lock the alphabet.
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tokiponizer import YOON_MAP, tokiponize  # noqa: E402

# Toki pona alphabet: 9 consonants + 5 vowels. 'y' is deliberately ABSENT.
_TOK_LETTERS = set("ptksmnlwj") | set("aeiou")
_TOK_VOWELS = set("aeiou")


# ── Engine: the four fixed glides render the /j/ sound as 'j', never 'y' ──

def test_fixed_glides_use_j_not_y():
    assert tokiponize("りゅう") == ["Liju"]     # ryu (was "Liyu")
    assert tokiponize("にゅう") == ["Niju"]     # nyu (was "Niyu")
    assert tokiponize("りょう") == ["Lijo"]     # ryo (was "Liyo")
    assert tokiponize("りゃく") == ["Lijaku"]   # rya (was "Liyaku")


def test_yoon_map_has_no_y():
    offenders = {k: v for k, v in YOON_MAP.items() if "y" in v}
    assert not offenders, f"YOON_MAP values must never contain 'y': {offenders}"


# ── Cross-generator invariant: NO committed tok label may violate the alphabet ──
# or the cluster rule (only 'n' may precede a consonant) or end in a non-'n'
# consonant. This guards every generator that emits Ltok, not just this engine.

_QS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "quickstatements")


def _phonotactic_violation(word):
    w = word.lower()
    if any(c not in _TOK_LETTERS for c in w):
        return f"illegal-letter in {word!r}"
    for i, c in enumerate(w):
        if c not in _TOK_VOWELS and i > 0 and w[i - 1] not in _TOK_VOWELS and w[i - 1] != "n":
            return f"illegal cluster {w[i-1]}{c} in {word!r}"
    if w and w[-1] not in _TOK_VOWELS and w[-1] != "n":
        return f"illegal final consonant in {word!r}"
    return None


def test_all_committed_tok_labels_are_phonotactically_legal():
    bad = []
    for path in glob.glob(os.path.join(_QS_DIR, "*.txt")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3 and parts[1] == "Ltok":
                    for word in parts[2].strip('"').split():
                        v = _phonotactic_violation(word)
                        if v:
                            bad.append((os.path.basename(path), parts[0], v))
    assert not bad, f"{len(bad)} tok labels violate toki pona phonotactics; e.g. {bad[:5]}"
