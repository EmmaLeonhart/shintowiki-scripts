"""Tests for the Ronsha Old-Japanese official-name removals (Emma 2026-07-09).

The load-bearing bit is the guard. `P31` is not exclusive: 15 items are typed
BOTH Q135022904 (Ronsha) and Q135038714 (Disputed Shikinaisha/Shikigeisha).
Those are Engishiki *entries* that also carry the Ronsha class, and their Old
Japanese official name is genuine. Removing it would be data loss, so the query
must exclude them.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import direct_daily_edits  # noqa: E402
import generate_ronsha_ojp_name_removals as g  # noqa: E402
import submit_daily_batch  # noqa: E402


def test_query_excludes_items_that_are_also_engishiki_entries():
    q = g.build_query()
    assert "FILTER NOT EXISTS" in q
    assert f"wd:{g.SHIKINAISHA}" in q and f"wd:{g.DISPUTED_ENTRY}" in q
    assert f"?item wdt:P31 wd:{g.RONSHA}" in q


def test_query_only_targets_old_japanese():
    assert 'STRSTARTS(LANG(?name), "ojp")' in g.build_query()


def test_removal_line_is_a_quickstatements_v1_monolingual_removal():
    line = g.qs_removal("Q11677110", "鹿島天足和気神社", "ojp-hani")
    assert line == '-Q11677110|P1448|ojp-hani:"鹿島天足和気神社"'


def test_removal_line_round_trips_through_the_daily_editor():
    """The generator's output must be exactly what direct_daily_edits can execute."""
    line = g.qs_removal("Q11677110", "鹿島天足和気神社", "ojp-hani")
    parsed = direct_daily_edits.parse_qs_line(line)
    assert parsed["is_removal"] is True
    assert parsed["entity"] == "Q11677110"
    assert parsed["property"] == "P1448"
    assert parsed["value"] == {
        "type": "monolingualtext",
        "value": {"text": "鹿島天足和気神社", "language": "ojp-hani"},
    }


def test_hyphenated_language_code_survives_the_parser():
    """`ojp-hani` must match the parser's language regex, not fall through to 'unknown'."""
    v = direct_daily_edits.parse_qs_value('ojp-hani:"x"')
    assert v["type"] == "monolingualtext"
    assert v["value"]["language"] == "ojp-hani"


def test_registered_in_both_atomic_file_lists():
    """Otherwise the file's lines silently never flow (the 2026-07-04 drift bug)."""
    assert g.OUTPUT_FILE in direct_daily_edits.ATOMIC_FILES
    assert g.OUTPUT_FILE in submit_daily_batch.ATOMIC_FILES


def test_embedded_double_quote_is_rejected():
    assert not g.is_quotable('name"with"quote')


def test_normal_japanese_names_are_quotable():
    assert g.is_quotable("鹿島天足和気神社")
    assert g.is_quotable("大麻止乃豆乃天神社")


def test_a_pipe_is_safe_because_the_splitter_honours_quotes():
    """Checked, not assumed: `|` inside the quoted value does not split the line."""
    parts = direct_daily_edits.split_qs_parts('Q1|P1448|ojp-hani:"a|b"|P580|+2020-00-00T00:00:00Z/9')
    assert parts == ["Q1", "P1448", 'ojp-hani:"a|b"', "P580", "+2020-00-00T00:00:00Z/9"]
    assert g.is_quotable("a|b")


def test_an_embedded_quote_swallows_the_following_field():
    """The actual hazard: the splitter is left inside-out, so P580 vanishes into the value."""
    parts = direct_daily_edits.split_qs_parts('Q1|P1448|ojp-hani:"a"b"|P580|+2020-00-00T00:00:00Z/9')
    assert parts == ["Q1", "P1448", 'ojp-hani:"a"b"|P580|+2020-00-00T00:00:00Z/9']


def test_p1448_table_is_scoped_off_the_candidates():
    """Emma: the official-names page looks at Shikinaisha and disputed entries, not candidates."""
    import generate_modern_shrine_ranking_qualifiers as ranking

    assert ranking.DUP_SUBJECT["P1448"] == [ranking.SHIKINAISHA, ranking.DISPUTED_ENTRY]
    assert ranking.RONSHA not in ranking.DUP_SUBJECT["P1448"]
    # addresses and part-of really are the candidates' problem
    assert ranking.DUP_SUBJECT["P6375"] == [ranking.RONSHA]
    assert ranking.DUP_SUBJECT["P361"] == [ranking.RONSHA]


def test_p1448_query_counts_statements_distinctly():
    """An item typed with two subject classes matches the VALUES join twice."""
    import inspect

    import generate_modern_shrine_ranking_qualifiers as ranking

    src = inspect.getsource(ranking.fetch_duplicate_qids)
    assert "COUNT(DISTINCT ?s)" in src
