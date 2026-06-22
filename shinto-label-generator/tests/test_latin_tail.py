"""B3 — Latin-script tail languages. Conventions from existing Wikidata labels:
  az:  "<Name> məbədi"        (space-suffix)
  tl:  "Dambanang <Name>"     (prefix)
  war: "Santuario <Name>"     (prefix)
  min: "Kuil <Name>" / "Kuil Gadang <Name>"  (prefix, grand)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, ALL_LANGS  # noqa: E402


def test_all_in_all_langs():
    for lang in ["az", "tl", "war", "min"]:
        assert lang in ALL_LANGS, lang


def test_az_space_suffix():
    assert format_label("az", "Yasukuni", False, "shrine") == "Yasukuni məbədi"


def test_tl_prefix():
    assert format_label("tl", "Itsukushima", False, "shrine") == "Dambanang Itsukushima"


def test_war_prefix():
    assert format_label("war", "Meiji", False, "shrine") == "Santuario Meiji"


def test_min_prefix():
    assert format_label("min", "Tagata", False, "shrine") == "Kuil Tagata"


def test_min_grand():
    assert format_label("min", "Ise", True, "shrine") == "Kuil Gadang Ise"
