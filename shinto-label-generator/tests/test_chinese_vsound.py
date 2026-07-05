"""The /v/ sound (katakana ヴ) in the kana→man'yōgana converter (2026-07-05).

Japanese has no man'yōgana for /v/; the standard convention approximates ヴ as ば行
(v→b). Before this, ヴ had no mapping and leaked verbatim into 15 zh-family labels
(Q1001037 ヴァルナ Varuna → "ヴ阿留奈"; Q20078554 ソヴィエト…). japanese_to_chinese's
pair-first lookahead now renders the combos as ば行 (ヴァ→马 ba, ヴィ→尾 bi, …).
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_chinese_quickstatements import japanese_to_chinese  # noqa: E402


# ── Unit: ヴ combos map to the ば行 Han characters (same as バ/ビ/ブ/ベ/ボ) ──

def test_vu_combos_render_as_b_row():
    assert japanese_to_chinese("ヴァルナ") == "马留奈"      # Varuna: ヴァ->马 (ba)
    assert japanese_to_chinese("ソヴィエト") == "曽尾江都"   # Soviet: ヴィ->尾 (bi)
    assert japanese_to_chinese("ヴ") == "武"                # bare ヴ -> 武 (bu)
    assert japanese_to_chinese("ヴェ") == "部"              # ヴェ -> 部 (be)
    assert japanese_to_chinese("ヴォ") == "母"              # ヴォ -> 母 (bo)


# ── File invariant: no zh-family committed label may contain a real kana letter ──
# (hiragana U+3041-3096, katakana U+30A1-30FA). The interpunct ・ (U+30FB) and the
# prolonged-sound mark ー (U+30FC) are excluded — ・ is a legitimate separator in
# compound-shrine zh labels (八幡神社・諏訪神社).

_QS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "quickstatements")
_ZH = {"zh", "zh-hant", "zh-hans", "zh-cn", "zh-tw", "zh-hk", "zh-sg", "zh-mo", "gan"}


def _has_real_kana(s):
    return any(0x3041 <= ord(c) <= 0x3096 or 0x30A1 <= ord(c) <= 0x30FA for c in s)


def test_no_kana_leak_in_committed_zh_labels():
    bad = []
    for path in glob.glob(os.path.join(_QS, "*.txt")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3 or not parts[1].startswith("L"):
                    continue
                if parts[1][1:] in _ZH and _has_real_kana(parts[2].strip('"')):
                    bad.append((os.path.basename(path), parts[0], parts[1], parts[2]))
    assert not bad, f"{len(bad)} zh labels leak untransliterated kana; e.g. {bad[:5]}"
