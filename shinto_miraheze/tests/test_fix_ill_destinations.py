"""Unit tests for fix_ill_destinations pure logic (no network).

The resolvers (enwiki pageprops / sitelink) are network calls exercised in CI;
here we test the parsing, the fillable decision, the surgical qid write, and the
process_text orchestration with the resolver monkeypatched.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fix_ill_destinations as f  # noqa: E402


# ─── is_fillable ─────────────────────────────────────────────

def test_is_fillable_decisions():
    assert f.is_fillable(None) is True          # no qid param
    assert f.is_fillable("") is True            # empty qid=
    assert f.is_fillable("Unknown") is True     # placeholder
    assert f.is_fillable("Q123") is False       # already resolved
    assert f.is_fillable("DELETED_QID") is False  # item 5's territory


def test_current_qid_value_last_wins():
    _, named = f.parse_ill_body("Foo|en|Foo|WD=Q1|qid=Q2")
    assert f.current_qid_value(named) == "Q2"
    _, named2 = f.parse_ill_body("Foo|en|Foo")
    assert f.current_qid_value(named2) is None
    _, named3 = f.parse_ill_body("Foo|qid=Unknown")
    assert f.current_qid_value(named3) == "Unknown"


# ─── english_target / non_en_pairs ───────────────────────────

def test_english_target_prefers_explicit_en_pair():
    pos, _ = f.parse_ill_body("Romaji Name|en|English Article|ja|日本語")
    assert f.english_target(pos, "") == "English Article"


def test_english_target_falls_back_to_positional0():
    pos, _ = f.parse_ill_body("Some Shrine|ja|某神社")
    assert f.english_target(pos, "") == "Some Shrine"


def test_english_target_unknown_is_none():
    pos, _ = f.parse_ill_body("Unknown|ja|某")
    assert f.english_target(pos, "") is None


def test_non_en_pairs_excludes_en_and_unknown():
    pos, _ = f.parse_ill_body("Foo|en|Foo|ja|日本語|fr|Unknown|de|Deutsch")
    assert f.non_en_pairs(pos) == [("ja", "日本語"), ("de", "Deutsch")]


# ─── write_qid (surgical) ────────────────────────────────────

def test_write_qid_appends_when_absent():
    assert f.write_qid("Foo|ja|日本語", "Q42") == "Foo|ja|日本語|qid=Q42"


def test_write_qid_replaces_placeholder_in_place():
    assert f.write_qid("Foo|qid=Unknown|lt=x", "Q42") == "Foo|qid=Q42|lt=x"


def test_write_qid_replaces_legacy_WD():
    assert f.write_qid("Foo|WD=|ja|日本語", "Q42") == "Foo|qid=Q42|ja|日本語"


# ─── process_text orchestration (resolver monkeypatched) ─────

def test_process_text_fills_only_fillable(monkeypatch):
    # Resolver always returns Q999 for anything it's asked.
    monkeypatch.setattr(f, "resolve_destination", lambda pos, body: "Q999")
    text = (
        "Intro.\n"
        "{{ill|Already|en|Already|qid=Q1}}\n"   # resolved → untouched
        "{{ill|DeadOne|qid=DELETED_QID}}\n"     # deleted → untouched
        "{{ill|FillMe|ja|埋めて}}\n"             # fillable → +qid=Q999
        "{{ill|Place|qid=Unknown}}\n"           # placeholder → replaced
    )
    new, filled = f.process_text(text)
    assert filled == 2
    assert "{{ill|Already|en|Already|qid=Q1}}" in new
    assert "{{ill|DeadOne|qid=DELETED_QID}}" in new
    assert "{{ill|FillMe|ja|埋めて|qid=Q999}}" in new
    assert "{{ill|Place|qid=Q999}}" in new


def test_process_text_leaves_unresolvable(monkeypatch):
    monkeypatch.setattr(f, "resolve_destination", lambda pos, body: None)
    text = "{{ill|Mystery|ja|謎}}\n"
    new, filled = f.process_text(text)
    assert filled == 0
    assert new == text


def test_resolve_destination_rejects_disambiguation(monkeypatch):
    # enwiki resolves to a QID, but it's a disambiguation page → must NOT fill.
    monkeypatch.setattr(f, "resolve_enwiki", lambda t: "Q4167410dab")
    monkeypatch.setattr(f, "resolve_sitelink", lambda l, t: None)
    monkeypatch.setattr(f, "is_bad_target",
                        lambda q: q == "Q4167410dab")
    pos, _ = f.parse_ill_body("Mountain Shrine|ja|山神社")
    assert f.resolve_destination(pos, "") is None


def test_resolve_destination_uses_good_enwiki(monkeypatch):
    monkeypatch.setattr(f, "resolve_enwiki", lambda t: "Q42")
    monkeypatch.setattr(f, "is_bad_target", lambda q: False)
    pos, _ = f.parse_ill_body("Good Article|ja|良記事")
    assert f.resolve_destination(pos, "") == "Q42"


def test_resolve_destination_dab_sitelink_not_counted(monkeypatch):
    # One real QID + one dab QID across pairs: dab dropped, single-unique → fill.
    monkeypatch.setattr(f, "resolve_enwiki", lambda t: None)
    site = {("ja", "良"): "Q100", ("fr", "dab"): "Qdab"}
    monkeypatch.setattr(f, "resolve_sitelink", lambda l, t: site.get((l, t)))
    monkeypatch.setattr(f, "is_bad_target", lambda q: q == "Qdab")
    pos, _ = f.parse_ill_body("X|ja|良|fr|dab")
    assert f.resolve_destination(pos, "") == "Q100"
