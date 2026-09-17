"""Every script-owned path into `docs/script-rationale/` must actually exist.

The 2026-09-17 move of 15 dated docs out of `docs/` fixed 41 references and missed
6, all of the same shape:

    DOC = os.path.join(REPO_ROOT, "docs", "izumo_ou_karakuni_2026-07.md")

A `git grep` for `docs/izumo_ou_karakuni_2026-07.md` cannot see that -- the
directory and the filename are separate string arguments, so the path only exists
once `os.path.join` has run. The move's own verification step was a grep, which is
exactly why all 6 survived it.

The two failure modes were not equally loud:
  * `build_label_typo_review_queue.py` READS its audit table, so it went straight
    to FileNotFoundError -- a dead queue builder.
  * The other five WRITE their report, so they would have silently recreated a
    second copy at the old `docs/` path, where the report-expiry rule would later
    delete it as stale while `script-rationale/` kept a diverging one.

So this test resolves the constants themselves rather than grepping for them.
"""
import importlib.util
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (module path relative to the repo root, constant name)
_DOC_CONSTANTS = [
    ("modern-quickstatements/generate_izumo_karakuni_page.py", "DOC"),
    ("modern-quickstatements/report_list_structure.py", "DOC"),
    ("modern-quickstatements/report_orphan_shikinaisha.py", "DOC"),
    ("modern-quickstatements/report_ronsha_list_membership.py", "DEFAULT_OUT"),
    ("modern-quickstatements/resolve_ronsha_addresses.py", "DEFAULT_OUT"),
    ("shinto_miraheze/build_label_typo_review_queue.py", "AUDIT"),
]


def _constant(rel_path, name):
    """Read the constant WITHOUT importing -- these modules do network work at
    import time in some cases, and the value is a plain os.path.join literal."""
    full = os.path.join(_ROOT, rel_path.replace("/", os.sep))
    assert os.path.isfile(full), f"{rel_path} is missing"
    src = open(full, encoding="utf-8").read()
    ns = {"os": os, "REPO_ROOT": _ROOT, "REPO": _ROOT, "ROOT": _ROOT,
          "HERE": os.path.join(_ROOT, os.path.dirname(rel_path))}
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{name} =") and "os.path.join" in stripped:
            exec(stripped, ns)  # noqa: S102 - a literal os.path.join, read above
            return ns[name]
    pytest.fail(f"{rel_path} no longer defines {name} as an os.path.join literal")


@pytest.mark.parametrize("rel_path,name", _DOC_CONSTANTS)
def test_the_doc_path_exists(rel_path, name):
    value = _constant(rel_path, name)
    assert os.path.exists(value), (
        f"{rel_path}:{name} points at {value!r}, which does not exist. If the doc "
        f"moved, update the constant -- a grep for the joined path will not find "
        f"it, which is how the 2026-09-17 move missed six of these."
    )


@pytest.mark.parametrize("rel_path,name", _DOC_CONSTANTS)
def test_the_doc_path_is_under_script_rationale(rel_path, name):
    value = _constant(rel_path, name)
    rel = os.path.relpath(value, _ROOT).replace(os.sep, "/")
    assert rel.startswith("docs/script-rationale/"), (
        f"{rel_path}:{name} writes or reads {rel!r}. These are script rationale "
        f"docs and live in docs/script-rationale/, which is EXEMPT from the "
        f"report-expiry rule. A copy written back to docs/ would be deleted as a "
        f"stale report while script-rationale/ kept a diverging one."
    )


def test_no_moved_doc_is_left_behind_in_docs():
    """The old location must stay empty for each moved doc."""
    rationale = os.path.join(_ROOT, "docs", "script-rationale")
    for name in os.listdir(rationale):
        if not name.endswith(".md") or name == "README.md":
            continue
        stale = os.path.join(_ROOT, "docs", name)
        assert not os.path.exists(stale), (
            f"docs/{name} exists again alongside docs/script-rationale/{name} -- "
            f"something is still writing to the pre-move path."
        )
