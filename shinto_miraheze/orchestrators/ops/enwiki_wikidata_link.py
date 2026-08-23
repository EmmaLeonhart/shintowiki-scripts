"""
enwiki_wikidata_link op
========================
For Template-namespace pages, looks up ``Template:<same-name>`` on
en.wikipedia.org via the MediaWiki API. If a same-named enwiki template
exists, makes sure the shintowiki page carries a
``{{wikidata link|QID|en|<TemplateName>}}`` template with the en pair
folded in (and the QID populated from enwiki's pageprops/wikibase_item
when our slot is still empty).

Behaviour
---------
* Same-named enwiki template doesn't exist → no-op.
* Page already has ``{{wikidata link|...}}`` → parse it, add the
  ``(en, <TemplateName>)`` pair if not already present, fill in the
  QID slot if it was empty. **Existing QIDs are never overwritten** —
  the local QID wins on disagreement.
* Page has no ``{{wikidata link|...}}`` → create one with the QID +
  en pair. Inserted inside the page's existing ``<noinclude>`` block
  (or a fresh trailing one) so the wikidata notice doesn't cascade
  into every page that transcludes the template — same convention
  ``wikidata_link.py`` uses for ``[[Category:Templates missing
  wikidata]]``.

Why pre-heavy
-------------
Marked ``PRE_HEAVY = True`` so the consolidated text is what
``history_offload``'s fandom mirror and XML archive snapshots capture
in the same cycle, rather than waiting for a follow-up cycle to
propagate the wikidata link into the offloaded copy.

Safety gate
-----------
Disabled unless ``ENABLE_ENWIKI_WIKIDATA_LINK=1``. Each visit costs one
HTTP round-trip to en.wikipedia.org, and we want a kill switch in case
the enwiki API rate-limits or the template-name heuristic produces
false positives on a particular cycle.
"""

import os
import re

import requests

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_for import ua_for

from ..common import REDIRECT_RE

NAME = "enwiki_wikidata_link"
NAMESPACES = (10,)
PRE_HEAVY = True

WD_LINK_RE = re.compile(
    r"\{\{\s*wikidata\s*link\s*((?:\|[^{}]*)*)\}\}",
    re.IGNORECASE,
)
_NOINCLUDE_BLOCK_RE = re.compile(
    r"<noinclude\s*>(?P<body>.*?)</noinclude\s*>",
    re.IGNORECASE | re.DOTALL,
)

_ENWIKI_API = "https://en.wikipedia.org/w/api.php"
# _USER_AGENT removed 2026-08-19: the request sites now resolve the agent from the URL via
# ua_for(), so this hand-built literal was dead and could only drift. Was: _USER_AGENT = "ShintoOrchestrator/1.0 (User:EmmaBot; shinto.miraheze.org)"
_HTTP_TIMEOUT = 10


def _parse_wd_params(raw: str) -> tuple[str, list[tuple[str, str]]]:
    """Split ``|Q|lang|title|lang|title...`` into (qid, pairs).

    A trailing orphan (odd number of pair slots) is dropped — the template
    expects language/title pairs, so a lone trailing value means the source
    was already malformed.
    """
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
    for lang, title in pairs:
        parts.append(lang)
        parts.append(title)
    return "{{wikidata link|" + "|".join(parts) + "}}"


def _insert_in_noinclude(text: str, snippet: str) -> str:
    """Insert ``snippet`` inside the first existing ``<noinclude>`` block,
    or append a fresh block containing it at the end of the page."""
    match = _NOINCLUDE_BLOCK_RE.search(text)
    if match:
        body = match.group("body")
        new_body = body.rstrip("\n") + f"\n{snippet}\n"
        return text[: match.start("body")] + new_body + text[match.end("body") :]
    sep = "" if text.endswith("\n") else "\n"
    return f"{text}{sep}<noinclude>\n{snippet}\n</noinclude>\n"


def _check_enwiki_template(template_name: str) -> tuple[bool, str | None]:
    """Returns (exists, qid).

    ``exists`` is True only when the enwiki page is a real article, not a
    redirect or missing entry. ``qid`` is the wikibase_item if available,
    None otherwise. Network failure also returns (False, None) so the op
    cleanly no-ops on transient errors.
    """
    full_title = f"Template:{template_name}"
    try:
        resp = requests.get(
            _ENWIKI_API,
            params={
                "action": "query",
                "titles": full_title,
                "prop": "pageprops|info",
                "ppprop": "wikibase_item",
                "format": "json",
            },
            headers={"User-Agent": ua_for(_ENWIKI_API)},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return False, None

    pages = data.get("query", {}).get("pages", {}) or {}
    if not pages:
        return False, None
    page = next(iter(pages.values()))
    if "missing" in page:
        return False, None
    if "redirect" in page:
        # Could chase the redirect, but cleaner to wait for the redirect
        # to be resolved at the source rather than aliasing two enwiki
        # template names onto our page.
        return False, None
    qid = page.get("pageprops", {}).get("wikibase_item")
    return True, qid


def apply(title: str, text: str):
    if os.getenv("ENABLE_ENWIKI_WIKIDATA_LINK") != "1":
        return None, None
    if not text:
        return None, None
    if REDIRECT_RE.search(text):
        return None, None
    if not title.startswith("Template:"):
        return None, None

    template_name = title[len("Template:") :]
    if not template_name:
        return None, None

    enwiki_exists, enwiki_qid = _check_enwiki_template(template_name)
    if not enwiki_exists:
        return None, None

    en_pair = ("en", template_name)

    wd_match = WD_LINK_RE.search(text)
    if wd_match:
        local_qid, existing_pairs = _parse_wd_params(wd_match.group(1))
        new_qid = local_qid or (enwiki_qid or "")
        merged = list(existing_pairs)
        added_pair = en_pair not in merged
        if added_pair:
            merged.append(en_pair)
        if new_qid == local_qid and not added_pair:
            return None, None
        new_template = _build_wd_template(new_qid, merged)
        new_text = text[: wd_match.start()] + new_template + text[wd_match.end() :]
        bits = []
        if added_pair:
            bits.append(f"add en pair from enwiki Template:{template_name}")
        if new_qid != local_qid:
            bits.append(f"fill QID {new_qid} from enwiki")
        return new_text, "; ".join(bits)

    new_template = _build_wd_template(enwiki_qid or "", [en_pair])
    new_text = _insert_in_noinclude(text, new_template)
    if new_text == text:
        return None, None
    summary = f"add wikidata link from enwiki Template:{template_name}"
    if enwiki_qid:
        summary += f" ({enwiki_qid})"
    return new_text, summary
