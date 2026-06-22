"""B3 — eo (Esperanto) and jv (Javanese), Latin-script. Conventions from existing
labels: eo "Jaŝiro <Name>" / "Ĉefjaŝiro <Name>" (grand); jv "Kuil <Name>"."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, ALL_LANGS  # noqa: E402


def test_in_all_langs():
    assert "eo" in ALL_LANGS and "jv" in ALL_LANGS


def test_eo_plain():
    assert format_label("eo", "Kasuga", False, "shrine") == "Jaŝiro Kasuga"


def test_eo_grand():
    assert format_label("eo", "Izumo", True, "shrine") == "Ĉefjaŝiro Izumo"


def test_jv_plain():
    assert format_label("jv", "Meiji", False, "shrine") == "Kuil Meiji"
