"""The dedication terms resolved to QIDs, and validated (2026-09-19).

`table_audit.tsv` was a lookup done for the LABEL work, where a wrong QID costs
nothing — the labels come from the morpheme table, not from the resolved item.
Used for `P825` it asserts a fact, and measured against the live P31 of all 101
rows the table is **52% wrong**.

The queue item named one: *"All Saints -> Q165386 is a girl group"*. It is not an
outlier. Unvalidated, this table would have dedicated churches to French
communes, a 1984 Mario Camus film and a Sufjan Stevens album.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import saint_qids as s  # noqa: E402


# --------------------------------------------------------------------------
# The named example, and the ones it turned out to be standing in for
# --------------------------------------------------------------------------
def test_the_girl_group():
    assert s.qid_for("All Saints") is None
    assert s.REFUSED["All Saints"][0] == "Q165386"


@pytest.mark.parametrize("term,what", [
    ("Saint Joseph", "commune of France"),
    ("Saint Thomas", "island"),
    ("the Holy Innocents", "film"),
    ("the Ascension", "album"),
    ("the Theotokos", "scholarly article"),
    ("the Presentation", "television series episode"),
    ("Peace", "family name"),
    ("Corpus Christi", "city"),
])
def test_the_ones_it_was_standing_in_for(term, what):
    assert s.qid_for(term) is None, term
    assert what in s.REFUSED[term][1], (term, s.REFUSED[term])


def test_a_church_is_not_a_dedicatee():
    """8 terms resolved to a CHURCH NAMED AFTER the dedicatee — `Our Lady Queen
    of Heaven` is a Catholic church in Bayswater. Dedicating a church to another
    church is the most plausible-looking wrong answer in the table."""
    for term in ("Our Lady Queen of Heaven", "Our Lady Queen of Poland",
                 "the Sacred Heart", "the Holy Cross"):
        assert s.qid_for(term) is None, term
        assert "church" in s.REFUSED[term][1], term


# --------------------------------------------------------------------------
# ⛔ A depiction of X is not X
# --------------------------------------------------------------------------
@pytest.mark.parametrize("term", [
    "the Transfiguration",      # Raphael's canvas
    "the Holy Trinity",         # El Greco's
    "the Epiphany",             # a Bosch triptych
    "the Visitation",
    "Saint Demetrius",
    "Our Lady of Kazan",        # the physical icon
    "Our Lady of Vladimir",
])
def test_a_depiction_is_refused(term):
    """⛔ The largest refused group. The feast has its own item and this lookup
    did not find it. `Our Lady of Kazan` is the icon in Kazan Cathedral — a real
    thing a church could be dedicated to, and still not the Marian title the
    label names. Same line `generate_honzon_quickstatements` holds when it
    refuses `P825 -> 重要文化財`."""
    assert s.qid_for(term) is None
    assert any(w in s.REFUSED[term][1]
               for w in ("painting", "icon", "triptych", "artistic theme",
                         "statue")), s.REFUSED[term]


# --------------------------------------------------------------------------
# What IS allowed
# --------------------------------------------------------------------------
@pytest.mark.parametrize("term,qid", [
    ("Saint Andrew", "Q43399"),
    ("Saint Anne", "Q164294"),
    ("Saint Michael", "Q45581"),        # archangel, not a human
    ("Our Lady of Guadalupe", "Q31877"),
    ("Our Lady of Lourdes", "Q21532387"),
])
def test_the_validated_ones(term, qid):
    assert s.qid_for(term) == qid


def test_the_assumption_survives_on_its_dogma_statement():
    """⚠ Q162691 carries `artistic theme` among its classes and would fail a
    naive depiction filter. It is allowed because it is also a DOGMA — the test
    is whether ANY class is a dedicatee class, not whether every one is."""
    assert s.qid_for("the Assumption") == "Q162691"


def test_unlisted_means_refuse():
    """⛔ The doctrine `romance_katakana.rules_for_country` already holds: a
    default is how the wrong answer gets in."""
    assert s.qid_for("Saint Nobody") is None
    assert len(s.ALLOWED_CLASSES) < 30, (
        "the allow-list is a list of what a dedicatee may BE; if it grows past "
        "a page it has stopped being one")


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------
def test_the_two_halves_do_not_overlap():
    assert not (set(s.SAINT_QIDS) & set(s.REFUSED))


def test_every_refusal_carries_a_reason():
    for term, (qid, why) in s.REFUSED.items():
        assert why and len(why) > 3, term
        assert qid.startswith("Q") or why == "no QID resolved", term


def test_the_rate_is_recorded_where_it_will_be_read():
    """The 52% is the reason this module exists; a later reader finding only the
    map would have no idea the seed was half wrong."""
    assert "52% wrong" in s.__doc__
    assert len(s.SAINT_QIDS) + len(s.REFUSED) == 100, (
        "101 rows, one term listed twice"
    )


def test_a_refused_term_is_never_a_fallback():
    """⚠ `REFUSED` records the wrong answer so the next lookup does not
    rediscover it — not so the term can be used anyway."""
    for term in s.REFUSED:
        assert s.qid_for(term) is None, term
