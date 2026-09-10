#!/usr/bin/env python3
"""
build_kana_disagreement_queue.py
================================
Tier 3 of the derived-kana programme: the shrines where the two mechanical
sources CONTRADICT each other, handed to the LLM queue so an article decides.

`generate_derived_name_in_kana.py` derives a reading from the English label and
compares it against the dominant reading carried by items with the identical
Japanese label. Measured on a held-out set of 5,781 shrines that have both an en
label and a real `P1814`, agreement is right 97.7% of the time and no-mate 93.9%
— but where the two DISAGREE, the derivation is right only 64.35%. Neither
source wins, and the disagreement is real rather than noisy:

    倭文神社  Shitori Shrine   derived しとりじんじゃ   mate しどりじんじゃ
    神門神社  Mikado Shrine    derived みかどじんじゃ   mate ごうどじんじゃ
    一宮神社  Ikku Shrine      derived いっくじんじゃ   mate いちのみやじんじゃ

Emma's call, 2026-09-10, choosing this over leaving them or filing a report:
route them to the LLM queue. So this script turns
`modern-quickstatements/derived_name_in_kana_disagreements.json` into
`name_in_kana/` work-files in the format `collect_name_in_kana.py` already
drains — no collector change, no second queue.

⚠ THIS IS THE ONE PLACE an en-labelled shrine legitimately goes back to an
article. CLAUDE.md's rule — *"Do not try to reason about what the KANA reading
would be on something with an English label"* — is about deriving a reading when
the label already carries it. Here the label's reading has been derived, and
something the project itself recorded says it is wrong. That is not a case the
rule contemplates, and Emma decided it directly.

The work-file states BOTH candidates and asks which the lead supports, rather
than asking for a reading from scratch: the two candidates are the finding, and
throwing them away would make the LLM redo work already done.

`BUCKET: a` is deliberate — every item here has an English label, and bucket a is
what stops `collect_name_in_kana.py` also generating an English label from the
answer. Nothing needs one.

Read-only: Wikidata is not touched at all (the QIDs come from the JSON) and
ja.wikipedia only for the leads.

Usage:
    python build_kana_disagreement_queue.py --limit 200
    python build_kana_disagreement_queue.py --stats
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.parse

import requests

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

OUT_DIR = os.path.join(REPO_ROOT, "name_in_kana")
SOURCE = os.path.join(REPO_ROOT, "modern-quickstatements",
                      "derived_name_in_kana_disagreements.json")
QS_OUT = os.path.join(REPO_ROOT, "modern-quickstatements", "name_in_kana.txt")
RESOLVED_LOG = os.path.join(OUT_DIR, "_resolved.log")

JA_API = "https://ja.wikipedia.org/w/api.php"
UA = WIKIDATA_USER_AGENT
THROTTLE = 0.4
BATCH = 20

NO_LEAD = (
    "(NO LEAD AVAILABLE — the jawiki article is a redirect, a disambiguation "
    "page, empty, or the item has no jawiki sitelink at all, so there is no "
    "first sentence to read a reading out of. This will never change on its own.\n"
    "The two candidates below are still real evidence: pick between them if you "
    "can, from the readings other shrines of this name carry or from the "
    "place-name the shrine is named for. Answer NO_KANA only if you genuinely "
    "cannot.)"
)


def task_block(derived, mate):
    """The TASK marker. Names both candidates, because they ARE the finding."""
    return (
        "<!-- TASK: this shrine's reading is DISPUTED between two mechanical "
        "sources, and the lead above is the tiebreak.\n"
        f"  CANDIDATE A (from the English label): {derived}\n"
        f"  CANDIDATE B (from other shrines whose Japanese name is identical): {mate}\n"
        "Read the LEAD and fill ANSWER with exactly one of:\n"
        "  KANA: <hiragana>        the LEAD states this reading — it may be A, B, "
        "or neither; the lead wins over both\n"
        "  GUESS: <hiragana>       the lead states no reading; this is the "
        "candidate the other evidence supports\n"
        "  KATAKANA: <katakana>    the lead gives only an ancient/katakana reading\n"
        "  NO_KANA: <reason>       no reading, and neither candidate can be "
        "chosen over the other\n"
        "Rules: give the reading of the SHRINE NAME itself, not a 通称 (common "
        "name), not a 旧称 (former name), and not the reading of the place it "
        "stands in. Drop interpuncts and spaces. Do NOT pick a candidate just "
        "because it looks more regular — shrine names take irregular local "
        "readings, which is exactly why these two disagree. A KATAKANA answer is "
        "recorded and NOT written to Wikidata.\n"
        "When ANSWER is filled this file is done. -->"
    )


def _utf8():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def already_handled():
    """QIDs already staged or already answered.

    Same reasoning as `build_name_in_kana_queue.already_handled`: the collector
    DELETES a work-file once answered, so "no file exists" does not mean "still
    needs work". The local staging is the only record of what has been done.
    """
    done = set()
    for path, first_field in ((QS_OUT, lambda ln: ln.split("|")[0]),
                              (RESOLVED_LOG, lambda ln: ln.split("\t")[0])):
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            q = first_field(line).strip()
            if q.startswith("Q") and q[1:].isdigit():
                done.add(q)
    return done


def leads(titles):
    """{title -> plain-text lead} via the extracts API, BATCH titles per call."""
    out = {}
    titles = [t for t in titles if t]
    for i in range(0, len(titles), BATCH):
        chunk = titles[i:i + BATCH]
        params = {"action": "query", "format": "json", "prop": "extracts",
                  "exintro": 1, "explaintext": 1, "redirects": 1,
                  "titles": "|".join(chunk), "formatversion": 2}
        time.sleep(THROTTLE)
        try:
            r = requests.get(JA_API, params=params,
                             headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", [])
        except Exception as e:
            print(f"  [jawiki batch {i // BATCH} failed] {e}", flush=True)
            continue
        # `redirects` rewrites titles, so map back through the normalisation the
        # API reports rather than assuming the response order matches the request.
        for p in pages:
            if "extract" in p and p.get("title"):
                out[p["title"]] = p["extract"]
        print(f"  leads {min(i + BATCH, len(titles))}/{len(titles)}", flush=True)
    return out


def write_work_file(rec, lead):
    path = os.path.join(OUT_DIR, f"{rec['qid']}.wiki")
    title = rec.get("ja_title") or ""
    art = ("https://ja.wikipedia.org/wiki/"
           + urllib.parse.quote(title.replace(" ", "_"))) if title else "(none)"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<!-- ITEM: https://www.wikidata.org/wiki/{rec['qid']} -->\n"
                f"<!-- JA: {rec['ja']} | EN_LABEL: {rec['en']} | BUCKET: a -->\n"
                f"<!-- ARTICLE: {art} -->\n"
                f"<!-- ANSWER: -->\n"
                f"{task_block(rec['derived'], rec['mate'])}\n"
                f"\n== LEAD ==\n{lead.strip()}\n")


def main():
    _utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=200,
                    help="max work-files to write this run (default 200)")
    ap.add_argument("--stats", action="store_true",
                    help="count only, write nothing")
    args = ap.parse_args()

    if not os.path.exists(SOURCE):
        print(f"{SOURCE} does not exist — run generate_derived_name_in_kana.py "
              f"first. Nothing to do.")
        return
    records = json.load(open(SOURCE, encoding="utf-8"))
    done = already_handled()
    todo = [r for r in records
            if r["qid"] not in done
            and not os.path.exists(os.path.join(OUT_DIR, f"{r['qid']}.wiki"))]
    print(f"{len(records)} disagreements; {len(records) - len(todo)} already "
          f"staged, answered, or queued; {len(todo)} outstanding")
    if args.stats:
        return
    todo = todo[:args.limit]
    if not todo:
        print("nothing to queue")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"downloading {len(todo)} jawiki leads...", flush=True)
    text = leads([r.get("ja_title") for r in todo])

    written, noext = 0, []
    for rec in todo:
        lead = text.get(rec.get("ja_title") or "")
        if not lead:
            # NO LEAD IS NOT A REASON TO SKIP. Skipping is a permanent loop, not
            # a retry — the article cannot acquire a lead, so every run refetches
            # and re-skips the same items (measured on the sibling builder,
            # 2026-08-23). The two candidates are still on the file, so the
            # answer can be a considered GUESS between them.
            noext.append(rec["qid"])
            lead = NO_LEAD
        write_work_file(rec, lead)
        written += 1
    print(f"\n{written} work-files -> {OUT_DIR}")
    if noext:
        print(f"{len(noext)} had NO lead extract — a work-file was still "
              f"written, with the lead marked unavailable: {', '.join(noext[:8])}")


if __name__ == "__main__":
    main()
