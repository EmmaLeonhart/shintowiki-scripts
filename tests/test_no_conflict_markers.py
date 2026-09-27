"""No committed generated file carries git conflict markers.

2026-09-27: a conflicted autostash pop in generate-quickstatements' commit step left
markers in the tree, `|| true` swallowed it, and `e37ded77c` committed nta_kana.txt and
nta_kana_targets.json with 22 markers each. The drip skipped the marker lines and read
both versions mixed together. The workflow now resolves such conflicts; this catches any
path that still lets markers through.
"""
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKERS = ("<<<<<<< ", ">>>>>>> ")


def test_generated_files_hold_no_conflict_markers():
    bad = []
    for pat in ("modern-quickstatements/*.txt", "modern-quickstatements/*.json",
                "modern-quickstatements/drip_tally/*.json"):
        for p in glob.glob(os.path.join(ROOT, pat)):
            with open(p, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    if line.startswith(MARKERS) or line.rstrip("\n") == "=======":
                        bad.append(f"{os.path.relpath(p, ROOT)}:{n}")
                        break
    assert not bad, bad
