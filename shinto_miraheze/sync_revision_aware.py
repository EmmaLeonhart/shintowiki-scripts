"""
sync_revision_aware.py
=======================
Shared helpers for the ``sync_*.py`` scripts' revision-aware conflict
resolution. Imported by ``sync_git_synced_pages``, ``sync_miraheze_unique_pages``,
``sync_fandom_unique_pages``, ``sync_need_translation``,
``sync_duplicated_content``.

Replaces the previous static per-directory policy (``feedback_sync_conflict
_policy.md``: wiki-wins for duplicated_content+need_translation, repo-wins for
git_synced+fandom_unique+miraheze_unique) with: count revisions on each side
since the last sync baseline; whichever side has more wins. The static policy
remains as the tie-break fallback per script, and is also the fallback whenever
the per-page baseline doesn't yet have a ``sync_commit`` recorded (for
backward-compat with existing ``sync_*.state`` files written before this
change).

Cost: one extra wiki API call per conflicting page (rare). The git rev-list
call is local and cheap.
"""

import subprocess
from pathlib import Path
from typing import Optional


def count_wiki_revs_since(site, title: str, baseline_revid: Optional[int]) -> Optional[int]:
    """Count wiki revisions of ``title`` more recent than ``baseline_revid``.

    Returns the integer count, or ``None`` if ``baseline_revid`` is falsy
    (no baseline → caller should fall back to static policy). Excludes the
    baseline revision itself from the count. Capped via ``rvlimit=500`` —
    if a page genuinely has more than 500 revisions since baseline, the
    cap is fine for the comparison (it just means "definitely a lot").
    """
    if not baseline_revid:
        return None
    result = site.api(
        "query",
        prop="revisions",
        rvprop="ids",
        rvstartid="now",
        rvendid=str(baseline_revid),
        rvlimit=500,
        titles=title,
        formatversion="2",
    )
    pages = result.get("query", {}).get("pages", []) or []
    if not pages:
        return 0
    revs = pages[0].get("revisions") or []
    # rvendid is inclusive — drop the baseline rev itself if present.
    return sum(1 for r in revs if r.get("revid") != baseline_revid)


def count_repo_commits_since(
    repo_root: Path,
    rel_file_path: str,
    baseline_commit: Optional[str],
) -> Optional[int]:
    """Count git commits on ``HEAD`` touching ``rel_file_path`` (relative to
    ``repo_root``) since ``baseline_commit``.

    Returns the integer count, or ``None`` if ``baseline_commit`` is falsy
    (no baseline → caller should fall back to static policy). Returns
    ``None`` (also fallback) if the baseline commit isn't reachable from
    HEAD (history rewrite, missing ref) — caller can't trust the count
    in that case.
    """
    if not baseline_commit:
        return None
    try:
        out = subprocess.run(
            [
                "git", "rev-list", "--count",
                f"{baseline_commit}..HEAD",
                "--", rel_file_path,
            ],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return int(out.stdout.strip() or "0")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return None


def head_commit(repo_root: Path) -> Optional[str]:
    """Current HEAD commit SHA of the repo, or ``None`` if unavailable.

    Used by sync scripts to stamp ``sync_commit`` on each state entry they
    write — that's the baseline the NEXT sync will count repo commits
    against.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def resolve_conflict(
    *,
    site,
    title: str,
    baseline_revid: Optional[int],
    baseline_commit: Optional[str],
    repo_root: Path,
    rel_file_path: str,
    static_policy: str,  # "wiki" or "repo" — the fallback
) -> str:
    """Decide a conflict winner.

    Returns ``"wiki"`` (caller should PULL) or ``"repo"`` (caller should
    PUSH). Algorithm:

    * If either count is unknown (no baseline of that type, or git ref
      lookup failed), fall back to ``static_policy`` immediately. The
      next sync will have a usable baseline on both sides and the
      revision count can take over.
    * Otherwise compare counts; whichever side has strictly more revs
      since baseline wins.
    * On tie (including 0–0, which happens if the page was simultaneously
      reverted on both sides between baselines): fall back to
      ``static_policy``.
    """
    if static_policy not in ("wiki", "repo"):
        raise ValueError(f"static_policy must be 'wiki' or 'repo', got {static_policy!r}")

    wiki_n = count_wiki_revs_since(site, title, baseline_revid)
    repo_n = count_repo_commits_since(repo_root, rel_file_path, baseline_commit)

    if wiki_n is None or repo_n is None:
        return static_policy
    if wiki_n > repo_n:
        return "wiki"
    if repo_n > wiki_n:
        return "repo"
    return static_policy
