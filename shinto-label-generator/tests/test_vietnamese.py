"""Tests for Vietnamese label formatting (B4). Convention from existing Wikidata
labels: "Đền <Name>" (shrine), "Thần cung <Name>" (grand/jingū), "Chùa" (temple)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, ALL_LANGS  # noqa: E402


def test_vi_in_all_langs():
    assert "vi" in ALL_LANGS


def test_vi_plain_shrine():
    assert format_label("vi", "Itsukushima", False, "shrine") == "Đền Itsukushima"


def test_vi_grand_shrine():
    assert format_label("vi", "Ise", True, "shrine") == "Thần cung Ise"


def test_vi_temple():
    assert format_label("vi", "Senso", False, "temple") == "Chùa Senso"
