"""Tests for the non-shrine exclusion in the name-in-kana builder.

The thing these pin down, because it is counter-intuitive and was diagnosed
wrong once already: our `?item wdt:P31 wd:Q845945` filter is NOT leaky. The
items that reach the target set and are not shrines genuinely carry
`P31 = Q845945` on Wikidata — Q7137401 水谷川忠起 is a human AND, per Wikidata,
a Shinto shrine. So the exclusion cannot be a tighter shrine test; it has to key
off the OTHER class the item carries.

The second half of the story is the deliberate NON-exclusions. Emma ruled in
queue.md A0 that the place-ish items stay in, because P1814 is "name in kana"
and not shrine-specific — a forest and a palace building-complex have real
readings. Excluding by "is it literally a shrine" would drop those too, which is
why the rule is "is it a nameable place", not "is it a shrine".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_name_in_kana_queue import (  # noqa: E402
    NOT_A_SHRINE, TARGET_QUERY, not_a_shrine_reason,
)


def test_no_co_class_is_not_excluded():
    assert not_a_shrine_reason(["Q845945"]) is None


def test_person_is_excluded():
    """Q7137401 水谷川忠起 — the item that prompted the whole investigation."""
    reason = not_a_shrine_reason(["Q845945", "Q5"])
    assert reason is not None
    assert "human" in reason


def test_order_of_classes_does_not_matter():
    assert not_a_shrine_reason(["Q5", "Q845945"]) is not None


def test_disambiguation_page_is_excluded():
    """A disambig item names several shrines, so a reading attaches to none."""
    assert not_a_shrine_reason(["Q845945", "Q4167410"]) is not None


def test_festival_and_book_and_organization_are_excluded():
    for qid in ("Q11487032", "Q11489226", "Q7725634", "Q11590703"):
        assert not_a_shrine_reason(["Q845945", qid]) is not None, qid


def test_legitimate_shrine_subtypes_are_kept():
    """The bulk of the corpus. Shikinaisha (442 items) and Kokuhei-sha (440) are
    the two most common co-classes in the target set — excluding either would
    empty the queue."""
    for qid in ("Q134917286", "Q135160342", "Q135022904", "Q11390939",
                "Q514480", "Q11590310", "Q1534477"):
        assert not_a_shrine_reason(["Q845945", qid]) is None, qid


def test_place_ish_items_are_deliberately_kept():
    """Emma's ruling, queue.md A0: these were answered, not worked around.
    Q5367406 春日山原始林 (old-growth forest) and Q7797685 宮中三殿 (building
    complex / triad) both have plainly-right readings."""
    for qid in ("Q208478", "Q1497364", "Q29430681", "Q8502", "Q1052919",
                "Q11394747", "Q114768"):
        assert not_a_shrine_reason(["Q845945", qid]) is None, qid


def test_query_returns_the_classes_the_filter_needs():
    """The filter is useless if the query stops returning co-classes. Pins both
    the projected variable and the GROUP BY that makes the aggregate legal."""
    assert "?classes" in TARGET_QUERY
    assert "GROUP_CONCAT" in TARGET_QUERY
    assert "GROUP BY" in TARGET_QUERY
    assert "wdt:P31 ?cls" in TARGET_QUERY


def test_exclusions_carry_a_reason():
    """The reason is printed in the build log; an empty one hides the drop."""
    for qid, reason in NOT_A_SHRINE.items():
        assert qid.startswith("Q") and reason.strip()
