"""The QuickStatements commit step must commit the INPUT cache, not just the output.

⛔ THE INCIDENT, 2026-09-21. CI commit `81fb4f0b1` wrote `nta_kana.txt` down from
1,481 lines to 772 and committed it alone. The `nta_kana_targets.json` that run had
just rewritten — the cached WDQS target rows the matching is done against — was
restored into the working tree by the backup/restore block and then never staged,
because the step said `git add *.txt` and `git add _site/`.

The result was a repo whose committed output did not follow from its committed
inputs, and no way to tell from inside the repo. Both natural explanations for the
drop were checked against live Wikidata and both were wrong: of 30 dropped items, 0
had gained `P1814` and 0 had gained an English label, and all 30 still carried the
`P131` the target query needs. Re-running the generator on the committed cache gave
1,481 lines, byte-identical to the pre-drop file.

⚠ The narrowness is the point. Four other `.json` files are rewritten by the same run
— `p958_summary`, `doujou_resolution`, `derived_name_in_kana_disagreements`,
`province_exclusions_report` — and they are NOT staged, deliberately. They are
reports ABOUT the run. A cache is an input TO it, and only an input makes the output
reproducible.
"""
import io
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "generate-quickstatements.yml")
CACHE = "nta_kana_targets.json"


def _workflow():
    return io.open(WORKFLOW, encoding="utf-8").read()


def test_every_staging_site_also_stages_the_cache():
    """There are two — one before the rebase and one after it — and the one after is
    the one that actually reaches the commit. Both are asserted, because a fix applied
    to only the first would look right in the diff and change nothing."""
    text = _workflow()
    txt_sites = len(re.findall(r"^\s*git add \*\.txt", text, re.M))
    cache_sites = len(re.findall(r"^\s*git add %s" % re.escape(CACHE), text, re.M))
    assert txt_sites >= 2, "expected the pre- and post-rebase staging sites"
    assert cache_sites == txt_sites, (
        "%d site(s) stage *.txt but %d stage %s — a staging site that omits the "
        "cache commits an output whose input is discarded"
        % (txt_sites, cache_sites, CACHE))


def test_the_cache_is_tracked_so_staging_it_is_meaningful():
    """If the cache were gitignored, the `git add` above would be a silent no-op."""
    import subprocess
    r = subprocess.run(["git", "check-ignore", "-q",
                        os.path.join("modern-quickstatements", CACHE)],
                       cwd=ROOT)
    assert r.returncode != 0, "%s is gitignored; staging it does nothing" % CACHE
    assert os.path.exists(os.path.join(ROOT, "modern-quickstatements", CACHE))


def test_the_backup_list_is_built_from_git_status_so_the_cache_survives_the_rebase():
    """Staging alone is not enough: the step wipes the tree (`git checkout -- .`,
    `git clean -fd`) and restores only the paths in `/tmp/qs_files.txt`. That list
    comes from `git status --porcelain`, which reports every changed file including
    `.json` — which is why this fix is a staging fix and not a restore-list fix. If
    the list is ever narrowed to `*.txt`, the cache is deleted before `git add` sees
    it and this test is what should fail."""
    text = _workflow()
    assert "status --porcelain --untracked-files=all -- modern-quickstatements" in text
    m = re.search(r"cut -c4- /tmp/qs_status\.txt.*", text)
    assert m, "the changed-file list is no longer derived from git status"
    # ⚠ Not a substring check for ".txt" — the pipeline names `qs_status.txt` and
    # `qs_files.txt`, so that matches the temp filenames and asserts nothing. What
    # must not appear is a FILTER narrowing the list to .txt files.
    pipeline = m.group(0)
    for narrowing in ("grep", "--include", ".txt$"):
        assert narrowing not in pipeline, (
            "the backup list looks filtered (%r); if it stops listing the cache, the "
            "cache is deleted by `git clean` before `git add` sees it" % narrowing)


@pytest.mark.parametrize("report", [
    "p958_summary.json",
    "doujou_resolution.json",
    "derived_name_in_kana_disagreements.json",
    "province_exclusions_report.json",
])
def test_reports_are_not_swept_in_alongside_the_cache(report):
    """Guards the scope: the fix was one cache, not `git add *.json`. These four are
    rewritten by the same run and stay unstaged."""
    text = _workflow()
    assert "git add *.json" not in text, "blanket .json staging sweeps in the reports"
    assert not re.search(r"^\s*git add %s" % re.escape(report), text, re.M), report
