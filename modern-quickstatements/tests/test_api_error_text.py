"""The drip's run log must say WHY a save failed, not only "The save has failed."

2026-09-24 and 2026-09-26: every write failed with that text and the log could not
say why, while 2026-09-25 landed 497. The reason lives in the error's `code` and
`messages`, so api_error_text() carries them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("WIKIDATA_EMAIL", "test@example.org")
os.environ.setdefault("MIRAHEZE_EMAIL", "test@example.org")

import direct_daily_edits as dde  # noqa: E402


def test_code_and_message_names_are_kept():
    err = {"code": "failed-save", "info": "The save has failed.",
           "messages": [{"name": "wikibase-api-failed-save"}, {"name": "blockedtext"}]}
    assert dde.api_error_text(err) == (
        "The save has failed. [failed-save; messages: wikibase-api-failed-save, blockedtext]")


def test_info_stays_first_so_already_present_still_matches():
    err = {"code": "modification-failed",
           "info": "The statement has already a reference with hash abc"}
    text = dde.api_error_text(err)
    assert text.startswith(err["info"])
    assert dde.is_already_present(text) == dde.is_already_present(err["info"])


def test_non_dict_error_is_stringified():
    assert dde.api_error_text("boom") == "boom"
