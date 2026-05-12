"""
normalize_ill_positional op
============================
For each ``{{ill|...}}`` call on a page that has a ``qid=Q...`` named
param, if there's an explicit ``|1=X`` named override, promote its
value to be the bare first positional parameter (replacing whatever
was there) and drop the ``|1=`` entry.

Why
---
The bare first positional of an ``{{ill}}`` call is the *target page
title* on enwiki. That value is brittle — it gets out of date when
pages get moved or renamed enwiki-side, and it was sometimes typed
wrong on import. Editors who fix a broken ill instead add an explicit
``|1=...`` named override so MediaWiki resolution picks up the right
title (``|1=`` wins over the bare positional). That leaves the wikitext
with two inconsistent values: the stale bare positional and the
correct ``|1=`` override.

Normalizing the bare positional to match ``|1=`` (and dropping the
override afterwards) makes the saved wikitext self-consistent — what
MW actually renders is what's on the page. Mirrors and archives that
just look at the wikitext (fandom mirror, XML history offload) then
see the correct title without having to evaluate the template.

Qid gate (user spec, 2026-05-12)
--------------------------------
Only run the promotion when the ill call already has a ``qid=Q\\d+``
named param. An ill without a Wikidata connection is the user's signal
that *something is unresolved* about that link (no QID could be
attached, possibly because the target is ambiguous or doesn't yet
exist on Wikidata). The ``|1=`` override on a no-qid ill is more
likely a deliberate human note about a conflict than a stale bare
positional, so we leave those alone for human review.

Example
-------
Before::

    {{ill|Sukunahikona-no-Mikoto|ja|少彦名命|1=Sukunabikona|12=simple|13=User:Immanuelle/Sukunahikona-no-Mikoto|13=User:Immanuelle/Sukunabikona|ja_comment=jawiki redirects to スクナビコナ|qid=Q1234567}}

After::

    {{ill|Sukunabikona|ja|少彦名命|12=simple|13=User:Immanuelle/Sukunahikona-no-Mikoto|13=User:Immanuelle/Sukunabikona|ja_comment=jawiki redirects to スクナビコナ|qid=Q1234567}}

Other numeric-named params (``|2=``, ``|12=``, ``|13=``, …) are left
verbatim — only ``|1=`` is normalized into the positional slot.
Duplicate ``|1=`` entries collapse to the last one (matching MW's
last-wins resolution).

PRE_HEAVY so the normalized text is what ``history_offload`` snapshots
into the fandom mirror and the XML archive.
"""

import re

NAME = "normalize_ill_positional"
# Mainspace only — {{ill}} is an inline-link template; matches the scope
# of deleted_qids_in_ill. Extend later if it ever appears elsewhere.
NAMESPACES = (0,)
PRE_HEAVY = True

# Same conservative pattern as deleted_qids_in_ill: requires the body
# to contain no nested {...} braces, which sidesteps the need for a
# real wikitext parser. Calls with nested templates inside the body are
# left untouched (they're rare in practice).
ILL_RE = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)
_QID_RE = re.compile(r"^Q\d+$")


def _normalize_ill_body(body: str) -> str:
    """Body is the part between ``{{ill|`` and ``}}`` (the leading pipe
    has already been stripped by the regex capture). Return the
    normalized body, or the input unchanged if there's no ``|1=``
    override to promote AND a ``qid=Q...`` to anchor the normalization."""
    parts = body.split("|")
    if not parts:
        return body

    # Find every `1=...` named param. MW takes the LAST occurrence when
    # the same name is repeated, so that's the value that survives.
    # Also check whether a qid= named param is present — without one,
    # we treat the ill as unresolved (the user's signal that something
    # ambiguous is going on with this link) and refuse to touch it.
    override_indices: list[int] = []
    override_value: str | None = None
    has_qid = False
    for i, p in enumerate(parts):
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        key = k.strip()
        if key == "1":
            override_indices.append(i)
            override_value = v
        elif key == "qid" and _QID_RE.fullmatch(v.strip()):
            has_qid = True

    if override_value is None:
        return body
    if not has_qid:
        # No Wikidata anchor on the ill → leave the |1= override in
        # place; it's likely a deliberate human note about an
        # unresolved conflict, not a stale positional.
        return body

    # Promote the surviving value into the bare positional and drop ALL
    # `|1=` entries — leaving any of them behind would override the new
    # positional and undo the normalization.
    new_parts = list(parts)
    new_parts[0] = override_value
    for i in reversed(override_indices):
        new_parts.pop(i)
    return "|".join(new_parts)


def apply(title: str, text: str):
    if not text:
        return None, None

    from ..common import REDIRECT_RE
    if REDIRECT_RE.search(text):
        return None, None

    changed_count = 0

    def replacer(match):
        nonlocal changed_count
        body = match.group(1)
        new_body = _normalize_ill_body(body)
        if new_body == body:
            return match.group(0)
        changed_count += 1
        return "{{ill|" + new_body + "}}"

    new_text = ILL_RE.sub(replacer, text)
    if new_text == text:
        return None, None

    return new_text, f"normalize {changed_count} {{{{ill}}}} call(s): promote |1= to first positional"
