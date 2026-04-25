"""
_archive_repo.py
================
Thin helper for reading/writing the XML archive repo
(EmmaLeonhart/shintowiki-xml-archives).

Per-page XML exports are stored under xml/{namespace}/{first_char}/{slug}.xml.
The namespace folder (e.g. main, category, template, module) prevents
collisions between pages with the same short title in different namespaces
(e.g. mainspace "Foo" vs "Category:Foo"). The first-char shard under each
namespace keeps individual directories from exploding past a few thousand
files once the archive is fully populated.

Authentication (picked automatically):
  * In GitHub Actions (GITHUB_ACTIONS=true): SSH via the ARCHIVE_REPO_DEPLOY_KEY
    secret, loaded into ~/.ssh by the orchestrator workflow.
  * Locally: HTTPS with a token obtained from `gh auth token`.
"""

import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

ARCHIVE_OWNER = "EmmaLeonhart"
ARCHIVE_NAME = "shintowiki-xml-archives"
ARCHIVE_SLUG = f"{ARCHIVE_OWNER}/{ARCHIVE_NAME}"

# Populated on first clone, reused for the rest of a run.
_clone_dir: Path | None = None


def _clone_url() -> str:
    """SSH in GH Actions (deploy key), HTTPS+gh-token locally."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        return f"git@github.com:{ARCHIVE_SLUG}.git"
    try:
        token = subprocess.run(
            ["gh", "auth", "token"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        raise RuntimeError(
            "Cannot determine archive-repo credentials: `gh auth token` failed "
            "and GITHUB_ACTIONS is not set. Run `gh auth login` or set up SSH."
        ) from e
    return f"https://x-access-token:{token}@github.com/{ARCHIVE_SLUG}.git"


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    # Suppress interactive credential prompts. The token is already embedded in
    # the clone URL, but Git Credential Manager on Windows will still pop up an
    # account picker unless we tell it not to.
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GCM_INTERACTIVE", "Never")
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True, env=env)


def ensure_clone() -> Path:
    """Clone the archive repo once per run; return the local checkout path."""
    global _clone_dir
    if _clone_dir is not None and _clone_dir.exists():
        return _clone_dir
    root = Path(tempfile.mkdtemp(prefix="xml-archives-"))
    _run(["git", "clone", "--depth", "1", _clone_url(), str(root)])
    _run(["git", "config", "user.name", "github-actions[bot]"], cwd=root)
    _run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=root)
    _clone_dir = root
    return root


_SAFE_RE = re.compile(r"[^A-Za-z0-9_\-\.]")

# Maps a numeric namespace (from mwclient Page.namespace or <ns> in export
# XML) to a filesystem folder name. Unknown namespaces fall through to
# "ns_<number>" so nothing silently collides if MediaWiki adds new namespaces.
NS_FOLDER = {
    0: "main",
    1: "talk",
    2: "user",
    3: "user_talk",
    4: "project",
    5: "project_talk",
    6: "file",
    7: "file_talk",
    8: "mediawiki",
    9: "mediawiki_talk",
    10: "template",
    11: "template_talk",
    12: "help",
    13: "help_talk",
    14: "category",
    15: "category_talk",
    420: "geojson",
    421: "geojson_talk",
    828: "module",
    829: "module_talk",
    860: "item",
    861: "item_talk",
    862: "property",
    863: "property_talk",
}


def namespace_folder(ns: int) -> str:
    return NS_FOLDER.get(ns, f"ns_{ns}")


def safe_title(title: str) -> str:
    """Turn a wiki title into a filesystem-safe slug. Spaces → underscores."""
    t = title.replace(" ", "_")
    return _SAFE_RE.sub("_", t)


def _bare_title(title: str, ns: int) -> str:
    """For non-mainspace titles, strip the leading namespace prefix so the
    slug doesn't redundantly carry it (the folder already distinguishes)."""
    if ns == 0 or ":" not in title:
        return title
    return title.split(":", 1)[1]


def archive_relpath(title: str, ns: int) -> str:
    """Compute the archive path for a title in a given numeric namespace.

    `ns` is REQUIRED and has no default. A silent default of ns=0 was the
    original collision bug — every non-mainspace page ended up at a
    mainspace path because callers didn't pass the namespace. Enforce it
    at the signature so it can't happen again.
    """
    folder = namespace_folder(ns)
    slug = safe_title(_bare_title(title, ns))
    first = slug[0].lower() if slug else "_"
    if not first.isalnum():
        first = "_"
    return f"xml/{folder}/{first}/{slug}.xml"


def archive_exists(title: str, ns: int) -> bool:
    """True if an XML archive for this title+namespace is already committed."""
    root = ensure_clone()
    return (root / archive_relpath(title, ns)).is_file()


def _recover_repo_state(root: Path) -> None:
    """Bring the local clone back to a clean state on the current remote tip.

    A previous failed push or interrupted rebase can leave the working tree
    in a half-rebased state ("you are currently rebasing"), or stack
    unpushed local commits that conflict with concurrent pushes from other
    jobs. Without recovery, every subsequent ``write_and_commit`` call
    inherits the broken state and raises — and because ``_clone_dir`` is
    cached at module level, the failure persists for the whole orchestrator
    run, which is exactly what was silently disabling history_offload's
    delete+recreate stage. Best-effort: each command tolerates "nothing to
    do" exits.
    """
    _run(["git", "rebase", "--abort"], cwd=root, check=False)
    _run(["git", "merge", "--abort"], cwd=root, check=False)
    _run(["git", "reset", "--hard", "HEAD"], cwd=root, check=False)
    _run(["git", "fetch", "origin"], cwd=root, check=False)
    # Determine the default branch name the remote uses (HEAD symref) so we
    # don't hard-code "main"/"master" — fall back to "HEAD" if the symref
    # query fails.
    sym = _run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=root, check=False,
    )
    branch_ref = sym.stdout.strip() or "refs/remotes/origin/HEAD"
    _run(["git", "reset", "--hard", branch_ref], cwd=root, check=False)


def write_and_commit(title: str, xml_text: str, run_tag: str, ns: int) -> bool:
    """Write the XML, commit, and push. Returns True on a new commit, False if nothing changed.

    Push failures retry with state recovery between attempts so that one
    transient failure (concurrent push from another orchestrator job, brief
    network blip, etc.) doesn't poison every subsequent call for the rest
    of the run.
    """
    root = ensure_clone()
    rel = archive_relpath(title, ns)
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(xml_text, encoding="utf-8")

    _run(["git", "add", rel], cwd=root)
    status = _run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False)
    if status.returncode == 0:
        return False  # no change

    message = f"archive: {title} {run_tag}"
    _run(["git", "commit", "-m", message], cwd=root)

    # Best-effort rebase + push, with retry. Each retry recovers repo state
    # first so a half-rebased tree from the prior attempt doesn't turn a
    # transient failure into a permanent one.
    last_error: Exception | None = None
    for attempt in range(1, 4):
        pull = _run(["git", "pull", "--rebase", "origin", "HEAD"], cwd=root, check=False)
        if pull.returncode != 0:
            print(f"  archive_repo: pull --rebase failed (attempt {attempt}): {pull.stderr.strip()[:200]}")
            _recover_repo_state(root)
            # State has been reset; the local commit is gone. Re-stage the
            # file and re-commit so we still have something to push.
            target.write_text(xml_text, encoding="utf-8")
            _run(["git", "add", rel], cwd=root)
            re_status = _run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False)
            if re_status.returncode == 0:
                # Already on remote — somebody else archived this title.
                return False
            _run(["git", "commit", "-m", message], cwd=root)
        push = _run(["git", "push", "origin", "HEAD"], cwd=root, check=False)
        if push.returncode == 0:
            return True
        last_error = RuntimeError(
            f"git push failed (attempt {attempt}): {push.stderr.strip()[:200]}"
        )
        print(f"  archive_repo: {last_error}")
        time.sleep(2)
        _recover_repo_state(root)
        target.write_text(xml_text, encoding="utf-8")
        _run(["git", "add", rel], cwd=root)
        re_status = _run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False)
        if re_status.returncode == 0:
            return False
        _run(["git", "commit", "-m", message], cwd=root)
    # Give up — but leave the clone in a clean state so the NEXT page's
    # call doesn't inherit a poisoned working tree.
    _recover_repo_state(root)
    raise last_error or RuntimeError("git push failed after retries")
