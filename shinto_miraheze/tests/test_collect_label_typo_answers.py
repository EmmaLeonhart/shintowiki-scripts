"""Tests for collect_label_typo_answers.parse_answer (no filesystem/network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collect_label_typo_answers import parse_answer  # noqa: E402


def _wf(answer):
    return ("<!-- ITEM: https://www.wikidata.org/wiki/Q1 -->\n"
            "<!-- JA: x | KANA: y | EN_LABEL: z | KANA_ROMANIZED: w -->\n"
            f"<!-- ANSWER: {answer} -->\n<!-- TASK: ... -->\n")


def test_empty_answer_pending():
    assert parse_answer(_wf("")) is None


def test_label_typo_parsed():
    assert parse_answer(_wf("LABEL_TYPO: Saruga Shrine")) == ("LABEL_TYPO", "Saruga Shrine")


def test_kana_issue_parsed():
    kind, note = parse_answer(_wf("KANA_ISSUE: historical kana ちりふ=Chiryū"))
    assert kind == "KANA_ISSUE" and "Chiry" in note


def test_prefix_ok_parsed():
    assert parse_answer(_wf("PREFIX_OK: Kurume is a legit disambiguator"))[0] == "PREFIX_OK"


def test_free_text_falls_to_other():
    assert parse_answer(_wf("the label is fine actually"))[0] == "OTHER"
