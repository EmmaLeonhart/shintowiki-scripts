#!/usr/bin/env python3
"""One correct way to capture a jawiki infobox field value.

Two separate bugs lived in the five importers that read these fields, and both were
found on 2026-07-10 while regenerating `souken_p571.txt`.

**1. The capture ran to the newline.**  `souken`, `kofun` and `p3225` used
`([^\\n]*)`. An article that puts its whole infobox on one line therefore bled the
next parameter into the value:

    {{日本の寺院|創建年=平安時代|開基=|中興年=[[1314年|1314年（正和3年）]]|…}}

`本願寺西山別院`'s founding was imported as **1314**, which is its 中興 (restoration)
year. Two more temples had the same defect. They were caught only because the bled
text happened to contain `中興`, a refused marker; a bled parameter carrying a bare
year would have leaked in silence.

**2. The alternation was in the wrong order.**  `saijin` and `honzon` bounded the
capture at `|`, but wrote it as::

    ((?:[^\\n|]|\\[\\[[^\\]]*\\]\\]|\\{\\{[^}]*\\}\\})*)

Regex alternation is ordered and non-backtracking once the `*` has succeeded, so
`[^\\n|]` eats `[`, `[`, `天`, `照`… and then halts at the `|` **inside** the
wikilink. `\\[\\[…\\]\\]` never gets a chance. Given

    |祭神 = [[天照大神|天照大御神]]、[[素戔嗚尊]]、[[大国主|大国主命]]

it captured `[[天照大神` — **silently dropping two of the three deities.** Japanese
era and deity links are piped constantly, so this was not an edge case.

Putting the bracketed alternatives first fixes both: a `|` inside `[[…]]` or `{{…}}`
is consumed as part of that token, and a bare `|` ends the field.
"""

# Bracketed forms FIRST — see above. `[^\n|]` must be the last alternative.
FIELD_TAIL = r"((?:\[\[[^\]]*\]\]|\{\{[^}]*\}\}|[^\n|])*)"


def field_pattern(name):
    """Regex source matching `| <name> = <value>` up to the next parameter.

    `name` is a regex fragment, so `築造(?:時期|年代)` works.
    """
    return r"\|\s*" + name + r"\s*=\s*" + FIELD_TAIL
