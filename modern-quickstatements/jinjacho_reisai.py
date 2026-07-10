#!/usr/bin/env python3
"""Parse a 例祭 date out of a prefectural 神社庁 database's free-text festival field.

Emma 2026-07-10 chose the 47 prefectural 神社庁 databases as the source for reisai
dates beyond jawiki. This module is the parser for the one record shape that has
actually been verified against a live site: Mie's 「主な祭典」 field, served from
`jinja-net.jp/jinjacho-mie`.

The field is free text, not structured. Real values, sampled live:

    例祭8月15日　かに祭9月23日　蛭子祭7月20日        鳥出神社   -> 8/15
    例祭 4月15日                                  梶賀神社   -> 4/15
    例祭１０月、祈年祭２月、天王祭7月                 八幡神社   -> month only, refused
    秋祭り１０月体育の日前日　八幡祭７月第４土日        大西神社   -> no 例祭 at all
    １０月第２日曜（神饌に特徴あり…                  島勝神社   -> relative date

So: normalise fullwidth digits, find the date that follows the **例祭** label
specifically (several festivals share the field), and refuse anything that gives a
month without a day, or a relative date such as 第２日曜 / 体育の日前日.

The value model stays `P837` day-of-year + `P3831` = `Q11385469` Reisai, per
`docs/wikidata_shrine_festival_model.md`. Nothing here emits QuickStatements; it is
a parser plus the scoping evidence, pending Emma's go/no-go on the whole avenue —
see `docs/reisai_prefectural_feasibility_2026-07.md`.
"""
import re

# ０-９ -> 0-9
_FULLWIDTH = {ord("０") + i: ord("0") + i for i in range(10)}

# The date must follow the 例祭 label. Other festivals in the same field
# (かに祭, 蛭子祭, 天王祭, 秋祭り) have their own dates and must not be picked up.
_REISAI_DATE = re.compile(r"例祭[^0-9]{0,6}(\d{1,2})月(\d{1,2})日")

# A 例祭 with a month but no day: 「例祭１０月、祈年祭２月」
_REISAI_MONTH_ONLY = re.compile(r"例祭[^0-9]{0,6}(\d{1,2})月(?!\s*\d{1,2}\s*日)")

# Relative dates the model cannot express as a day-of-year.
_RELATIVE = re.compile(r"第\s*\d+\s*[日月火水木金土]曜|体育の日|敬老の日|春分|秋分|海の日|祝日")


def normalise_digits(text):
    return (text or "").translate(_FULLWIDTH)


def parse_reisai(field):
    """(month, day) of the 例祭, or None.

    Refuses a month without a day, a relative date, an out-of-range value, and any
    field that never names 例祭 at all.
    """
    if not field:
        return None
    text = normalise_digits(field)

    m = _REISAI_DATE.search(text)
    if not m:
        return None

    # A relative qualifier attached to the 例祭 itself makes the day meaningless.
    tail = text[m.end():m.end() + 8]
    if _RELATIVE.search(tail):
        return None

    month, day = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return month, day


def has_reisai_month_only(field):
    """True when the field names a 例祭 month but no day — counted, never guessed."""
    text = normalise_digits(field)
    return bool(_REISAI_MONTH_ONLY.search(text)) and parse_reisai(text) is None


def is_relative(field):
    """True when the field's dates are relative (第2日曜, 体育の日前日, …)."""
    return bool(_RELATIVE.search(normalise_digits(field or "")))
