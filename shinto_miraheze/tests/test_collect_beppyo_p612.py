"""Tests for the Beppyo mother-house collector (queue item A0b).

Two things are worth pinning. First the MODEL: docs/wikidata_shrine_festival_model.md
makes ONE P612 with P1013=Q195793 in the same statement an invariant, and a bare
P612 a defect that a separate repair script exists to clean up — so the emitted
line shape is not cosmetic. Second the GATES: the answers come from an LLM
reading prose about major, highly-visible shrines, where a guessed mother house
is a worse outcome than a missing one.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collect_beppyo_p612 import (  # noqa: E402
    AUTOCHTHONOUS, BUNREI, mother_target, parse_answer,
)


def _wf(answer):
    return ("<!-- ITEM: https://www.wikidata.org/wiki/Q701403 -->\n"
            "<!-- JA: 鶴岡八幡宮 | EN: Tsurugaoka Hachimangū | SITELINKS: 21 -->\n"
            "<!-- ARTICLE: https://ja.wikipedia.org/wiki/%E9%B6%B4%E5%B2%A1 -->\n"
            f"<!-- ANSWER: {answer} -->\n<!-- TASK: ... -->\n\n== ARTICLE ==\n...\n")


def test_empty_answer_is_still_pending():
    assert parse_answer(_wf("")) is None


def test_three_answer_kinds_parse():
    assert parse_answer(_wf("MOTHER: Q710098 # 石清水八幡宮"))[0] == "MOTHER"
    assert parse_answer(_wf("AUTOCHTHONOUS: founded in situ 593"))[0] == "AUTOCHTHONOUS"
    assert parse_answer(_wf("UNCLEAR: two competing 社伝"))[0] == "UNCLEAR"


def test_undeclared_answer_is_malformed():
    assert parse_answer(_wf("Iwashimizu Hachimangu probably"))[0] == "MALFORMED"


# ─────────────────────────── the gates ───────────────────────────

def test_mother_target_extracted_before_the_comment():
    assert mother_target("Q710098 # 石清水八幡宮", "Q701403") == ("Q710098", "")


def test_a_name_without_a_qid_is_refused():
    """'Do not guess a Q-id from a name' — a bare name must not become a claim."""
    q, why = mother_target("石清水八幡宮", "Q701403")
    assert q is None and "Q-id" in why


def test_self_reference_is_refused():
    """A shrine cannot be its own mother house; this is the shape an LLM produces
    when it echoes the subject back."""
    q, why = mother_target("Q701403 # itself", "Q701403")
    assert q is None and "subject" in why


def test_autochthonous_via_mother_is_refused():
    """Q135508874 belongs in the AUTOCHTHONOUS branch; accepting it here would let
    the same fact arrive by two paths with different log labels."""
    q, why = mother_target(f"{AUTOCHTHONOUS} # autochthonous", "Q701403")
    assert q is None and "AUTOCHTHONOUS" in why


# ─────────────────────────── the model ───────────────────────────

def test_emitted_line_carries_the_criterion_qualifier():
    """The invariant: ONE P612 with P1013=Q195793 in the SAME statement, never
    bare. generate_bunrei_qualifier_repair.py exists to clean up bare ones."""
    line = f'Q701403|P612|Q710098|P1013|{BUNREI}|S854|"https://ja.wikipedia.org/wiki/x"'
    assert re.match(r'^Q\d+\|P612\|Q\d+\|P1013\|Q195793\|S854\|"https://', line)
    assert BUNREI == "Q195793"


def test_autochthonous_is_a_real_value_not_a_skip():
    """Q135508874 is emitted as the P612 value — 'no mother house' is a finding
    that gets recorded, not a silently dropped row."""
    line = f'Q191763|P612|{AUTOCHTHONOUS}|P1013|{BUNREI}|S854|"https://ja.wikipedia.org/wiki/x"'
    assert AUTOCHTHONOUS == "Q135508874"
    assert "|P612|Q135508874|P1013|Q195793|" in line
