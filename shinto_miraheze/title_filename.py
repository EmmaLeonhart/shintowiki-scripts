#!/usr/bin/env python3
"""
title_filename.py
=================
The canonical page-title <-> filename mapping for every wiki<->repo sync
directory (``git_synced/``, ``fandom_unique/``, ``miraheze_unique/``,
``need_translation/``, ``duplicated_content/``).

Until 2026-09-01 this mapping was copy-pasted into nine scripts. It lives here
now so there is one definition to change; ``tests/test_title_filename.py``
imports it directly, which the old source-extracting test could not do because
the sync scripts install a ``sys.stdout`` wrapper at module load that breaks
pytest capture. This module has no import side effects, deliberately -- keep it
that way so it stays importable from tests and from any directory.

THE CASE-COLLISION PROBLEM
--------------------------
``title_to_filename`` percent-encodes only ``<>:"/\\|?*`` and ``%``. Case is not
encoded, so two page titles differing only in case -- ``Template:Infobox
Historic Site`` and ``Template:Infobox historic site``, both legitimate distinct
MediaWiki titles -- map to ONE filename on a case-insensitive filesystem. With
``core.ignorecase=true`` only one can exist on disk, so git reports the other as
modified forever, and worse, it DEADLOCKS ``git pull --rebase``: rebase checks
out a commit that still holds both index entries, which instantly re-creates the
mismatch, and restoring either path dirties the other, so it never converges.

Escaping case unconditionally would fix it and is the wrong fix: 4,128 of the
4,143 files across the three main sync dirs (99.6%) contain an uppercase letter,
so it would rename essentially the whole corpus to resolve what is currently a
single collision.

So: ``assign_filenames`` encodes case ONLY within a group of titles that would
otherwise collide. Groups of one -- almost all of them -- get byte-identical
output to before, so the corpus does not churn.

The reader needs no special case. ``filename_to_title`` is ``unquote``, which
already inverts ``%48`` back to ``H``.
"""

from __future__ import annotations

import urllib.parse

# Characters Windows forbids in a filename, plus '%' itself so the encoding is
# reversible (a literal '%' in a title must not be read back as an escape).
_FORBIDDEN = set('<>:"/\\|?*')


def title_to_filename(title: str) -> str:
    """Title -> filename. The historical mapping; case is NOT encoded."""
    out = []
    for c in title:
        if c in _FORBIDDEN or c == "%":
            out.append(f"%{ord(c):02X}")
        else:
            out.append(c)
    return "".join(out) + ".wiki"


def title_to_filename_case_escaped(title: str) -> str:
    """Title -> filename with EVERY cased ASCII letter percent-encoded.

    Both cases, not just uppercase. Escaping only uppercase is a no-op on an
    all-lowercase title, so in a three-way group like ``Foo Bar`` / ``foo bar``
    / ``FOO BAR`` the escaped ``foo bar`` would still collide with the plain
    ``FOO BAR``. Encoding every cased letter makes the mapping injective over
    case: two titles differing only in case escape to different hex bytes
    (``%46`` vs ``%66``), which survive the case-fold that compares filenames.

    Single pass over the title, so an escape introduced here can never be
    re-escaped -- encoding the title first and then running the normal mapping
    would corrupt ``%3A`` into ``%3%41`` (its 'A' is itself uppercase).
    """
    out = []
    for c in title:
        if c in _FORBIDDEN or c == "%" or ("A" <= c <= "Z") or ("a" <= c <= "z"):
            out.append(f"%{ord(c):02X}")
        else:
            out.append(c)
    return "".join(out) + ".wiki"


def filename_to_title(filename: str) -> str:
    """Filename -> title. Inverts BOTH mappings above; unquote handles each."""
    name = filename[:-5] if filename.endswith(".wiki") else filename
    return urllib.parse.unquote(name)


def assign_filenames(titles) -> dict:
    """Map every title to a filename, escaping case only where one is needed.

    Returns ``{title: filename}``. Titles whose plain filename is unique keep
    exactly the filename they have always had. Within a set of titles whose
    filenames differ only by case, the first by sort order keeps the plain form
    and the rest are case-escaped, so all of them can coexist on a
    case-insensitive filesystem.

    Sorting is the tie-break because there is no canonical member to prefer:
    MediaWiki capitalises only the first character after the namespace, so both
    halves of a pair like Historic Site / historic site are real, distinct
    pages. A stable sort keeps the assignment identical across runs; do not
    replace it with a heuristic that guesses which one is "the real" page.
    """
    groups: dict = {}
    for t in titles:
        fn = title_to_filename(t)
        groups.setdefault(fn.lower(), []).append(t)

    out = {}
    for members in groups.values():
        if len(members) == 1:
            t = members[0]
            out[t] = title_to_filename(t)
            continue

        ordered = sorted(members)
        fns = [title_to_filename(t) for t in ordered]

        # Escape ONLY the positions where the group actually disagrees, so the
        # result stays readable: the live pair becomes
        # 'Template%3AInfobox %68istoric %73ite.wiki', not a filename where
        # every single letter is a hex escape. Members of a group case-fold to
        # the same string, so they are the same length and index-aligned; the
        # length check is defensive, and falls back to escaping every cased
        # letter if that assumption is ever violated.
        if len({len(f) for f in fns}) == 1:
            differing = {
                i for i in range(len(fns[0]))
                if len({f[i] for f in fns}) > 1
            }
            out[ordered[0]] = fns[0]
            for t, fn in zip(ordered[1:], fns[1:]):
                out[t] = _escape_positions(fn, differing)
        else:
            out[ordered[0]] = fns[0]
            for t in ordered[1:]:
                out[t] = title_to_filename_case_escaped(t)
    return out


def _escape_positions(filename: str, positions) -> str:
    """Percent-encode exactly the given character indices of ``filename``."""
    return "".join(
        f"%{ord(c):02X}" if i in positions else c
        for i, c in enumerate(filename)
    )


def find_collisions(titles) -> list:
    """Groups of titles that collide case-insensitively. Empty list = clean."""
    groups: dict = {}
    for t in titles:
        groups.setdefault(title_to_filename(t).lower(), []).append(t)
    return [sorted(m) for m in groups.values() if len(m) > 1]
