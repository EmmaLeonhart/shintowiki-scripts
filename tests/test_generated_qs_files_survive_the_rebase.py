"""A brand-new generated `.txt` must survive `generate-quickstatements.yml`'s rebase dance.

The commit step in that workflow backs up this run's own output, resets and
`git clean -fd`s the tree, rebases onto origin, restores the backup, and commits.
The list of "this run's own output" is built from two git commands, and they
disagree about path format when run from inside a subdirectory:

    git diff --name-only -- .                 -> modern-quickstatements/foo.txt
    git ls-files --others --exclude-standard  -> foo.txt          (CWD-relative)

The `sed -n 's|^modern-quickstatements/||p'` that follows prints ONLY lines whose
substitution succeeded. So every untracked — that is, every BRAND-NEW — file was
dropped from the list, then not backed up, then deleted by the `git clean -fd`,
then never restored and never committed. Every run, identically, so a new atomic
file could never enter the repo through this workflow at all.

Found 2026-09-12: `souken_p571_citations.txt` and `saijin_named_as.txt` (both
added 2026-09-11, both written unconditionally by generators that demonstrably
ran, since their tracked siblings `souken_p571.txt` and `saijin_p825.txt` changed
in the same commit) were absent from the repo after a successful run.

`--full-name` makes `ls-files` agree with `diff`. This test pins that, because the
symptom is invisible: the workflow succeeds, the commit lands, and only a file
nobody is looking for is missing.
"""

import os


WORKFLOW = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".github", "workflows", "generate-quickstatements.yml",
)


def _text():
    with open(WORKFLOW, encoding="utf-8") as fh:
        return fh.read()


def test_ls_files_emits_repo_root_relative_paths():
    """Without --full-name the untracked half of the list is silently discarded."""
    text = _text()
    # Command lines only. The explanatory comment above the fix names the same
    # command in prose, and matching that instead of the call is how this test
    # first went red against a workflow that was already correct.
    calls = [ln.strip() for ln in text.splitlines()
             if "git ls-files --others" in ln and not ln.lstrip().startswith("#")]
    assert calls, "the untracked-file listing is gone — the backup list is now incomplete"
    for call in calls:
        assert "--full-name" in call, (
            "git ls-files --others must carry --full-name so its paths match "
            "`git diff --name-only`'s; without it every new file is dropped by the "
            f"sed prefix filter and deleted by the git clean. Found: {call!r}")


def test_the_prefix_filter_and_the_listing_still_belong_to_each_other():
    """If the sed prefix stops matching what git emits, the same bug returns in a
    new shape. Both halves are asserted together so a rename of the directory
    cannot quietly re-open it."""
    text = _text()
    assert "sed -n 's|^modern-quickstatements/||p'" in text, (
        "the prefix filter changed — re-check that BOTH git commands feeding it "
        "still emit paths carrying that prefix")


def test_the_clean_that_makes_this_destructive_is_still_there():
    """The dropped-from-the-list file is only lost because of this line. If the
    clean ever goes away, this test should be re-read rather than deleted — the
    list would still be wrong, just no longer fatal."""
    text = _text()
    assert "git clean -fd modern-quickstatements/" in text
