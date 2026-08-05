"""The description pipeline must never overwrite a hand-written description.

Caught 2026-08-05, before anything was delivered, and only because the Wikidata
freeze was still on. `Den` SETS a description — it does not add — and 15 of the
first 22 staged lines would have replaced an Engishiki annotation with location
boilerplate:

    'The 1111th Shrine of the Engishiki Jinmyōchō (Ronsha)'
        -> 'Shinto shrine in Kōfu, Yamanashi Prefecture, Japan'
    'Ronsha 3 of Yaahino Shrine'
        -> 'Shinto shrine in Azai district, Ōmi Province, Japan'

The left side records the shrine's position in the 927 register, which disputed
entry it is a candidate for, and which numbered Ronsha it is. The right side
records where it is. Nothing recovers the former from the latter.

183 of the queued members carried one, so the majority of that queue was work
that had to NOT be done — the failure CLAUDE.md names outright: an unfamiliar
pattern in this data is signal, not corruption.

Two independent gates, because they fail differently. The builder stops the ask
being made; the collector stops an answer already sitting in a work-file from
being emitted.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_description_enrichment_queue import needs_a_description  # noqa: E402
from collect_description_enrichment import protected_members  # noqa: E402

REAL_ANNOTATIONS = [
    "1297th Shrine (Ronsha)",
    "The 1111th Shrine of the Engishiki Jinmyōchō (Ronsha)",
    "Ronsha 3 of Yaahino Shrine",
    "Toshitano Shrine (Ronsha 1)",
    "A candidate shrine for Nakagawa Shrine",
    "Candidate shrine for Suisaki-no-kami Shrine",
    "A shrine complex consisting of three different shrines. "
    "Present in the Engishiki Jinmyocho",
    "The 427th Shrine of the Engishiki Jinmyōchō, Tajihayahime Shrine Left Hall",
]


def test_absent_description_may_be_written():
    assert needs_a_description(None)
    assert needs_a_description("")
    assert needs_a_description("   ")


def test_only_the_exact_generic_may_be_replaced():
    assert needs_a_description("Shinto shrine in Japan")
    assert needs_a_description("  shinto shrine in japan  ")


def test_a_located_description_may_NOT_be_replaced():
    """Emma 2026-08-05: "We were never supposed to enrich English descriptions
    that aren't equal to Shinto shrine in Japan."

    The first version of this gate allowed every `Shinto shrine in X`, treating
    a prefecture-level description as a placeholder worth improving. Wrong:
    naming the prefecture IS the information, put there deliberately, and this
    pipeline does not get to overrule it. 11,369 shrine items carry one of these
    forms, so the earlier rule put all of them in reach."""
    for d in ("Shinto shrine in Saikai, Japan",
              "Shinto shrine in Shizuoka Prefecture, Japan",
              "Shinto shrine in Tokyo, Japan",
              "Former Shinto shrine in Taiwan",
              "shinto shrine in Kyoto, Japan"):
        assert not needs_a_description(d), d


def test_the_exact_generic_does_not_actually_occur():
    """Measured 2026-08-05: ZERO of the 14,300 English descriptions on Shinto
    shrine items are exactly 'Shinto shrine in Japan'. The exact-match arm is
    therefore dead in the current corpus, and the rule reduces to "only items
    with no description at all". Kept because the arm is what Emma's wording
    licenses, not because it fires — if it silently started matching, that
    would be a corpus change worth noticing, not a licence to rewrite."""
    assert needs_a_description("Shinto shrine in Japan")
    assert not needs_a_description("Shinto shrine in Japan, Kansai")


def test_hand_written_annotations_are_protected():
    for d in REAL_ANNOTATIONS:
        assert not needs_a_description(d), d


def test_a_description_merely_containing_the_phrase_is_still_protected():
    """Exact match, not substring. 'Ronsha 2 of the Shinto shrine in Kuwana'
    mentions the generic form but is not it."""
    assert not needs_a_description("Ronsha 2 of the Shinto shrine in Kuwana")
    assert not needs_a_description("Shinto shrine in Japan; Ronsha 2")


def test_collector_finds_protected_members_in_a_work_file():
    """Both members are protected under Emma's rule — the annotation obviously,
    and the located description because it names Kuwana. Only the member with no
    description at all stays answerable."""
    body = (
        "<!-- ANSWERS:\nQ1: \nQ2: \nQ3: \n-->\n\n== Members ==\n"
        "* [[d:Q1]] — en='A Shrine' | ja='あ' | EXISTING en desc: 'Ronsha 3 of Yaahino Shrine'\n"
        "* [[d:Q2]] — en='B Shrine' | ja='い' | EXISTING en desc: 'Shinto shrine in Kuwana, Japan'\n"
        "* [[d:Q3]] — en='C Shrine' | ja='う'\n"
    )
    prot = protected_members(body)
    assert set(prot) == {"Q1", "Q2"}
    assert prot["Q1"] == "Ronsha 3 of Yaahino Shrine"


def test_member_with_no_existing_description_is_not_protected():
    body = ("== Members ==\n* [[d:Q9]] — en='C Shrine' | ja='う'\n")
    assert protected_members(body) == {}


def test_protection_does_not_span_lines():
    """One member's description must not be attributed to the member above it —
    that would protect the wrong QID and silently drop a legitimate answer."""
    body = (
        "== Members ==\n"
        "* [[d:Q1]] — en='A Shrine' | ja='あ'\n"
        "* [[d:Q2]] — en='B Shrine' | EXISTING en desc: 'Ronsha 1 of X'\n"
    )
    assert set(protected_members(body)) == {"Q2"}
