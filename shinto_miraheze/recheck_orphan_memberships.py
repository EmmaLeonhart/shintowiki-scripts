#!/usr/bin/env python3
"""Re-check the 42 "the list names this item nowhere" verdicts in the p361 audit.

WHY THIS EXISTS
---------------
`modern-quickstatements/p361_multi_part_of_audit.json` classifies 55 shrines that carry
an unqualified `part of` alongside an ordinalled one. 42 got the verdict

    "list names this item nowhere -- removing the blank fixes nothing"

and queue.md turned that into "work these as an orphan-membership problem". Spot-checking
the first one killed the premise:

  Q10896675 出雲大神宮 / Q11368560 List of Shikinaisha in Tanba Province -> `list_says: []`

出雲大神宮 is the **ichinomiya of Tanba**. It is in that register under its Engishiki name
出雲神社 (イツモノ, 名神大), and the entry links straight to [[出雲大神宮]].

WHAT THE METHOD ACTUALLY WAS is not knowable: the audit script is **not in the repo**,
only its JSON output, so the verdicts cannot be re-derived — only re-measured. What can be
said is what it disagreed with.

A first guess — "the register lists are transclusion shells, so it read an empty article" —
is tidy and WRONG, and is recorded here so nobody re-derives it. `丹波国の式内社一覧` is
indeed 1,471 characters of `{{丹波国桑田郡の式内社一覧}}` and friends, with every shrine name
inside the per-district templates. But `丹後国の式内社一覧` is a shell too (806 chars) and the
audit read ordinals out of it fine. So shells are not the discriminator.

What IS measurable: the list *item* on Wikidata mirrors the register in `P527`, and that
mirror is incomplete. `Q11368560` (Tanba) carries 72 `P527` values and **Q10896675 is not
among them** — exactly matching the audit's verdict, and exactly contradicting the register.
Whatever the method was, it agreed with Wikidata's copy of the list and disagreed with the
list itself.

Which is the lesson worth keeping: **the register is the source; Wikidata's `P527` is a
partial transcription of it.** Checking membership against the transcription answers a
different question than the one asked.

WHAT IT DOES
------------
For each flagged (item, list) pair: fetch the list's jawiki page with templates EXPANDED
(`action=parse`, which renders transclusions) and look for the item — by its jawiki
sitelink title first, then by its ja label. Prints one line per pair and a summary.

Read-only. No Wikidata writes, no Miraheze requests. jawiki only, throttled.
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_for import ua_for  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "modern-quickstatements", "p361_multi_part_of_audit.json")
WD_API = "https://www.wikidata.org/w/api.php"
JA_API = "https://ja.wikipedia.org/w/api.php"
THROTTLE = 1.0


def _get(api, params, host):
    params["format"] = "json"
    url = api + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": ua_for(host)})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.load(fh)


def entities(qids):
    """ja label + jawiki sitelink for each QID, in batches of 50 (not one call each)."""
    out = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        d = _get(WD_API, {"action": "wbgetentities", "ids": "|".join(chunk),
                          "props": "labels|sitelinks", "languages": "ja"},
                 "www.wikidata.org")
        for q, e in d.get("entities", {}).items():
            out[q] = {
                "ja": e.get("labels", {}).get("ja", {}).get("value"),
                "jawiki": e.get("sitelinks", {}).get("jawiki", {}).get("title"),
            }
        time.sleep(THROTTLE)
    return out


def rendered(title, cache):
    """The list page with transclusions EXPANDED. This is the whole point."""
    if title in cache:
        return cache[title]
    try:
        d = _get(JA_API, {"action": "parse", "page": title, "prop": "wikitext",
                          "formatversion": "2"}, "ja.wikipedia.org")
        text = d.get("parse", {}).get("wikitext", "")
    except Exception:
        text = ""
    if text:
        # `prop=wikitext` returns the SOURCE, which is the shell. Expand it.
        try:
            d = _get(JA_API, {"action": "expandtemplates", "title": title,
                              "text": text, "prop": "wikitext"}, "ja.wikipedia.org")
            text = d.get("expandtemplates", {}).get("wikitext", text)
        except Exception:
            pass
    cache[title] = text
    time.sleep(THROTTLE)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="check only the first N pairs")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    audit = json.load(open(AUDIT, encoding="utf-8"))
    flagged = [e for e in audit["blank_ordinal_side"] if not e.get("list_says")]
    if args.limit:
        flagged = flagged[:args.limit]
    print(f"{len(flagged)} pairs verdicted 'list names this item nowhere'")

    meta = entities(sorted({e["item"] for e in flagged} | {e["list"] for e in flagged}))
    cache, found, missing, unresolved = {}, [], [], []

    for e in flagged:
        item, lst = e["item"], e["list"]
        list_title = meta.get(lst, {}).get("jawiki")
        if not list_title:
            unresolved.append((item, lst, "list has no jawiki sitelink"))
            continue
        text = rendered(list_title, cache)
        if not text:
            unresolved.append((item, lst, "could not fetch/expand the list"))
            continue
        needles = [n for n in (meta.get(item, {}).get("jawiki"),
                               meta.get(item, {}).get("ja"), e.get("ja")) if n]
        hit = next((n for n in needles if n in text), None)
        if hit:
            found.append((item, e.get("ja"), lst, hit))
            print(f"NAMED      {item} {e.get('ja')} in {list_title}  (matched {hit!r})")
        else:
            missing.append((item, e.get("ja"), lst))
            print(f"not named  {item} {e.get('ja')} in {list_title}")

    print("\n--- summary ---")
    print(f"verdict WRONG (list does name it): {len(found)}")
    print(f"verdict holds (still not named)  : {len(missing)}")
    print(f"unresolved                       : {len(unresolved)}")
    for item, lst, why in unresolved:
        print(f"  {item} / {lst}: {why}")


if __name__ == "__main__":
    main()
