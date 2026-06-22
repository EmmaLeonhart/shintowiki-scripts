"""Tests for extract_name_from_en — B1: derive downstream-language labels from
the English label (the new accurate source) instead of the Indonesian one.

The English shrine labels produced by Stages 0/1/2 are "<Name> Shrine",
"<Name> Grand Shrine", "<Name> Daijinja/Daijingu", "<Name>-gu Shrine",
"<Name>-sha Shrine". Anything that doesn't end in a recognised English shrine
suffix returns None so that shrine falls back to the Indonesian-derived path.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import extract_name_from_en  # noqa: E402


def test_plain_shrine():
    assert extract_name_from_en("Kasuga Shrine") == ("Kasuga", False, "shrine")


def test_grand_shrine_is_grand():
    assert extract_name_from_en("Kasuga Grand Shrine") == ("Kasuga", True, "shrine")


def test_daijinja_is_grand():
    assert extract_name_from_en("Kasuga Daijinja") == ("Kasuga", True, "shrine")


def test_daijingu_is_grand():
    assert extract_name_from_en("Niigata Daijingu") == ("Niigata", True, "shrine")


def test_gu_suffix_keeps_hyphenated_name():
    assert extract_name_from_en("Tenman-gu Shrine") == ("Tenman-gu", False, "shrine")


def test_sha_suffix_keeps_hyphenated_name():
    assert extract_name_from_en("Suwa-sha Shrine") == ("Suwa-sha", False, "shrine")


def test_paren_disambiguator_stripped():
    assert extract_name_from_en("Mishima Shrine (Oita)") == ("Mishima", False, "shrine")


def test_grand_checked_before_plain():
    # must not strip only " Shrine" and leave "Kasuga Grand"
    assert extract_name_from_en("Kasuga Grand Shrine")[0] == "Kasuga"


def test_unrecognised_suffix_returns_none():
    # reused Wikidata label not in canonical form -> fall back to id path
    assert extract_name_from_en("Fushimi Inari Taisha") is None


def test_suffix_only_returns_none():
    assert extract_name_from_en("Shrine") is None
    assert extract_name_from_en("Grand Shrine") is None
