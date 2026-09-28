"""Deity work (Emma 2026-09-28): deified people get P3831 = the 'deified person' item;
red-link deity names become create batches; create_items can key a batch on its ja label."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("WIKIDATA_EMAIL", "test@example.org")
os.environ.setdefault("MIRAHEZE_EMAIL", "test@example.org")

import create_items as ci  # noqa: E402
import generate_deity_creates as gdc  # noqa: E402
import generate_saijin_deity_research as g  # noqa: E402


def test_a_deified_person_line_carries_the_role():
    ln = g.qs_line("Q1", "Q317997", False, "応神天皇", "https://ja.wikipedia.org/wiki/X", "Q999")
    assert "|P825|Q317997|P3831|Q999|" in ln


def test_principal_and_deified_roles_both_appear():
    ln = g.qs_line("Q1", "Q2", True, "", "u", "Q999")
    assert f"|P3831|{g.PRINCIPAL_DEITY_ROLE}|P3831|Q999" in ln


def test_ordinary_deities_get_no_person_role():
    sd = {("A神社", "Q1"): {"天照大神": {"principal": False, "named": "天照大神"},
                          "応神天皇": {"principal": False, "named": "応神天皇"}}}
    lines, _ = g.build_lines(sd, {}, {"天照大神": "Q30", "応神天皇": "Q317997"}, set(), set(),
                             deified={"Q317997"}, deified_role="Q999")
    assert any("|Q317997|P3831|Q999" in l for l in lines)
    assert not any("|Q30|P3831|Q999" in l for l in lines)


def test_the_role_qid_comes_from_create_items_state(tmp_path):
    p = tmp_path / "deity_role_creates.state"
    assert g.deified_role_qid(str(p)) is None                  # not created yet: held back
    p.write_text(json.dumps({"deified person": "Q123"}), encoding="utf-8")
    assert g.deified_role_qid(str(p)) == "Q123"


def test_red_link_names_that_already_have_an_item_are_skipped():
    blocks = gdc.deity_blocks(["十城別王", "既存神", 'bad"name'], existing={"既存神"})
    assert blocks == ["CREATE", 'LAST|Lja|"十城別王"', f"LAST|P31|{gdc.KAMI}"]


def test_create_items_keys_a_ja_only_block_on_its_ja_label():
    assert ci.block_label_lang(['LAST|Lja|"十城別王"', "LAST|P31|Q524158"]) == ("ja", "十城別王")
    assert ci.block_label_lang(['LAST|Len|"Kamo Shrine"', 'LAST|Lja|"加茂神社"']) == ("en", "Kamo Shrine")


def test_both_deity_batches_are_gated():
    assert ci.GATES["deity_creates.txt"] == "lockout_gate"
    assert ci.GATES["deity_role_creates.txt"] == "lockout_gate"


def test_a_batch_not_generated_yet_is_a_clean_skip(monkeypatch, capsys):
    monkeypatch.setattr(ci, "wikidata_editing_allowed", lambda *a, **k: (True, "open"))
    monkeypatch.setattr(sys, "argv", ["create_items.py", "--batch", "no_such_batch_yet.txt"])
    assert ci.main() == 0
    assert "not generated yet" in capsys.readouterr().out


def test_a_blocked_runner_stops_at_the_first_failed_create(monkeypatch, tmp_path, capsys):
    """2026-09-28: every create on a globally blocked runner fails with permissiondenied;
    stop at the first and report blocked=true so create-items.yml retries on a fresh runner."""
    batch = tmp_path / "t_batch.txt"
    batch.write_text('CREATE\nLAST|Lja|"甲神"\nCREATE\nLAST|Lja|"乙神"\n', encoding="utf-8")
    monkeypatch.setattr(ci, "_here", str(tmp_path))
    monkeypatch.setitem(ci.GATES, "t_batch.txt", "lockout_gate")
    monkeypatch.setattr(ci, "wikidata_editing_allowed", lambda *a, **k: (True, "open"))

    class _R:
        def __init__(self, d): self._d = d
        def json(self): return self._d

    class _S:
        headers = {}
        calls = 0
        def post(self, *a, **k):
            _S.calls += 1
            return _R({"error": {"code": "permissiondenied",
                                 "info": "You do not have the permissions needed to carry out this action."}})

    monkeypatch.setattr(ci, "wd_login", lambda: (_S(), "csrf"))
    out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setattr(sys, "argv", ["create_items.py", "--batch", "t_batch.txt", "--apply"])
    assert ci.main() == 3
    assert _S.calls == 1
    assert "blocked=true" in out.read_text(encoding="utf-8")


def test_namespace_links_are_never_deity_names():
    assert not g._is_deity_link("Image:Okami_10.5pt.png")
    assert not g._is_deity_link("画像:Foo.jpg")
    assert gdc.deity_blocks(["Image:Okami_10.5pt.png", "十城別王"], existing=set()) == [
        "CREATE", 'LAST|Lja|"十城別王"', f"LAST|P31|{gdc.KAMI}"]
