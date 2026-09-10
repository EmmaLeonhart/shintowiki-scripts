"""
generate_description_restores.py
================================
Put back the descriptions the description-fix drip replaced with a less specific
one.

Emma, 2026-09-10: *"we're actively worsening Ukrainian descriptions why is this?
Turning descriptive ones into generic highly duplicative ones"*.

GENERATOR ONLY — writes QuickStatements lines into an atomic .txt file that the
single daily submitter runs. It never edits Wikidata and the lines carry no edit
summaries (CLAUDE.md "Wikidata editing — ONE path only").

## What happened

`generate_description_fixes.py` infers a per-(class, language) standardized
description from the corpus and, for each target, uses the PREFECTURE form when
it can resolve the item's prefecture and the GENERIC modal otherwise. Prefecture
detection was a substring test against the full prefecture label — and Ukrainian
labels the prefecture `Префектура Наґано` (nominative) while writing descriptions
`…у префектурі Наґано, Японія` (locative). The substring never matched, so no
prefecture template was ever inferred for uk and every uk target fell through to
the generic:

    Q100902082, 2026-09-10T01:10:41Z
      before  Синтоїстське святилище у префектурі Наґано, Японія
      after   синтоїстське святилище в Японії

3,509 queued lines carried that identical string. Indonesian's `Prefektur
Nagano` does not decline, which is why id worked, uk did not, and the fault read
as a uk oddity instead of a design fault in any inflecting language.

`pref_keys` in the fixes generator now matches on the part that does not inflect,
and a rule there refuses outright to replace a description carrying the item's
prefecture with one that does not. This script repairs what already went out.

## How the original is recovered

**From the revision history, not reconstructed.** Every edit is in our own
contributions with a `wbsetdescription-set:1|<lang>` comment; the parent revision
of each carries the exact description that was there before. Rebuilding the
prefecture form from `P131` instead would risk a different string from the one
the community actually had — capitalisation, the wording of the connective, an
item whose description was specific for some other reason entirely.

The FIRST of our edits per (item, language) is the one whose parent holds the
true original, because a second pass would only ever show the generic we had
already written.

## The restore rule, and why it is the same rule as the fix

Restore where **the original names the item's prefecture and the current value
does not.** That is the downgrade, stated exactly, and it means:

  * an item whose description was already generic is not touched — nothing was
    lost;
  * an item a human has since repaired reads as already-carrying its prefecture,
    so no line is emitted. Self-healing, and it cannot fight a person.

Language-agnostic on purpose. uk is 241 of the 306 description edits in the
window, but cs, pl and ru are inflecting too and were exposed to the identical
fault; nothing here is keyed to a language list.

Output: description_restores.txt
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

import argparse
import collections
import io
import json
import os
import re
import shutil
import sys
import time

import requests

_usys.path.insert(0, _uos.path.dirname(_uos.path.abspath(__file__)))
from generate_description_fixes import pref_keys  # noqa: E402

WD_API = "https://www.wikidata.org/w/api.php"
SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
OUTPUT_FILE = "description_restores.txt"

# Our editing account, whose contributions are the record of what the drip did.
BOT_USER = "Immanuelle"

# The drip's first uk description edit was 2026-09-10T01:10:41Z. Starting the
# scan the day before covers it with room to spare, and bounds the walk so this
# does not page through the whole account's history on every CI run.
SINCE = "2026-09-09T00:00:00Z"

DESC_SET = re.compile(r"wbsetdescription-set:1\|([a-zA-Z-]+)")
THROTTLE = 0.5

# One query for all 47 prefectures in every language, rather than one per
# language. CLAUDE.md: do not hammer Wikidata.
PREF_QUERY = """
SELECT ?pref ?label WHERE {
  ?pref wdt:P31 wd:Q50337 ; rdfs:label ?label .
}
"""


def _get(params, endpoint=WD_API):
    time.sleep(THROTTLE)
    r = requests.get(endpoint, params=params,
                     headers={"User-Agent": UA}, timeout=120)
    if r.status_code == 429:
        raise SystemExit("429 — bailing (CLAUDE.md 429 policy).")
    r.raise_for_status()
    return r.json()


def our_description_edits():
    """[(qid, lang, parentid, timestamp)] — every description SET we made since
    SINCE, EARLIEST FIRST per (item, language).

    Walks contributions rather than reading the batch file: the file says what is
    queued, the contributions say what actually landed, and only the second can
    be repaired."""
    seen, cont = {}, None
    while True:
        params = {"action": "query", "list": "usercontribs", "ucuser": BOT_USER,
                  "uclimit": 500, "ucprop": "ids|title|timestamp|comment",
                  "ucnamespace": 0, "ucend": SINCE,
                  "format": "json", "formatversion": 2}
        if cont:
            params["uccontinue"] = cont
        payload = _get(params)
        for e in payload.get("query", {}).get("usercontribs", []):
            m = DESC_SET.search(e.get("comment", ""))
            if not m or not e.get("parentid"):
                continue
            key = (e["title"], m.group(1))
            # Contributions come newest-first, so each later assignment is an
            # EARLIER edit; the last one to win is the first we made.
            seen[key] = (e["parentid"], e["timestamp"])
        cont = payload.get("continue", {}).get("uccontinue")
        if not cont:
            break
    return [(qid, lang, parent, ts)
            for (qid, lang), (parent, ts) in sorted(seen.items())]


def previous_descriptions(edits):
    """{(qid, lang): description-before-our-edit}. Revision content is fetched in
    batches of 50 revids, so 300 edits cost six requests rather than 300."""
    out = {}
    by_parent = collections.defaultdict(list)
    for qid, lang, parent, _ts in edits:
        by_parent[parent].append((qid, lang))
    parents = sorted(by_parent)
    for i in range(0, len(parents), 50):
        chunk = parents[i:i + 50]
        payload = _get({"action": "query", "revids": "|".join(map(str, chunk)),
                        "prop": "revisions", "rvprop": "content|ids",
                        "rvslots": "main", "format": "json", "formatversion": 2})
        for page in payload.get("query", {}).get("pages", []):
            for rev in page.get("revisions", []):
                try:
                    content = json.loads(rev["slots"]["main"]["content"])
                except (KeyError, ValueError):
                    continue
                for qid, lang in by_parent.get(rev["revid"], []):
                    value = content.get("descriptions", {}).get(lang, {}).get("value")
                    if value:
                        out[(qid, lang)] = value
    return out


def current_descriptions(qids):
    """{qid: {lang: value}} as Wikidata stands right now."""
    out = {}
    qids = sorted(set(qids))
    for i in range(0, len(qids), 50):
        payload = _get({"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
                        "props": "descriptions", "format": "json"})
        for qid, entity in payload.get("entities", {}).items():
            if "missing" in entity:
                continue
            out[qid] = {lang: d["value"]
                        for lang, d in entity.get("descriptions", {}).items()}
    return out


def prefecture_keys_by_language():
    """{lang: {distinctive place-name: full label}} for all 47 prefectures.

    Reuses `pref_keys` from the fixes generator so the restore's idea of "names
    its prefecture" is the SAME idea the fix uses. Two definitions here would let
    the two scripts disagree about a given item forever."""
    time.sleep(THROTTLE)
    r = requests.post(SPARQL_ENDPOINT, data={"query": PREF_QUERY, "format": "json"},
                      headers={"User-Agent": UA,
                               "Accept": "application/sparql-results+json"},
                      timeout=300)
    if r.status_code == 429:
        raise SystemExit("429 from WDQS — bailing (CLAUDE.md 429 policy).")
    r.raise_for_status()
    by_lang = collections.defaultdict(list)
    for b in r.json()["results"]["bindings"]:
        by_lang[b["label"]["xml:lang"]].append(b["label"]["value"])
    return {lang: pref_keys(labels) for lang, labels in by_lang.items()}


def names_a_prefecture(text, keys):
    """The distinctive place-name this description carries, or None."""
    if not text:
        return None
    return next((k for k in sorted(keys, key=len, reverse=True) if k in text), None)


def build_lines(edits, previous, current, keys_by_lang):
    """(lines, report). A row per edit, restored or not, with the reason — a
    refusal that vanishes into a shorter file is a refusal nobody can check."""
    lines, report = [], []
    for qid, lang, _parent, ts in edits:
        was = previous.get((qid, lang))
        now = current.get(qid, {}).get(lang)
        keys = keys_by_lang.get(lang, {})
        if not was:
            report.append((qid, lang, was, now, "no prior description — nothing lost"))
            continue
        old_pref = names_a_prefecture(was, keys)
        if not old_pref:
            report.append((qid, lang, was, now, "original named no prefecture"))
            continue
        if now and old_pref in now:
            report.append((qid, lang, was, now, "already carries its prefecture"))
            continue
        if now == was:
            report.append((qid, lang, was, now, "already restored"))
            continue
        esc = was.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{qid}|D{lang}|"{esc}"')
        report.append((qid, lang, was, now, "RESTORE"))
    return lines, report


def publish_to_site(path):
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--stats", action="store_true", help="report only, write nothing")
    ap.add_argument("--verbose", action="store_true", help="print every row")
    args = ap.parse_args()

    print("=== Restore descriptions the fix drip made less specific ===\n")
    edits = our_description_edits()
    print(f"{len(edits)} description SET edits by {BOT_USER} since {SINCE}")
    by_lang = collections.Counter(lang for _q, lang, _p, _t in edits)
    print(f"  by language: {dict(by_lang.most_common())}\n")
    if not edits:
        lines, report = [], []
    else:
        previous = previous_descriptions(edits)
        current = current_descriptions([q for q, _l, _p, _t in edits])
        keys_by_lang = prefecture_keys_by_language()
        lines, report = build_lines(edits, previous, current, keys_by_lang)

    verdicts = collections.Counter(r[4] for r in report)
    for verdict, n in verdicts.most_common():
        print(f"  {n:>5}  {verdict}")
    shown = [r for r in report if r[4] == "RESTORE"]
    for qid, lang, was, now, _v in (shown if args.verbose else shown[:8]):
        print(f"    {qid:<12} {lang:<6} {now!r} -> {was!r}")

    if args.stats:
        print(f"\n--stats: {len(lines)} lines would be written")
        return

    path = args.out if os.path.dirname(args.out) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), args.out)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    publish_to_site(path)
    print(f"\nWrote {len(lines)} lines to {path}")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
