"""A /doc subpage is documentation, not a second entity.

21 of the 177 groups on [[Duplicate page QIDs]] on 2026-08-26 were
``Template:X`` beside ``Template:X/doc``. The subpage carries its parent's
``{{wikidata link}}`` by design, so collecting it manufactured a duplicate for
every documented template.

The link is NOT stripped from the wiki. Read live that day, ``Template:Cite
NIE/doc`` carries ``en|Cite NIE/doc`` where its parent carries ``en|Cite NIE``
-- parameterised per page, therefore deliberate. Per this repo's own rule, a
weird thing here is signal until proven otherwise. The noise is ours to stop
collecting.
"""
import json
import os
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "shinto_miraheze")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from shinto_miraheze.orchestrators.ops import duplicate_qids as op  # noqa: E402

WDLINK = "{{wikidata link|Q9002097|en|Template:When}}"


def test_doc_subpages_are_not_tracked():
    assert op.is_tracked_title("Template:When") is True
    assert op.is_tracked_title("Template:When/doc") is False
    assert op.is_tracked_title("Module:Foo/doc") is False


def test_a_page_merely_containing_doc_is_still_tracked():
    """Only a trailing /doc is a documentation subpage."""
    assert op.is_tracked_title("Doctor Shrine") is True
    assert op.is_tracked_title("Template:Doc") is True
    assert op.is_tracked_title("Template:When/doc/old") is True


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    f = tmp_path / "duplicate_qids.state"
    monkeypatch.setattr(op, "_STATE_FILE", str(f))
    return f


def _read(f):
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def test_parent_template_is_still_recorded(state_file):
    op.apply("Template:When", WDLINK)
    assert _read(state_file) == {"Template:When": "Q9002097"}


def test_doc_subpage_is_never_recorded(state_file):
    op.apply("Template:When/doc", WDLINK)
    assert _read(state_file) == {}


def test_an_already_recorded_doc_subpage_is_popped(state_file):
    """The state self-cleans as the orchestrator revisits these pages."""
    state_file.write_text(
        json.dumps({"Template:When": "Q9002097", "Template:When/doc": "Q9002097"}),
        encoding="utf-8",
    )
    op.apply("Template:When/doc", WDLINK)
    assert _read(state_file) == {"Template:When": "Q9002097"}


def test_popping_is_skipped_when_there_is_nothing_to_pop(state_file):
    """No write, so no needless state churn for every doc page every sweep."""
    op.apply("Template:When/doc", WDLINK)
    assert not state_file.exists()


def test_the_op_never_asks_the_orchestrator_to_save(state_file):
    assert op.apply("Template:When", WDLINK) == (None, None)
    assert op.apply("Template:When/doc", WDLINK) == (None, None)
