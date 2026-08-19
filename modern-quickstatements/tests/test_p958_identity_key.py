"""The Kokugakuin identity key is (P13677 + section P958) -- and two section values
carry no uniqueness at all.

Emma, 2026-08-19, correcting a report that matched duplicate shrines on the bare id:

    "They are meant to be unique by the combination of Kokugakuin University Digital
     Museum entry ID (P13677) and its qualifier section (P958)... each ID is supposed to
     have many different entries... except if their qualifier is zero, at which point
     they do not even need to be unique"

and then, on the one pair that survived that first correction:

    "'n/a' is not uniqueness protected"

Both exemptions are load-bearing. With the bare id as the key, 11 pairs looked like
duplicates; with `0` exempt, 1 survived; with `n/a` also exempt, none did. A regression
here does not crash anything -- it silently re-manufactures duplicate shrine pairs and
puts them in front of Emma as a merge decision.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report_orphan_shikinaisha import dup_key


def test_a_real_section_makes_a_key():
    assert dup_key("183217", "1") == ("183217", "1")
    assert dup_key("183217", "2") == ("183217", "2")


def test_section_zero_is_not_uniqueness_protected():
    assert dup_key("183192", "0") is None


def test_section_na_is_not_uniqueness_protected():
    assert dup_key("181621", "n/a") is None


def test_a_missing_section_establishes_nothing():
    assert dup_key("183217", None) is None


def test_the_id_alone_never_matches_two_items():
    """The original bug, stated as a property: same id, different sections, no match."""
    living, twin = dup_key("183217", "1"), dup_key("183217", "n/a")
    assert living != twin
    assert twin is None


def test_two_exempt_sections_do_not_match_each_other():
    """Both sides 'n/a' was the last surviving pair. It is not a match either."""
    assert dup_key("181621", "n/a") == dup_key("181621", "n/a") == None
