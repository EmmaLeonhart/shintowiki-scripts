"""
deleted_qids_in_ill op
=======================
Ported from ``shinto_miraheze/tag_deleted_qids_in_ill.py``. Finds
``{{ill}}`` templates whose ``WD=Qxxx`` or ``qid=Qxxx`` parameter
points at a Wikidata QID that has since been deleted or merged out of
existence, and rewrites the parameter to ``qid=DELETED_QID``. Also
renames the legacy ``WD=`` parameter to the current ``qid=`` form even
when the QID is still valid.

Pages that end up with at least one DELETED_QID replacement are tagged
``[[Category:Pages with deleted QID in ill template]]``.

Network: each page visit batch-queries Wikidata's ``wbgetentities`` for
any QIDs it hasn't seen yet this run. The result cache lives at
module level, so QIDs shared across pages are only fetched once per
orchestrator process.

Mainspace-only — {{ill}} is an inline-link template; it doesn't appear
meaningfully in templates or categories. If a later need surfaces, add
other namespaces to NAMESPACES.
"""

import re
import time

import requests

NAME = "deleted_qids_in_ill"
NAMESPACES = (0,)

_WD_API = "https://www.wikidata.org/w/api.php"
_USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

CATEGORY_TAG = "[[Category:Pages with deleted QID in ill template]]"

ILL_RE = re.compile(r"\{\{ill\|([^{}]*)\}\}", re.IGNORECASE)
QID_RE = re.compile(r"^Q\d+$")

# Module-level cache: True = QID exists on Wikidata, False = missing/deleted.
# Persists for the lifetime of the orchestrator process.
_qid_exists: dict[str, bool] = {}


def _extract_qids(text: str) -> set[str]:
    qids: set[str] = set()
    for match in ILL_RE.finditer(text):
        for p in match.group(1).split("|"):
            p = p.strip()
            if p.upper().startswith("WD=") or p.lower().startswith("qid="):
                val = p.split("=", 1)[1].strip()
                if QID_RE.match(val):
                    qids.add(val)
    return qids


def _has_wd_param(text: str) -> bool:
    for match in ILL_RE.finditer(text):
        for p in match.group(1).split("|"):
            if p.strip().upper().startswith("WD="):
                return True
    return False


def _check_qids_batch(qids: list[str]) -> None:
    """Populate `_qid_exists` for any QIDs not yet cached. On network
    error the missing entries are assumed to exist — we refuse to mark
    a live QID as DELETED_QID just because Wikidata's API hiccuped."""
    uncached = [q for q in qids if q not in _qid_exists]
    for i in range(0, len(uncached), 50):
        batch = uncached[i : i + 50]
        try:
            resp = requests.get(
                _WD_API,
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(batch),
                    "props": "info",
                    "format": "json",
                },
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            resp.raise_for_status()
            entities = resp.json().get("entities", {})
            for qid in batch:
                entity = entities.get(qid, {})
                _qid_exists[qid] = "missing" not in entity
        except Exception:
            for qid in batch:
                _qid_exists[qid] = True
        time.sleep(0.5)


def _fix_ill(text: str, deleted: set[str]) -> str:
    def replacer(match):
        inner = match.group(1)
        params = inner.split("|")
        changed = False
        for i, p in enumerate(params):
            ps = p.strip()
            if ps.upper().startswith("WD=") or ps.lower().startswith("qid="):
                val = ps.split("=", 1)[1].strip()
                if val in deleted:
                    params[i] = "qid=DELETED_QID"
                    changed = True
                elif ps.upper().startswith("WD="):
                    params[i] = f"qid={val}"
                    changed = True
        if not changed:
            return match.group(0)
        return "{{ill|" + "|".join(params) + "}}"

    return ILL_RE.sub(replacer, text)


def apply(title: str, text: str):
    qids = _extract_qids(text)
    has_wd = _has_wd_param(text)
    if not qids and not has_wd:
        return None, None

    deleted: set[str] = set()
    if qids:
        _check_qids_batch(list(qids))
        deleted = {q for q in qids if _qid_exists.get(q) is False}

    if not deleted and not has_wd:
        return None, None

    new_text = _fix_ill(text, deleted)
    if deleted and CATEGORY_TAG not in new_text:
        new_text = new_text.rstrip() + "\n" + CATEGORY_TAG + "\n"

    if new_text == text:
        return None, None

    parts = []
    if deleted:
        parts.append(f"mark {len(deleted)} deleted QID(s) as DELETED_QID")
    if has_wd:
        parts.append("rename WD= to qid=")
    return new_text, " + ".join(parts) + " in ill templates"
