"""The 2026-08-24 sort-at-the-writer fix does not silently come undone (2026-09-20).

`8c65d9b6` sorted six generators at the writer after finding that the scheduled
build rewrote them entirely for no content change — *"~12,000 lines of pure
reshuffle per build"*. Ten files were covered in all, across that commit and its
predecessor.

⛔ **The damage a reshuffle does is to the diff, not the data.** A file that
reorders every run makes its own history unreadable, and an unreadable history is
how a dead pipeline went unnoticed for two days (the 2026-08-21 tok.txt /
id_proposed.txt churn) and how `description_label_pairs.txt` sat unchanged through
three Sundays with nothing looking wrong.

The fix was verified per-file from git rather than asserted. For
`migrate_ritsuryo_funding_remove.txt`, the last of the ten and the one the Wikidata
lockout had kept unmeasurable, on 2026-09-20:

    before  08-15 -> 08-25   9 commits   +2880/-2880 .. +3950/-3950
                                          sorted md5 0a042f48bc5f on ALL NINE
    after   09-07 -> 09-17   9 commits   +0/-5 .. +0/-499
                                          sorted md5 changes every time

Pure reshuffle became pure deletion. That reading is in
`docs/deferred_verification.md`; what is here is the standing guard, so the next
regression is caught by a test rather than by someone re-running that comparison.
"""
import io
import os

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The nine of the ten whose writers emit ONE plain-sorted block.
SORTED_FILES = (
    "kana_qualifier_add.txt",
    "migrate_ritsuryo_funding_remove.txt",
    "ronsha_ojp_name_removals.txt",
    "shikinaisha_kokugakuin_refs.txt",
    "address_citation_backfill.txt",
    "kana_redundant_remove.txt",
    "multi_ordinal_removals.txt",
    "orphan_membership_removals.txt",
    "tenjinsha_en_labels.txt",
)

# ⛔ The tenth, and it is NOT an oversight. `daily_operations.txt` is built by
# `generate_modern_shrine_ranking_qualifiers.generate_daily_operations`, which
# CONCATENATES the other files in a documented priority order — "Phase 1 (P459
# qualifiers) until complete, Phase 2 (property edits) after Phase 1 complete,
# P4656 references..." — so its order is the instruction, and sorting it would
# destroy exactly what it is for.
#
# It is also not churning, which is the property that actually matters and which
# a sort check is only ever a proxy for. Measured over its six most recent
# commits (09-12 -> 09-19): +0/-2 .. +2/-75, sorted md5 different every time.
CONCATENATED = "daily_operations.txt"


def _lines(filename):
    path = os.path.join(HERE, filename)
    if not os.path.exists(path):
        pytest.skip("%s is not present" % filename)
    return [l for l in io.open(path, encoding="utf-8").read().splitlines()
            if l.strip()]


@pytest.mark.parametrize("filename", SORTED_FILES)
def test_stays_sorted(filename):
    lines = _lines(filename)
    if not lines:
        pytest.skip("%s is empty; a drained file cannot be out of order" % filename)
    assert lines == sorted(lines), (
        "%s is no longer written in sorted order, so every build will rewrite it "
        "whole and its diff stops being readable — the 2026-08-24 churn" % filename)


def test_the_tenth_is_excluded_for_a_reason_and_still_looks_like_one():
    """⚠ Guard the EXCLUSION, not just the rule.

    An exclusion with a comment is an exclusion someone can quietly widen. This
    asserts the one excluded file still has the shape that earned it: a
    concatenation whose first block is another of the ten, so sorting it would
    interleave sources that are meant to stay in priority order.
    """
    lines = _lines(CONCATENATED)
    assert lines, "daily_operations.txt is empty; the aggregate should not be"
    assert lines != sorted(lines), (
        "daily_operations.txt is now plain-sorted. If its writer was changed to "
        "sort, the priority order that generate_daily_operations() documents is "
        "gone — move it into SORTED_FILES only after checking that was intended")
    first = _lines("migrate_ritsuryo_funding_remove.txt")
    if first:
        assert lines[0] == first[0], (
            "the aggregate no longer opens with the first block it concatenates; "
            "the exclusion above was argued from that shape")


def test_the_ten_are_all_accounted_for():
    """Nine plus the concatenated one. A file dropping out of this list silently
    is the same failure as the sort coming undone."""
    assert len(SORTED_FILES) == 9
    assert CONCATENATED not in SORTED_FILES


def test_the_files_are_all_registered_for_the_drip():
    """A sorted file nothing submits is a file this test is guarding for nothing.

    ⚠ `daily_operations.txt` is deliberately NOT asserted here — it is the human
    "what to run now" aggregate, not an atomic input.
    """
    import sys
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import direct_daily_edits as d
    atomic = set(d.ATOMIC_FILES)
    missing = [f for f in SORTED_FILES if f not in atomic]
    assert not missing, (
        "these are pinned as sorted but no longer reach the drip: %s" % missing)
