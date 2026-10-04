"""The wiki-link fallback tops up the staged file from the title map and never removes."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import wiki_link_state_fallback as fb  # noqa: E402

LINE_RE = re.compile(r'^(Q\d+)\|P6262\|"shinto:(?!(?:Category|Template):).+"$')


def _state(tmp_path):
    p = tmp_path / "duplicate_qids.state"
    p.write_text(json.dumps({
        "Ise Grand Shrine": "Q1",
        "Category:Shrines": "Q2",
        "Template:Infobox": "Q3",
        "Izumo-taisha": "Q4",
        "Kasuga-taisha": "Q5",
    }), encoding="utf-8")
    return str(p)


def test_lines_from_state_refuses_category_and_template(tmp_path):
    lines = fb.lines_from_state("P6262", LINE_RE, _state(tmp_path))
    assert lines == ['Q1|P6262|"shinto:Ise Grand Shrine"',
                     'Q4|P6262|"shinto:Izumo-taisha"',
                     'Q5|P6262|"shinto:Kasuga-taisha"']


def test_merge_keeps_existing_lines_and_adds_only_new_qids(tmp_path):
    out = tmp_path / "p6262_fandom_links.txt"
    out.write_text('Q1|P6262|"shinto:Ise Grand Shrine"\nQ9|Len|"something else"\n',
                   encoding="utf-8")
    added = fb.merge_into(str(out), ['Q1|P6262|"shinto:Ise Grand Shrine"',
                                     'Q4|P6262|"shinto:Izumo-taisha"'], LINE_RE)
    assert added == 1
    assert out.read_text(encoding="utf-8").splitlines() == [
        'Q1|P6262|"shinto:Ise Grand Shrine"',
        'Q9|Len|"something else"',
        'Q4|P6262|"shinto:Izumo-taisha"',
    ]


def test_fallback_filters_existing_and_redirects(tmp_path, monkeypatch):
    monkeypatch.setattr(fb, "STATE", _state(tmp_path))
    monkeypatch.setattr(fb.lines_from_state, "__defaults__", (fb.STATE,))
    out = tmp_path / "out.txt"
    fb.state_fallback("P6262", LINE_RE, str(out), existing_qids={"Q1"},
                      fetch_redirect_qids=lambda qids: {"Q5"} & qids)
    assert out.read_text(encoding="utf-8").splitlines() == ['Q4|P6262|"shinto:Izumo-taisha"']


def test_fallback_keeps_file_when_sparql_failed(tmp_path):
    out = tmp_path / "out.txt"
    out.write_text('Q1|P6262|"shinto:Ise Grand Shrine"\n', encoding="utf-8")
    fb.state_fallback("P6262", LINE_RE, str(out), existing_qids=None,
                      fetch_redirect_qids=lambda q: set())
    assert out.read_text(encoding="utf-8") == 'Q1|P6262|"shinto:Ise Grand Shrine"\n'


def test_a_title_with_a_quote_is_never_emitted(tmp_path):
    p = tmp_path / "s.state"
    p.write_text(json.dumps({'List of Kofun in Japan with the Name "Hyo"': "Q1"}), encoding="utf-8")
    assert fb.lines_from_state("P6262", LINE_RE, str(p)) == []


def test_no_staged_link_line_is_oversized():
    for name in ("p6262_fandom_links.txt", "p11250_miraheze_links.txt"):
        path = os.path.join(os.path.dirname(HERE), name)
        with open(path, encoding="utf-8") as f:
            for line in f:
                assert len(line) < 2000, "%s: %s..." % (name, line[:80])
