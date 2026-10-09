"""Kami label fan-out (Emma, 2026-10-08): same romanised label in mul/en/en-us/fr/es."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import generate_kami_label_fanout as g  # noqa: E402


def test_fills_only_missing_languages_from_en():
    lines, missing = g.build_lines({"Q1": {"en": "Ontake Ōkami", "mul": "Ontake Ōkami"}}, {})
    assert lines == ['Q1|Len-us|"Ontake Ōkami"', 'Q1|Lfr|"Ontake Ōkami"', 'Q1|Les|"Ontake Ōkami"']
    assert missing == []


def test_reading_used_when_no_en_and_never_overwrites():
    lines, _ = g.build_lines({"Q2": {"fr": "Autre"}}, {"Q2": "Hime-no-Mikoto"})
    assert 'Q2|Lfr|"Hime-no-Mikoto"' not in lines
    assert {l.split("|")[1] for l in lines} == {"Lmul", "Len", "Len-us", "Les"}


def test_item_with_neither_is_reported_not_guessed():
    lines, missing = g.build_lines({"Q3": {}}, {})
    assert lines == [] and missing == ["Q3"]


def test_every_created_kami_without_en_has_a_reading():
    readings = g.load_readings()
    assert len(readings) == 126
    assert set(readings) <= set(g.created_qids())


def test_registered():
    assert '"kami_label_fanout.txt"' in open(os.path.join(HERE, "direct_daily_edits.py"), encoding="utf-8").read()
    wf = os.path.join(os.path.dirname(HERE), ".github", "workflows", "generate-quickstatements.yml")
    assert "python generate_kami_label_fanout.py" in open(wf, encoding="utf-8").read()
