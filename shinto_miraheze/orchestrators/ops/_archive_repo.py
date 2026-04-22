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


def write_and_commit(title: str, xml_text: str, run_tag: str, ns: int) -> bool:
    """Write the XML, commit, and push. Returns True on a new commit, False if nothing changed."""
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
    # Best-effort rebase to absorb concurrent pushes, then push.
    _run(["git", "pull", "--rebase", "origin", "HEAD"], cwd=root, check=False)
    _run(["git", "push", "origin", "HEAD"], cwd=root)
    return True
