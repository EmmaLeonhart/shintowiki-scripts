"""`git_synced/Open questions.wiki` must keep `[[Category:Git synced pages]]`.

That category is not decoration — it is the sync's membership test. Drop it and
`sync_git_synced_pages.py` does exactly what it is written to do: pushes the local
text to the wiki with the summary "removed from Git synced pages category", then
`local_path.unlink()`s the file. Both halves are correct behaviour.

Happened 2026-08-23. A session rewrote this page wholesale to trim it (Emma had asked
for that three times) and did not carry the last line across. The CI sync ran at
04:03:59Z, pushed the categoryless text to the wiki, and deleted the local file at
04:04:08Z. Nothing was lost — the wiki kept the content and git kept everything — but
the page silently left the sync set, and the only visible symptom was the file
vanishing on the next `git pull`.

This file is the one in `git_synced/` that humans and sessions edit by hand; the other
~2,850 are written by the sync itself. So it is the one that needs the guard.

The test is deliberately narrow. Nine other files in the directory have sat there for
months without the category and are not being deleted, so a blanket "every file carries
it" assertion would be false — and asserting something false to feel thorough is worse
than asserting the one thing that is true.
"""
import io
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE = os.path.join(_ROOT, "git_synced", "Open questions.wiki")
CATEGORY = "[[Category:Git synced pages]]"


def test_the_page_exists():
    assert os.path.exists(PAGE), (
        "git_synced/Open questions.wiki is missing. If it vanished after a pull, the "
        "sync un-synced it — check that the last commit to touch it kept " + CATEGORY)


def test_the_page_carries_the_gating_category():
    text = io.open(PAGE, encoding="utf-8").read()
    assert CATEGORY in text, (
        "Open questions.wiki lost " + CATEGORY + ", so the next sync run will push it "
        "to the wiki and DELETE the local copy. Re-add it as the last line.")


def test_the_category_sits_after_the_last_section():
    """Where it sits matters: a category in the tail survives an edit to any section, one
    buried mid-file is easy to cut along with the section around it.

    It is NOT pinned as the literal last line. It was, until 2026-08-24, when the wiki
    sync appended `<references />` below it (bot commit bfd5abc4, 05:44:59Z). This page is
    wiki-wins, so the wiki putting something after the category is the wiki being
    authoritative — the assertion was mine and it was too strict. The property that
    actually protects the file is that the category comes after all the content."""
    text = io.open(PAGE, encoding="utf-8").read()
    assert CATEGORY in text
    last_section = text.rfind("\n== ")
    assert last_section != -1, "page has no section headings any more"
    assert text.index(CATEGORY) > last_section, "category is buried above a section"


def test_the_sync_still_decides_membership_by_this_category():
    """Pinned against the sync itself, so this test cannot outlive the rule it guards."""
    import re
    src = io.open(os.path.join(_ROOT, "shinto_miraheze", "sync_git_synced_pages.py"),
                  encoding="utf-8").read()
    assert re.search(r'CATEGORY\s*=\s*"Git synced pages"', src)
    assert "local_path.unlink()" in src
