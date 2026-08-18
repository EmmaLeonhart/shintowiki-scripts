#!/usr/bin/env python3
"""
fix_ill_destinations.py
=======================
Backlog item 2 — fill the missing Wikidata ``qid=`` on ``{{ill}}`` calls that
have no resolved destination, **without ever overwriting an existing valid QID**.

Input is the live tracking category ``[[Category:Pages with unresolved QID in ill
template]]`` (populated by the ``unresolved_ill_qid`` orchestrator op). For every
``{{ill|…}}`` call on a member page whose qid is missing, empty, or the literal
placeholder ``Unknown`` (NOT ``DELETED_QID`` — that's item 5's separate
category), resolve a destination QID and write it surgically into the call.

Resolution, in priority order (only fill when confident):

1. **enwiki pageprops (strongest).** Take the call's English target — an explicit
   ``en|Target`` pair if present, else the canonical positional[0] — and query
   ``en.wikipedia.org`` ``action=query&prop=pageprops&ppprop=wikibase_item``
   (following redirects). A returned ``wikibase_item`` is the destination. This
   is the NEW capability over ``normalize_ill_wikidata`` Mode B, which only
   resolves from the cleaned interwiki pairs and never asks enwiki about
   positional[0].
2. **Sitelink resolution of the non-en pairs.** Query every ``lang|title`` pair
   against Wikidata; a SINGLE unique QID across all pairs → use it; **2+ distinct
   QIDs → do NOT fill** (genuine ambiguity, leave for review).
3. **Unresolvable (literal "Unknown" target, no enwiki article, no pairs) →
   leave untouched.** It stays in the category and surfaces on the dashboard.

Any candidate QID whose ``P31`` marks it as a Wikimedia disambiguation page,
category, or list is REJECTED before filling — these resolve "confidently" from
enwiki/sitelinks but are never a valid ill destination (the case that motivated
this guard: ``{{ill|Mountain Shrine|ja|山神社}}`` → Q11470798, a disambiguation
page).

The write is surgical: the resolved ``qid=Q…`` replaces an existing
``qid=Unknown`` / empty ``qid=`` / ``WD=`` placeholder in place, or is appended as
``|qid=Q…`` when the call had no qid param at all. No other parameter is touched
(pair cleanup / sitelink sync is ``normalize_ill_wikidata``'s job). A call that
already carries a valid ``qid=Q\\d+`` is never modified. The ``unresolved_ill_qid``
op then self-heals the page out of the category on the next sweep once every ill
carries a qid.

Stateless. Bounded by ``--max-edits`` (page saves) and ``MAX_PAGES_PER_RUN``
(pages visited) so it can't hang the cleanup loop. Standard flags: ``--apply``
(default dry-run), ``--max-edits``, ``--run-tag``.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT
import argparse
import io
import os
import re
import sys
import time

import mwclient
import requests

from wiki_login import login_with_retry

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5


SOURCE_CATEGORY = "Pages with unresolved QID in ill template"

_WD_API = "https://www.wikidata.org/w/api.php"
_ENWIKI_API = "https://en.wikipedia.org/w/api.php"
READ_THROTTLE = 0.3
HTTP_TIMEOUT = 20

# Bound the per-run page visits so a 800+ member category drains over many
# cleanup cycles rather than hammering the wiki in one run.
MAX_PAGES_PER_RUN = 300

REDIRECT_RE = re.compile(r"^\s*#redirect\b", re.IGNORECASE | re.MULTILINE)
# Conservative: body cannot contain nested {...} braces (matches every other
# ill op; nested-template calls are left alone).
ILL_RE = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)
QID_RE = re.compile(r"^Q\d+$")

# Per-run caches (module-level so pages sharing a lookup pay once per run).
_enwiki_cache: dict[str, "str | None"] = {}
_sitelink_cache: dict[tuple, "str | None"] = {}
_bad_qid_cache: dict[str, bool] = {}

# Wikidata classes that are NEVER a valid {{ill}} destination — filling one of
# these is a confident-looking but wrong resolution (e.g. "Mountain Shrine" →
# Q11470798, a Wikimedia disambiguation page). A candidate QID whose P31
# includes any of these is rejected and the call is left for review.
_REJECT_P31 = frozenset({
    "Q4167410",   # Wikimedia disambiguation page
    "Q4167836",   # Wikimedia category
    "Q13406463",  # Wikimedia list article
    "Q22808320",  # Wikimedia human name disambiguation page
})


# ─── parsing helpers (mirror normalize_ill_wikidata conventions) ───

def parse_ill_body(body: str) -> tuple[list[str], list[tuple[int, str, str]]]:
    """Return (positional, named) where named is a list of (index, key, value)
    in body order so a value can be rewritten in place. Splitting on '|' only;
    keys are stripped, values preserved."""
    positional: list[str] = []
    named: list[tuple[int, str, str]] = []
    for i, p in enumerate(body.split("|")):
        if "=" in p:
            k, _, v = p.partition("=")
            named.append((i, k.strip(), v))
        else:
            positional.append(p)
    return positional, named


def current_qid_value(named: list[tuple[int, str, str]]) -> "str | None":
    """The last qid=/WD= value (matches the op's last-wins rule), or None."""
    value = None
    for _, k, v in named:
        if k.lower() == "qid" or k.upper() == "WD":
            value = v.strip()
    return value


def is_fillable(qid_value: "str | None") -> bool:
    """True when the call should be filled: no qid param, empty, or the literal
    Unknown placeholder. A valid Q\\d+ or DELETED_QID is NOT fillable."""
    if qid_value is None or qid_value == "":
        return True
    if qid_value == "DELETED_QID":
        return False
    if QID_RE.match(qid_value):
        return False
    # Any other non-Q value (e.g. "Unknown") is a placeholder → fillable.
    return True


def english_target(positional: list[str], body: str) -> "str | None":
    """Prefer an explicit ``en|Target`` pair's target; else positional[0].
    Returns None when the target is empty or the literal 'Unknown'."""
    # Walk positional[1:] as (lang, title) pairs looking for en.
    i = 1
    while i < len(positional):
        lang = positional[i].strip().lower()
        target = positional[i + 1].strip() if i + 1 < len(positional) else ""
        if lang == "en" and target:
            return _clean_target(target)
        i += 2
    if positional:
        return _clean_target(positional[0].strip())
    return None


def _clean_target(t: str) -> "str | None":
    if not t or t.lower() == "unknown":
        return None
    return t


def non_en_pairs(positional: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    i = 1
    while i < len(positional):
        lang = positional[i].strip()
        target = positional[i + 1].strip() if i + 1 < len(positional) else ""
        if lang and lang.lower() != "en" and target and target.lower() != "unknown":
            pairs.append((lang, target))
        i += 2
    return pairs


# ─── resolvers ──────────────────────────────────────────────

def resolve_enwiki(target: str) -> "str | None":
    """enwiki pageprops wikibase_item for an English article title, following
    redirects. None on miss/error."""
    if target in _enwiki_cache:
        return _enwiki_cache[target]
    try:
        time.sleep(READ_THROTTLE)
        resp = requests.get(
            _ENWIKI_API,
            params={
                "action": "query",
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "titles": target,
                "redirects": "1",
                "format": "json",
                "formatversion": "2",
            },
            headers={"User-Agent": ua_for(_ENWIKI_API)},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", [])
    except Exception:
        _enwiki_cache[target] = None
        return None
    for pg in pages:
        if pg.get("missing"):
            continue
        qid = (pg.get("pageprops", {}) or {}).get("wikibase_item")
        if qid and QID_RE.match(qid):
            _enwiki_cache[target] = qid
            return qid
    _enwiki_cache[target] = None
    return None


def resolve_sitelink(lang: str, target: str) -> "str | None":
    """Wikidata QID for a (lang)wiki:target sitelink. None on miss/error."""
    key = (lang, target)
    if key in _sitelink_cache:
        return _sitelink_cache[key]
    try:
        time.sleep(READ_THROTTLE)
        resp = requests.get(
            _WD_API,
            params={
                "action": "wbgetentities",
                "sites": f"{lang}wiki",
                "titles": target,
                "props": "info",
                "format": "json",
            },
            headers={"User-Agent": ua_for(_WD_API)},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        entities = resp.json().get("entities", {}) or {}
    except Exception:
        _sitelink_cache[key] = None
        return None
    for qid, entity in entities.items():
        if qid.startswith("Q") and "missing" not in entity:
            _sitelink_cache[key] = qid
            return qid
    _sitelink_cache[key] = None
    return None


def is_bad_target(qid: str) -> bool:
    """True if the QID's P31 marks it as a disambiguation page / category /
    list — never a valid ill destination. None/error → treated as NOT bad (we
    don't reject a candidate just because the type fetch hiccuped; the worst
    case is one over-fill, mirrored on the conservative side elsewhere)."""
    if qid in _bad_qid_cache:
        return _bad_qid_cache[qid]
    try:
        time.sleep(READ_THROTTLE)
        resp = requests.get(
            _WD_API,
            params={
                "action": "wbgetentities",
                "ids": qid,
                "props": "claims",
                "format": "json",
            },
            headers={"User-Agent": ua_for(_WD_API)},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        entity = resp.json().get("entities", {}).get(qid, {}) or {}
    except Exception:
        _bad_qid_cache[qid] = False
        return False
    p31 = entity.get("claims", {}).get("P31", []) or []
    classes = {
        (c.get("mainsnak", {}).get("datavalue", {}) or {}).get("value", {}).get("id")
        for c in p31
    }
    bad = bool(classes & _REJECT_P31)
    _bad_qid_cache[qid] = bad
    return bad


def resolve_destination(positional: list[str], body: str) -> "str | None":
    """Step 1 enwiki pageprops → Step 2 single-unique sitelink QID → else None.
    Any candidate that resolves to a disambiguation/category/list item is
    rejected (``is_bad_target``) so a confident-looking wrong target isn't
    filled."""
    target = english_target(positional, body)
    if target:
        qid = resolve_enwiki(target)
        if qid and not is_bad_target(qid):
            return qid
    # Step 2: sitelink resolution of the non-en pairs. Drop dab/category/list
    # candidates BEFORE the single-unique test — a dab QID shouldn't count
    # toward (or veto) consensus.
    resolved: set[str] = set()
    for lang, t in non_en_pairs(positional):
        r = resolve_sitelink(lang, t)
        if r and not is_bad_target(r):
            resolved.add(r)
    if len(resolved) == 1:
        return next(iter(resolved))
    return None  # 0 (nothing) or 2+ (ambiguous → leave for review)


def write_qid(body: str, new_qid: str) -> str:
    """Set qid=new_qid surgically. Replace an existing qid=/WD= part's value in
    place; otherwise append |qid=new_qid. Nothing else is touched."""
    parts = body.split("|")
    last_qid_idx = None
    for i, p in enumerate(parts):
        k = p.partition("=")[0].strip()
        if "=" in p and (k.lower() == "qid" or k.upper() == "WD"):
            last_qid_idx = i
    if last_qid_idx is not None:
        parts[last_qid_idx] = f"qid={new_qid}"
        return "|".join(parts)
    return body + f"|qid={new_qid}"


# ─── per-page processing ────────────────────────────────────

def process_text(text: str) -> tuple[str, int]:
    """Return (new_text, num_calls_filled). Pure given the resolver caches."""
    filled = [0]

    def replacer(m):
        body = m.group(1)
        positional, named = parse_ill_body(body)
        if not is_fillable(current_qid_value(named)):
            return m.group(0)
        new_qid = resolve_destination(positional, body)
        if not new_qid:
            return m.group(0)
        filled[0] += 1
        return "{{ill|" + write_qid(body, new_qid) + "}}"

    new_text = ILL_RE.sub(replacer, text)
    return new_text, filled[0]


def get_category_members(site) -> list[str]:
    cat = site.categories[SOURCE_CATEGORY]
    return [p.name for p in cat if p.namespace == 0]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="Write changes (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Maximum page saves this run (default 50).")
    parser.add_argument("--run-tag", required=True,
                        help="Run tag appended to the edit summary for auditing.")
    args = parser.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=ua_for(WIKI_URL))
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    members = get_category_members(site)
    print(f"{len(members)} member(s) in [[Category:{SOURCE_CATEGORY}]]")

    edits = 0
    visited = 0
    filled_total = 0
    for title in members:
        if edits >= args.max_edits:
            print("MAX EDITS reached, stopping.")
            break
        if visited >= MAX_PAGES_PER_RUN:
            print(f"MAX_PAGES_PER_RUN ({MAX_PAGES_PER_RUN}) reached, stopping.")
            break
        visited += 1
        try:
            page = site.pages[title]
            text = page.text()
        except Exception as e:
            print(f"  read error {title}: {e}")
            continue
        if REDIRECT_RE.search(text):
            continue
        new_text, filled = process_text(text)
        if filled == 0 or new_text == text:
            continue
        filled_total += filled
        if not args.apply:
            print(f"  [DRY] would fill {filled} ill qid(s) on [[{title}]]")
            edits += 1
            continue
        summary = (f"Bot: fill {filled} unresolved {{{{ill}}}} qid(s) from "
                   f"enwiki/sitelinks {args.run_tag}")
        try:
            page.save(new_text, summary=summary)
            print(f"  FILLED {filled} on [[{title}]]")
            edits += 1
        except Exception as e:
            print(f"  ERROR saving {title}: {e}")
        time.sleep(THROTTLE)

    print(f"\nDone. Pages visited: {visited} | "
          f"{'pages that would change' if not args.apply else 'pages edited'}: "
          f"{edits} | ill calls filled: {filled_total}")


if __name__ == "__main__":
    main()
