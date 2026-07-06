"""
merged_qids_in_ill op
======================
Rewrites ``{{ill|…|qid=Qxxx}}`` (and the legacy ``WD=Qxxx``) where ``Qxxx`` has been
**merged** on Wikidata — turned into a *redirect* to a surviving item — to the surviving
target QID.

A merge is not a deletion: ``wbgetentities`` (default ``redirects=yes``) resolves the
redirect and exposes ``redirects: {from, to}``, so the stale QID keeps *resolving* but is
never canonicalized. ``deleted_qids_in_ill`` only acts on ``"missing"`` entities, so it
never catches merges — this op fills that gap (Emma 2026-07-06: many of these ill targets
are odd sub-topics with a decent chance of being merged over time).

Follows redirect chains (Wikidata resolves double-redirects, but the loop is cheap and
cycle-guarded). Network: batch ``wbgetentities``, cached module-level for the orchestrator
run; on API error or 429 the QID is treated as canonical (never rewrite on a hiccup).
Mainspace-only — ``{{ill}}`` is an inline-link template.
"""
import re
import time

import requests

NAME = "merged_qids_in_ill"
NAMESPACES = (0,)

_WD_API = "https://www.wikidata.org/w/api.php"
_USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

ILL_RE = re.compile(r"\{\{ill\|([^{}]*)\}\}", re.IGNORECASE)
QID_RE = re.compile(r"^Q\d+$")

# qid -> surviving target QID if merged, else None (canonical / unknown / error).
# Persists for the lifetime of the orchestrator process.
_merge_target: "dict[str, str | None]" = {}


def _extract_qids(text: str) -> set:
    qids = set()
    for m in ILL_RE.finditer(text):
        for p in m.group(1).split("|"):
            p = p.strip()
            if p.upper().startswith("WD=") or p.lower().startswith("qid="):
                val = p.split("=", 1)[1].strip()
                if QID_RE.match(val):
                    qids.add(val)
    return qids


def _resolve_batch(qids) -> None:
    """Populate `_merge_target` for uncached QIDs. redirects.to → merge target;
    absent → None (canonical). Any error/429 → None (never rewrite on a hiccup)."""
    uncached = [q for q in qids if q not in _merge_target]
    for i in range(0, len(uncached), 50):
        batch = uncached[i:i + 50]
        try:
            resp = requests.get(
                _WD_API,
                params={"action": "wbgetentities", "ids": "|".join(batch),
                        "props": "info", "format": "json"},
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            if resp.status_code == 429:
                for q in batch:
                    _merge_target.setdefault(q, None)
                return
            resp.raise_for_status()
            entities = resp.json().get("entities", {})
            for q in batch:
                red = (entities.get(q) or {}).get("redirects")
                _merge_target[q] = red["to"] if red and red.get("to") else None
        except Exception:
            for q in batch:
                _merge_target[q] = None
        time.sleep(0.5)


def _final_target(qid: str) -> "str | None":
    """Follow the merge chain to the final surviving QID, or None if canonical."""
    seen = set()
    cur = qid
    result = None
    while cur not in seen:
        seen.add(cur)
        if cur not in _merge_target:
            _resolve_batch([cur])
        tgt = _merge_target.get(cur)
        if not tgt:
            break
        result = tgt
        cur = tgt
    return result


def _fix_ill(text: str, rewrites: dict) -> str:
    def replacer(match):
        params = match.group(1).split("|")
        for i, p in enumerate(params):
            ps = p.strip()
            if ps.upper().startswith("WD=") or ps.lower().startswith("qid="):
                val = ps.split("=", 1)[1].strip()
                if val in rewrites:
                    params[i] = "qid=" + rewrites[val]
        return "{{ill|" + "|".join(params) + "}}"

    return ILL_RE.sub(replacer, text)


def apply(title: str, text: str):
    if not text:
        return None, None
    qids = _extract_qids(text)
    if not qids:
        return None, None
    _resolve_batch(list(qids))
    rewrites = {}
    for q in qids:
        final = _final_target(q)
        if final and final != q:
            rewrites[q] = final
    if not rewrites:
        return None, None
    new_text = _fix_ill(text, rewrites)
    if new_text == text:
        return None, None
    summary = ("canonicalize merged Wikidata QID(s) in {{ill}}: "
               + ", ".join(f"{k}→{v}" for k, v in sorted(rewrites.items())))
    return new_text, summary
