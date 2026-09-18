"""A paused label file must not drift back into the drip.

`select_label_proposals.py` builds the daily submission with
`QS_DIR.glob("*.txt")` over `shinto-label-generator/quickstatements/` and pools the
raw lines, ignoring filenames entirely. So membership of that directory IS the
decision to submit, and it is a decision made by a file's location rather than by
anything that reads like a switch. A file moved back for any reason starts editing
Wikidata again with no other change and no announcement.

`religious_building_en.txt` was paused on 2026-09-17 (Emma: the Commons-only premise
was wrong; 67% of its 22,548 "English" labels carry no English type word and many are
plain German or Italian). It is out of the pool and out of CI, and this keeps it
that way until someone decides otherwise on purpose.
"""
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LG = os.path.join(_ROOT, "shinto-label-generator")
_POOL = os.path.join(_LG, "quickstatements")
_PAUSED = os.path.join(_LG, "paused")

# Basenames that must stay out of the pooled directory.
_PAUSED_FILES = ["religious_building_en.txt"]


@pytest.mark.parametrize("name", _PAUSED_FILES)
def test_the_paused_file_is_not_in_the_drip_pool(name):
    assert not os.path.exists(os.path.join(_POOL, name)), (
        f"{name} is back in shinto-label-generator/quickstatements/, so "
        f"select_label_proposals.py is pooling it again and it is being submitted "
        f"to Wikidata. See shinto-label-generator/paused/README.md."
    )


@pytest.mark.parametrize("name", _PAUSED_FILES)
def test_the_paused_file_still_exists(name):
    """Paused, not deleted -- the work is 22,548 generated lines."""
    assert os.path.exists(os.path.join(_PAUSED, name)), (
        f"{name} is gone from shinto-label-generator/paused/. Pausing must not "
        f"lose the file; if it was resumed, this test should have been updated."
    )


def test_the_pause_directory_explains_itself():
    readme = os.path.join(_PAUSED, "README.md")
    assert os.path.isfile(readme), "paused/ has no README saying why anything is here"
    text = open(readme, encoding="utf-8").read()
    for name in _PAUSED_FILES:
        assert name in text, f"paused/README.md does not mention {name}"


def test_no_workflow_regenerates_a_paused_file():
    """Unwired from CI in the same commit. A workflow step that refreshes a paused
    file would rewrite it in place and, on resume, hide that it had ever stopped."""
    wf_dir = os.path.join(_ROOT, ".github", "workflows")
    for fn in os.listdir(wf_dir):
        if not fn.endswith((".yml", ".yaml")):
            continue
        text = open(os.path.join(wf_dir, fn), encoding="utf-8").read()
        assert "generate_religious_building_labels" not in text, (
            f".github/workflows/{fn} runs generate_religious_building_labels.py, "
            f"which regenerates a paused file. Unwire it or un-pause deliberately."
        )
