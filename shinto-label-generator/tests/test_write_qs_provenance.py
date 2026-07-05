"""write_qs provenance comments (todo: "annotate output lines with the source label
they derive from"). A 4th `source` element emits a '# <source>' comment line before
the label; 3-tuples are unchanged. Comment lines are skipped by the drip selector and
the submitter, so they never reach Wikidata.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translit_common import write_qs  # noqa: E402


def _write(tmp, lines):
    p = os.path.join(tmp, "out.txt")
    write_qs(p, lines)
    with open(p, encoding="utf-8") as f:
        return f.read().splitlines()


def test_three_tuple_unchanged(tmp_path):
    out = _write(tmp_path, [("Q1", "de", 'Kasuga')])
    assert out == ['Q1\tLde\t"Kasuga"']


def test_four_tuple_emits_provenance_comment_before_label(tmp_path):
    out = _write(tmp_path, [("Q1", "de", "Kasuga", 'romaji "kasuga"')])
    assert out == ['# romaji "kasuga"', 'Q1\tLde\t"Kasuga"']
    # the provenance line is a comment (drip/submitter skip '#') — never submitted
    assert out[0].startswith("#")


def test_falsy_source_emits_no_comment(tmp_path):
    out = _write(tmp_path, [("Q1", "de", "Kasuga", ""), ("Q2", "de", "Ise", None)])
    assert out == ['Q1\tLde\t"Kasuga"', 'Q2\tLde\t"Ise"']


def test_source_is_sanitised_to_one_tab_free_line(tmp_path):
    out = _write(tmp_path, [("Q1", "de", "X", "ja\tkanji\n\"神\"")])
    # no tab/newline survives in the comment, so it can't be misparsed as QS fields
    assert out[0].startswith("# ") and "\t" not in out[0]
    assert out[1] == 'Q1\tLde\t"X"'


def test_quotes_in_label_still_doubled_with_provenance(tmp_path):
    out = _write(tmp_path, [("Q1", "de", 'A"B', "src")])
    assert out == ['# src', 'Q1\tLde\t"A""B"']
