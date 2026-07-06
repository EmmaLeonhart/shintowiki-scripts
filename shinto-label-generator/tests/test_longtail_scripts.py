"""Tests for the long-tail transliterators added 2026-07-06:
Newari (Devanagari reuse), Punjabi (Gurmukhi +0x100), Madurese (Latin affix), and the
Brahmic set Burmese/Khmer/Lao/Tibetan/Shan via Aksharamukha (Devanagari→target).
Each check asserts the output lands in the correct Unicode script block.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_multilang_quickstatements as g  # noqa: E402


def _in_block(s, lo, hi):
    return s and any(lo <= c <= hi for c in s)


def test_all_registered():
    for lang in ("new", "pa", "mad", "my", "km", "lo", "dz", "shn"):
        assert lang in g.ALL_LANGS


def test_newari_devanagari():
    assert _in_block(g.format_label("new", "Ise"), "ऀ", "ॿ")


def test_punjabi_gurmukhi():
    assert _in_block(g.format_label("pa", "Ise"), "਀", "੿")


def test_madurese_latin_affix():
    assert g.format_label("mad", "Ise") == "Kuil Ise"


def test_burmese():
    assert _in_block(g.format_label("my", "Ise"), "က", "႟")


def test_khmer():
    assert _in_block(g.format_label("km", "Ise"), "ក", "៿")


def test_lao():
    assert _in_block(g.format_label("lo", "Ise"), "຀", "໿")


def test_tibetan():
    assert _in_block(g.format_label("dz", "Ise"), "ༀ", "࿿")


def test_shan_myanmar_block():
    # Shan uses the extended Myanmar block
    assert _in_block(g.format_label("shn", "Ise"), "က", "ꩿ")
