"""Tests for Greek (el) label generation (B3 tier-2 script map). Convention from
existing Wikidata labels: "Ιερό <Name>" / "Μεγάλο Ιερό <Name>", name transliterated
to Greek (unaccented). Structural tests here; exact transliterations are spot-
checked against real labels in the loop's verification step."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, grecify, ALL_LANGS  # noqa: E402

IERO = "Ιερό"
MEGALO = "Μεγάλο"


def _is_greek(s):
    return all(ch == " " or 0x0370 <= ord(ch) <= 0x03FF for ch in s)


def test_el_in_all_langs():
    assert "el" in ALL_LANGS


def test_grecify_is_greek_script():
    out = grecify("Yasaka")
    assert out and _is_greek(out)


def test_grecify_voiced_stop_digraph():
    # d -> ντ (Takeda -> ...ντα), g -> γκ (gu -> γκου)
    assert "ντ" in grecify("Takeda")
    assert "γκ" in grecify("Nagu")


def test_grecify_titlecased():
    out = grecify("Yasaka")
    assert out[0].isupper()


def test_format_label_el_prefix():
    label = format_label("el", "Yasaka", False, "shrine")
    assert label.startswith(IERO + " ")
    assert _is_greek(label)


def test_format_label_el_grand():
    label = format_label("el", "Ise", True, "shrine")
    assert label.startswith(MEGALO + " " + IERO + " ")
