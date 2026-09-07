r"""Escape and UNESCAPE for QuickStatements v1 quoted values -- an inverse pair.

``qs_escape`` existed in four copies across the generators; ``qs_unescape`` existed
nowhere, and that asymmetry is what broke [[QuickStatements/P6262]].

The generators are read-modify-write: each run parses the QS lines already on the
wiki page, keeps the ones it cannot yet retire, and re-renders the whole page. The
parse captured each value *as written* -- i.e. still escaped -- and the render
escaped it again. So every backslash in a preserved value doubled on every run.

``List of Kofun in Japan with the Name "Hyo"`` (Q123999885) is a real shintowiki
title with two double quotes in it. Its two backslashes became four, then eight; by
2026-08-30 that one line was 1,048,643 bytes -- 1,048,574 backslashes -- the page
could no longer be saved under MediaWiki's 2,048 KB ceiling, and the next doubling
would have put the single line over the ceiling on its own. No pagination scheme
survives that: a line is indivisible.

Two properties are the whole point of this module, and both are tested:

* ``qs_unescape(qs_escape(v)) == v`` for every ``v``.
* Parsing and re-rendering is therefore a fixed point: a value survives any number
  of read-modify-write cycles unchanged.

``qs_unescape`` is a left-to-right scan, not a pair of ``str.replace`` calls.
Unescaping quotes before backslashes (or after) mis-reads an escaped backslash that
happens to be followed by a quote, in one direction or the other. And only ONE
level is ever removed: a title may genuinely contain a backslash -- shintowiki has
``Template:\`` and ``Template:\sandbox`` -- so unescaping until the string stops
changing would corrupt those.
"""

__all__ = ["qs_escape", "qs_unescape"]

_BACKSLASH = "\\"
_QUOTE = '"'


def qs_escape(value: str) -> str:
    """Escape a string for inclusion in a QS v1 double-quoted value."""
    return value.replace(_BACKSLASH, _BACKSLASH * 2).replace(_QUOTE, _BACKSLASH + _QUOTE)


def qs_unescape(value: str) -> str:
    """Invert ``qs_escape``: the text between the quotes back to the real value.

    A backslash before anything other than a backslash or a quote is not something
    ``qs_escape`` can emit, so it is left alone rather than swallowed.
    """
    out = []
    i = 0
    n = len(value)
    while i < n:
        c = value[i]
        if c == _BACKSLASH and i + 1 < n and value[i + 1] in (_BACKSLASH, _QUOTE):
            out.append(value[i + 1])
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


# No value this pipeline writes comes near this. A MediaWiki page title is capped at 255
# bytes and a Wikidata label/description at 250 characters, so every legitimate parsed
# value -- a "shinto:Title" article id, an en label, a category label -- is an order of
# magnitude under it. Runaway escaping is the only thing that produces a longer one, and it
# produces one that is exponentially longer.
MAX_PARSED_VALUE = 1000


def qs_parse_value(value: str, limit: int = MAX_PARSED_VALUE) -> str:
    r"""``qs_unescape`` for a value read off a QS page, with a bounded repair.

    The 2026-09-04 fix made parse-then-render a FIXED POINT, which stopped Q123999885's
    P6262 line doubling. It does not shrink it. The repair there re-derives a preserved
    line from the state file, and that state does not know this QID -- its page is missing
    on miraheze, so it never enters the fresh set, which is the same reason the line ran
    away in the first place. ``desired.get(qid, on_page)`` therefore hands back the
    corrupted page text, and the line has sat at 1,048,623 characters of value ever since:
    two runs of 524,287 backslashes, or ``escape`` applied 19 times to

        shinto:List of Kofun in Japan with the Name "Hyō"

    ⚠ THE GATE IS WHAT MAKES THIS SAFE, and it is not a formality. Unescaping to a fixed
    point is WRONG in general -- ``a\\b`` escapes to ``a\\\\b`` and a second unescape eats
    a real backslash, which is why ``qs_unescape`` removes exactly one level. It is right
    HERE only because a value over ``limit`` cannot be a title or a label at all, so
    nothing legitimate reaches the loop. Under the limit this is plain ``qs_unescape`` and
    the parse is unchanged.
    """
    if len(value) <= limit:
        return qs_unescape(value)
    while True:
        reduced = qs_unescape(value)
        if reduced == value:
            return value
        value = reduced
