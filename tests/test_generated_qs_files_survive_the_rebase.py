"""A generated `.txt` must survive `generate-quickstatements.yml`'s rebase dance.

The commit step in that workflow backs up this run's own output, resets and
`git clean -fd`s the tree, rebases onto origin, restores the backup, and commits.
Anything missing from the backup list is therefore reverted to HEAD — silently,
in a run that reports success.

That list was built from two git commands until 2026-09-13, and the pair got it
wrong twice. Both are recorded because the second one arrived while the first was
still being called the cause.

**1. The path formats disagreed** (found 2026-09-12). Run from inside a
subdirectory::

    git diff --name-only -- .                 -> modern-quickstatements/foo.txt
    git ls-files --others --exclude-standard  -> foo.txt          (CWD-relative)

and `sed -n 's|^modern-quickstatements/||p'` prints only lines whose substitution
succeeded, so every untracked — that is, every BRAND-NEW — file was dropped.
`souken_p571_citations.txt` and `saijin_named_as.txt` (added 2026-09-11) had never
been able to enter the repo. `--full-name` on the `ls-files` call fixed that half.

**2. `git diff` is index-relative**, and the fix for (1) did not touch it. The
step above this one staged `modern-quickstatements/*.txt` and then failed to
commit (no git identity), so on 2026-09-13 about thirty regenerated files were
sitting in the index and `git diff` — which compares the worktree against the
index, not HEAD — reported none of them. It listed 25 of ~45.
`invalid_p825_removals.txt` went from its regenerated 17 lines back to 16 and
`ronsha_role_qualifiers.txt` from 497 back to 502, with nothing in the log.

So the list is now one command, `git status --porcelain`, which reports staged,
unstaged and untracked alike in one root-relative format. Neither mistake is
expressible in it: one command cannot disagree with itself about paths, and
porcelain has no blind spot for the index. The staging that triggered (2) was
also removed, and `test_workflow_commit_steps_can_commit.py` pins both that and
the shape of this command.

This file pins the consequences — that the list is complete, that the prefix
filter still matches what git emits, and that the `git clean` which makes an
incomplete list destructive is still the thing to look at.
"""

import os


WORKFLOW = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".github", "workflows", "generate-quickstatements.yml",
)


def _text():
    with open(WORKFLOW, encoding="utf-8") as fh:
        return fh.read()


def _command_lines():
    """Command lines only — the comment block above the fix names every retired
    command in prose to explain why it is retired, and matching that instead of
    the call is how an earlier version of this test went red against a workflow
    that was already correct."""
    return [ln.strip() for ln in _text().splitlines()
            if not ln.lstrip().startswith("#")]


def test_the_backup_list_can_see_a_staged_change():
    """The listing command must report the index, not just the worktree.

    `git diff --name-only` cannot, and that is what lost ~20 files on 2026-09-13.
    `git ls-files --others` is gone with it: a staged BRAND-NEW file is invisible
    to that too, so between them the two commands had no way to see one at all.
    """
    calls = [ln for ln in _command_lines() if "status --porcelain" in ln]
    assert len(calls) == 1, (
        "expected exactly one `git status --porcelain` building the backup list; "
        f"found {len(calls)}: {calls}")
    call = calls[0]
    assert "--untracked-files=all" in call, (
        "without it git names a new DIRECTORY rather than the files inside it, and "
        f"the backup loop's `[ -f ]` skips directories. Found: {call!r}")
    assert '-C "$GITHUB_WORKSPACE"' in call, (
        "the step runs from inside modern-quickstatements, so without -C the paths "
        f"lose the prefix the sed below strips. Found: {call!r}")

    for retired in ("git diff --name-only", "git ls-files --others"):
        assert not [ln for ln in _command_lines() if retired in ln], (
            f"{retired} is back in the backup-list path; it has a blind spot that "
            "this test exists to keep closed")


def test_the_prefix_filter_and_the_listing_still_belong_to_each_other():
    """If the sed prefix stops matching what git emits, the same bug returns in a
    new shape. Both halves are asserted together so a rename of the directory
    cannot quietly re-open it."""
    text = _text()
    assert "sed -n 's|^modern-quickstatements/||p'" in text, (
        "the prefix filter changed — re-check that the git command feeding it "
        "still emits paths carrying that prefix")


def test_the_clean_that_makes_this_destructive_is_still_there():
    """The dropped-from-the-list file is only lost because of this line. If the
    clean ever goes away, this test should be re-read rather than deleted — the
    list would still be wrong, just no longer fatal."""
    text = _text()
    assert "git clean -fd modern-quickstatements/" in text
