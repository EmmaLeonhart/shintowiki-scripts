"""Tests for the ronsha ranking collector (cloud-RAG back half)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import collect_ronsha_rankings as c  # noqa: E402

BODY = (
    "<!-- RONSHA: https://www.wikidata.org/wiki/Q135039638 | Sakitamahimeno- Shrine |  -->\n"
    "<!-- ANSWER: {ans} -->\n"
    "<!-- TASK: ... LIKELY: <QID> ... UNDECIDABLE: <why> ... -->\n\n"
    "== Candidates (P460, all unranked) ==\n"
    "* [[d:Q110915859]] Oshaku Shrine\n"
    "* [[d:Q134930603]] Ryou Shrine\n"
)


def test_unanswered_is_none():
    assert c.parse(BODY.format(ans="")) is None


def test_likely_parses():
    r, cands, kind, payload = c.parse(BODY.format(ans="LIKELY: Q110915859"))
    assert r == "Q135039638" and kind == "LIKELY"
    assert cands == ["Q110915859", "Q134930603"]
    assert "Q110915859" in payload


def test_undecidable_parses():
    _, _, kind, payload = c.parse(BODY.format(ans="UNDECIDABLE: both equally attested"))
    assert kind == "UNDECIDABLE" and payload.startswith("both")


def test_freeform_is_malformed():
    _, _, kind, _ = c.parse(BODY.format(ans="probably the first one"))
    assert kind == "MALFORMED"


def test_task_example_not_matched_as_answer():
    # the TASK comment quotes 'LIKELY:' examples; an empty ANSWER must stay pending
    assert c.parse(BODY.format(ans=" ")) is None
