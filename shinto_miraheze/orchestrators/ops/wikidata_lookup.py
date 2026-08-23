"""
wikidata_lookup op
==================
Fills in {{wikidata link|...}} templates by looking up the Wikidata
sitelinks API. Two resolutions can happen on a single page:

1. Template has an empty QID slot but ≥1 (lang, target) pair (typical
   shape after interlang_consolidate folded raw [[ja:X]] interwikis but
   left the QID blank): query
   ``wbgetentities?sites=<lang>wiki&titles=<target>&props=info`` for
   EVERY pair, collect every resolved QID, then:
     * Exactly 1 unique QID resolved → use it (the interwikis agree).
     * 2+ unique QIDs resolved → leave the QID slot empty and stamp
       ``|consistent_qid=false`` on the template so the disagreement
       is visible. The user's stated rule: if the interwikis disagree
       we don't auto-pick — surface the conflict for human review.
     * 0 resolved → leave the QID slot empty, no flag.
   If a later run finds the interwikis now do agree (e.g. one of them
   got renamed Wikidata-side), the QID resolves normally and the
   ``consistent_qid=false`` flag is dropped.

2. Template has a real QID: fetch the entity's sitelinks via
   ``wbgetentities&props=sitelinks`` and REPLACE the template's pair
   list with what Wikidata says (capped at MAX_PAIRS). Existing pairs
   are NOT preserved — the template is treated as a derived view of
   Wikidata's sitelinks. The previous append-don't-replace semantics
   let stale pairs accumulate forever (e.g. a `fr|User:Immanuelle/X`
   draft marker survived every run because it was always "already
   present"). Failure handling: if the sitelinks fetch fails (network
   error, bad response), existing pairs are kept untouched; only a
   verified-empty answer from Wikidata authorises clearing them. A
   pre-existing ``consistent_qid=false`` is dropped (the manual fix
   is in — the flag was a question, not an answer).

After processing, the op stamps a ``check_date=YYYY-MM-DD`` named
parameter on the template. On future runs, pages whose ``check_date``
is younger than ``CHECK_INTERVAL_DAYS`` are skipped entirely — most
content settles for months at a time, so re-querying every 6h cron
fire just burns API quota. The user-stated rationale: "for the most
part for a lot of things they might get a new article or something
every six months but not otherwise."

Cost: 0–2 Wikidata API calls per page on the first visit (resolve QID
+ fetch sitelinks), then 0 calls for ~6 months until check_date
expires. Per-run caches keep repeated lookups cheap when many pages
share a QID within a single run.

Disabled unless ``ENABLE_WIKIDATA_LOOKUP=1``. Marked PRE_HEAVY so the
filled-in template is what fandom_mirror and the XML archive snapshot
in the same cycle.
"""

import datetime
import os
import re
import time

import requests

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_for import ua_for

from ..common import REDIRECT_RE

NAME = "wikidata_lookup"
# Mainspace, Template, Category only — matches interlang_consolidate's
# scope and the user directive (2026-05-08): wikidata links are only
# meaningful on these three namespaces, so don't fill/refresh them on
# User/Project/File/Help/Talk pages even if older runs left a template
# there.
NAMESPACES = (0, 10, 14)
PRE_HEAVY = True

WD_LINK_RE = re.compile(
    r"\{\{\s*wikidata\s*link\s*((?:\|[^{}]*)*)\}\}",
    re.IGNORECASE,
)

_WD_API = "https://www.wikidata.org/w/api.php"
# _USER_AGENT removed 2026-08-19: the request sites now resolve the agent from the URL via
# ua_for(), so this hand-built literal was dead and could only drift. Was: _USER_AGENT = "ShintoOrchestrator/1.0 (User:EmmaBot; shinto.miraheze.org)"
_HTTP_TIMEOUT = 15
_API_THROTTLE = 0.3

# Cap pairs in the template to avoid bloat — Template:Wikidata link
# accepts up to 20 positional pair slots.
_MAX_PAIRS = 20

# Skip-recheck window. A page whose ``check_date`` is younger than this
# (in days) is skipped without an API call — six months matches the
# user's heuristic for how often Wikidata picks up new sitelinks for
# the kind of content shintowiki tracks.
_CHECK_INTERVAL_DAYS = 180

# Cutover: stamps from BEFORE this date are treated as stale regardless
# of age. Originally set to 2026-05-15 (Phase 1 voting rewrite); bumped
# to 2026-05-20 to also re-evaluate every page touched between
# 05-15 and 05-20 under the old append-don't-replace Phase 2 logic.
# Those entries accumulated stale (lang, title) pairs (e.g.
# `fr|User:Immanuelle/Futemimi` on Q65266228 even though Wikidata has
# no fr-wiki sitelink for that QID). The new Phase 2 logic replaces
# the entire pair list with what Wikidata actually has, so a re-pass
# clears the crud.
_CHECK_DATE_CUTOVER = datetime.date(2026, 5, 20)

# Sites to skip when reading sitelinks back into pair form — sister
# projects (Commons, Wikidata itself, Species) and meta-wikis aren't
# language pairs in the {{wikidata link}} sense.
_NON_LANGUAGE_SITES = frozenset({
    "commonswiki", "metawiki", "specieswiki", "wikidatawiki",
    "mediawikiwiki", "incubatorwiki", "outreachwiki", "testwiki",
    "test2wiki", "wikitech",
})

# Per-run caches; cleared implicitly by process exit. Module-level so
# different pages within the same run share lookups. The sitelinks
# cache value is None when the fetch failed (so Phase 2 knows not to
# treat that as a verified-empty answer and accidentally nuke
# existing pairs on transient errors); a list (possibly empty) means
# the fetch succeeded.
_qid_cache: dict[tuple[str, str], "str | None"] = {}
_sitelinks_cache: dict[str, "list[tuple[str, str]] | None"] = {}


def _check_date_is_recent(date_str: str) -> bool:
    """True if the ISO date is within ``_CHECK_INTERVAL_DAYS`` of today
    AND on/after the cutover date. Stamps from before the cutover are
    treated as stale — they came from the pre-2026-05-15 Phase 1
    logic which only looked at the first interwiki match, so the
    consistency rule didn't get a chance to run on them."""
    if not date_str:
        return False
    try:
        d = datetime.date.fromisoformat(date_str.strip())
    except ValueError:
        return False
    if d < _CHECK_DATE_CUTOVER:
        return False
    age = (datetime.date.today() - d).days
    return 0 <= age < _CHECK_INTERVAL_DAYS


def _parse_wd_params(raw: str) -> tuple[str, list[tuple[str, str]], dict[str, str]]:
    """Split ``|Q|lang|title|...|key=val`` into (qid, pairs, named).

    Named parameters (anything containing ``=``) are pulled out into a
    dict so they don't get treated as positional. Order of the named
    dict is preserved (insertion-ordered since Python 3.7).
    """
    parts = [p.strip() for p in raw.split("|")[1:]]
    named: dict[str, str] = {}
    positional: list[str] = []
    for p in parts:
        if "=" in p:
            name, _, value = p.partition("=")
            named[name.strip()] = value.strip()
        else:
            positional.append(p)
    qid = positional[0] if positional else ""
    pair_parts = positional[1:]
    pairs: list[tuple[str, str]] = []
    i = 0
    while i + 1 < len(pair_parts):
        pairs.append((pair_parts[i], pair_parts[i + 1]))
        i += 2
    return qid, pairs, named


def _build_wd_template(
    qid: str,
    pairs: list[tuple[str, str]],
    named: "dict[str, str] | None" = None,
) -> str:
    parts = [qid]
    for lang, t in pairs:
        parts.append(lang)
        parts.append(t)
    body = "|".join(parts)
    if named:
        for key, value in named.items():
            body += f"|{key}={value}"
    return "{{wikidata link|" + body + "}}"


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
            headers={"User-Agent": ua_for(_WD_API)},
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


def _fetch_sitelinks(qid: str) -> "list[tuple[str, str]] | None":
    """Fetch the entity's sitelinks and return [(lang, title), ...].

    Returns ``None`` if the fetch failed (network error, malformed
    response). A returned empty list means the fetch SUCCEEDED and the
    entity genuinely has no language-wiki sitelinks — Phase 2 uses
    that as ground-truth permission to clear stale pairs from the
    template, so the failure-vs-empty distinction is load-bearing.
    Treat both ``[]`` and ``None`` as "no pairs to add" in append-mode
    callers, but only ``[]`` (not ``None``) authorises a wholesale
    replace.
    """
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
            headers={"User-Agent": ua_for(_WD_API)},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        entity = resp.json().get("entities", {}).get(qid, {}) or {}
    except Exception:
        _sitelinks_cache[qid] = None
        return None
    if "missing" in entity:
        # Entity-missing IS a verified-empty answer (Wikidata told us
        # the QID doesn't exist), so return [], not None.
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

    qid, pairs, named = _parse_wd_params(wd_match.group(1))

    # Skip pages we already touched recently. Pair count is no longer a
    # gate — even a 10-pair page is worth re-checking after 6 months
    # since Wikidata may have added a new sitelink.
    if _check_date_is_recent(named.get("check_date", "")):
        return None, None

    # Phase 1: resolve QID if missing.
    #
    # Query every (lang, target) pair on the template and collect the
    # set of QIDs they resolve to. Three outcomes:
    #   * |resolved| == 1: interwikis agree → use that QID.
    #   * |resolved| > 1: interwikis disagree → leave QID empty,
    #     stamp consistent_qid=false so the conflict is visible.
    #   * |resolved| == 0: nothing matched → leave QID empty, no flag.
    # On a subsequent run, if the interwikis come into agreement (e.g.
    # one of them got renamed Wikidata-side and now points at the
    # majority QID), the consistent_qid=false flag is dropped.
    new_qid = qid
    phase1_ran = False
    phase1_resolved: set[str] = set()
    if not qid:
        if not pairs:
            # No QID and no pairs to look up by. Stamp the check_date
            # anyway so we don't re-evaluate every cycle for a page
            # that has no signal to act on.
            new_named = dict(named)
            new_named["check_date"] = datetime.date.today().isoformat()
            if new_named == named:
                return None, None
            new_template = _build_wd_template(qid, pairs, new_named)
            new_text = text[: wd_match.start()] + new_template + text[wd_match.end() :]
            return new_text, f"stamp check_date={new_named['check_date']} (no signal to resolve)"
        phase1_ran = True
        for (lang, target) in pairs:
            resolved = _resolve_qid_from_sitelink(lang, target)
            if resolved:
                phase1_resolved.add(resolved)
        if len(phase1_resolved) == 1:
            new_qid = next(iter(phase1_resolved))

    # Phase 2: fetch sitelinks and REPLACE the pair list with what
    # Wikidata says. The previous append-don't-replace semantics let
    # stale pairs accumulate forever — e.g., `fr|User:Immanuelle/X`
    # written by a prior script as a draft marker would survive every
    # subsequent run because the op only ever ADDED sitelinks. The
    # template's pair list is now treated as a derived view of the
    # QID's Wikidata sitelinks; existing pairs are not preserved.
    #
    # Failure handling: a fetch failure (None) keeps the existing
    # pairs untouched. Only a verified-empty answer ([]) — meaning
    # Wikidata returned successfully and that QID has no language
    # sitelinks — clears the list. This protects against transient
    # API errors silently nuking valid data.
    new_pairs = list(pairs)
    if new_qid:
        sitelinks = _fetch_sitelinks(new_qid)
        if sitelinks is not None:
            new_pairs = sitelinks[:_MAX_PAIRS]

    # Always stamp check_date so the next 6 months of cycles skip this page.
    today = datetime.date.today().isoformat()
    new_named = dict(named)
    new_named["check_date"] = today

    # consistent_qid flag handling:
    #   * If we now have a resolved QID, drop the flag (resolved or
    #     never set — either way, no longer a question).
    #   * If Phase 1 ran and produced 2+ disagreeing QIDs, set the flag.
    #   * Otherwise leave the flag as-is (Phase 1 found nothing, or
    #     Phase 1 didn't run because qid was already set going in).
    flag_set = False
    flag_cleared = False
    if new_qid:
        if "consistent_qid" in new_named:
            new_named.pop("consistent_qid")
            flag_cleared = True
    elif phase1_ran and len(phase1_resolved) > 1:
        if new_named.get("consistent_qid") != "false":
            flag_set = True
        new_named["consistent_qid"] = "false"

    if new_qid == qid and new_pairs == pairs and new_named == named:
        return None, None

    new_template = _build_wd_template(new_qid, new_pairs, new_named)
    new_text = text[: wd_match.start()] + new_template + text[wd_match.end() :]

    bits: list[str] = []
    if new_qid != qid:
        bits.append(f"resolve QID {new_qid} from interwiki")
    added = len(new_pairs) - len(pairs)
    removed = len(set(pairs) - set(new_pairs))
    if added > 0 and removed > 0:
        bits.append(
            f"sync sitelinks from Wikidata (+{added}, -{removed})"
        )
    elif added > 0:
        bits.append(f"add {added} sitelink pair(s) from Wikidata")
    elif removed > 0:
        bits.append(
            f"drop {removed} stale pair(s) not in Wikidata sitelinks"
        )
    if flag_set:
        bits.append(
            f"flag consistent_qid=false ({len(phase1_resolved)} disagreeing QIDs from interwikis)"
        )
    if flag_cleared:
        bits.append("clear consistent_qid flag (now resolved)")
    bits.append(f"check_date={today}")
    return new_text, "; ".join(bits)
