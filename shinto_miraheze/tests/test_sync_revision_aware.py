"""Unit tests for sync_revision_aware.resolve_conflict.

These lock in the 2026-06-07 clobber fix: a shallow CI checkout made the per-file
`git log` blind, so `repo_latest_edit_epoch` returned None and the resolver fell
back to static_policy="repo", silently overwriting live human wiki edits. The
shallow backstop must prefer "wiki" on that uncertainty.

No wiki/git access — the timestamp readers and the shallow check are monkeypatched
so the decision logic is exercised in isolation.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sync_revision_aware as sra  # noqa: E402

REPO = Path(".")


def _patch(monkeypatch, wiki_t, repo_t, shallow):
    monkeypatch.setattr(sra, "wiki_latest_edit_epoch", lambda site, title: wiki_t)
    monkeypatch.setattr(sra, "repo_latest_edit_epoch", lambda root, rel: repo_t)
    monkeypatch.setattr(sra, "_repo_is_shallow", lambda root: shallow)


def _resolve(static_policy="repo"):
    return sra.resolve_conflict(
        site=None, title="X", baseline_revid=None, baseline_commit=None,
        repo_root=REPO, rel_file_path="git_synced/X.wiki", static_policy=static_policy,
    )


def test_wiki_newer_wins(monkeypatch):
    _patch(monkeypatch, wiki_t=200.0, repo_t=100.0, shallow=False)
    assert _resolve("repo") == "wiki"


def test_repo_newer_wins(monkeypatch):
    _patch(monkeypatch, wiki_t=100.0, repo_t=200.0, shallow=False)
    assert _resolve("wiki") == "repo"


def test_tie_falls_back_to_static_policy(monkeypatch):
    _patch(monkeypatch, wiki_t=100.0, repo_t=100.0, shallow=False)
    assert _resolve("repo") == "repo"
    assert _resolve("wiki") == "wiki"


def test_shallow_backstop_prefers_wiki_even_when_static_is_repo(monkeypatch):
    # The exact clobber scenario: shallow checkout → repo_t unreadable. Must NOT
    # fall back to repo-wins and overwrite the live wiki edit.
    _patch(monkeypatch, wiki_t=200.0, repo_t=None, shallow=True)
    assert _resolve("repo") == "wiki"


def test_repo_none_not_shallow_uses_static_policy(monkeypatch):
    # repo_t genuinely None but full clone (e.g. file never committed) → the
    # backstop must NOT trigger; honour the directory's static policy.
    _patch(monkeypatch, wiki_t=200.0, repo_t=None, shallow=False)
    assert _resolve("repo") == "repo"
    assert _resolve("wiki") == "wiki"


def test_wiki_none_uses_static_policy(monkeypatch):
    _patch(monkeypatch, wiki_t=None, repo_t=100.0, shallow=False)
    assert _resolve("repo") == "repo"


def test_invalid_static_policy_raises(monkeypatch):
    _patch(monkeypatch, wiki_t=100.0, repo_t=200.0, shallow=False)
    import pytest
    with pytest.raises(ValueError):
        _resolve("neither")
