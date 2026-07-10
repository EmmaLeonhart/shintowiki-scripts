"""Tests for generate_saijin_deity_research pure logic (no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_saijin_deity_research import (  # noqa: E402
    link_targets, link_pairs, plain_names, qs_line, build_lines, principal_refs,
    PRINCIPAL_DEITY_ROLE,
)


def test_link_pairs_captures_display_name():
    v = "[[天照大神|天照皇大御神]]、[[素戔嗚尊]]"
    assert link_pairs(v) == [("天照大神", "天照皇大御神"), ("素戔嗚尊", "素戔嗚尊")]


def test_principal_refs_label_form():
    # 主祭神：X、Y  → X, Y principal (up to the 配神 label)
    v = "主祭神：[[天照大神]]、[[豊受大神]]<br>配神：[[素戔嗚尊]]"
    links, plain = principal_refs(v)
    assert links == {"天照大神", "豊受大神"}


def test_principal_refs_annotation_form():
    # X（主祭神）  → the deity RIGHT BEFORE the marker is principal (the 高麗神社 bug)
    v = "[[高麗王若光]]（主祭神）<br>[[サルタヒコ|猿田彦命]]、[[武内宿禰]]"
    links, plain = principal_refs(v)
    assert links == {"高麗王若光"}


def test_principal_refs_absent():
    assert principal_refs("[[天照大神]]、[[素戔嗚尊]]") == (set(), set())


def test_link_targets_piped_and_plain():
    v = "[[天照大神|天照大御神]]、[[素戔嗚尊]]、[[大国主|大国主命]]"
    assert link_targets(v) == ["天照大神", "素戔嗚尊", "大国主"]


def test_link_targets_excludes_file_category():
    v = "[[File:x.jpg|thumb]]、[[天照大神]]、[[Category:y]]"
    assert link_targets(v) == ["天照大神"]


def test_plain_names_splits_and_strips_readings():
    v = "天照大神（あまてらす）、素戔嗚尊 ・ 大国主命"
    assert plain_names(v) == ["天照大神", "素戔嗚尊", "大国主命"]


def test_plain_names_ignores_wikilinked():
    # linked names are handled via pageprops, not the plain path
    v = "[[天照大神]]、素戔嗚尊"
    assert plain_names(v) == ["素戔嗚尊"]


def test_plain_names_drops_annotation_tokens():
    v = "天照大神、配神 素戔嗚尊、など"
    # "配神 素戔嗚尊" contains an annotation word -> whole token dropped
    assert plain_names(v) == ["天照大神"]


def test_plain_names_drops_latin_and_short():
    assert plain_names("ABC、一") == []


def test_qs_line_general_vs_principal():
    url = "https://ja.wikipedia.org/wiki/X"
    assert qs_line("Q1", "Q2", False, "天照大御神", url) == \
        f'Q1|P825|Q2|P1932|"天照大御神"|S4656|"{url}"'
    assert qs_line("Q1", "Q2", True, "天照皇大御神", url) == \
        f'Q1|P825|Q2|P3831|{PRINCIPAL_DEITY_ROLE}|P1932|"天照皇大御神"|S4656|"{url}"'


def _ref(principal, named):
    return {"principal": principal, "named": named}


def test_build_lines_dedupes_and_principal_wins():
    # same deity reached by a link (general) and a plain name (principal) -> one
    # principal-qualified line, principal spelling wins as P1932
    shrine_deities = {("神社A", "Q10"): {"天照大神": _ref(False, "天照大神"),
                                          "天照大御神": _ref(True, "天照大御神")}}
    resolved = {"天照大神": "Q2"}
    matched = {"天照大御神": "Q2"}
    lines = build_lines(shrine_deities, resolved, matched, have=set(), have_principal=set())
    assert len(lines) == 1
    assert f'|P825|Q2|P3831|{PRINCIPAL_DEITY_ROLE}|P1932|"天照大御神"|S4656|' in lines[0]


def test_build_lines_skips_existing_general_but_adds_principal_qualifier():
    shrine_deities = {("A", "Q10"): {"d1": _ref(False, "n1"), "d2": _ref(True, "n2")}}
    resolved = {"d1": "Q2", "d2": "Q3"}
    # Q2 general pair already present -> skipped; Q3 principal not yet qualified -> emitted
    lines = build_lines(shrine_deities, resolved, {},
                        have={("Q10", "Q2"), ("Q10", "Q3")},
                        have_principal=set())
    assert len(lines) == 1
    assert "|P825|Q3|P3831|" in lines[0]


def test_build_lines_skips_already_principal_qualified():
    shrine_deities = {("A", "Q10"): {"d2": _ref(True, "n2")}}
    resolved = {"d2": "Q3"}
    lines = build_lines(shrine_deities, resolved, {},
                        have={("Q10", "Q3")}, have_principal={("Q10", "Q3")})
    assert lines == []
