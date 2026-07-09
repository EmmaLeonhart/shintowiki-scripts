"""Scope guard for the P361 Shikinaisha-list rebuild (2026-07-09).

`P361` on a shrine means many things: "listed in a province's Shikinaisha list",
but also "this subshrine is part of Kamigamo Shrine", "part of the Twenty-Two
Shrines ranking", "part of the Ninety-Nine Ōji Shrines of the Kumano Kodō".

The first version of the batch treated every P361 target as a Shikinaisha list.
Of 249 targets, only 47 were: the other 202 were shrines and classes. Its removal
lines would have deleted 425 real statements, including subshrines' membership of
their parent shrines. It was never run.

Emma: "here's how you find the lists — they are linked as a part of the Engishiki
Jinmyōchō on Wikidata."
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_p361_shikinaisha_list_fix as g  # noqa: E402


def _fake_sparql(monkeypatch, real_lists):
    def fake(query):
        assert f"wdt:P361 wd:{g.ENGISHIKI_JINMYOCHO}" in query
        return [
            {"l": {"value": "http://www.wikidata.org/entity/" + q}}
            for q in real_lists
            if f"wd:{q} " in query + " " or f"wd:{q}}}" in query
        ]

    monkeypatch.setattr(g, "sparql", fake)


def test_only_engishiki_lists_survive(monkeypatch):
    targets = {
        "Q1": {"Q11658590", "Q700448"},   # a real list + Kamigamo Shrine
        "Q2": {"Q3200280"},               # Ninety-Nine Ōji Shrines: not a list
        "Q3": {"Q11642130"},              # a real list
    }
    _fake_sparql(monkeypatch, {"Q11658590", "Q11642130"})
    kept, lists, dropped = g.filter_shikinaisha_lists(targets)

    assert lists == ["Q11642130", "Q11658590"]
    assert set(dropped) == {"Q3200280", "Q700448"}
    assert kept["Q1"] == {"Q11658590"}     # Kamigamo dropped, list kept
    assert "Q2" not in kept                # nothing left in scope for it
    assert kept["Q3"] == {"Q11642130"}


def test_an_item_whose_every_target_is_out_of_scope_is_dropped(monkeypatch):
    """Q11398393 pointed only at the Ninety-Nine Ōji list; it must not be edited."""
    _fake_sparql(monkeypatch, set())
    kept, lists, dropped = g.filter_shikinaisha_lists({"Q11398393": {"Q3200280"}})
    assert kept == {}
    assert lists == []
    assert dropped == ["Q3200280"]


def test_the_known_offenders_are_not_lists(monkeypatch):
    """Real QIDs the first batch would have stripped statements from."""
    offenders = ["Q700448", "Q704702", "Q10898274", "Q215320", "Q3530344", "Q3200280"]
    _fake_sparql(monkeypatch, set())
    kept, lists, dropped = g.filter_shikinaisha_lists({"Q1": set(offenders)})
    assert kept == {}
    assert sorted(dropped) == sorted(offenders)
