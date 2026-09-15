"""A suppressed page does not gate — and the suppression expires by itself.

Emma, 2026-09-15: *"uhh stop that mention gate thing for 30 days on the AI noticeboard,
it is a mostly unrelated item and we need to get our items through. Another user who
once copied something from me"*.

So the gate keeps watching both pages and keeps recording both counts; one named page
simply stops holding it shut, until a date that lives in
`shinto_miraheze/enwiki_mention_suppressions.state` and nowhere else. The three things
worth pinning are the three ways this could quietly go wrong:

  * the suppression is not read at all, and the gate stays shut;
  * the suppression outlives its date, because nothing checks it;
  * the suppression file is unreadable and is treated as "suppress everything".
"""
import datetime
import importlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

cem = importlib.import_module("shinto_miraheze.check_enwiki_mentions")

NOTICEBOARD, WIKIPROJECT = cem.PAGES


def _counts(monkeypatch, mapping):
    def fake(title):
        v = mapping[title]
        return (None, v) if isinstance(v, str) else (v, None)
    monkeypatch.setattr(cem, "count_mentions", fake)


def _suppress(monkeypatch, tmp_path, entries):
    path = tmp_path / "suppressions.state"
    path.write_text(json.dumps({"suppressions": entries}), encoding="utf-8")
    monkeypatch.setattr(cem, "SUPPRESSIONS", path)
    return path


def test_a_mention_on_the_suppressed_page_no_longer_closes_the_gate(
        monkeypatch, tmp_path):
    _suppress(monkeypatch, tmp_path,
              [{"page": NOTICEBOARD, "until": "2999-01-01"}])
    _counts(monkeypatch, {NOTICEBOARD: 1, WIKIPROJECT: 0})
    clear, per_page, failed, suppressed = cem.evaluate()
    assert clear is True and not failed
    # Still read, still reported — suppressed, not unwatched.
    assert per_page[NOTICEBOARD] == 1
    assert NOTICEBOARD in suppressed


def test_the_other_page_still_gates(monkeypatch, tmp_path):
    _suppress(monkeypatch, tmp_path,
              [{"page": NOTICEBOARD, "until": "2999-01-01"}])
    _counts(monkeypatch, {NOTICEBOARD: 1, WIKIPROJECT: 1})
    assert cem.evaluate()[0] is False


def test_an_unreadable_suppressed_page_does_not_reinstate_the_block(
        monkeypatch, tmp_path):
    """Otherwise an enwiki outage restores exactly the block being lifted."""
    _suppress(monkeypatch, tmp_path,
              [{"page": NOTICEBOARD, "until": "2999-01-01"}])
    _counts(monkeypatch, {NOTICEBOARD: "URLError: timed out", WIKIPROJECT: 0})
    clear, _, failed, _ = cem.evaluate()
    assert clear is True and failed is False


def test_an_unreadable_UNsuppressed_page_still_fails_closed(monkeypatch, tmp_path):
    _suppress(monkeypatch, tmp_path,
              [{"page": NOTICEBOARD, "until": "2999-01-01"}])
    _counts(monkeypatch, {NOTICEBOARD: 0, WIKIPROJECT: "URLError: timed out"})
    clear, _, failed, _ = cem.evaluate()
    assert failed is True and clear is False


def test_the_suppression_expires_on_its_date(monkeypatch, tmp_path):
    _suppress(monkeypatch, tmp_path,
              [{"page": NOTICEBOARD, "until": "2026-10-15"}])
    _counts(monkeypatch, {NOTICEBOARD: 1, WIKIPROJECT: 0})
    # Day before: suppressed. On the day and after: back to normal, same as
    # wikidata_edit_allowed.py's `today >= until`.
    assert cem.evaluate(datetime.date(2026, 10, 14))[0] is True
    assert cem.evaluate(datetime.date(2026, 10, 15))[0] is False
    assert cem.evaluate(datetime.date(2027, 1, 1))[0] is False


def test_an_unreadable_suppression_file_suppresses_nothing(monkeypatch, tmp_path):
    path = tmp_path / "suppressions.state"
    path.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setattr(cem, "SUPPRESSIONS", path)
    _counts(monkeypatch, {NOTICEBOARD: 1, WIKIPROJECT: 0})
    assert cem.evaluate()[0] is False


def test_a_missing_suppression_file_suppresses_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(cem, "SUPPRESSIONS", tmp_path / "absent.state")
    _counts(monkeypatch, {NOTICEBOARD: 1, WIKIPROJECT: 0})
    assert cem.evaluate()[0] is False


def test_the_live_file_names_a_real_page_and_a_parseable_date():
    """A typo'd page title would suppress nothing and look like it worked."""
    live = json.loads(cem.SUPPRESSIONS.read_text(encoding="utf-8"))
    for entry in live["suppressions"]:
        assert entry["page"] in cem.PAGES, entry["page"]
        datetime.date.fromisoformat(entry["until"])
        assert entry.get("reason"), "a suppression without a reason is a mystery later"
