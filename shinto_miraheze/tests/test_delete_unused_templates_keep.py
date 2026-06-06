"""Unit test for the never-delete keep-list in delete_unused_templates.

Guards the root-cause fix for the undelete_gaiad_date kludge: Template:GaiadDate
keeps appearing in Special:UnusedTemplates (it has zero transclusions) and was
being deleted every cycle. The deletion loop must skip protected titles while
still deleting ordinary unused templates.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import delete_unused_templates as d  # noqa: E402


class _FakePage:
    def __init__(self, exists=True):
        self.exists = exists
        self.deleted = False

    def delete(self, reason=""):
        self.deleted = True


class _FakeSite:
    def __init__(self, pages):
        self.pages = pages


def test_is_protected():
    assert d.is_protected("Template:GaiadDate")
    assert not d.is_protected("Template:SomethingElse")


def test_gaiaddate_in_keep_titles():
    assert "Template:GaiadDate" in d.KEEP_TITLES


def test_main_skips_protected_but_deletes_ordinary(monkeypatch):
    pages = {
        "Template:GaiadDate": _FakePage(exists=True),
        "Template:UnusedOrdinary": _FakePage(exists=True),
    }
    site = _FakeSite(pages)

    monkeypatch.setattr(d, "_ensure_utf8_stdout", lambda: None)  # keep pytest capture intact
    monkeypatch.setattr(d.mwclient, "Site", lambda *a, **k: site)
    monkeypatch.setattr(d, "login_with_retry", lambda *a, **k: None)
    monkeypatch.setattr(
        d, "iter_unused_templates",
        lambda s: iter(["Template:GaiadDate", "Template:UnusedOrdinary"]),
    )
    monkeypatch.setattr(d.time, "sleep", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["prog", "--run-tag", "[[test]]"])

    d.main()

    assert pages["Template:GaiadDate"].deleted is False   # protected → skipped
    assert pages["Template:UnusedOrdinary"].deleted is True  # ordinary → deleted
