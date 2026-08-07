"""The enwiki-mention gate must fail CLOSED.

Emma 2026-08-06: no Wikidata editing while "Immanuelle" is named on
[[Wikipedia:AI noticeboard]] or [[Wikipedia talk:WikiProject Japan]]. The gate is
evaluated live in cleanup-loop.yml's window-gate, which reads only this script's exit
code — so every way the check can go wrong has to end in "still blocked". An
unreadable page in particular is not evidence of absence.
"""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

cem = importlib.import_module("shinto_miraheze.check_enwiki_mentions")


def _counts(monkeypatch, mapping):
    def fake(title):
        v = mapping[title]
        return (None, v) if isinstance(v, str) else (v, None)
    monkeypatch.setattr(cem, "count_mentions", fake)


def test_clear_only_when_both_pages_are_at_zero(monkeypatch):
    _counts(monkeypatch, {p: 0 for p in cem.PAGES})
    clear, _, failed = cem.evaluate()
    assert clear and not failed


def test_any_mention_closes_the_gate(monkeypatch):
    first, second = cem.PAGES
    _counts(monkeypatch, {first: 0, second: 1})
    assert cem.evaluate()[0] is False

    _counts(monkeypatch, {first: 7, second: 2})
    assert cem.evaluate()[0] is False


def test_a_failed_read_is_not_absence(monkeypatch):
    first, second = cem.PAGES
    # Zero mentions on the page we could read, and the other unreachable.
    _counts(monkeypatch, {first: 0, second: "URLError: timed out"})
    clear, _, failed = cem.evaluate()
    assert failed
    assert clear is False


def test_both_watched_pages_are_still_the_ones_emma_named():
    assert cem.PAGES == ["Wikipedia:AI noticeboard",
                         "Wikipedia talk:WikiProject Japan"]
    assert cem.NEEDLE == "Immanuelle"

# main()'s exit code is `0 if clear else 1` over evaluate() — that one line is what
# the window-gate reads. It is not exercised here because main() rebinds sys.stdout
# to a UTF-8 wrapper (repo-wide convention) and pytest's capture cannot survive it.
