"""B3 tier-2 batch 2. Conventions from existing Wikidata labels:
  la:  "Templum <Name>" / "Magnum Templum <Name>"  (prefix)
  ast: "Santuariu <Name>" / "Gran Santuariu <Name>" (prefix)
  sh/hr: "<Name> hram"                               (space-suffix)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, ALL_LANGS  # noqa: E402


def test_all_in_all_langs():
    for lang in ["la", "ast", "sh", "hr"]:
        assert lang in ALL_LANGS, lang


def test_la_prefix():
    assert format_label("la", "Kasuga", False, "shrine") == "Templum Kasuga"


def test_la_grand():
    assert format_label("la", "Izumo", True, "shrine") == "Magnum Templum Izumo"


def test_ast_prefix():
    assert format_label("ast", "Itsukushima", False, "shrine") == "Santuariu Itsukushima"


def test_ast_grand():
    assert format_label("ast", "Izumo", True, "shrine") == "Gran Santuariu Izumo"


def test_sh_space_suffix():
    assert format_label("sh", "Yasukuni", False, "shrine") == "Yasukuni hram"


def test_hr_space_suffix():
    assert format_label("hr", "Yasukuni", False, "shrine") == "Yasukuni hram"
