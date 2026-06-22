"""Tests for B3 tier-2 European affix languages. Conventions taken from existing
Wikidata labels (romaji name + the language's shrine word reproduces them):
  ca: "Santuari <Name>"        gl: "Santuario <Name>"   (prefix)
  sv: "<Name>-templet"  nb/da: "<Name>-helligdommen"  hu: "<Name>-szentély" (suffix)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, ALL_LANGS  # noqa: E402


def test_all_in_all_langs():
    for lang in ["ca", "gl", "sv", "nb", "da", "hu"]:
        assert lang in ALL_LANGS, lang


def test_ca_prefix():
    assert format_label("ca", "Yasukuni", False, "shrine") == "Santuari Yasukuni"


def test_ca_grand():
    assert format_label("ca", "Izumo", True, "shrine") == "Gran Santuari Izumo"


def test_gl_prefix():
    assert format_label("gl", "Itsukushima", False, "shrine") == "Santuario Itsukushima"


def test_sv_suffix():
    assert format_label("sv", "Yasukuni", False, "shrine") == "Yasukuni-templet"


def test_nb_suffix():
    assert format_label("nb", "Yasukuni", False, "shrine") == "Yasukuni-helligdommen"


def test_da_suffix():
    assert format_label("da", "Yasukuni", False, "shrine") == "Yasukuni-helligdommen"


def test_hu_suffix():
    assert format_label("hu", "Yasukuni", False, "shrine") == "Yasukuni-szentély"


def test_hu_grand():
    assert format_label("hu", "Fushimi", True, "shrine") == "Fushimi-nagyszentély"
