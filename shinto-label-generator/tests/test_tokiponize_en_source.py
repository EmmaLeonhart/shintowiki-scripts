"""Tests for the English source branch of fetch_shrines_tokiponize (B1b):
Toki Pona names now derive from the English label too, suffix-stripped via
extract_name_from_en, then despaced/lowercased like the other sources."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_shrines_tokiponize import process_label, make_tokipona_label  # noqa: E402


def test_en_plain_shrine():
    # ("Shrine", "kasuga") -> non-grand
    assert process_label("en", "Kasuga Shrine") == ("Shrine", "kasuga")


def test_en_grand_shrine_is_grand():
    assert process_label("en", "Kasuga Grand Shrine") == ("Temple Grand", "kasuga")


def test_en_hyphenated_name_despaced():
    assert process_label("en", "Tenman-gu Shrine") == ("Shrine", "tenmangu")


def test_en_non_canonical_label_skipped():
    assert process_label("en", "Fushimi Inari Taisha") is None


def test_en_grand_produces_suli():
    prefix, name = process_label("en", "Meiji Daijingu")
    assert make_tokipona_label(prefix, name).startswith("tomo sewi suli ")


def test_en_plain_no_suli():
    prefix, name = process_label("en", "Kasuga Shrine")
    label = make_tokipona_label(prefix, name)
    assert label == "tomo sewi kasuga"


def test_existing_id_source_unchanged():
    # the kept Indonesian path must still work exactly as before
    assert process_label("id", "Kuil Kasuga") == ("Kuil", "kasuga")
