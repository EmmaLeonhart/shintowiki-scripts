"""
normalize_ill_wikidata op
==========================
Rewrites messy ``{{ill|...}}`` templates back to a canonical clean form
by pulling the language/title pairs straight from Wikidata via the
template's ``qid=`` parameter.

Messy form (what import / hand-editing leaves behind)::

    {{ill|Northern Dynasties|ja|北朝|12=simple|13=User:Immanuelle/Northern Court (Japan)|comment=changed title based on wikidata|qid=Q1207446}}

Canonical form (what this op produces)::

    {{ill|Northern Dynasties|ja|北朝|ko|북조|vi|Bắc triều|zh|北朝 (消歧義)|zh_classical|北朝|zh_yue|北朝|qid=Q1207446}}

i.e. ``positional[0]`` (enwiki target) + every Wikidata language sitelink
sorted alphabetically by language code (enwiki excluded — already the
positional) + ``qid=`` + ``lt=`` (if present, kept verbatim, placed last).

Two modes:

**A. Has ``qid=Q\\d+`` and at least one "junk" param/positional.**
Rebuild from the QID's Wikidata sitelinks. This is the original path.

**B. No qid but has ≥1 ``lang|target`` positional pair.** Query every
pair against Wikidata via ``wbgetentities?sites=<lang>wiki&titles=…``
to discover which QID each interwiki points to, then:

  * Exactly 1 unique QID resolved → use it, continue with mode A's
    rebuild (positional[0] / last ``1=`` stays + replace interwikis
    with sitelinks from that QID).
  * 2+ unique QIDs resolved → leave the template structure as-is but
    append ``|consistent_qid=false``. The disagreement gets surfaced
    for human review; the bot doesn't pick a winner.
  * 0 resolved → no-op. No signal to act on.

A ``1=`` override, if present, is treated as authoritative for the
new positional[0] — MW resolves last-wins on duplicate names, so we
do the same. Per user directive (2026-05-12), a ``redirects to``
substring in the body is NOT a disqualifier when a qid is present:
the qid is treated as sufficient evidence the link is correct.

Mode B is the same consistency rule that ``wikidata_lookup`` applies
to ``{{wikidata link}}`` templates, just extended to ``{{ill}}``. The
two ops share ``_resolve_qid_from_sitelink`` and its per-run cache so
the API cost is bounded by unique (lang, target) pairs across the
whole run, not per-template.

Transformation:
  1. Determine effective positional[0]: if ``1=`` is named (any number
    of times), use the LAST value; otherwise keep the bare positional[0].
  2. Discard every other positional + every named param except ``qid=``
    and ``lt=``.
  3. Fetch sitelinks for the QID from Wikidata.
  4. Emit (lang, title) pairs sorted alphabetically by lang code,
    excluding ``enwiki`` (already the positional) and sister-project
    sites (Commons, Wiktionary, Wikiquote, etc.). Underscored lang
    codes (``zh_classical``, ``zh_yue``) ARE included — those are
    distinct languages on Wikipedia and the user's spec calls for them.
  5. Append ``qid=Q...``, then ``lt=...`` if present.

Gated on ``ENABLE_NORMALIZE_ILL_WIKIDATA=1`` so the per-cycle Wikidata
API churn isn't on by default. Per-run cache means each unique QID
costs at most one API call regardless of how many pages reference it
within the same orchestrator run.

PRE_HEAVY so the cleaned text is what fandom_mirror and history_offload's
XML archive capture inside the same cycle.
"""

import os
import re
import time

import requests

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
_USER_AGENT = "ShintoOrchestrator/1.0 (User:EmmaBot; shinto.miraheze.org)"
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
            headers={"User-Agent": _USER_AGENT},
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


def apply(title: str, text: str):
    if os.getenv("ENABLE_NORMALIZE_ILL_WIKIDATA") != "1":
        return None, None
    if not text:
        return None, None
    if REDIRECT_RE.search(text):
        return None, None

    edits = 0
    fetch_failed = 0
    flagged_inconsistent = 0

    def _extract_lang_pairs(positional: list[str]) -> list[tuple[str, str]]:
        """Read positional[1:] as alternating lang|title pairs.
        Trailing orphan (odd count) is dropped — matches MW's behaviour
        for ``{{ill}}``'s pair slots."""
        pairs: list[tuple[str, str]] = []
        i = 1
        while i + 1 < len(positional):
            lang = positional[i].strip()
            target = positional[i + 1].strip()
            if lang and target:
                pairs.append((lang, target))
            i += 2
        return pairs

    def replacer(match: "re.Match[str]") -> str:
        nonlocal edits, fetch_failed, flagged_inconsistent
        body = match.group(1)
        positional, named = _parse_ill_body(body)
        qid = named.get("qid", "").strip()

        # Mode B: no qid → try to resolve from interwiki pairs.
        if not _QID_RE.fullmatch(qid):
            pairs = _extract_lang_pairs(positional)
            if not pairs:
                return match.group(0)
            resolved: set[str] = set()
            had_fetch_failure = False
            for (lang, target) in pairs:
                r = wikidata_lookup._resolve_qid_from_sitelink(lang, target)
                # _resolve_qid_from_sitelink returns None for "no entity"
                # AND for "fetch failed" — we can't tell them apart at
                # this layer. Continue collecting; an empty resolved set
                # falls through to the no-op branch which is the right
                # behaviour either way.
                if r:
                    resolved.add(r)
            if len(resolved) == 1:
                qid = next(iter(resolved))
                # Fall through to Mode A's rebuild path with the new qid.
                # We intentionally inject qid into `named` so the rebuild
                # code below treats this consistently with Mode A.
                named = dict(named)
                named["qid"] = qid
            elif len(resolved) > 1:
                # Disagreement: flag and leave structure alone.
                if named.get("consistent_qid") == "false":
                    return match.group(0)  # already flagged
                new_body = body.rstrip().rstrip("|") + "|consistent_qid=false"
                flagged_inconsistent += 1
                return "{{ill|" + new_body + "}}"
            else:
                return match.group(0)

        # Mode A (or fall-through from B with a resolved qid): rebuild.
        # Cost gate: skip already-clean templates. "Clean" means: at
        # most one positional, and named keys ⊆ {qid, lt}.
        junk_named = {k for k in named if k not in ("qid", "lt")}
        extra_positional = len(positional) > 1
        if not junk_named and not extra_positional:
            return match.group(0)

        # Resolve effective positional[0]: a 1= override wins (MW
        # last-wins is already what _parse_ill_body gives us — a plain
        # dict overwrites duplicate keys).
        if "1" in named and named["1"].strip():
            effective_positional = named["1"].strip()
        elif positional and positional[0].strip():
            effective_positional = positional[0]
        else:
            return match.group(0)

        sitelinks = _fetch_sitelinks(qid)
        if sitelinks is None:
            fetch_failed += 1
            return match.group(0)

        new_parts: list[str] = [effective_positional]
        for lang, t in sitelinks:
            new_parts.append(lang)
            new_parts.append(t)
        new_parts.append(f"qid={qid}")
        if "lt" in named:
            new_parts.append(f"lt={named['lt']}")
        edits += 1
        return "{{ill|" + "|".join(new_parts) + "}}"

    new_text = ILL_RE.sub(replacer, text)
    if new_text == text:
        return None, None
    bits: list[str] = []
    if edits:
        bits.append(f"normalize {edits} {{{{ill}}}} call(s) from Wikidata sitelinks")
    if flagged_inconsistent:
        bits.append(
            f"flag {flagged_inconsistent} {{{{ill}}}} call(s) consistent_qid=false (interwikis disagree)"
        )
    if fetch_failed:
        bits.append(f"{fetch_failed} skipped (Wikidata fetch failed)")
    return new_text, "; ".join(bits)
