"""
normalize_ill_wikidata op
==========================
Rewrites messy ``{{ill|...}}`` calls back to a clean, predictable
form. The wiki accumulated a lot of ill-template junk over time — bad
import patterns, hand-editing, partially-completed migrations — and
this op is the centralised cleanup.

What "messy" looks like (real example)::

    {{ill|Ame-no-Fuyukinu|en|12=simple|13=User:Immanuelle/Ame-no-Fuyukinu|qq=}}

What this op produces (no QID resolvable)::

    {{ill|Ame-no-Fuyukinu|en|Ame-no-Fuyukinu}}

What this op produces (QID resolved)::

    {{ill|Ame-no-Fuyukinu|<sorted sitelinks>|qid=Q…}}

Three modes, in priority order:

**Mode A. ``qid=Q\\d+`` is already on the call.**
Fetch the QID's Wikidata sitelinks and REPLACE the existing pair list
with them (capped at MAX_PAIRS, alphabetical by lang). Existing pairs
are not preserved — the template is treated as a derived view of the
QID's sitelinks. Failure handling: if the sitelinks fetch fails
(network/parse), keep the existing call untouched; only a successful
fetch authorises rewriting.

**Mode B. No qid, has ≥1 cleaned ``lang|target`` pair.** Query every
cleaned pair against Wikidata to discover which QID each resolves to:

  * 1 unique QID → use it, continue with Mode A's rebuild.
  * 2+ unique QIDs → cleaned form + ``|consistent_qid=false`` flag so
    the disagreement is visible.
  * 0 resolved → fall through to Mode C.

**Mode C. No qid resolvable.** Emit the cleaned form anyway (drop
junk, make pairs explicit). This is the path that catches the
``{{ill|Foo|en|12=simple|13=User:Foo}}`` case shown above — Wikidata
has nothing to anchor to, but we still want the bad pattern gone.

Cleanups applied across all modes:

  * **Numeric-named keys (12=, 13=, …) are dropped wholesale.** Per
    user direction (2026-05-14), every such pattern on the wiki came
    from an early import mistake; there are no legitimate uses to
    preserve. Bare positionals (positional[1], positional[2], …) are
    still treated as the real interwiki pair sequence — only the
    NAMED numeric overrides get stripped.
  * **Empty target → canonical fallback.** ``{{ill|Foo|en}}`` (no
    positional[2]) becomes ``{{ill|Foo|en|Foo}}``. MW already
    resolves the implicit form to the same thing; making it explicit
    makes the wikitext easier to read and reason about.
  * **Bogus targets dropped.** Pairs whose target hits a placeholder
    namespace prefix (``User:``, ``Talk:``, ``Special:``, etc.) are
    excluded. Wikipedia interlangs require article-namespace targets.
  * **Noise named params dropped.** Only ``qid``, ``lt``, and
    ``consistent_qid`` are kept; everything else (``qq=``,
    ``comment=``, ``ja_comment=``, ``check_date=``, the various junk
    markers) is discarded.

The ``1=`` positional-1 override is handled by the sibling
``normalize_ill_positional`` op; this op runs after it in the OPS
list, so by the time we get a call, any ``1=`` has already been
resolved into the bare positional[0].

Mode B shares ``_resolve_qid_from_sitelink`` (and its per-run cache)
with ``wikidata_lookup`` so the API cost is bounded by unique
(lang, target) pairs across the whole run, not per-template.

Gated on ``ENABLE_NORMALIZE_ILL_WIKIDATA=1`` so the per-cycle API
churn isn't on by default. PRE_HEAVY so the cleaned text is what
``fandom_mirror`` and ``history_offload``'s XML archive capture in
the same cycle.
"""

import os
import re
import time

import requests

from shinto_miraheze.ua_for import ua_for

from . import wikidata_lookup
from ..common import REDIRECT_RE

NAME = "normalize_ill_wikidata"
NAMESPACES = (0,)
PRE_HEAVY = True

# Conservative pattern (matches the other ill-related ops): the body
# cannot contain nested {...} braces. Calls with nested templates inside
# the body are left untouched.
ILL_RE = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)
_QID_RE = re.compile(r"^Q\d+$")

_WD_API = "https://www.wikidata.org/w/api.php"
# _USER_AGENT removed 2026-08-19: the request sites now resolve the agent from the URL via
# ua_for(), so this hand-built literal was dead and could only drift. Was: _USER_AGENT = "ShintoOrchestrator/1.0 (User:EmmaBot; shinto.miraheze.org)"
_HTTP_TIMEOUT = 15
_API_THROTTLE = 0.3

# Sister-project / meta sites that aren't language sitelinks in the
# {{ill}} sense.
_NON_LANGUAGE_SITES = frozenset({
    "commonswiki", "metawiki", "specieswiki", "wikidatawiki",
    "mediawikiwiki", "incubatorwiki", "outreachwiki", "testwiki",
    "test2wiki", "wikitech",
})
# Project suffixes that aren't Wikipedia (Wikiquote, Wikisource, ...).
# Each is the trailing portion of the site key, e.g. ``enwiktionary``
# ends in ``wiktionary``. ``wiki`` itself isn't in this list — that's
# the suffix we want.
_NON_WIKIPEDIA_SUFFIXES = (
    "wiktionary", "wikiquote", "wikisource", "wikibooks",
    "wikinews", "wikiversity", "wikivoyage",
)

# Per-run cache: QID → list[(lang, title)]. Module-level so all pages
# within a single orchestrator run share the lookup.
_sitelinks_cache: "dict[str, list[tuple[str, str]] | None]" = {}


def _fetch_sitelinks(qid: str) -> "list[tuple[str, str]] | None":
    """Return [(lang, title), ...] sorted by lang, or None if the
    Wikidata fetch failed. Empty list means the entity exists but has
    no usable language sitelinks (rare). enwiki and sister-project
    sitelinks are filtered out here."""
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
        _sitelinks_cache[qid] = []
        return []
    sitelinks = entity.get("sitelinks", {}) or {}
    pairs: list[tuple[str, str]] = []
    for site, info in sitelinks.items():
        if site in _NON_LANGUAGE_SITES:
            continue
        if not site.endswith("wiki"):
            continue
        # Strip trailing "wiki" suffix to recover the lang code.
        lang = site[:-4]
        if not lang:
            continue
        # Drop sister projects (lang ends with wiktionary/wikiquote/...).
        if any(lang.endswith(suf) for suf in _NON_WIKIPEDIA_SUFFIXES):
            continue
        # Drop enwiki — already the bare positional.
        if lang == "en":
            continue
        # Disallow spaces; underscores ARE allowed (zh_classical etc.).
        if " " in lang:
            continue
        target = (info.get("title") or "").strip()
        if target:
            pairs.append((lang, target))
    pairs.sort(key=lambda p: p[0])
    _sitelinks_cache[qid] = pairs
    return pairs


def _parse_ill_body(body: str) -> tuple[list[str], dict[str, str]]:
    """Return (positional, named). Whitespace inside values is preserved
    (matches MW behaviour); keys are stripped because MW resolves names
    after trimming."""
    positional: list[str] = []
    named: dict[str, str] = {}
    for p in body.split("|"):
        if "=" in p:
            k, _, v = p.partition("=")
            named[k.strip()] = v
        else:
            positional.append(p)
    return positional, named


_NUMERIC_KEY_RE = re.compile(r"^\d+$")


def _strip_numeric_named(named: dict[str, str]) -> dict[str, str]:
    """Drop every numeric-named key (1=, 2=, ..., 12=, 13=, ...).

    Per user direction (2026-05-14): every `12=simple|13=User:Foo|...`
    pattern on the wiki originated from an early import mistake that
    applied broadly. There are no legitimate uses to preserve, so we
    just discard them wholesale during normalization rather than try
    to validate each pair individually. Bare positionals
    (positional[1], positional[2], ...) are still treated as the
    real interwiki pair sequence — only the numeric-NAMED overrides
    are dropped.

    `1=` would have already been promoted into positional[0] by the
    sibling `normalize_ill_positional` op when present alongside a
    qid; in the no-qid path it's left alone as a deliberate human
    note. Dropping it here would conflict with that policy, so the
    op is run *before* normalize_ill_positional in the orchestrator
    OPS list — which means by the time this op gets a call, any
    `1=` has already been resolved.
    """
    return {k: v for k, v in named.items() if not _NUMERIC_KEY_RE.match(k)}


# Targets we know are placeholders / wrong namespaces for an interlang
# link. User:Immanuelle/X is the canonical case — a draft holding-page
# on miraheze that prior scripts wrote into ill calls when they had no
# real interwiki target. The simple/Wikipedia-site interlangs require
# article-namespace targets, never User:/Talk:/Special:/etc.
_BOGUS_PREFIXES = (
    "User:", "User talk:", "Talk:", "Special:",
    "File talk:", "Category talk:", "Template talk:",
    "Module talk:", "Help talk:", "MediaWiki talk:",
    "Project talk:",
)


def _is_bogus_target(target: str) -> bool:
    return target.startswith(_BOGUS_PREFIXES)


def _extract_clean_pairs(
    positional: list[str],
    canonical_title: str,
) -> list[tuple[str, str]]:
    """Walk positional[1:] as alternating (lang, title) pairs. Two
    cleanups applied per pair:

    * **Empty title → canonical fallback.** ``{{ill|Foo|en}}`` (with no
      positional[2]) is MW shorthand for "use Foo as the en title", so
      we make it explicit: the pair becomes (en, Foo). This is the
      "make calls more understandable" piece — readers shouldn't have
      to know the implicit fallback.
    * **Bogus targets dropped.** A pair whose target hits
      ``_is_bogus_target`` is excluded from the result entirely.
    """
    pairs: list[tuple[str, str]] = []
    i = 1
    n = len(positional)
    while i < n:
        lang = positional[i].strip()
        target = positional[i + 1].strip() if i + 1 < n else ""
        if lang:
            if not target:
                target = canonical_title
            if not _is_bogus_target(target):
                pairs.append((lang, target))
        i += 2
    return pairs


# Named params we keep on the cleaned output. Everything else (qq=,
# comment=, ja_comment=, the various junk markers prior scripts left
# behind, and any numeric-named keys consumed by _full_positional)
# is dropped.
_KEEP_NAMED = ("qid", "lt", "consistent_qid")


def _emit_clean_call(
    canonical: str,
    pairs: list[tuple[str, str]],
    named: dict[str, str],
) -> str:
    parts: list[str] = [canonical]
    for lang, target in pairs:
        parts.append(lang)
        parts.append(target)
    for key in _KEEP_NAMED:
        v = named.get(key, "").strip() if key != "lt" else named.get(key, "")
        if v:
            parts.append(f"{key}={v}")
    return "{{ill|" + "|".join(parts) + "}}"


def apply(title: str, text: str):
    if os.getenv("ENABLE_NORMALIZE_ILL_WIKIDATA") != "1":
        return None, None
    if not text:
        return None, None
    if REDIRECT_RE.search(text):
        return None, None

    edits_from_sitelinks = 0
    cleaned_no_resolve = 0
    fetch_failed = 0
    flagged_inconsistent = 0

    def replacer(match: "re.Match[str]") -> str:
        nonlocal edits_from_sitelinks, cleaned_no_resolve
        nonlocal fetch_failed, flagged_inconsistent
        body = match.group(1)
        positional, named = _parse_ill_body(body)

        # Need a canonical title to anchor the rest.
        if not positional or not positional[0].strip():
            return match.group(0)
        canonical = positional[0].strip()

        # Drop numeric-named keys wholesale (per user direction — see
        # `_strip_numeric_named` docstring) AND drop empty-value
        # markers (qq=, etc.). consistent_qid is the one named param
        # where empty is meaningful — the existing flag logic uses
        # "false" so empty would be malformed anyway.
        named_clean = _strip_numeric_named(named)
        named_clean = {
            k: v for k, v in named_clean.items()
            if v.strip() or k == "consistent_qid"
        }

        cleaned_pairs = _extract_clean_pairs(positional, canonical)
        qid = named_clean.get("qid", "").strip()

        # Mode A: existing qid → fetch sitelinks and replace the pair
        # list wholesale. Same semantics as the wikidata_lookup op for
        # {{wikidata link}}: the template is a derived view of Wikidata.
        if _QID_RE.fullmatch(qid):
            sitelinks = _fetch_sitelinks(qid)
            if sitelinks is None:
                fetch_failed += 1
                return match.group(0)
            new_named = {"qid": qid}
            if "lt" in named_clean:
                new_named["lt"] = named_clean["lt"]
            new_call = _emit_clean_call(canonical, sitelinks, new_named)
            if new_call != match.group(0):
                edits_from_sitelinks += 1
            return new_call

        # Mode B: no qid → try to resolve via the cleaned interwiki pairs.
        # _resolve_qid_from_sitelink returns None for both "no entity"
        # and "fetch failed"; we can't distinguish, so an empty set
        # falls through to Mode C (cleanup) which is the right
        # behaviour either way.
        resolved: set[str] = set()
        for (lang, target) in cleaned_pairs:
            r = wikidata_lookup._resolve_qid_from_sitelink(lang, target)
            if r:
                resolved.add(r)

        if len(resolved) == 1:
            new_qid = next(iter(resolved))
            sitelinks = _fetch_sitelinks(new_qid)
            if sitelinks is None:
                fetch_failed += 1
                return match.group(0)
            new_named = {"qid": new_qid}
            if "lt" in named_clean:
                new_named["lt"] = named_clean["lt"]
            new_call = _emit_clean_call(canonical, sitelinks, new_named)
            if new_call != match.group(0):
                edits_from_sitelinks += 1
            return new_call

        if len(resolved) > 1:
            # Interwikis disagree — flag and emit cleaned form so the
            # disagreement stays visible after junk-pair pruning.
            new_named = dict(named_clean)
            new_named["consistent_qid"] = "false"
            new_call = _emit_clean_call(canonical, cleaned_pairs, new_named)
            if new_call != match.group(0):
                flagged_inconsistent += 1
            return new_call

        # Mode C: 0 resolved, no Wikidata anchor available. Emit the
        # cleaned form with bogus pairs dropped, empty titles
        # substituted with the canonical, and noise named params
        # discarded. This is what makes {{ill|Foo|en|12=simple|13=
        # User:Foo|qq=}} collapse to {{ill|Foo|en|Foo}} — explicit
        # lang|title pairs even when the title would default to
        # positional[0], for downstream readability.
        new_call = _emit_clean_call(canonical, cleaned_pairs, named_clean)
        if new_call != match.group(0):
            cleaned_no_resolve += 1
        return new_call

    new_text = ILL_RE.sub(replacer, text)
    if new_text == text:
        return None, None
    bits: list[str] = []
    if edits_from_sitelinks:
        bits.append(
            f"sync {edits_from_sitelinks} {{{{ill}}}} call(s) from Wikidata sitelinks"
        )
    if cleaned_no_resolve:
        bits.append(
            f"clean {cleaned_no_resolve} {{{{ill}}}} call(s) "
            f"(drop bogus pairs / make implicit en pair explicit)"
        )
    if flagged_inconsistent:
        bits.append(
            f"flag {flagged_inconsistent} {{{{ill}}}} call(s) consistent_qid=false (interwikis disagree)"
        )
    if fetch_failed:
        bits.append(f"{fetch_failed} skipped (Wikidata fetch failed)")
    return new_text, "; ".join(bits)
