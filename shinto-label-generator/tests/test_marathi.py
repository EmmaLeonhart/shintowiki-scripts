"""Deep tail — mr (Marathi). Devanagari (reuses hindify) with explicit aa-matras
(Marathi renders names कामिकावा, not कमिकव) + तीर्थ suffix (dominant convention,
6/8 labels). Expected strings are the ACTUAL Wikidata labels (verification gate).
Known limitation: geminated names (Hokkaido→होक्काइदो) aren't reproduced because
hindify itself drops gemination — same gap as Hindi, documented."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, marathify, ALL_LANGS  # noqa: E402

TIRTH = "".join(chr(c) for c in [0x0924, 0x0940, 0x0930, 0x094D, 0x0925])  # तीर्थ


def test_mr_in_all_langs():
    assert "mr" in ALL_LANGS


def test_marathify_reproduces_real_names():
    assert marathify("Kamikawa") == "कामिकावा"
    assert marathify("Obihiro") == "ओबिहिरो"
    assert marathify("Saruka") == "सारुका"


def test_format_label_mr_suffix():
    label = format_label("mr", "Kamikawa", False, "shrine")
    assert label == f"कामिकावा {TIRTH}"
