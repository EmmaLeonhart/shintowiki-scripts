"""
grokipedia_link op
==================
Mainspace only. Probes ``https://grokipedia.com/page/<slug>`` to decide
whether the visited shintowiki page has a corresponding Grokipedia
article, and stamps the result onto the page's ``{{wikidata link|...}}``
template as a **named parameter** so the next cycle can skip the probe:

* Grokipedia HAS the page → set ``|grok=<canonical-slug>``.
* Grokipedia does NOT have the page (every casing probe returned 404) →
  set ``|grok=none`` (the literal sentinel ``none``, NOT empty). Empty
  ``grok=`` is treated by MediaWiki the same way as a missing parameter,
  so the template can't distinguish "checked, no article" from "never
  checked" if the slot is empty.
* Transient error / inconclusive (5xx, timeout, mixed) → no-op for this
  visit; re-probe next cycle.
* Legacy ``|grok=`` (empty) markers from before the sentinel switch get
  rewritten to ``|grok=none`` on re-visit (no re-probe — the original
  "missing" determination is preserved).

Categorisation is handled by ``Template:Wikidata link`` itself, NOT by
this op. The template emits one of three categories based on the
``grok`` parameter state (configured by
``configure_wikidata_link_grok_categories.py``):

* ``grok=<slug>`` (any non-empty value other than ``none``) → ``[[Category:Pages with Grokipedia links]]``
* ``grok=none`` → ``[[Category:Pages without Grokipedia links]]``
* no ``grok`` parameter at all, OR ``grok=`` empty → ``[[Category:Pages to be checked for Grokipedia]]``

So this op only sets the param state; the template propagates the
visible classification. That's why the missing case stamps the literal
sentinel ``none`` — MediaWiki collapses ``grok=`` (empty) into the
same state as "no parameter passed", so an empty present ``grok`` slot
CANNOT be distinguished from "we haven't checked yet". The ``none``
sentinel is the **positive marker** for "we checked, nothing on
Grokipedia".

The named-param shape is deliberate: Grokipedia is NOT a language wiki,
so modelling it as one of the positional ``lang|title`` pairs would
(a) misrepresent its semantics and (b) get wiped on every Phase-2
sitelinks refresh in ``wikidata_lookup`` (which replaces the entire
pair list with whatever Wikidata reports for the QID — Grokipedia is
never in that set). Named params, by contrast, survive
``wikidata_lookup`` untouched (it preserves ``named`` via
``dict(named)`` and only mutates ``check_date`` and ``consistent_qid``).

Grokipedia is case-sensitive (verified 2026-05-26: ``Tokyo`` → 200,
``tokyo`` → 404; ``yamato_no_kuni_no_miyatsuko`` → 200,
``Yamato_no_Kuni_no_Miyatsuko`` → 404). There is NO predictable casing
convention — articles are stored in whatever case they were created
with. So we try the shintowiki title verbatim first, then the
all-lowercase form, and use whichever resolves.

Why PRE_HEAVY: runs in the same pre-heavy phase as ``wikidata_lookup``
so the ``grok=`` named param lands in the cycle's single combined save
and is captured by ``history_offload``'s fandom mirror / XML archive
in the same cycle. Ordering relative to ``wikidata_lookup`` no longer
matters for correctness (named params survive Phase 2), but we still
place it AFTER ``wikidata_lookup`` so the ``check_date`` Wikidata stamps
is always present before we touch the template.

Skip gates (cheap, run before the HTTP probe):
* page is a redirect
* ``grok`` named param already present AND non-empty (either a real
  slug or the ``none`` sentinel — both mean "checked, here's the
  result"). Empty ``grok=`` is NOT a skip — it triggers the legacy
  rewrite to ``grok=none``.
* no ``{{wikidata link}}`` template at all (we'd have no place to cache
  the result, and re-probing every cycle would hammer grokipedia.com —
  the explicit user concern)

Per-page cost: 1–2 HTTPS probes against grokipedia.com on the first
visit, then 0 forever (the ``grok`` param is on the page after). Throttled
to keep load on grokipedia.com gentle.
"""

import datetime
import re
import time
import urllib.parse
from shinto_miraheze.ua_contact import contact

import requests

from ..common import REDIRECT_RE

NAME = "grokipedia_link"
NAMESPACES = (0,)  # mainspace ONLY — by explicit user directive
PRE_HEAVY = True

_GROK_URL_BASE = "https://grokipedia.com/page/"
_HTTP_TIMEOUT = 10
_PROBE_THROTTLE = 0.3

# User-agent owner contact rotation (per user directive 2026-05-26).
# Initial contact is the gmail address; one week from the op-launch date,
# switch to the custom-domain address (which the user expects to have
# live by then). The switchover is automatic so we don't have to remember
# to swap it back manually.
_UA_OWNER_NAME = "Emma Leonhart"
_UA_CONTACT_INITIAL = f"{contact('miraheze')}"
_UA_CONTACT_AFTER = f"{contact('miraheze')}"
_UA_SWITCHOVER_DATE = datetime.date(2026, 6, 2)  # 2026-05-26 + 7 days


def _user_agent() -> str:
    contact = (
        _UA_CONTACT_AFTER
        if datetime.date.today() >= _UA_SWITCHOVER_DATE
        else _UA_CONTACT_INITIAL
    )
    return (
        f"Mozilla/5.0 (compatible; ShintoOrchestrator/1.0; "
        f"owner={_UA_OWNER_NAME} <{contact}>; "
        f"+https://shinto.miraheze.org User:EmmaBot)"
    )


WD_LINK_RE = re.compile(
    r"\{\{\s*wikidata\s*link\s*((?:\|[^{}]*)*)\}\}",
    re.IGNORECASE,
)


def _parse_wd_params(raw: str) -> tuple[str, list[tuple[str, str]], dict[str, str]]:
    """Same splitter shape as wikidata_lookup uses: positional [Q, lang,
    title, lang, title, ...] plus named ``key=value`` parameters."""
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


def _probe(slug: str) -> str:
    """Returns 'exists', 'missing', or 'error'."""
    url = _GROK_URL_BASE + urllib.parse.quote(slug, safe="_-")
    try:
        time.sleep(_PROBE_THROTTLE)
        resp = requests.head(
            url,
            headers={"User-Agent": _user_agent()},
            timeout=_HTTP_TIMEOUT,
            allow_redirects=False,
        )
    except Exception:
        return "error"
    code = resp.status_code
    if code == 200:
        return "exists"
    if code == 404:
        return "missing"
    return "error"


def _find_canonical_slug(title: str) -> tuple["str | None", str]:
    """Probe Grokipedia for the page corresponding to ``title``.

    Returns (slug, status) where:
      * status == 'exists': slug is the form that returned 200.
      * status == 'missing': slug is None; every candidate returned 404.
      * status == 'error': slug is None; at least one probe was
        inconclusive (5xx, timeout, etc.) and none returned 200.
    """
    underscored = title.replace(" ", "_")
    candidates = [underscored]
    lower = underscored.lower()
    if lower != underscored:
        candidates.append(lower)

    all_missing = True
    for slug in candidates:
        status = _probe(slug)
        if status == "exists":
            return slug, "exists"
        if status != "missing":
            all_missing = False

    return None, ("missing" if all_missing else "error")


def apply(title: str, text: str):
    if not text:
        return None, None
    if REDIRECT_RE.search(text):
        return None, None

    wd_match = WD_LINK_RE.search(text)
    if not wd_match:
        # No template to cache into. Skip to avoid hammering Grokipedia
        # for the same page every cycle (the user's stated concern).
        return None, None

    qid, pairs, named = _parse_wd_params(wd_match.group(1))
    existing_grok = named.get("grok")

    # Skip when the slot is already conclusively filled:
    #   * a non-empty value that isn't the legacy empty marker — either a
    #     real slug or the new "none" sentinel.
    if existing_grok is not None and existing_grok != "":
        return None, None

    # Legacy `grok=` (empty) markers from earlier runs are no longer
    # interpreted by Template:Wikidata link the way we wanted — MediaWiki
    # treats `grok=` as if the param weren't passed, so those pages fall
    # into "to be checked" instead of "without Grokipedia links". Rewrite
    # the empty marker to the explicit sentinel `none` without re-probing
    # Grokipedia (the missing determination from the original run is
    # still authoritative; if Grokipedia adds the article later, a human
    # can clear the param to force a re-check).
    if existing_grok == "":
        new_named: dict[str, str] = {"grok": "none"}
        for key, value in named.items():
            if key != "grok":
                new_named[key] = value
        new_template = _build_wd_template(qid, pairs, new_named)
        new_text = text[: wd_match.start()] + new_template + text[wd_match.end() :]
        return new_text, "rewrite legacy empty grok= to grok=none"

    # No grok param at all → probe Grokipedia.
    slug, status = _find_canonical_slug(title)
    if status == "error":
        return None, None

    # Insert grok= as the first named param so it appears prominently in
    # the wikitext. wikidata_lookup will not touch it on future cycles —
    # it only mutates check_date / consistent_qid. The value is either
    # the canonical Grokipedia slug (status == 'exists') or the literal
    # sentinel 'none' (status == 'missing'); Template:Wikidata link's
    # conditional categorisation reads the param state to emit one of
    # three tracking categories.
    grok_value = slug if status == "exists" else "none"
    new_named = {"grok": grok_value}
    for key, value in named.items():
        if key != "grok":
            new_named[key] = value
    new_template = _build_wd_template(qid, pairs, new_named)
    new_text = text[: wd_match.start()] + new_template + text[wd_match.end() :]
    if status == "exists":
        return new_text, f"add grok={slug} to wikidata link (Grokipedia)"
    return new_text, "set grok=none (no Grokipedia article)"
