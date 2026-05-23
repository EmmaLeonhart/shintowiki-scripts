"""
straggler_link_to_ill op
=========================
Converts "straggler" raw internal wikilinks into proper ``{{ill}}``
interlanguage-link templates by resolving the link target to a Wikidata
QID and building the ill from the item's sitelinks / P11250 / en label.

Example
-------
Before::

    [[四所神社 (豊岡市)|四所神社]]

After (Q11419885 has P11250 ``shinto:Shisho Shrine (Toyooka)``,
en label ``Shisho Shrine``, jawiki sitelink ``四所神社 (豊岡市)``)::

    {{ill|Shisho Shrine (Toyooka)|ja|四所神社 (豊岡市)|lt=Shisho Shrine|qid=Q11419885}}

Scope — straggler links ONLY
----------------------------
Matches plain internal wikilinks: ``[[Target]]`` or ``[[Target|Display]]``.
A link is converted only if ALL of these hold:

  * The target contains no colon ``:`` — that excludes File:/Image:/
    Category:/other-namespace links and interwiki links (``en:``, ``ja:``,
    ``zh:`` …). Emma's wording said "semicolon" but means the colon.
  * The link is NOT already inside an ``{{ill|…}}``, ``{{jalink|…}}``,
    ``{{nihongo|…}}`` call, nor any other template parameter (i.e. not
    inside ``{{ … }}``). We only touch free-standing wikilinks in body
    prose.
  * The target has no leading/trailing pipe shenanigans and isn't a
    section-only link (``[[#Foo]]``).

File links, interwiki links, and existing ills are left untouched.

Resolution — find the QID, STRICT priority order
------------------------------------------------
1. **Shinto wiki first.** Resolve the target on shinto.miraheze.org
   (following redirects). If the resolved page carries a
   ``{{wikidata link|Q…}}`` template, use THAT QID.
2. **Otherwise** search Wikipedias in order — en → ja → zh → ko → fr →
   de → ru — and stop at the first one that has an article matching the
   target; take that article's Wikidata item (QID).

If no QID is found anywhere, the link is left unchanged.

Build the ill from the QID (mirrors the sibling ill ops)
--------------------------------------------------------
  * First positional (title) = the Miraheze title from P11250 (value
    like ``shinto:Shisho Shrine (Toyooka)`` → strip the ``shinto:``
    prefix). If the item has no P11250, fall back to the English
    Wikidata label.
  * One ``lang|sitelink-title`` pair per Wikipedia sitelink on the item
    (sorted by lang for determinism; enwiki and sister projects
    excluded, matching ``normalize_ill_wikidata``).
  * ``lt=`` (display) = the English Wikidata label. If the item has no
    English label, ``lt=`` is omitted entirely.
  * ``qid=QID`` always.

Pacing / safety
---------------
  * Standard always-on op (strictly programmatic; not gated behind any
    env flag) — runs on every wikitext orchestrator visit.
  * PRE_HEAVY so the converted text is what ``history_offload``'s
    fandom mirror and XML archive capture in the same cycle (same as
    the other ill ops).
  * Read-only API calls (miraheze + Wikidata + the Wikipedias) are
    throttled ~0.3s and cached at module level, so the cost is bounded
    by unique targets across the whole run, not per-link.
  * ``MAX_CONVERSIONS_PER_PAGE`` caps how many links a single page visit
    will convert — conservative start; the rest get picked up on the
    next cycle's visit.
  * Any HTTP 429 trips a module-level kill switch: all further lookups
    this run short-circuit to "not found" (no retries), so the op
    cleanly stops doing network work and stops converting. Consistent
    with the repo-wide 429-bail policy.
"""

import re
import time

import requests

from ..common import REDIRECT_RE

NAME = "straggler_link_to_ill"
# Every wikitext namespace, subject and talk side — straggler links show
# up wherever prose does, not just mainspace. Matches ill_category_to_link's
# coverage. Non-wikitext namespaces (geojson 420, module 828, item 860,
# property 862) don't carry wikilinks/templates so they're excluded.
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    421, 829, 861, 863,
)
PRE_HEAVY = True

# Conservative per-page cap. A page with many straggler links is
# converted a few at a time across successive cycles rather than all at
# once — keeps any single edit small/reviewable and bounds the per-page
# network cost.
MAX_CONVERSIONS_PER_PAGE = 5

_WD_API = "https://www.wikidata.org/w/api.php"
_MIRAHEZE_API = "https://shinto.miraheze.org/w/api.php"
_USER_AGENT = "ShintoOrchestrator/1.0 (User:EmmaBot; shinto.miraheze.org)"
_HTTP_TIMEOUT = 15
_API_THROTTLE = 0.3

# Wikipedias searched, in strict priority order, when the shinto wiki
# doesn't yield a QID. Each entry is the wbgetentities ``sites`` value.
_WIKIPEDIA_ORDER = ("enwiki", "jawiki", "zhwiki", "kowiki", "frwiki", "dewiki", "ruwiki")

# Sister-project / meta sites that aren't language sitelinks in the
# {{ill}} sense (mirrors normalize_ill_wikidata).
_NON_LANGUAGE_SITES = frozenset({
    "commonswiki", "metawiki", "specieswiki", "wikidatawiki",
    "mediawikiwiki", "incubatorwiki", "outreachwiki", "testwiki",
    "test2wiki", "wikitech",
})
_NON_WIKIPEDIA_SUFFIXES = (
    "wiktionary", "wikiquote", "wikisource", "wikibooks",
    "wikinews", "wikiversity", "wikivoyage",
)

# {{wikidata link|Q...}} on a shinto-wiki page.
_WDLINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)", re.IGNORECASE)
_QID_RE = re.compile(r"^Q\d+$")

# A plain internal wikilink: [[Target]] or [[Target|Display]]. The target
# group stops at the first '|' or ']]'; no nested brackets. Display group
# is optional and stops at ']]'. We deliberately do NOT match links whose
# target contains '|' more than once or any '{' '}' — those are inside or
# around templates and are handled by the in-template masking below.
_WIKILINK_RE = re.compile(r"\[\[([^\[\]|{}\n]+?)(?:\|([^\[\]{}\n]*?))?\]\]")

# Templates whose interior must never be touched (their wikilinks are
# parameters, not stragglers). Used by the masking pass below alongside a
# generic "any {{ ... }}" mask.
_TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}")


# ── Module-level per-run caches & kill switch ──────────────────────────
# target (str) → QID (str) or None ("looked up, not found / can't use").
_target_qid_cache: "dict[str, str | None]" = {}
# QID → item-data dict {'p11250','en_label','sitelinks'} or None on fail.
_item_cache: "dict[str, dict | None]" = {}
# Once a 429 is seen, every subsequent lookup short-circuits to "not
# found" with no further network calls (repo-wide 429-bail policy).
_rate_limited = False


class _RateLimited(Exception):
    pass


def _get(url: str, params: dict) -> "dict | None":
    """Throttled GET returning parsed JSON, or None on any non-429 error.
    A 429 raises _RateLimited so callers can trip the kill switch."""
    global _rate_limited
    if _rate_limited:
        return None
    try:
        time.sleep(_API_THROTTLE)
        resp = requests.get(
            url, params=params,
            headers={"User-Agent": _USER_AGENT},
            timeout=_HTTP_TIMEOUT,
        )
    except Exception:
        return None
    if resp.status_code == 429:
        _rate_limited = True
        raise _RateLimited()
    try:
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ── Resolution: target → QID ───────────────────────────────────────────

def _qid_from_shinto(target: str) -> "str | None":
    """If `target` is (or redirects to) a shinto.miraheze.org page that
    carries {{wikidata link|Q...}}, return that QID; else None."""
    data = _get(_MIRAHEZE_API, {
        "action": "query",
        "titles": target,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "redirects": "1",
        "format": "json",
    })
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {}) or {}
    for page in pages.values():
        if "missing" in page:
            continue
        revs = page.get("revisions") or []
        if not revs:
            continue
        try:
            content = revs[0]["slots"]["main"]["*"]
        except (KeyError, IndexError, TypeError):
            continue
        m = _WDLINK_RE.search(content or "")
        if m:
            return m.group(1).upper()
    return None


def _qid_from_wikipedias(target: str) -> "str | None":
    """Search en→ja→zh→ko→fr→de→ru for an article matching `target`; return
    the first matching article's Wikidata QID, else None. Redirects are
    NOT followed — wbgetentities resolves the exact sitelink title."""
    for site in _WIKIPEDIA_ORDER:
        data = _get(_WD_API, {
            "action": "wbgetentities",
            "sites": site,
            "titles": target,
            "props": "info",
            "format": "json",
        })
        if not data:
            continue
        entities = data.get("entities", {}) or {}
        for qid, entity in entities.items():
            if qid.startswith("Q") and "missing" not in entity:
                return qid
    return None


def _resolve_qid(target: str) -> "str | None":
    """Strict priority: shinto wiki first, then the Wikipedia chain.
    Cached per-run by target string."""
    if target in _target_qid_cache:
        return _target_qid_cache[target]
    qid = _qid_from_shinto(target)
    if not qid:
        qid = _qid_from_wikipedias(target)
    _target_qid_cache[target] = qid
    return qid


# ── Item data: QID → (p11250, en_label, sitelinks) ─────────────────────

def _fetch_item(qid: str) -> "dict | None":
    """Fetch {'p11250': str|None, 'en_label': str|None,
    'sitelinks': [(lang, title), ...]} for `qid`, or None on fetch
    failure. Cached per-run."""
    if qid in _item_cache:
        return _item_cache[qid]
    data = _get(_WD_API, {
        "action": "wbgetentities",
        "ids": qid,
        "props": "sitelinks|labels|claims",
        "format": "json",
    })
    if not data:
        _item_cache[qid] = None
        return None
    entity = data.get("entities", {}).get(qid, {}) or {}
    if "missing" in entity:
        _item_cache[qid] = None
        return None

    # en label
    en_label = (entity.get("labels", {}).get("en", {}) or {}).get("value") or None

    # P11250 (first value)
    p11250 = None
    for claim in entity.get("claims", {}).get("P11250", []) or []:
        try:
            p11250 = claim["mainsnak"]["datavalue"]["value"]
        except (KeyError, TypeError):
            continue
        if p11250:
            break

    # sitelinks → [(lang, title)], filtered like normalize_ill_wikidata.
    pairs: list[tuple[str, str]] = []
    for site, info in (entity.get("sitelinks", {}) or {}).items():
        if site in _NON_LANGUAGE_SITES:
            continue
        if not site.endswith("wiki"):
            continue
        lang = site[:-4]
        if not lang or " " in lang:
            continue
        if any(lang.endswith(suf) for suf in _NON_WIKIPEDIA_SUFFIXES):
            continue
        t = (info.get("title") or "").strip()
        if t:
            pairs.append((lang, t))
    pairs.sort(key=lambda p: p[0])

    result = {"p11250": p11250, "en_label": en_label, "sitelinks": pairs}
    _item_cache[qid] = result
    return result


def _strip_shinto_prefix(p11250: str) -> str:
    """`shinto:Shisho Shrine (Toyooka)` → `Shisho Shrine (Toyooka)`."""
    if p11250.lower().startswith("shinto:"):
        return p11250[len("shinto:"):]
    return p11250


def _build_ill(item: dict) -> "str | None":
    """Build the {{ill|...}} string from item data, or None if there's
    no usable canonical title (no P11250 and no en label)."""
    p11250 = item.get("p11250")
    en_label = item.get("en_label")
    if p11250:
        canonical = _strip_shinto_prefix(p11250).strip()
    elif en_label:
        canonical = en_label.strip()
    else:
        return None
    if not canonical:
        return None

    parts = [canonical]
    for lang, t in item.get("sitelinks", []):
        parts.append(lang)
        parts.append(t)
    if en_label:
        parts.append(f"lt={en_label}")
    parts.append(f"qid={item['_qid']}")
    return "{{ill|" + "|".join(parts) + "}}"


# ── Masking: find regions that are inside templates ────────────────────

def _template_spans(text: str) -> list[tuple[int, int]]:
    """Return [(start, end), ...] character spans covered by any template
    call ``{{ ... }}`` (including nested ones). Wikilinks overlapping any
    such span are NOT stragglers — they're template parameters (ill,
    jalink, nihongo, infobox fields, …) and must be left alone.

    Computed via brace-depth scanning so nested templates are covered as
    one outer span; the conservative {{ }} regexes elsewhere only match
    flat templates, but for masking we want the full nested extent."""
    spans: list[tuple[int, int]] = []
    depth = 0
    start = -1
    i = 0
    n = len(text)
    while i < n - 1:
        two = text[i:i + 2]
        if two == "{{":
            if depth == 0:
                start = i
            depth += 1
            i += 2
            continue
        if two == "}}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                spans.append((start, i + 2))
                start = -1
            i += 2
            continue
        i += 1
    # Unbalanced trailing '{{' (no closer) — mask to end so we never
    # convert a link inside a malformed/unterminated template.
    if depth > 0 and start >= 0:
        spans.append((start, n))
    return spans


def _in_spans(pos: int, spans: list[tuple[int, int]]) -> bool:
    for s, e in spans:
        if s <= pos < e:
            return True
        if s > pos:
            break
    return False


# ── Straggler eligibility ──────────────────────────────────────────────

def _is_straggler_target(target: str) -> bool:
    """True if `target` is a plain internal article link we may convert."""
    t = target.strip()
    if not t:
        return False
    if ":" in t:                 # File:/Category:/namespace/interwiki links
        return False
    if t.startswith("#"):        # section-only link
        return False
    if "{" in t or "}" in t:
        return False
    return True


def apply(title: str, text: str):
    global _rate_limited
    if not text:
        return None, None
    if REDIRECT_RE.search(text):
        return None, None
    if _rate_limited:
        return None, None

    spans = _template_spans(text)

    # Collect candidate links (left-to-right) that are real stragglers and
    # not inside any template. We resolve + replace at most
    # MAX_CONVERSIONS_PER_PAGE of them this visit.
    replacements: list[tuple[int, int, str]] = []  # (start, end, new)
    converted = 0

    try:
        for m in _WIKILINK_RE.finditer(text):
            if converted >= MAX_CONVERSIONS_PER_PAGE:
                break
            if _in_spans(m.start(), spans):
                continue
            target = (m.group(1) or "").strip()
            if not _is_straggler_target(target):
                continue

            qid = _resolve_qid(target)
            if not qid or not _QID_RE.match(qid):
                continue
            item = _fetch_item(qid)
            if not item:
                continue
            item = dict(item)
            item["_qid"] = qid
            ill = _build_ill(item)
            if not ill:
                continue
            replacements.append((m.start(), m.end(), ill))
            converted += 1
    except _RateLimited:
        # Kill switch tripped mid-page. Apply whatever we resolved before
        # the 429 (those calls already succeeded), then stop.
        pass

    if not replacements:
        return None, None

    # Apply right-to-left so earlier offsets stay valid.
    new_text = text
    for start, end, repl in reversed(replacements):
        new_text = new_text[:start] + repl + new_text[end:]

    if new_text == text:
        return None, None
    return new_text, (
        f"convert {len(replacements)} straggler wikilink(s) to {{{{ill}}}} "
        f"(resolved via Wikidata)"
    )
