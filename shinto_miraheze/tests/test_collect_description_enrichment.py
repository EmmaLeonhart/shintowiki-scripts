"""Tests for the description-enrichment collector (stage 1, EN-first)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import collect_description_enrichment as c  # noqa: E402

BODY = (
    "<!-- GROUP: id|Kuil X | proposed-collides: y -->\n"
    "<!-- STAGE: EN-first -->\n"
    "<!-- ANSWERS:\n"
    "Q1: {a1}\n"
    "Q2: {a2}\n"
    "-->\n"
    "<!-- TASK: ... -->\n"
)


def test_untouched_block_is_pending():
    # regression: \s* after the colon swallowed the next line's QID as an
    # "answer", making every fresh file look resolved (2026-07-08)
    assert c.parse(BODY.format(a1="", a2="")) is None


def test_filled_answers_parse():
    got = c.parse(BODY.format(a1="Shinto shrine in Maebashi, Japan",
                              a2="Shinto shrine in Shibukawa, Japan"))
    assert got == {"Q1": "Shinto shrine in Maebashi, Japan",
                   "Q2": "Shinto shrine in Shibukawa, Japan"}


def test_partial_fill_parses_only_filled():
    got = c.parse(BODY.format(a1="Shinto shrine in Maebashi, Japan", a2=""))
    assert got == {"Q1": "Shinto shrine in Maebashi, Japan"}
