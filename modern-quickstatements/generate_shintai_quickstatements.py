#!/usr/bin/env python3
"""
generate_shintai_quickstatements.py
===================================
Import 神体 (shintai — the object in which a kami is held to reside) from the jawiki
`{{神社}}` shrine infobox:

    <shrine>|P825|<shintai>|P3831|Q327532|S143|Q177837|S4656|"<jawiki url>"

Emma 2026-07-10: *"shintai modelling find a property and it will have the object of
statement has role shintai"*, then, shown the candidates: **`P825` 'dedicated to' +
role**.

`Q327532` verified live: *shintai / 神体 — "objects worshipped at or near Shinto
shrines" / 「神道で神が宿るとされる物体」*. **No item on Wikidata currently uses
`P3831 = Q327532`**, so every statement here is a first use of the role.

WHY P825
--------
No property fits cleanly — the values are mountains (弥彦山, 富士山, 立山), swords
(草薙剣, 布都御魂剣) and mirrors (八咫鏡), and Wikidata has no "object of veneration".
`P825`'s own description says "person or organization", which a mountain is not. It
wins on internal consistency: `generate_honzon_quickstatements` already imports 本尊 —
a temple's principal object of veneration — as bare `P825`. Shintai is the shrine's
exact analogue, and the `P3831` role is what tells them apart. `P527` "has part(s)"
was rejected: Mt Fuji is not a *part* of Fujisan Hongū Sengen Taisha.

THE TWO TRAPS, BOTH REAL
------------------------
**1. `（[[神体山]]）` is a class annotation, not the shintai.**  36 of the 45 link
targets in the raw field are the word 神体山 (or 磐座, 御霊代) sitting in a trailing
parenthetical that says *what kind of thing* the shintai is. Reading links naively
would emit `<shrine>|P825|神体山` 36 times. Same shape as the `[[宮内庁]]` attributor
in the kofun 被葬者 field. It is removed by name, **not** by stripping parentheticals —
doing that also eats a link's disambiguator and turns `[[弥山 (広島県)|弥山]]` into
`[[弥山 |弥山]]`, losing the article title. A test pins this.

**2. A piped link's target is often the containing article, not the shintai.**

    [[柊野#名所・旧跡|神山]]        target = a DISTRICT; the shintai is 神山
    [[春日山 (奈良県)|御蓋山]]      target = the RANGE; the shintai is the peak 御蓋山
    [[天叢雲剣|草薙神剣（草薙剣）]]   display is a variant spelling

Emma chose the conservative rule: **refuse a piped link whose display text differs
from its target**, ignoring a parenthetical disambiguator (`[[弥山 (広島県)|弥山]]`
and `[[富士山 (代表的なトピック)|富士山]]` are fine). Three ambiguous links are lost
rather than attached to the wrong item.

ADD-only. Output: `shintai_p825.txt`, registered in `ATOMIC_FILES`.

    python generate_shintai_quickstatements.py [--out FILE] [--limit N]
"""
import argparse
import io
import os
import re
import shutil
import sys
import time
import urllib.parse

from infobox_fields import field_pattern
from generate_souken_quickstatements import (
    embedded_titles,
    fetch_batch,
    strip_citations,
)
from generate_saijin_quickstatements import resolve_links

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "shintai_p825.txt"
OUTPUT = os.path.join(HERE, OUTPUT_FILE)

TEMPLATE = "Template:神社"
SHINTAI = "Q327532"       # shintai — "objects worshipped at or near Shinto shrines"
P_DEDICATED = "P825"
P_ROLE = "P3831"

_FIELD_RE = re.compile(field_pattern("神体"))
# target, display (display is None for a bare link)
_LINK = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]")
_BREAK = re.compile(r"<br\s*/?>|\n")
# A trailing disambiguator on the TARGET, which the display legitimately drops.
_DISAMBIG = re.compile(r"\s*[（(][^）)]*[）)]\s*$")

# Words naming the *kind* of shintai, never the shintai itself.
CLASS_WORDS = {"神体山", "磐座", "御霊代", "神体"}

# Link targets that are jawiki REDIRECTS onto an article about something else.
# Named rather than thresholded: a blanket "refuse redirects" rule would also drop
# `富士山 (代表的なトピック)` -> `富士山`, which is the same entity and correct.
#
#   鉾   -> 矛           大神神社 (栃木市)'s shintai is a halberd; the article is the
#                       weapon CLASS, so P825 would point at a type, not an object.
#   蓑山 -> 美の山公園    皆野椋神社's shintai is Mt Minoyama; jawiki has no article for
#                       the mountain, only for the park on it (P31 = park).
REFUSED_TARGETS = {
    "鉾": "redirects to 矛, the weapon class, not this shrine's halberd",
    "蓑山": "redirects to 美の山公園, a park, not the mountain",
}


def _target_base(target):
    """`弥山 (広島県)` -> `弥山`; `柊野#名所・旧跡` -> `柊野`."""
    return _DISAMBIG.sub("", target.split("#", 1)[0]).strip()


def extract_shintai(field):
    """The jawiki article title of the single shintai, or None.

    Refuses: multiple segments, no non-class link, more than one distinct link, and
    a piped link whose display text does not match its target.
    """
    if not field:
        return None
    s = strip_citations(field)
    segments = [seg for seg in _BREAK.split(s) if seg.strip()]
    if len(segments) != 1:
        return None

    # Do NOT strip parentheticals before reading links. The class annotation
    # `（[[神体山]]）` is itself a link and is removed by the CLASS_WORDS filter
    # below — whereas stripping `（…）` first also eats a link's *disambiguator*,
    # turning `[[弥山 (広島県)|弥山]]` into `[[弥山 |弥山]]` and losing the article
    # title we need to resolve. A test caught exactly that.
    candidates = []
    for target, display in _LINK.findall(segments[0]):
        target = target.strip()
        base = _target_base(target)
        if not base or base in CLASS_WORDS or base in REFUSED_TARGETS:
            continue
        if display and display.strip() != base:
            # [[柊野#名所・旧跡|神山]] — the target is not the shintai.
            return None
        candidates.append(target)

    if len(set(candidates)) != 1:
        return None
    return candidates[0]


def qs_line(shrine, shintai_qid, url):
    return '{}|{}|{}|{}|{}|S143|Q177837|S4656|"{}"'.format(
        shrine, P_DEDICATED, shintai_qid, P_ROLE, SHINTAI, url)


def publish_to_site(path):
    """Mirror the batch into _site/ so the dashboard can link it."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    titles = embedded_titles(TEMPLATE)
    if args.limit:
        titles = titles[:args.limit]
    print("{} jawiki shrine articles".format(len(titles)))

    found, no_field, refused, no_qid = [], 0, 0, 0
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            m = _FIELD_RE.search(text or "")
            if not m or not m.group(1).strip():
                no_field += 1
                continue
            shintai = extract_shintai(m.group(1))
            if shintai is None:
                refused += 1
                continue
            if not qid:
                no_qid += 1
                continue
            url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(
                title.replace(" ", "_"))
            found.append((qid, shintai, url))
        time.sleep(0.3)
    print("{} single-shintai values ({} refused, {} no field, {} no QID)".format(
        len(found), refused, no_field, no_qid))

    resolved = resolve_links(sorted({s for _, s, _ in found}))
    print("{} shintai targets resolve to Wikidata items".format(len(resolved)))

    lines = [qs_line(shrine, resolved[s], url)
             for shrine, s, url in found if s in resolved]
    lines = sorted(set(lines))
    assert all(not l.startswith("-") for l in lines), "shintai import is ADD-only"

    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")
    publish_to_site(path)

    print("\n{} shintai lines -> {}".format(len(lines), path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
