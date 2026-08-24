"""What did a merge actually move? Attribute every statement on a target to its source.

Emma asked this twice on `[[Open questions]]`, the second time as *"Oh my god please investigate
why the shrine was removed and what was going on with it"*, about 御笏神社 (`Q110915859`):

    "Please investigate the shrine and what links to it in order to see if any errors may have
     been introduced by the redirect being resolved and why I originally merged it. The fact
     they were merged is nontrivial as to why I did it and what information may have been lost."

A merge is hard to reason about after the fact because it destroys its own evidence. The source
item is blanked before it is turned into a redirect, so reading it now shows nothing, and the
target just quietly has more statements than it used to. The only durable record is the pair of
revisions either side of the merge edit.

So this walks the target's history, finds every `wbmergeitems-from` edit, and for each one diffs
the target's statements immediately before and immediately after. What appears in the "after" and
not the "before" is what that source contributed — which is the question, and the thing no amount
of reading the current item can answer.

READ-ONLY. It issues a handful of revision fetches against `www.wikidata.org` and writes nothing,
so the Wikidata lockout (`shinto_miraheze/wikidata_editing_lockout.state`) does not apply. Per
`CLAUDE.md` it deliberately does not use SPARQL: this is a walk of one item's history, not a sweep.

Usage:
    python modern-quickstatements/audit_merge_provenance.py Q110915859
    python modern-quickstatements/audit_merge_provenance.py Q110915859 --json out.json
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

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

API = "https://www.wikidata.org/w/api.php"
THROTTLE = 1.0


def api(params):
    params.update({"format": "json", "formatversion": "2"})
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    time.sleep(THROTTLE)
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def revisions(qid):
    """Every revision, oldest first, with timestamp/comment/user."""
    out, cont = [], {}
    while True:
        params = {"action": "query", "prop": "revisions", "titles": qid,
                  "rvlimit": "max", "rvprop": "ids|timestamp|comment|user", "rvdir": "newer"}
        params.update(cont)
        data = api(params)
        page = data["query"]["pages"][0]
        out.extend(page.get("revisions", []))
        if "continue" not in data:
            return out
        cont = data["continue"]


def entity_at(revid):
    data = api({"action": "query", "prop": "revisions", "revids": str(revid),
                "rvprop": "content|timestamp", "rvslots": "main"})
    rev = data["query"]["pages"][0]["revisions"][0]
    return json.loads(rev["slots"]["main"]["content"])


def statement_keys(entity):
    """A statement as a comparable string: property|value|sorted qualifiers.

    Statement GUIDs are deliberately NOT used. A merge rewrites them, so keying on the GUID
    would report every statement as new and answer nothing.
    """
    keys = {}
    for pid, statements in (entity.get("claims") or {}).items():
        for st in statements:
            value = st["mainsnak"].get("datavalue", {}).get("value")
            if isinstance(value, dict):
                value = value.get("id") or value.get("text") or json.dumps(value, sort_keys=True)
            quals = []
            for qpid, snaks in (st.get("qualifiers") or {}).items():
                for snak in snaks:
                    qv = snak.get("datavalue", {}).get("value")
                    if isinstance(qv, dict):
                        qv = qv.get("id") or qv.get("text") or json.dumps(qv, sort_keys=True)
                    quals.append("%s=%s" % (qpid, qv))
            key = "%s -> %s" % (pid, value)
            if quals:
                key += "  [%s]" % ", ".join(sorted(quals))
            keys[key] = keys.get(key, 0) + 1
    return keys


def labels_of(entity):
    labs = entity.get("labels") or {}
    if not isinstance(labs, dict):
        return {}
    return {k: v["value"] for k, v in labs.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qid")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    revs = revisions(args.qid)
    print("%s: %d revisions, %s .. %s"
          % (args.qid, len(revs), revs[0]["timestamp"], revs[-1]["timestamp"]))

    merges = [(i, r) for i, r in enumerate(revs) if "wbmergeitems-from" in (r.get("comment") or "")]
    if not merges:
        print("no wbmergeitems-from edits in this item's history")
        return

    report = {"qid": args.qid, "revisions": len(revs), "merges": []}

    for i, rev in merges:
        source = (rev["comment"].rsplit("|", 1)[-1].strip().rstrip("*/ ").strip()
                  if "|" in rev["comment"] else "?")
        before = statement_keys(entity_at(revs[i - 1]["revid"])) if i else {}
        after = statement_keys(entity_at(rev["revid"]))

        gained = []
        for key, n in sorted(after.items()):
            delta = n - before.get(key, 0)
            for _ in range(max(0, delta)):
                gained.append(key)
        lost = []
        for key, n in sorted(before.items()):
            delta = n - after.get(key, 0)
            for _ in range(max(0, delta)):
                lost.append(key)

        src_labels = {}
        try:
            src_rev = revisions(source)
            pre = [r for r in src_rev if "Clearing item" not in (r.get("comment") or "")
                   and "wbcreateredirect" not in (r.get("comment") or "")
                   and "wbmergeitems-to" not in (r.get("comment") or "")]
            if pre:
                src_labels = labels_of(entity_at(pre[-1]["revid"]))
        except Exception as exc:                                    # noqa: BLE001
            src_labels = {"__error__": str(exc)}

        print("\n=== merged FROM %s at %s by %s" % (source, rev["timestamp"], rev["user"]))
        if src_labels:
            shown = {k: v for k, v in src_labels.items() if k in ("ja", "en", "fr", "id")}
            print("    source was: %s" % (shown or src_labels))
        print("    statements before: %d   after: %d   gained: %d   lost: %d"
              % (sum(before.values()), sum(after.values()), len(gained), len(lost)))
        for key in gained:
            print("    + %s" % key)
        for key in lost:
            print("    - %s" % key)

        report["merges"].append({
            "source": source, "timestamp": rev["timestamp"], "user": rev["user"],
            "source_labels": src_labels, "gained": gained, "lost": lost,
            "before_count": sum(before.values()), "after_count": sum(after.values()),
        })

    if args.json_out:
        path = args.json_out if os.path.isabs(args.json_out) else \
            os.path.join(os.path.dirname(os.path.abspath(__file__)), args.json_out)
        io.open(path, "w", encoding="utf-8").write(
            json.dumps(report, ensure_ascii=False, indent=2))
        print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
