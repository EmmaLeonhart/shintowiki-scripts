"""
wikidata_lookup op
==================
Fills in {{wikidata link|...}} templates by looking up the Wikidata
sitelinks API. Two resolutions can happen on a single page:

1. Template has an empty QID slot but ≥1 (lang, target) pair (typical
   shape after interlang_consolidate folded raw [[ja:X]] interwikis but
   left the QID blank): query
   ``wbgetentities?sites=<lang>wiki&titles=<target>&props=info`` for
   each pair until one resolves, then drop that QID into the template.

2. Template has a real QID but few/no language pairs (the user's
   primary motivating case — "where the wiki link doesn't have any
   actual articles linked"): fetch the entity's sitelinks via
   ``wbgetentities&props=sitelinks`` and append any (lang, title) pair
   not already present, capped at MAX_PAIRS to keep the template
   readable.

The op only acts on pages that already carry a {{wikidata link|...}}
template — interlang_consolidate (which runs first as PRE_HEAVY) is
responsible for creating the template + folding standalone interwikis
into pair slots, including the empty-QID case. This op then converts
that placeholder into a real wikidata link.

Cost: 0–2 Wikidata API calls per page, throttled at 0.3s between calls
and cached within a single run so pages sharing a QID don't refetch
sitelinks.

Disabled unless ``ENABLE_WIKIDATA_LOOKUP=1``. Marked PRE_HEAVY so the
filled-in template is what fandom_mirror and the XML archive snapshot
in the same cycle.
"""

import os
import re
import time

import requests

from ..common import REDIRECT_RE

NAME = "wikidata_lookup"
# Same coverage as interlang_consolidate — every wikitext namespace.
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    421, 829, 861, 863,
)
PRE_HEAVY = True

WD_LINK_RE = re.compile(
    r"\{\{\s*wikidata\s*link\s*((?:\|[^{}]*)*)\}\}",
    re.IGNORECASE,
)

_WD_API = "https://www.wikidata.org/w/api.php"
_USER_AGENT = "ShintoOrchestrator/1.0 (User:EmmaBot; shinto.miraheze.org)"
_HTTP_TIMEOUT = 15
_API_THROTTLE = 0.3

# Cap pairs in the template to avoid bloat — Template:Wikidata link
# accepts up to 20 positional pair slots.
_MAX_PAIRS = 20

# Skip the sitelinks merge once a page has this many pairs already —
# diminishing returns vs cost of the API call.
_PAIRS_SATURATED = 5

# Try these languages first when resolving an unknown QID; English and
# Japanese tend to have the highest hit rate for shintowiki content.
_PREFERRED_LANGS = ("en", "ja", "de", "fr", "zh", "ko")

# Sites to skip when reading sitelinks back into pair form — sister
# projects (Commons, Wikidata itself, Species) and meta-wikis aren't
# language pairs in the {{wikidata link}} sense.
_NON_LANGUAGE_SITES = frozenset({
    "commonswiki", "metawiki", "specieswiki", "wikidatawiki",
    "mediawikiwiki", "incubatorwiki", "outreachwiki", "testwiki",
    "test2wiki", "wikitech",
})

# Per-run caches; cleared implicitly by process exit. Module-level so
# different pages within the same run share lookups.
_qid_cache: dict[tuple[str, str], "str | None"] = {}
_sitelinks_cache: dict[str, list[tuple[str, str]]] = {}


def _parse_wd_params(raw: str) -> tuple[str, list[tuple[str, str]]]:
    parts = [p.strip() for p in raw.split("|")[1:]]
    qid = parts[0] if parts else ""
    pair_parts = parts[1:]
    pairs: list[tuple[str, str]] = []
    i = 0
    while i + 1 < len(pair_parts):
        pairs.append((pair_parts[i], pair_parts[i + 1]))
        i += 2
    return qid, pairs


def _build_wd_template(qid: str, pairs: list[tuple[str, str]]) -> str:
    parts = [qid]
    for lang, t in pairs:
        parts.append(lang)
        parts.append(t)
    return "{{wikidata link|" + "|".join(parts) + "}}"


def _resolve_qid_from_sitelink(lang: str, target: str) -> "str | None":
    """Look up the Wikidata QID for a given (lang)wiki:target sitelink."""
    key = (lang, target)
    if key in _qid_cache:
        return _qid_cache[key]
    try:
        time.sleep(_API_THROTTLE)
        resp = requests.get(
            _WD_API,
            params={
                "action": "wbgetentities",
                "sites": f"{lang}wiki",
                "titles": target,
                "props": "info",
                "format": "json",
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        entities = resp.json().get("entities", {}) or {}
    except Exception:
        _qid_cache[key] = None
        return None
    for qid, entity in entities.items():
        if qid.startswith("Q") and "missing" not in entity:
            _qid_cache[key] = qid
            return qid
    _qid_cache[key] = None
    return None


def _fetch_sitelinks(qid: str) -> list[tuple[str, str]]:
    """Fetch the entity's sitelinks and return [(lang, title), ...]."""
    if qid in _sitelinks_cache:
        return _sitelinks_cache[qid]
    try:
        time.sleep(_API_THROTTLE)
        resp = requests.get(
            _WD_API,
            params={
                "action": "wbgetentities",
                "ids": qid,
                "props": "sitelinks",
                "format": "json",
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        entity = resp.json().get("entities", {}).get(qid, {}) or {}
    except Exception:
        _sitelinks_cache[qid] = []
        return []
    if "missing" in entity:
        _sitelinks_cache[qid] = []
        return []
    sitelinks = entity.get("sitelinks", {}) or {}
    pairs: list[tuple[str, str]] = []
    for site, info in sitelinks.items():
        if site in _NON_LANGUAGE_SITES:
            continue
        # Only standard <lang>wiki sites — skip Wikiquote, Wikisource, etc.
        if not site.endswith("wiki") or site.endswith(("quotewiki", "sourcewiki",
                                                       "bookswiki", "newswiki",
                                                       "versitywiki", "voyagewiki",
                                                       "wiktionarywiki")):
            continue
        lang = site[:-4]  # strip "wiki" suffix
        if not lang or "_" in lang or " " in lang:
            continue
        title = (info.get("title") or "").strip()
        if title:
            pairs.append((lang, title))
    _sitelinks_cache[qid] = pairs
    return pairs


def _ordered_pairs_for_resolution(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Try preferred languages first, then everything else."""
    ordered: list[tuple[str, str]] = []
    for lang in _PREFERRED_LANGS:
        for p in pairs:
            if p[0].lower() == lang and p not in ordered:
                ordered.append(p)
    for p in pairs:
        if p not in ordered:
            ordered.append(p)
    return ordered


def apply(title: str, text: str):
    if os.getenv("ENABLE_WIKIDATA_LOOKUP") != "1":
        return None, None
    if not text:
        return None, None
    if REDIRECT_RE.search(text):
        return None, None

    wd_match = WD_LINK_RE.search(text)
    if not wd_match:
        # No template to fill — interlang_consolidate is responsible for
        # creating the empty-QID placeholder when interwikis exist; if
        # it didn't, there's nothing for us to do here.
        return None, None

    qid, pairs = _parse_wd_params(wd_match.group(1))

    # Phase 1: resolve QID if missing and we have at least one interwiki pair.
    new_qid = qid
    if not qid:
        if not pairs:
            return None, None  # nothing to look up by
        for (lang, target) in _ordered_pairs_for_resolution(pairs):
            resolved = _resolve_qid_from_sitelink(lang, target)
            if resolved:
                new_qid = resolved
                break

    # Phase 2: merge sitelinks if the page would benefit. Skip if pairs
    # already saturated to avoid spending an API call for diminishing
    # returns.
    new_pairs = list(pairs)
    if new_qid and len(new_pairs) < _PAIRS_SATURATED:
        sitelinks = _fetch_sitelinks(new_qid)
        existing = {(l.lower(), t) for l, t in new_pairs}
        for (lang, t) in sitelinks:
            if len(new_pairs) >= _MAX_PAIRS:
                break
            if (lang.lower(), t) not in existing:
                new_pairs.append((lang, t))
                existing.add((lang.lower(), t))

    if new_qid == qid and new_pairs == pairs:
        return None, None

    new_template = _build_wd_template(new_qid, new_pairs)
    new_text = text[: wd_match.start()] + new_template + text[wd_match.end() :]

    bits: list[str] = []
    if new_qid != qid:
        bits.append(f"resolve QID {new_qid} from interwiki")
    added = len(new_pairs) - len(pairs)
    if added > 0:
        bits.append(f"add {added} sitelink pair(s) from Wikidata")
    return new_text, "; ".join(bits) or "wikidata lookup update"
