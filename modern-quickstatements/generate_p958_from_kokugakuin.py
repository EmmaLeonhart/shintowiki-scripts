"""Read P958 sections off the Kokugakuin pages for the items no ranking can reach.

Emma, 2026-08-25: *"grind it."* This is the grind, run over the 228 items in
`p958_derivability.json`'s `no_ranking` bucket — the ones with no `P1352` anywhere, whose section
therefore exists only on their entry's own page.

**How it decides.** `kokugakuin_candidates.resolve()` matches the item's ja label against that one
entry's numbered candidate slots, exact normalised equality only, and defers on a tie or a miss.
The set matched against is 2–5 names belonging to that single entry, never a global search — which
is the distinction between this and the jawiki text-matching that produced false positives before.

**Measured before use, not asserted.** Against 120 items whose `P958` is already set
(`p958_ground_truth_sample.json`): 72 agreed, 46 deferred, and 2 disagreed — both of which turned
out to be Wikidata being wrong, each confirmed by opening the page. So it answered 74 times and was
right 74 times, at 60% coverage. Re-run that measurement after any change to the matcher; the
fixture exists for exactly that.

**Live state is checked before emitting.** `p958_derivability.json` is a snapshot, so an item may
have gained a section since. Anything that already carries one on the id in question is skipped
rather than re-stated — this is an ADD-only file and must not fight an existing value. Correcting a
WRONG existing section is a different job with a different shape (remove + add), and it lives in
`generate_p958_corrections.py`.

⛔ Generates only. Nothing is delivered before the Wikidata lockout lifts on 2026-09-18 — but the
generating is not gated, which is the correction Emma made when three of my four "locked" labels
turned out to be wrong.

Usage:
    python modern-quickstatements/generate_p958_from_kokugakuin.py
    python modern-quickstatements/generate_p958_from_kokugakuin.py --limit 40
"""
import argparse
import collections
import io
import json
import os
import sys
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.wd_pace import wd_pace, READ_INTERVAL
import kokugakuin_candidates as kc

SRC = os.path.join(HERE, "p958_derivability.json")
OUT = os.path.join(HERE, "p958_from_kokugakuin.txt")
REPORT = os.path.join(HERE, "p958_from_kokugakuin.json")
API = "https://www.wikidata.org/w/api.php"


def existing_sections(qids):
    """{qid: {kokugakuin_id: [sections]}} straight from Wikidata."""
    out = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        url = API + "?" + urllib.parse.urlencode(
            {"action": "wbgetentities", "ids": "|".join(chunk), "props": "claims",
             "format": "json", "formatversion": "2"})
        req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
        wd_pace(READ_INTERVAL)
        with urllib.request.urlopen(req, timeout=90) as r:
            ents = json.loads(r.read().decode("utf-8"))["entities"]
        for q, e in ents.items():
            per = collections.defaultdict(list)
            for st in e.get("claims", {}).get("P13677", []):
                dv = st["mainsnak"].get("datavalue")
                if not dv:
                    continue
                for qual in st.get("qualifiers", {}).get("P958", []):
                    qv = qual.get("datavalue", {}).get("value")
                    if qv:
                        per[dv["value"]].append(qv)
            out[q] = dict(per)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="stop after N items (for a short run)")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    rows = json.load(io.open(SRC, encoding="utf-8"))["no_ranking"]
    if args.limit:
        rows = rows[:args.limit]
    print("items with no ranking anywhere: %d" % len(rows))

    qids = sorted({r["item"] for r in rows})
    print("checking live P958 on %d items..." % len(qids))
    live = existing_sections(qids)

    lines, resolved, skipped_live, deferred = [], [], [], collections.Counter()
    detail = []
    for i, r in enumerate(rows, 1):
        qid, kid, ja = r["item"], r["kid"], r.get("ja", "")
        if kid in live.get(qid, {}):
            skipped_live.append((qid, kid, live[qid][kid]))
            continue
        try:
            sec, why = kc.resolve(kid, ja)
        except Exception as exc:
            deferred["fetch failed"] += 1
            detail.append({"item": qid, "kid": kid, "ja": ja, "section": None,
                           "why": "fetch failed: %s" % exc})
            continue
        if sec is None:
            key = why.split(":")[0].split("(")[0].strip()
            deferred[key] += 1
            detail.append({"item": qid, "kid": kid, "ja": ja, "section": None, "why": why})
        else:
            lines.append('%s|P13677|"%s"|P958|"%s"' % (qid, kid, sec))
            resolved.append((qid, kid, ja, sec))
            detail.append({"item": qid, "kid": kid, "ja": ja, "section": sec, "why": why})
        if i % 40 == 0:
            print("  %d/%d ..." % (i, len(rows)), flush=True)

    # ⛔ COLLISION GUARD — correctness, not caution.
    #
    # Identity here is the (Kokugakuin id, section) PAIR; that is the whole reason P958
    # exists. Two Wikidata items can carry the SAME ja label — two 比佐豆知神社, two 神明社 —
    # and resolve() judges each item alone against the page, so both match the same slot and
    # both get emitted. A section claimed by two items identifies neither. The earlier audit
    # of every multi-holder id found ZERO collisions live on Wikidata, so emitting these
    # would not be adding a flawed value: it would be creating the first instances of a class
    # of error that does not currently exist anywhere in the data.
    #
    # The whole colliding group is dropped, never thinned to one. The page cannot say which
    # of two identically-named items it lists, and choosing would be exactly the guess this
    # reader was built to refuse.
    claims = collections.defaultdict(list)
    for qid, kid, ja, sec in resolved:
        claims[(kid, sec)].append(qid)
    collided = {k: v for k, v in claims.items() if len(v) > 1}
    dropped_lines = set()
    if collided:
        dropped_lines = {'%s|P13677|"%s"|P958|"%s"' % (q, k, s)
                         for q, k, j, s in resolved if (k, s) in collided}
        lines = [l for l in lines if l not in dropped_lines]
        for (kid, sec), qs in sorted(collided.items()):
            for q in qs:
                detail.append({"item": q, "kid": kid, "ja": "", "section": None,
                               "why": "collision: section %s on %s also claimed by %s"
                                      % (sec, kid, ", ".join(x for x in qs if x != q))})
        resolved = [r for r in resolved if (r[1], r[3]) not in collided]

    n = len(rows)
    if collided:
        print("\n⛔ dropped %d line(s) across %d colliding group(s) — one (id, section) claimed twice:"
              % (len(dropped_lines), len(collided)))
        for (kid, sec), qs in sorted(collided.items()):
            print("     kid %-8s section %-3s <- %s" % (kid, sec, ", ".join(qs)))
    print("\nresolved off the page: %d  (%.0f%% of %d)" % (len(resolved), 100.0 * len(resolved) / n, n))
    print("already had a section:  %d" % len(skipped_live))
    print("deferred:               %d" % sum(deferred.values()))
    for why, c in deferred.most_common():
        print("    %-46s %d" % (why[:46], c))

    print("\nsample of what resolved:")
    for qid, kid, ja, sec in resolved[:12]:
        print("   %-14s %-22s kid %-8s -> section %s" % (qid, ja[:20], kid, sec))

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        "\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"resolved": len(resolved), "deferred": sum(deferred.values()),
                    "already_set": len(skipped_live), "total": n,
                    "items": detail}, ensure_ascii=False, indent=1))
    print("\nwrote %s (%d lines)" % (OUT, len(lines)))
    print("wrote %s" % REPORT)


if __name__ == "__main__":
    main()
