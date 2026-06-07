"""
sync_revision_aware.py
=======================
Shared helpers for the ``sync_*.py`` scripts' revision-aware conflict
resolution. Imported by ``sync_git_synced_pages``, ``sync_miraheze_unique_pages``,
``sync_fandom_unique_pages``, ``sync_need_translation``,
``sync_duplicated_content``.

Conflict resolution is '''most-recent-edit-wins''': compare the timestamp of the
latest edit on each side (the wiki page's top revision vs the most recent git
commit touching the file) and let whichever was edited more recently win. The
static per-directory policy (``feedback_sync_conflict_policy.md``) remains only as
the tie-break / fallback when a timestamp can't be read.

'''Why timestamp, not revision count''' (Emma 2026-05-30): revision/commit COUNT
is arbitrary on both sides and must NOT be treated as authoritative — these unique
pages especially have near-empty wiki histories (intentionally truncated for
stability/error reasons) and were newly created in the repo, so "more revisions"
indicates nothing about which side holds the intended content. The side that was
'''edited most recently''' is the right winner. (A count-based version once
overwrote a genuine wiki edit on Kamitsukeno_no_Michiji because the losing side
merely had a higher rev count — the bug this fixes.)

Cost: one extra wiki API call per conflicting page (rare). The git log call is
local and cheap. The ``baseline_*`` params are accepted for caller compatibility
but no longer affect the decision (timestamps are absolute, not baseline-relative).
"""

import datetime
import subprocess
from pathlib import Path
from typing import Optional


# Lowercase case-collision template twins (wiki titles) that
# delete_lowercase_template_collisions.py is removing on-wiki. The
# unique-pages sync scripts (sync_miraheze_unique_pages.py,
# sync_fandom_unique_pages.py) MUST skip these titles entirely: otherwise,
# once the deleter removes the lowercase wiki page, the sync's orphan/PULL
# logic recreates it (the local twin still carries the gating category),
# and the deleter + sync ping-pong forever. Skipping also keeps the sync
# from decategorizing the wiki page, which preserves the deleter's
# "byte-identical to canonical twin" precondition. The matching local
# .wiki files were removed from the repo in the same change. See the
# deleter's TEMPLATE_PAIRS, docs/case_collision_report.md, and DEVLOG
# 2026-05-28. Includes the 10 base templates plus the 3 noble sub-variants
# (family / (Japan) / /doc) that also collide.
LOWERCASE_COLLISION_TITLES = {
    "Template:Infobox chinese",
    "Template:Infobox film",
    "Template:Infobox historic site",
    "Template:Infobox holiday",
    "Template:Infobox kofun",
    "Template:Infobox mountain",
    "Template:Infobox museum",
    "Template:Infobox noble",
    "Template:Infobox noble (Japan)",
    "Template:Infobox noble family",
    "Template:Infobox noble/doc",
    "Template:Infobox officeholder",
    "Template:Infobox organization",
}


def _iso_to_epoch(ts: Optional[str]) -> Optional[float]:
    """Parse a MediaWiki ISO-8601 UTC timestamp ('2026-05-30T17:23:10Z') to
    epoch seconds. Returns None on missing/unparseable input."""
    if not ts:
        return None
    try:
        return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc).timestamp()
    except (ValueError, TypeError):
        return None


def wiki_latest_edit_epoch(site, title: str) -> Optional[float]:
    """Epoch seconds of the most recent revision of ``title`` on the wiki, or
    ``None`` if it can't be read."""
    result = site.api(
        "query",
        prop="revisions",
        rvprop="timestamp",
        rvlimit=1,
        titles=title,
        formatversion="2",
    )
    pages = result.get("query", {}).get("pages", []) or []
    if not pages:
        return None
    revs = pages[0].get("revisions") or []
    if not revs:
        return None
    return _iso_to_epoch(revs[0].get("timestamp"))


def repo_latest_edit_epoch(repo_root: Path, rel_file_path: str) -> Optional[float]:
    """Epoch seconds of the most recent git commit touching ``rel_file_path``
    (committer date, UTC), or ``None`` if unavailable."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", rel_file_path],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        s = out.stdout.strip()
        return float(s) if s else None
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


def _repo_is_shallow(repo_root: Path) -> bool:
    """True if the git checkout is shallow. In a shallow clone, per-file
    ``git log`` can't see history that didn't touch HEAD, so
    ``repo_latest_edit_epoch`` returns None for most files and the conflict
    resolver would fall back to its static policy — clobbering live wiki edits
    on git_synced (static_policy='repo'). The resolver uses this to fail safe
    to wiki-wins instead. The real fix is ``fetch-depth: 0`` in CI; this is the
    backstop so a future shallow checkout can never silently clobber again."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=str(repo_root), check=True, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() == "true"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


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
    """Decide a conflict winner — '''most-recent-edit wins'''.

    Returns ``"wiki"`` (caller should PULL) or ``"repo"`` (caller should
    PUSH). Algorithm:

    * Read the latest-edit timestamp on each side (wiki top-revision time,
      most recent git commit touching the file).
    * Whichever side was edited strictly more recently wins.
    * If either timestamp can't be read, or they're equal, fall back to
      ``static_policy``.

    ``baseline_revid`` / ``baseline_commit`` are accepted for caller
    compatibility but unused: timestamps are absolute, not baseline-relative.
    Revision COUNT is deliberately NOT used — see the module docstring.
    """
    if static_policy not in ("wiki", "repo"):
        raise ValueError(f"static_policy must be 'wiki' or 'repo', got {static_policy!r}")

    wiki_t = wiki_latest_edit_epoch(site, title)
    repo_t = repo_latest_edit_epoch(repo_root, rel_file_path)

    # Shallow-clone backstop: if we couldn't read the repo's per-file time AND
    # the checkout is shallow, we can't trust the repo side at all — never
    # clobber a live wiki edit on that uncertainty. Prefer wiki.
    if repo_t is None and _repo_is_shallow(repo_root):
        return "wiki"
    if wiki_t is None or repo_t is None:
        return static_policy
    if wiki_t > repo_t:
        return "wiki"
    if repo_t > wiki_t:
        return "repo"
    return static_policy
