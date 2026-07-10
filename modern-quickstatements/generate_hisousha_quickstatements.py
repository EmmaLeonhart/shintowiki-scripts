#!/usr/bin/env python3
"""
generate_hisousha_quickstatements.py
====================================
Import 被葬者 (the interred person) from the jawiki `{{日本の古墳}}` kofun infobox,
in **both directions**:

    <person>|P119|<kofun>     place of burial
    <kofun>|P547|<person>     commemorates

Emma 2026-07-10, shown the real numbers: *"Build it, 伝-marked get P1480"* and
*"Both directions, unconditionally."*

WHY ALMOST EVERY LINE CARRIES P1480
-----------------------------------
Who is buried in a kofun is disputed scholarship. Of the 1,528 kofun articles, 303
fill 被葬者, and after the exclusions below **73 statements** are emittable — of
which only **4** state the occupant without hedging. The other 69 are marked
推定 (presumed) / 治定 (designated by the Imperial Household Agency) / 伝
(traditionally) / 一説 (one theory). Those get

    P1480 = Q18122778  "presumably"

the same sourcing-circumstances qualifier the 伝-dates use, for the same reason: the
source gives a value and says the value is presumed. Asserting an Imperial Household
Agency *designation* as plain fact would be a claim jawiki does not make.

THE TRAPS, ALL SEEN IN LIVE DATA
--------------------------------
    （[[宮内庁]]治定）第16代[[仁徳天皇]]     the wikilink is the ATTRIBUTOR, not the occupant
    （推定）第26代[[継体天皇]]              hedge outside the link
    （宮内庁推定）第21代[[雄略天皇]]<br />（一説）第27代[[安閑天皇]]   two rival candidates
    不明（伝・[[平将門]]）                  the only link sits inside the hedge
    稲荷前古墳群 -> [[都筑郡]]              a DISTRICT
    幾坂古墳群   -> [[峰山盆地]]            a mountain BASIN
    大谷古墳     -> [[紀氏]]                a CLAN

So: the attributor names are excluded by name; the person is read from *outside* the
parenthetical hedge; a field naming more than one candidate is refused; and the link
target must resolve to a Wikidata item that is `P31 = Q5` (human). 111 of 112 targets
resolve; only 68 are humans.

ADD-only. Output: `hisousha_p119_p547.txt`, registered in `ATOMIC_FILES`.

    python generate_hisousha_quickstatements.py [--out FILE] [--limit N]
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request

from infobox_fields import field_pattern
from generate_souken_quickstatements import (
    embedded_titles,
    fetch_batch,
    strip_citations,
)
from generate_saijin_quickstatements import resolve_links

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "hisousha_p119_p547.txt"
OUTPUT = os.path.join(HERE, OUTPUT_FILE)

WD_API = "https://www.wikidata.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

TEMPLATE = "Template:日本の古墳"
HUMAN = "Q5"
PRESUMABLY = "Q18122778"
P_BURIAL = "P119"       # place of burial   (person -> kofun)
P_COMMEMORATES = "P547"  # commemorates     (kofun -> person)
P_SOURCING = "P1480"

_FIELD_RE = re.compile(field_pattern("被葬者"))
_LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
_PAREN = re.compile(r"[（(][^）)]*[）)]")
_BREAK = re.compile(r"<br\s*/?>|\n")

# The hedges. Their presence anywhere in the field means the attribution is not
# asserted as fact — including 治定, which is an Imperial Household Agency
# designation, not an excavation result.
_UNCERTAIN = re.compile(r"伝|推定|治定|一説|比定|とされる|\?|？|説|候補|不明")

# Wikilinked inside 被葬者 but never the occupant: they are who says so.
ATTRIBUTORS = {"宮内庁", "日本書紀", "古事記", "延喜式", "続日本紀"}


def extract_person(field):
    """(jawiki title of the single interred person, uncertain?) or (None, _).

    The person is read from OUTSIDE the parenthetical hedge, because the hedge is
    where the attributor lives: `（[[宮内庁]]治定）第16代[[仁徳天皇]]`.
    """
    if not field:
        return None, False
    s = strip_citations(field)
    uncertain = bool(_UNCERTAIN.search(s))

    segments = [seg for seg in _BREAK.split(s) if seg.strip()]
    if len(segments) != 1:
        return None, uncertain          # rival candidates — refuse

    outside = _PAREN.sub("", segments[0])
    people = [t.strip() for t in _LINK.findall(outside)
              if t.strip() and t.strip() not in ATTRIBUTORS]
    if len(set(people)) != 1:
        return None, uncertain
    return people[0], uncertain


def _api(params):
    params = dict(params, format="json")
    req = urllib.request.Request(WD_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def humans(qids):
    """The subset that is P31 = Q5. A clan, a district and a basin are not."""
    out, qids = set(), sorted(qids)
    for i in range(0, len(qids), 50):
        d = _api({"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
                  "props": "claims"})
        for qid, ent in d.get("entities", {}).items():
            for c in ent.get("claims", {}).get("P31", []):
                dv = c["mainsnak"].get("datavalue")
                if dv and dv["value"]["id"] == HUMAN:
                    out.add(qid)
                    break
        time.sleep(0.3)
    return out


def qs_lines(person, kofun, uncertain, url):
    """Both directions. The hedge, when present, rides on both statements."""
    hedge = "|{}|{}".format(P_SOURCING, PRESUMABLY) if uncertain else ""
    return [
        '{}|{}|{}{}|S4656|"{}"'.format(person, P_BURIAL, kofun, hedge, url),
        '{}|{}|{}{}|S4656|"{}"'.format(kofun, P_COMMEMORATES, person, hedge, url),
    ]


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
    print("{} jawiki kofun articles".format(len(titles)))

    found = []          # (kofun_qid, person_title, uncertain, url)
    no_field = refused = no_qid = 0
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            m = _FIELD_RE.search(text or "")
            if not m or not m.group(1).strip():
                no_field += 1
                continue
            person, uncertain = extract_person(m.group(1))
            if person is None:
                refused += 1
                continue
            if not qid:
                no_qid += 1
                continue
            url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(
                title.replace(" ", "_"))
            found.append((qid, person, uncertain, url))
        time.sleep(0.3)
    print("{} single-person values ({} refused, {} no field, {} no QID)".format(
        len(found), refused, no_field, no_qid))

    resolved = resolve_links(sorted({p for _, p, _, _ in found}))
    print("{} link targets resolve to Wikidata items".format(len(resolved)))
    human = humans(set(resolved.values()))
    print("{} of those are humans (P31=Q5)".format(len(human)))

    lines, certain = [], 0
    for kofun, person_title, uncertain, url in found:
        person = resolved.get(person_title)
        if not person or person not in human:
            continue
        lines.extend(qs_lines(person, kofun, uncertain, url))
        if not uncertain:
            certain += 1

    lines = sorted(set(lines))
    assert all(not l.startswith("-") for l in lines), "被葬者 import is ADD-only"
    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")
    publish_to_site(path)

    statements = len(lines) // 2
    print("\n{} burials emitted ({} stated plainly, {} marked presumably)".format(
        statements, certain, statements - certain))
    print("{} lines -> {}".format(len(lines), path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
