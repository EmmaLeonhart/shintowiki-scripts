"""The multi-P13677 resolution rule in generate_p958_qualifiers.

Before 2026-08-16 every item carrying more than one Kokugakuin ID was pushed to manual
review, on the belief that you cannot tell which ID a section number belongs to. You can:
a 論社 candidate is listed under every parent entry it is a candidate for and carries one
P13677 per parent entry, so the ID matching THIS parent's own ID is this parent's.

The three multi-ID cases below are real, taken from p958_manual_review.txt and checked
against live Wikidata on 2026-08-16.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The generator rebinds sys.stdout to a UTF-8 wrapper at import time (every script here
# does, so Japanese labels survive a cp1252 console). Under pytest that wrapper takes
# over the capture object's buffer and closing it later breaks capture teardown with
# "I/O operation on closed file". Restoring stdout straight after the import keeps the
# generator's real behaviour untouched while leaving pytest's capture intact.
# _KEEPALIVE is not dead code: dropping the wrapper lets it be garbage-collected, and
# TextIOWrapper closes the buffer it wraps when it finalises, which is pytest's capture
# buffer. Holding the reference for the life of the module is what keeps it open.
_saved_stdout = sys.stdout
try:
    from generate_p958_qualifiers import resolve_multi_p13677  # noqa: E402
finally:
    _KEEPALIVE = sys.stdout
    sys.stdout = _saved_stdout


class TestRealCases:
    """Verified live 2026-08-16 — each child's IDs and each parent's own ID."""

    def test_amanokaguyama_two_parents(self):
        # Q98082987 carries 180853 and 180859; its two parents hold one each.
        child = ["180853", "180859"]
        assert resolve_multi_p13677(child, "180853") == "180853"   # Q135039029 Unehino
        assert resolve_multi_p13677(child, "180859") == "180859"   # Q135039033 Amanokakoyamano

    def test_rokusho_three_parents(self):
        # Q135190252 carries three IDs and is a candidate under three parent entries.
        child = ["181505", "181507", "181506"]
        assert resolve_multi_p13677(child, "181505") == "181505"   # Q135039595 Takane
        assert resolve_multi_p13677(child, "181506") == "181506"   # Q135039596 Rokusho
        assert resolve_multi_p13677(child, "181507") == "181507"   # Q135039597 Wakayamatono

    def test_iino_two_parents(self):
        child = ["181268", "181278"]
        assert resolve_multi_p13677(child, "181268") == "181268"   # Q135039374 Takaichino
        assert resolve_multi_p13677(child, "181278") == "181278"   # Q135039382 Ihinono


class TestRefusals:
    """Anything that cannot be settled must return None, so the item reaches a human.

    Guessing here would attach a section number to the wrong identifier on a real
    shrine, which is the same class of error as the 18% author-duplicate rate: a
    confident wrong statement is worse than a missing one.
    """

    def test_no_parent_value_refuses(self):
        assert resolve_multi_p13677(["180853", "180859"], None) is None
        assert resolve_multi_p13677(["180853", "180859"], "") is None

    def test_parent_id_not_among_the_children_refuses(self):
        assert resolve_multi_p13677(["180853", "180859"], "999999") is None

    def test_no_ids_at_all_refuses(self):
        assert resolve_multi_p13677([], "180853") is None

    def test_duplicate_identical_ids_refuse(self):
        # Two identical values are not a unique match; refuse rather than pick one.
        assert resolve_multi_p13677(["180853", "180853"], "180853") is None


class TestSingleIdStillWorks:
    """The rule must not disturb the ordinary one-ID case."""

    def test_single_matching_id(self):
        assert resolve_multi_p13677(["180853"], "180853") == "180853"

    def test_single_non_matching_id(self):
        assert resolve_multi_p13677(["180853"], "180859") is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
