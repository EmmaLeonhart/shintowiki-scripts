"""Guard the page-title <-> filename mapping used by every wiki<->repo sync.

REWRITTEN 2026-09-01. This test used to extract ``_FORBIDDEN`` /
``title_to_filename`` / ``filename_to_title`` from three sync scripts with a
regex and exec them in an isolated namespace, because the scripts install a
``sys.stdout`` wrapper at module load that breaks pytest capture, and because
the definitions were copy-pasted into nine files that could silently diverge.

Both reasons are gone: the definitions now live once in
``shinto_miraheze/title_filename.py``, which has no import side effects. What
this file guards now is that **no copy has come back** -- a re-pasted definition
is exactly the drift the old test existed to catch, and it would not be caught
by importing the module.

Behavioural tests for the mapping itself live in ``test_title_filename.py``.
"""

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Every script that maps titles to filenames. All nine were migrated to import
# from the shared module on 2026-09-01.
CONSUMERS = [
    "shinto_miraheze/sync_git_synced_pages.py",
    "shinto_miraheze/sync_fandom_unique_pages.py",
    "shinto_miraheze/sync_miraheze_unique_pages.py",
    "shinto_miraheze/sync_need_translation.py",
    "shinto_miraheze/sync_duplicated_content.py",
    "fandom/fandom_subset_orchestrator.py",
    "recreate-deleted-wikidata/match_new_qids.py",
    "recreate-deleted-wikidata/pull_ill_pages_to_git_synced.py",
    "recreate-deleted-wikidata/relink_duplicate_ills.py",
    # A TENTH copy, found by this test on 2026-09-01: it had no _FORBIDDEN, so the
    # grep that found the other nine missed it, and it escaped only ":" and "/" --
    # not "%", so a title with a literal percent read back wrong.
    "shinto_miraheze/git_sync_strip_property_dumps.py",
]

_DEF_RE = re.compile(r"^def (title_to_filename|filename_to_title)\(", re.M)
_FORBIDDEN_RE = re.compile(r"^_FORBIDDEN\s*=", re.M)


def _read(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def test_no_consumer_redefines_the_mapping():
    """A re-pasted copy is the drift this file exists to catch."""
    offenders = []
    for rel in CONSUMERS:
        src = _read(rel)
        for m in _DEF_RE.finditer(src):
            offenders.append(f"{rel}: redefines {m.group(1)}()")
        if _FORBIDDEN_RE.search(src):
            offenders.append(f"{rel}: redefines _FORBIDDEN")
    assert not offenders, (
        "These files define the title<->filename mapping locally instead of "
        "importing it from shinto_miraheze.title_filename:\n  "
        + "\n  ".join(offenders)
    )


def test_every_consumer_imports_from_the_shared_module():
    missing = [
        rel for rel in CONSUMERS
        if "from shinto_miraheze.title_filename import" not in _read(rel)
    ]
    assert not missing, f"not importing the shared mapping: {missing}"


def test_the_shared_module_is_the_only_definition():
    """Exactly one file in the repo may define the mapping."""
    definers = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", "_site"}]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
            if rel.startswith("shinto_miraheze/tests/"):
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    src = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
            if _DEF_RE.search(src):
                definers.append(rel)
    assert definers == ["shinto_miraheze/title_filename.py"], definers


def test_the_retired_collision_skip_has_not_come_back():
    """LOWERCASE_COLLISION_TITLES skipped 13 real pages so an on-wiki deleter
    could remove them. Emma retired that plan 2026-08-31 ("supposed to
    diverge"); the twins coexist via case-escaped filenames now. A reappearing
    skip list would silently stop mirroring those pages again."""
    offenders = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", "_site"}]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
            if rel in ("shinto_miraheze/sync_revision_aware.py",
                       "shinto_miraheze/tests/test_title_filename_roundtrip.py"):
                continue  # both only mention it in a comment/docstring
            try:
                with open(path, encoding="utf-8") as fh:
                    if "LOWERCASE_COLLISION_TITLES" in fh.read():
                        offenders.append(rel)
            except (OSError, UnicodeDecodeError):
                continue
    assert not offenders, f"the retired collision skip is back in: {offenders}"
