"""Recreate the shrines whose items were taken over by the ブルーノ・プラス repurposing.

Emma, 2026-08-19: *"we create new items for the ones lost due to their messing with them."* And
2026-08-25, authorising the build: the batch is generated now, staged, and submitted when the
lockout lifts.

**What was lost.** Three items were repurposed to describe different subjects entirely. The shrines
they used to describe now have no item at all:

    Q123044569  Kamo Shrine, Odawara      -> became 大美和神社, different coordinates
    Q134886554  Chikadono Shrine, Kumagaya -> became 近殿神社 in Yokosuka, a different prefecture
    Q134736575  見光寺, Hanno, Saitama      -> re-pointed to a different temple

**⛔ The repurposed items are NOT touched.** This is additive. Emma's standing rule (queue.md A5) is
document, don't touch, and no contact with that editor. Creating a fresh item for the lost shrine is
independent of whatever they are doing with the old one.

**Only these three, out of 24 archived items.** `destroyed_items/` is a record of every item that
editor damaged, and 21 of them were damaged *as themselves* — a property stripped, a label removed —
so they still describe the shrine they always did. Creating a new item for one of those would be a
straightforward duplicate. The three below are different in kind: the item was **repurposed** onto a
different subject, so the original shrine now has no item anywhere. That is what is being replaced.

**Where the content comes from.** `destroyed_items/*.json` records the pre-damage *revision id*, not
the content, so the labels, descriptions and statements are read back from that revision through the
API. That is the only surviving description of these shrines.

**The references are carried, and that is load-bearing — not tidiness.** `近殿神社`'s reading is
`ちかどのじんしゃ`, which is the じんしゃ-for-じんじゃ misspelling Emma has ruled on. Her rule is that a
*cited* one is preserved and an *uncited* one is corrected, and this one is cited to
`houjin-bangou.nta.go.jp` — the National Tax Agency registry, i.e. the corporation's legally
registered フリガナ. So the value is preserved. But a first draft of this script emitted statements
without their references, which would have put a bare `ちかどのじんしゃ` on a brand-new item — and the
next pass of the pipeline, seeing an uncited じんしゃ, would have "corrected" the legally registered
reading. **The citation is the thing that protects the value**, so it travels with it.

**One description is deliberately dropped.** `見光寺`'s pre-damage `ja` description read
"横浜市保土ケ谷区にある浄土宗の仏教寺院" — a temple in Hodogaya, Yokohama — while the item's own P131
(`Q850472` 飯能市), coordinates, address and English description all say Hannō, Saitama. It is
contradicted by every other statement on the item, so it is not re-imported. Nothing is invented in
its place; the new item simply has no ja description.

**A creation is a different QuickStatements shape** — `CREATE` followed by `LAST|…` lines — and
creations have been switched off in the past. This file is therefore kept SEPARATE from the
statement batches and is registered nowhere by default; wiring it into `ATOMIC_FILES` is a
deliberate act, not a side effect of running this.

⛔ Generates only. Nothing is created before the Wikidata lockout lifts on 2026-09-18.

Usage:
    python modern-quickstatements/generate_lost_shrine_creates.py
"""
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

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(HERE, "destroyed_items")

# The repurposed three, named explicitly. NOT "every file in the archive" — see the
# module docstring; the other 21 archived items still describe their own subject.
LOST = ["Q123044569", "Q134736575", "Q134886554"]
OUT = os.path.join(HERE, "lost_shrine_creates.txt")
THROTTLE = 1.5

# Properties worth carrying onto the new item. Identifiers tying the record to the OLD
# item are deliberately excluded — the new item is a new record of the same shrine, not
# a clone, and re-asserting an external id that now resolves to the repurposed subject
# would propagate the damage.
CARRY = ["P31", "P17", "P131", "P625", "P825", "P6375", "P1814", "P1448"]

# Reference properties carried onto the new statements, in QuickStatements `S…` form.
# See the docstring: dropping these would strip the citation that marks a legally
# registered reading as deliberate rather than as a typo to be fixed.
REF_PROPS = ["P248", "P854", "P143", "P4656", "P813"]

# Descriptions that contradict the rest of their own item and are not re-imported.
DROP_DESC = {("Q134736575", "ja")}


def revision(revid):
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "prop": "revisions", "revids": str(revid),
         "rvprop": "content", "rvslots": "main", "format": "json", "formatversion": "2"})
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    time.sleep(THROTTLE)
    with urllib.request.urlopen(req, timeout=60) as r:
        page = json.loads(r.read().decode("utf-8"))["query"]["pages"][0]
    return json.loads(page["revisions"][0]["slots"]["main"]["content"])


def qs_value(snak):
    dv = snak.get("datavalue", {})
    v, t = dv.get("value"), dv.get("type")
    if t == "wikibase-entityid":
        return v.get("id")
    if t == "string":
        return '"%s"' % v
    if t == "monolingualtext":
        return '%s:"%s"' % (v["language"], v["text"])
    if t == "globecoordinate":
        return "@%s/%s" % (v["latitude"], v["longitude"])
    if t == "time":
        return "%s/%s" % (v["time"], v["precision"])
    return None


def refs_for(statement):
    """The statement's first reference, as QuickStatements `|S…|value` suffixes."""
    for ref in statement.get("references", []):
        out = []
        for pid in REF_PROPS:
            for snak in ref.get("snaks", {}).get(pid, []):
                val = qs_value(snak)
                if val is not None:
                    out.append("|S%s|%s" % (pid[1:], val))
        if out:
            return "".join(out)
    return ""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    lines, summary = [], []
    for qid in LOST:
        rec = json.load(io.open(os.path.join(ARCHIVE, qid + ".json"), encoding="utf-8"))
        revid = rec["pre_damage_revision"]["revid"]
        ent = revision(revid)

        block = ["CREATE"]
        labs = ent.get("labels") or {}
        descs = ent.get("descriptions") or {}
        for lg in sorted(labs):
            block.append('LAST|L%s|"%s"' % (lg, labs[lg]["value"].replace('"', "'")))
        for lg in sorted(descs):
            if (qid, lg) in DROP_DESC:
                print("  dropping %s description on %s (contradicts its own P131)" % (lg, qid))
                continue
            block.append('LAST|D%s|"%s"' % (lg, descs[lg]["value"].replace('"', "'")))
        # an entity with no aliases serialises them as [] , not {}
        aliases = ent.get("aliases")
        for al in (aliases if isinstance(aliases, dict) else {}).get("ja", []):
            block.append('LAST|Aja|"%s"' % al["value"].replace('"', "'"))
        n_st = 0
        for pid in CARRY:
            for st in (ent.get("claims") or {}).get(pid, []):
                val = qs_value(st["mainsnak"])
                if val is None:
                    continue
                block.append("LAST|%s|%s%s" % (pid, val, refs_for(st)))
                n_st += 1

        ja = labs.get("ja", {}).get("value", "(no ja label)")
        summary.append((qid, ja, revid, len(block) - 1, n_st))
        lines.extend(block)
        lines.append("")

    print("lost shrines to recreate: %d\n" % len(summary))
    for qid, ja, revid, n, n_st in summary:
        print("  %-14s %-24s from revision %s — %d lines, %d statements"
              % (qid, ja, revid, n, n_st))

    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines).rstrip("\n") + "\n")
    print("\nwrote %s" % OUT)
    print("NOT registered in ATOMIC_FILES — creations are switched on deliberately, not by default.")


if __name__ == "__main__":
    main()
