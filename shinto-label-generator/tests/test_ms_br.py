"""Deep tail — ms (Malay) and br (Breton), Latin affix. Conventions from existing
labels: ms "Kuil <Name>" / "Kuil Agung <Name>" (grand); br "Santual <Name>"."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, ALL_LANGS  # noqa: E402


def test_in_all_langs():
    assert "ms" in ALL_LANGS and "br" in ALL_LANGS


def test_ms_prefix():
    assert format_label("ms", "Itsukushima", False, "shrine") == "Kuil Itsukushima"


def test_ms_grand():
    assert format_label("ms", "Izumo", True, "shrine") == "Kuil Agung Izumo"


def test_br_prefix():
    assert format_label("br", "Yasukuni", False, "shrine") == "Santual Yasukuni"
