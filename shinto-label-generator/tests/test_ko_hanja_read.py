"""hanja_read must yield a PURE-Hangul sino-Korean reading or None (2026-07-05).

hanja.translate only converts Han characters, leaving Japanese kana (and Latin)
verbatim. The old guard rejected only residual Han, so pure-katakana names (ターラカ)
and partial conversions (国指定文化財等データベース → '국지정문화재등データベース') leaked
mixed-script garbage into 19 committed ko labels. The guard now also rejects any
surviving kana.
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translit_common import hanja_read  # noqa: E402


def _is_han(c):
    return "一" <= c <= "鿿" or "㐀" <= c <= "䶿"


def _is_kana(c):
    return "ぁ" <= c <= "ゖ" or "ァ" <= c <= "ヺ"


# ── Unit ──

def test_pure_kanji_still_reads():
    ko = hanja_read("日本書紀")
    assert ko and all("가" <= c <= "힣" for c in ko)   # 일본서기, pure Hangul


def test_kana_bearing_input_rejected():
    assert hanja_read("ターラカ") is None                    # pure katakana
    assert hanja_read("国指定文化財等データベース") is None    # Han converts, katakana survives
    assert hanja_read("仮名遣い") is None                     # trailing hiragana い


# ── File invariant: no committed ko label carries Han or kana ──

_QS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "quickstatements")


def test_no_committed_ko_label_has_han_or_kana():
    bad = []
    for path in glob.glob(os.path.join(_QS, "*.txt")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3 or parts[1] != "Lko":
                    continue
                v = parts[2].strip('"')
                if any(_is_han(c) or _is_kana(c) for c in v):
                    bad.append((os.path.basename(path), parts[0], v))
    assert not bad, f"{len(bad)} ko labels leak Han/kana; e.g. {bad[:5]}"
