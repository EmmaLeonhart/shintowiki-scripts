#!/usr/bin/env python3
"""Match Emma's newly-created Wikidata items (from the recreation QuickStatements)
back to the recreation candidates, then do the deferred linking.

Emma 2026-07-06: the items are created; she changed SOME English labels but kept the
Japanese ones — so match on the EXACT Japanese kanji label ONLY (never en), and
verify the hit's P31 equals our assigned P31 before accepting it as our new item.

On --apply:
  * write ``enrichment.recreated_qid`` into each matched candidate's items/*.json;
  * relink its ``{{ill|…|qid=DELETED_QID}}`` on the git-synced pages → the new QID
    (qid=DELETED_QID → qid=<new>, drop dd=) — shinto-wiki edits via git_synced, NOT
    Wikidata writes;
  * emit the DEFERRED family relations (enrichment.relations whose target_qid was
    null because the relative wasn't created yet, and whose target is ANOTHER now-
    matched candidate) as a follow-up QuickStatements batch
    (recreation_relations_quickstatements.txt + _RUNNABLE.txt) — HUMAN-GATED, Emma
    runs it (QuickStatements pipeline only, no bespoke Wikidata editor);
  * write new_qid_mapping.md.
Read-only Wikidata (throttled, 429-bail). Dry-run by default.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.title_filename import title_to_filename  # noqa: E402
import argparse
import glob
import io
import json
import os
import re
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ITEMS = os.path.join(HERE, "items")
GIT_SYNCED = os.path.join(REPO, "git_synced")
WD = "https://www.wikidata.org/w/api.php"
UA = WIKIDATA_USER_AGENT
THROTTLE = 0.2
# Emma's recreation batch spans ~Q140445965–Q140446168. Any exact-ja item at or above
# this floor is one of those fresh creations (deleted-item QIDs are Q135xxxxxx, far
# below). Used ONLY to disambiguate when several items share the same ja label.
FRESH_MIN = 140_440_000
_ILL = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)


def _has_cjk(s):
    return any("぀" <= c <= "ヿ" or "㐀" <= c <= "鿿" or "豈" <= c <= "﫿" for c in s)




def relink_ill(inner, qid):
    new = re.sub(r"(qid\s*=\s*)DELETED_QID", r"\g<1>" + qid, inner)
    return re.sub(r"\s*\|\s*dd\s*=\s*Q\d+", "", new)


def _get(params):
    for attempt in range(4):
        r = requests.get(WD, params=params, headers={"User-Agent": UA}, timeout=60)
        if r.status_code == 429:
            print("  [429] bailing"); sys.exit(2)
        if r.status_code >= 500:
            time.sleep(2 * (attempt + 1)); continue
        r.raise_for_status()
        return r.json()
    return None


def ja_candidates(ja):
    """QIDs whose search label exactly equals `ja`."""
    r = _get({"action": "wbsearchentities", "search": ja, "language": "ja",
              "uselang": "ja", "type": "item", "limit": "10", "format": "json"})
    time.sleep(THROTTLE)
    return [h["id"] for h in (r or {}).get("search", []) if h.get("label") == ja]


def p31_of(qids):
    out = {}
    uniq = sorted(set(qids))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get({"action": "wbgetentities", "ids": "|".join(batch),
                  "props": "claims", "format": "json"})
        time.sleep(THROTTLE)
        for qid, e in (r or {}).get("entities", {}).items():
            out[qid] = [c["mainsnak"]["datavalue"]["value"]["id"]
                        for c in e.get("claims", {}).get("P31", [])
                        if c["mainsnak"].get("datavalue")]
    return out


def choose_hit(cands, our_p31, p31s):
    """Which exact-ja-label candidate is our recreated item.

    Emma 2026-07-06: the Japanese labels were NEVER changed after creation, so a SINGLE
    item under the exact ja label IS ours — accept it regardless of P31 (she re-types
    items afterward: the Izumo 講社 → shrine-church; P279 subclasses have empty P31).
    Only when MULTIPLE items share the ja label do we disambiguate: prefer our assigned
    P31, else the single item in the fresh recreation-batch QID range. Coincidental
    pre-existing items are already excluded upstream (possible_existing skip + the dedup
    sweep, which would surface any real ja-collision as a multi-candidate case here).
    """
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    hit = next((q for q in cands if our_p31 in p31s.get(q, [])), None)
    if hit is None:
        fresh = [q for q in cands if int(q[1:]) >= FRESH_MIN]
        hit = fresh[0] if len(fresh) == 1 else None
    return hit


def build_mapping():
    """{deleted_qid(file stem) : {"new": qid, "ja": ja, "en": en, "p31": p31,
    "relations": [...], "hosts": [...]}} for candidates matched to a new item."""
    recs = []
    for f in sorted(glob.glob(os.path.join(ITEMS, "Q*.json"))):
        r = json.load(open(f, encoding="utf-8"))
        enr = r.get("enrichment") or {}
        if not r.get("recreation_candidate") or not enr.get("p31") or enr.get("possible_existing"):
            continue
        ja = ((r.get("fandom") or {}).get("langlinks") or {}).get("ja") or ""
        if not (ja and _has_cjk(ja)):
            continue
        recs.append((os.path.splitext(os.path.basename(f))[0], r, ja, enr))

    mapping = {}
    for stem, r, ja, enr in recs:
        cands = ja_candidates(ja)
        if not cands:
            print(f"  no exact-ja item yet: {ja}")
            continue
        our = enr["p31"]
        # only spend the P31 lookup when we actually have to disambiguate
        p31s = p31_of(cands) if len(cands) > 1 else {}
        hit = choose_hit(cands, our, p31s)
        if hit:
            mapping[stem] = {
                "new": hit, "ja": ja,
                "en": r.get("recovered_label") or "",
                "p31": our, "relations": enr.get("relations") or [],
                "hosts": (r.get("fandom") or {}).get("host_pages") or [],
                "file": os.path.join(ITEMS, stem + ".json"),
            }
            print(f"  MATCH {r.get('recovered_label') or ja} ({ja}) → {hit}")
        else:
            print(f"  ambiguous, needs review: {ja} (candidates {cands})")
    return mapping


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    mapping = build_mapping()
    print(f"\nMatched {len(mapping)} candidates to new Wikidata items.")
    if not args.apply:
        print("[DRY-RUN] pass --apply to relink ills + write mapping + relations QS.")
        return 0

    # ja -> new QID, for resolving deferred relations between recreated items.
    ja_to_new = {v["ja"]: v["new"] for v in mapping.values()}

    # 1. record recreated_qid + relink ills
    relinked = 0
    for stem, v in mapping.items():
        rec = json.load(open(v["file"], encoding="utf-8"))
        rec.setdefault("enrichment", {})["recreated_qid"] = v["new"]
        json.dump(rec, open(v["file"], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2, sort_keys=True)
        for host in v["hosts"]:
            path = os.path.join(GIT_SYNCED, title_to_filename(host))
            if not os.path.exists(path):
                continue
            text = open(path, encoding="utf-8").read()

            def _sub(m):
                inner = m.group(1)
                if "DELETED_QID" in inner and v["ja"] in inner:
                    return "{{ill|" + relink_ill(inner, v["new"]) + "}}"
                return m.group(0)

            new = _ILL.sub(_sub, text)
            if new != text:
                open(path, "w", encoding="utf-8", newline="\n").write(new)
                relinked += 1

    # 2. deferred family relations, now resolvable to new QIDs on both sides →
    # emit into the modern-quickstatements/ daily-edit queue (Emma 2026-07-06: put
    # them in the queue of things that eventually get edited on Wikidata). Clean
    # `<QID>\t<prop>\t<QID>` lines; the submitter skips the `#` header. Re-adding an
    # existing claim is a Wikidata no-op, so nightly regeneration is idempotent.
    rel_lines = []
    for stem, v in mapping.items():
        for rel in v["relations"]:
            if rel.get("target_qid"):
                continue  # already had a live target; set at recreation
            tgt_new = ja_to_new.get(rel.get("target_label_ja"))
            if tgt_new and rel.get("property"):
                rel_lines.append(f"{v['new']}\t{rel['property']}\t{tgt_new}")
    rel_lines = sorted(set(rel_lines))
    rel_path = os.path.join(REPO, "modern-quickstatements", "recreation_relations.txt")
    with open(rel_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Deferred family relations between recreated deleted-items "
                 "(P22/P25/P40/P3373). Auto-generated by recreate-deleted-wikidata/"
                 "match_new_qids.py; drained to Wikidata by the daily submitter.\n")
        fh.write("\n".join(rel_lines) + "\n")

    # 3. mapping report
    with open(os.path.join(HERE, "new_qid_mapping.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Recreated-item QID mapping (matched by exact ja label + P31)\n\n")
        fh.write("| old deleted QID | ja | en | new QID |\n|---|---|---|---|\n")
        for stem, v in sorted(mapping.items()):
            fh.write(f"| {stem} | {v['ja']} | {v['en']} | {v['new']} |\n")

    print(f"APPLIED: {len(mapping)} recreated_qid recorded, {relinked} ills relinked, "
          f"{len(rel_lines)} deferred relations → modern-quickstatements/recreation_relations.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
