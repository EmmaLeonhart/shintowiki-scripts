"""Assign P958 sections one ENTRY at a time, against that entry's full set of holders.

The per-item reader (`generate_p958_from_kokugakuin.py`) judges each item alone, which is why it
had to drop 17 lines across 8 groups where two identically-named items both matched one slot. That
was the right guard, but it treats the symptom: the unit was wrong. **A section is an assignment
within an entry, not a property of an item**, so the whole entry has to be resolved at once.

Input is `p958_candidates_audit.json`, which is already grouped that way — every Kokugakuin id with
all of its holders and whatever section each already carries:

    "180695": [ {"item": "Q119929663", "ja": "平群石床神社",      "section": null},
                {"item": "Q135184983", "ja": "平群石床神社 旧社地", "section": null} ]

Three things fall out of resolving per entry that the per-item reader could not do:

1. **Collisions become impossible rather than detected.** A slot is claimed at most once, so the
   guard is structural instead of a post-hoc filter.
2. **Sections already on Wikidata act as constraints.** If a holder already occupies slot 2, that
   slot is taken and nothing else may be assigned to it. This is what makes the `MISSING-SOME`
   bucket (197 entries) tractable at all.
3. Elimination *appears* available — one holder left, one slot left, so the assignment looks
   forced. **It is off by default, because measurement killed it.**

**⛔ ELIMINATION IS UNSOUND AND DEFAULTS TO OFF.** Held out 280 already-known sections and asked
the resolver to recover each: exact match got **142 of 142 right**; elimination got **3 right and 1
wrong**. Four samples is thin, but the failure is not bad luck — it exposes the assumption:

> Elimination assumes the holder set is COMPLETE, i.e. that every numbered slot's occupant is
> among the items holding this id. That is not guaranteed. When a slot's shrine has no Wikidata
> item, or has one that does not carry the id, elimination hands that slot to whoever is left.

The item it broke on, `Q140465982`, is labelled **未知の神社** — "unknown shrine", a placeholder
with no identifying content. It was assigned slot 1 and belongs in slot 2. An inference that
cannot distinguish "this is the only candidate" from "this is the only candidate I can see" is
not evidence, and `--elimination` exists only so the rule can be re-measured, never for a
production run.

**So: exact-match only, and everything else defers.** Two holders and two free slots defer; the
page cannot say which is which, and guessing is what this refuses to do.

⛔ Generates only. Nothing is delivered before the Wikidata lockout lifts on 2026-09-18; the
generating is not gated.

Usage:
    python modern-quickstatements/generate_p958_by_entry.py
    python modern-quickstatements/generate_p958_by_entry.py --elimination   # measurement only
"""
import argparse
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import kokugakuin_candidates as kc

AUDIT = os.path.join(HERE, "p958_candidates_audit.json")
OUT = os.path.join(HERE, "p958_by_entry.txt")
REPORT = os.path.join(HERE, "p958_by_entry.json")

# Sections that occupy no numbered slot — they mean "not one of the numbered candidates",
# so they neither consume a slot nor need one. Emma, 2026-08-19: 0 and n/a "do not even
# need to be unique".
NON_SLOT = {"0", "n/a", "N/A", None, ""}


def resolve_entry(kid, holders, allow_elimination=False):
    """[(item, section, why)] for the holders this entry can place."""
    try:
        slots = kc.candidates(kid, offline=True)
    except kc.NotCached:
        return [], "page not in the corpus yet", {}
    except Exception as exc:
        return [], "page unavailable (%s)" % type(exc).__name__, {}
    if not slots:
        return [], "page lists no candidates", {}

    taken = {h["section"] for h in holders if h.get("section") not in NON_SLOT}
    free = {s: n for s, n in slots.items() if s not in taken}
    # A holder already carrying a real section is settled; one carrying 0/n/a is
    # deliberately outside the numbering and is not looking for a slot.
    open_holders = [h for h in holders if h.get("section") is None]

    placed, used = [], set()
    for h in open_holders:
        target = kc.normalise(h.get("ja", ""))
        if not target:
            continue
        hits = [s for s, n in free.items() if kc.normalise(n) == target and s not in used]
        if len(hits) == 1:
            placed.append((h["item"], hits[0], "exact match"))
            used.add(hits[0])

    rest = [h for h in open_holders if h["item"] not in {p[0] for p in placed}]
    spare = [s for s in free if s not in used]
    if allow_elimination and len(rest) == 1 and len(spare) == 1:
        placed.append((rest[0]["item"], spare[0],
                       "elimination: only holder left, only slot left"))
        rest, spare = [], []

    why = "placed %d/%d open holder(s); %d slot(s) left" % (
        len(placed), len(open_holders), len(spare))
    return placed, why, {"slots": slots, "taken": sorted(taken),
                         "unplaced": [h["item"] for h in rest]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elimination", action="store_true",
                    help="re-enable the unsound 1x1 elimination rule; for measurement only")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    audit = json.load(io.open(AUDIT, encoding="utf-8"))
    entries = []
    for bucket in ("MISSING-ALL", "MISSING-SOME", "ALL-UNSET"):
        for rec in audit.get(bucket, []):
            entries.append((bucket, rec["kokugakuin_id"], rec["holders"]))
    print("entries to resolve: %d" % len(entries))

    lines, detail = [], []
    by_reason = collections.Counter()
    stats = collections.Counter()
    for bucket, kid, holders in entries:
        placed, why, extra = resolve_entry(kid, holders,
                                           allow_elimination=args.elimination)
        for item, sec, how in placed:
            lines.append('%s|P13677|"%s"|P958|"%s"' % (item, kid, sec))
            by_reason[how.split(":")[0]] += 1
        stats[bucket] += len(placed)
        detail.append({"bucket": bucket, "kid": kid, "placed": len(placed),
                       "why": why, "assignments": [{"item": i, "section": s, "how": h}
                                                   for i, s, h in placed], **extra})
        if not placed:
            by_reason["nothing placed"] += 0

    lines = sorted(set(lines))
    print("\nassignments: %d" % len(lines))
    for how, c in by_reason.most_common():
        if c:
            print("   %-52s %d" % (how, c))
    print("\nby bucket:")
    for b, c in stats.most_common():
        print("   %-14s %d" % (b, c))

    # Structural check: an entry may claim each slot at most once. Cheap, and it is the
    # invariant this whole rewrite exists to guarantee, so it is asserted rather than trusted.
    seen = collections.Counter()
    for ln in lines:
        p = ln.split("|")
        seen[(p[2].strip('"'), p[4].strip('"'))] += 1
    dupes = [k for k, v in seen.items() if v > 1]
    print("\n(id, section) claimed more than once: %d" % len(dupes))
    if dupes:
        print("   " + ", ".join("%s/%s" % d for d in dupes[:10]))
        sys.exit("refusing to write a colliding batch")

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        "\n".join(lines) + ("\n" if lines else ""))
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(detail, ensure_ascii=False, indent=1))
    print("\nwrote %s (%d lines)" % (OUT, len(lines)))


if __name__ == "__main__":
    main()
