"""Tests for the canonical title <-> filename mapping in ``title_filename.py``.

This imports the module directly, which the older
``test_title_filename_roundtrip.py`` could not do: it extracts source with a
regex because the sync scripts install a ``sys.stdout`` wrapper at module load
that breaks pytest capture. ``title_filename.py`` has no import side effects, so
keep it that way.

That older test still guards the nine copied definitions and stays until the
call sites are migrated.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.title_filename import (  # noqa: E402
    assign_filenames,
    filename_to_title,
    find_collisions,
    title_to_filename,
    title_to_filename_case_escaped,
)

TITLES = [
    "Kehi Jingū", "Why am I me?", "Template:Interlanguage link",
    "List of Shikinaisha in Awa Province (Chiba)", "无邪志国造",
    "100%/path", 'A<b>"c*d|e?f', "Main Page",
]

# The live pair, and the reason this module exists.
PAIR = ["Template:Infobox Historic Site", "Template:Infobox historic site"]


def test_plain_mapping_roundtrips():
    for t in TITLES + PAIR:
        fn = title_to_filename(t)
        assert fn.endswith(".wiki")
        assert filename_to_title(fn) == t


def test_case_escaped_mapping_roundtrips():
    for t in TITLES + PAIR:
        assert filename_to_title(title_to_filename_case_escaped(t)) == t


def test_case_escaping_does_not_double_encode_existing_escapes():
    # ':' -> '%3A' contains an uppercase 'A'. Escaping the title first and then
    # running the plain mapping would produce '%3%41', which reads back wrong.
    fn = title_to_filename_case_escaped("Template:Infobox Historic Site")
    assert "%3%41" not in fn
    assert filename_to_title(fn) == "Template:Infobox Historic Site"


def test_the_two_forms_do_not_collide_case_insensitively():
    a = title_to_filename_case_escaped(PAIR[0])
    b = title_to_filename(PAIR[1])
    assert a.lower() != b.lower()


def test_non_colliding_titles_are_completely_unchanged():
    # The whole point of collision-ONLY escaping: 99.6% of the corpus has an
    # uppercase letter, so anything that churns a non-colliding name is a bug.
    got = assign_filenames(TITLES)
    for t in TITLES:
        assert got[t] == title_to_filename(t)


def test_colliding_pair_gets_distinct_filenames():
    got = assign_filenames(PAIR)
    assert len(set(fn.lower() for fn in got.values())) == 2
    for t, fn in got.items():
        assert filename_to_title(fn) == t


def test_first_by_sort_order_keeps_the_plain_form():
    got = assign_filenames(PAIR)
    first = sorted(PAIR)[0]
    assert got[first] == title_to_filename(first)
    assert got[sorted(PAIR)[1]] != title_to_filename(sorted(PAIR)[1])


def test_assignment_is_stable_regardless_of_input_order():
    assert assign_filenames(PAIR) == assign_filenames(list(reversed(PAIR)))


def test_three_way_collision_all_distinct():
    trio = ["Foo Bar", "foo bar", "FOO BAR"]
    got = assign_filenames(trio)
    assert len(set(fn.lower() for fn in got.values())) == 3
    for t, fn in got.items():
        assert filename_to_title(fn) == t


def test_find_collisions_reports_the_pair_and_nothing_else():
    assert find_collisions(TITLES) == []
    assert find_collisions(TITLES + PAIR) == [sorted(PAIR)]


def test_forbidden_chars_still_encoded_in_both_mappings():
    for fn in (title_to_filename("a:b/c?d"), title_to_filename_case_escaped("a:b/c?d")):
        assert ":" not in fn and "/" not in fn and "?" not in fn
        assert "%3A" in fn and "%2F" in fn and "%3F" in fn


def test_percent_escaped_first():
    assert title_to_filename("100%").startswith("100%25")
    assert title_to_filename_case_escaped("100%").startswith("100%25")


def test_the_historical_mapping_is_unchanged():
    """The corpus on disk was written by the old copied definitions, so the
    plain mapping must not shift -- any divergence silently re-maps ~4,000
    pages. These expectations are hardcoded rather than read back out of a
    script, because after the 2026-09-01 migration there is no other copy left
    to compare against."""
    assert title_to_filename("Kehi Jingu") == "Kehi Jingu.wiki"
    assert title_to_filename("Template:Interlanguage link") == "Template%3AInterlanguage link.wiki"
    assert title_to_filename("a:b/c?d") == "a%3Ab%2Fc%3Fd.wiki"
    assert title_to_filename("100%") == "100%25.wiki"
    assert title_to_filename('A<b>"c*d|e?f') == 'A%3Cb%3E%22c%2Ad%7Ce%3Ff.wiki'
