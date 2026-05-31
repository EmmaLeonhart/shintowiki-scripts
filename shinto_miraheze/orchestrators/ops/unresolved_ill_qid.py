"""
unresolved_ill_qid op
======================
Detector + tagger for backlog item 3 ("ILLs without WD= / 'Unknown'
targets"). After ``normalize_ill_wikidata`` has run, a ``{{ill|…}}`` call
carries a resolved Wikidata target as ``qid=Q\\d+``. A call with NO usable
qid — no ``qid=``/``WD=`` at all, ``qid=Unknown``, or a literal "Unknown"
target — is one whose Wikidata destination is still unknown and needs filling
(the fix_ill_destinations work).

Pages with at least one such unresolved ill are tagged
``[[Category:Pages with unresolved QID in ill template]]``. Pure-text and
self-healing: once every ill on a page has a valid qid (or only the
``qid=DELETED_QID`` marker, which is the *separate* deleted-QID category) the
tag is stripped again.

``qid=DELETED_QID`` is deliberately NOT counted as unresolved here — that case
is owned by ``deleted_qids_in_ill`` / ``[[Category:Pages with deleted QID in
ill template]]`` (backlog item 8). This op runs AFTER ``deleted_qids_in_ill``
in the OPS list so the DELETED_QID marker is already in place.

Mainspace-only — {{ill}} is an inline-link template. Redirects are skipped.
"""

import re

from ..common import REDIRECT_RE

NAME = "unresolved_ill_qid"
NAMESPACES = (0,)

CATEGORY = "Pages with unresolved QID in ill template"
CATEGORY_TAG = f"[[Category:{CATEGORY}]]"

# Conservative: body cannot contain nested {...} braces (matches the other
# ill-related ops; nested-template calls are left alone).
ILL_RE = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)
QID_RE = re.compile(r"^Q\d+$")

CATEGORY_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Pages with unresolved QID in ill template\s*\]\]\n?",
    re.IGNORECASE,
)


def _ill_qid_value(body: str):
    """Return the qid/WD value of an ill body, or None if no such param.
    The last qid=/WD= param wins (matches normalize_ill_wikidata's output,
    which emits a single qid=)."""
    value = None
    for p in body.split("|"):
        ps = p.strip()
        if ps.lower().startswith("qid=") or ps.upper().startswith("WD="):
            value = ps.split("=", 1)[1].strip()
    return value


def _has_unresolved_ill(text: str) -> bool:
    for match in ILL_RE.finditer(text):
        value = _ill_qid_value(match.group(1))
        if value == "DELETED_QID":
            continue  # owned by deleted_qids_in_ill (item 8)
        if value is None or not QID_RE.match(value):
            # no qid/WD param, qid=Unknown, or any non-Q\d+ value
            return True
    return False


def apply(title: str, text: str):
    if REDIRECT_RE.search(text):
        return None, None
    if "{{ill" not in text.lower():
        return None, None

    wants_tag = _has_unresolved_ill(text)
    has_tag = bool(CATEGORY_RE.search(text))

    if has_tag == wants_tag:
        return None, None

    if wants_tag:
        new_text = text.rstrip() + "\n" + CATEGORY_TAG + "\n"
        return new_text, f"tag [[:Category:{CATEGORY}]] (ill without resolved qid)"

    new_text = CATEGORY_RE.sub("", text)
    if new_text == text:
        return None, None
    return new_text, f"strip [[:Category:{CATEGORY}]] (all ill qids resolved)"
