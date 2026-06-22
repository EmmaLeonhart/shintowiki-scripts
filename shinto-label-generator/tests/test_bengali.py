"""Tests for Bengali label generation (B4b). Bengali is built by transliterating
the Devanagari (hindify) output character-by-character to Bengali script, then
appending the Bengali shrine word মন্দির (mirroring the Hindi convention)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_multilang_quickstatements as g  # noqa: E402

MANDIR = "".join(chr(c) for c in [0x09AE, 0x09A8, 0x09CD, 0x09A6, 0x09BF, 0x09B0])  # মন্দির
MAHA = "".join(chr(c) for c in [0x09AE, 0x09B9, 0x09BE])  # মহা


def _is_bengali_or_space(s):
    return all(ch == " " or 0x0980 <= ord(ch) <= 0x09FF for ch in s)


def test_bn_in_all_langs():
    assert "bn" in g.ALL_LANGS


def test_map_covers_every_char_hindify_can_emit():
    emitted = set()
    for d in (g.HINDI_BASE, g.HINDI_YOON, g.HINDI_INITIAL):
        for v in d.values():
            emitted.update(v)
    missing = emitted - set(g.DEVANAGARI_TO_BENGALI)
    assert not missing, f"unmapped Devanagari chars: {[hex(ord(c)) for c in missing]}"


def test_bengalify_produces_bengali_script():
    out = g.bengalify("Kasuga")
    assert out and _is_bengali_or_space(out)


def test_bengalify_multiword():
    out = g.bengalify("Ataka Sumiyoshi")
    assert out and _is_bengali_or_space(out)
    assert " " in out  # space preserved between words


def test_format_label_bn_appends_mandir():
    label = g.format_label("bn", "Kasuga", False, "shrine")
    assert label.endswith(MANDIR)
    assert _is_bengali_or_space(label)


def test_format_label_bn_grand_has_maha():
    label = g.format_label("bn", "Ise", True, "shrine")
    assert MAHA in label
