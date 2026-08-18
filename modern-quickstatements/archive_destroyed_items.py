#!/usr/bin/env python3
"""Preserve, in their ORIGINAL form, every Wikidata item ブルーノ・プラス has damaged.

Emma 2026-07-10:

    "All this stuff that they are destroying … we should be preserving the
    information on them so they could potentially be recreated. I want something
    that will actually go through their edits and find and track the destructive
    edits that they've been making, which would mean large-scale property removals
    and things like that. Basically, we'll be archiving all of the items that
    they've removed properties from in their original forms, and then we will figure
    out what to do with the information once there's more information on how this
    person works."

    "They seem destructive, but it isn't clear that they are an existential threat.
    These actions that specifically preserve the stuff that they've damaged are very
    good because it means that we have the ability to [act] once we know what's
    going on with them."

Two shrines already have **no item at all** on Wikidata — Kamo Shrine (Odawara) and
Chikadono Shrine (Saitama). Their statements exist now only in revision history,
which is exactly the thing this script copies into the repo.

READ-ONLY. It never edits Wikidata, never posts, and never touches the watched user.

WHAT COUNTS AS DESTRUCTIVE
--------------------------
Any edit whose summary shows a *removal*: `wbremoveclaims`, `wbsetlabel-remove`,
`wbsetdescription-remove`, `wbsetaliases-remove`, `wbsetsitelink-remove`. Additions
and description rewrites are not destructive and are ignored.

WHAT IS ARCHIVED
----------------
For each damaged item, the full entity JSON of the revision **immediately before
their first destructive edit on that item** — the last undamaged state. If they come
back and damage it further, the archive is not overwritten: the original is the point.

    python archive_destroyed_items.py [--refresh] [--dry-run]

Output: `destroyed_items/<QID>.json` + `destroyed_items/INDEX.md`.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import datetime
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(HERE, "destroyed_items")
INDEX = os.path.join(ARCHIVE_DIR, "INDEX.md")

WD_API = "https://www.wikidata.org/w/api.php"
UA = WIKIDATA_USER_AGENT
WATCHED_USER = "ブルーノ・プラス"

# A removal of anything: statements, labels, descriptions, aliases, sitelinks.
DESTRUCTIVE = re.compile(
    r"wbremoveclaims|wbset(?:label|description|aliases|sitelink)-remove")

_PROP = re.compile(r"Property:(P\d+)")
_TERM = re.compile(r"wbset(label|description|aliases|sitelink)-remove:\d+\|([a-z-]*)")


def _api(params):
    params = dict(params, format="json")
    req = urllib.request.Request(WD_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(4)


def fetch_contributions(user=WATCHED_USER):
    """Every Wikidata edit, newest first."""
    edits, cont = [], None
    while True:
        p = {"action": "query", "list": "usercontribs", "ucuser": user,
             "uclimit": "500", "ucprop": "title|timestamp|comment|ids"}
        if cont:
            p["uccontinue"] = cont
        d = _api(p)
        edits += d.get("query", {}).get("usercontribs", [])
        cont = d.get("continue", {}).get("uccontinue")
        if not cont:
            return edits
        time.sleep(0.3)


def is_destructive(comment):
    return bool(DESTRUCTIVE.search(comment or ""))


def is_item(title):
    return bool(re.match(r"^Q\d+$", title or ""))


def destructive_by_item(edits):
    """{qid: [edit, …]} — only items where something was removed, oldest first."""
    out = {}
    for e in edits:
        if is_item(e["title"]) and is_destructive(e.get("comment")):
            out.setdefault(e["title"], []).append(e)
    for qid in out:
        out[qid].sort(key=lambda e: e["timestamp"])
    return out


def first_destructive_timestamp(item_edits):
    return item_edits[0]["timestamp"]


def summarize_removals(item_edits):
    """What was taken off the item, for the index."""
    props, terms = [], []
    for e in item_edits:
        c = e.get("comment") or ""
        m = _PROP.search(c)
        if m and "wbremoveclaims" in c:
            props.append(m.group(1))
        t = _TERM.search(c)
        if t:
            terms.append("{}:{}".format(t.group(1), t.group(2) or "?"))
    return props, terms


def revision_by_id(revid):
    """Full content of one revision, or None."""
    d = _api({"action": "query", "prop": "revisions", "revids": revid,
              "rvprop": "ids|timestamp|user|content", "rvslots": "main",
              "formatversion": 2})
    pages = d.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return None
    revs = pages[0].get("revisions", [])
    return revs[0] if revs else None


def pre_damage_revid(item_edits):
    """The PARENT of their first destructive edit on the item.

    Anchoring on the parent revision id, not on a timestamp, is load-bearing.
    `rvstart` is **inclusive**, so `rvstart=<first destructive timestamp>` with
    `rvdir=older` returns that very edit whenever it cannot be excluded — which is
    exactly the case for the seven items they created themselves. `Q140476265` was
    archived with 0 labels and 0 statements: we had captured the blanking, not the
    state before it.
    """
    return item_edits[0].get("parentid") or None


def is_own_creation(item_edits, rev):
    """True when the pre-damage revision was authored by them.

    Two different situations, both flagged: an item they created and then blanked
    (`Q140476265`, 琵琶島神社, emptied two minutes after creation), and an item where
    an additive edit of theirs immediately preceded the removal (`Q28069431`: they
    set a description at 06:20, then stripped the claims at 06:25). In both cases the
    parent revision is still the last undamaged state, which is what we want.
    """
    return bool(rev) and rev.get("user") == WATCHED_USER


def entity_summary(entity):
    """Counts, so INDEX.md is readable without opening the JSON."""
    labels = entity.get("labels") or {}
    claims = entity.get("claims") or {}
    sitelinks = entity.get("sitelinks") or {}
    return {
        "labels": len(labels),
        "en_label": (labels.get("en") or {}).get("value"),
        "ja_label": (labels.get("ja") or {}).get("value"),
        "properties": sorted(claims, key=lambda p: int(p[1:])),
        "statement_count": sum(len(v) for v in claims.values()),
        "sitelinks": sorted(sitelinks) if isinstance(sitelinks, dict) else [],
    }


def archive_path(qid):
    return os.path.join(ARCHIVE_DIR, qid + ".json")


def build_record(qid, item_edits, rev):
    entity = json.loads(rev["slots"]["main"]["content"])
    props, terms = summarize_removals(item_edits)
    return {
        "qid": qid,
        "archived_at": datetime.datetime.now(datetime.timezone.utc)
                               .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "damaged_by": WATCHED_USER,
        "first_destructive_edit": first_destructive_timestamp(item_edits),
        "destructive_edit_count": len(item_edits),
        "properties_removed": props,
        "terms_removed": terms,
        "pre_damage_revision": {
            "revid": rev["revid"],
            "timestamp": rev["timestamp"],
            "user": rev["user"],
            # True when the ONLY pre-damage revision is one of their own: they
            # created the item and then blanked it. Still worth preserving.
            "authored_by_watched_user": rev.get("authored_by_watched_user", False),
        },
        "summary": entity_summary(entity),
        "entity": entity,
    }


def write_index(records):
    lines = [
        "# Items damaged by ブルーノ・プラス — preserved originals",
        "",
        "Each `<QID>.json` holds the **full entity JSON of the last revision before their first",
        "destructive edit on that item**, so the item can be recreated or repaired later. Written",
        "by `archive_destroyed_items.py`; read-only, never overwritten once captured.",
        "",
        "Emma 2026-07-10: *\"we will figure out what to do with the information once there's more",
        "information on how this person works.\"*",
        "",
        "| QID | Was | Statements | Properties removed | Terms removed | First damaged |",
        "|---|---|---:|---|---|---|",
    ]
    for r in sorted(records, key=lambda r: r["first_destructive_edit"]):
        s = r["summary"]
        was = s["en_label"] or s["ja_label"] or "—"
        lines.append("| [`{}`](https://www.wikidata.org/wiki/{}) | {} | {} | {} | {} | {} |".format(
            r["qid"], r["qid"], was, s["statement_count"],
            " ".join("`%s`" % p for p in r["properties_removed"]) or "—",
            " ".join("`%s`" % t for t in r["terms_removed"]) or "—",
            r["first_destructive_edit"][:10]))
    lines += ["", "{} items archived.".format(len(records)), ""]
    io.open(INDEX, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="re-capture items already archived (normally refused: the "
                         "ORIGINAL state is the point)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    edits = fetch_contributions()
    damaged = destructive_by_item(edits)
    print("{} Wikidata edits; {} items had something removed".format(
        len(edits), len(damaged)))

    records, skipped, failed = [], 0, 0
    for qid, item_edits in sorted(damaged.items()):
        path = archive_path(qid)
        if os.path.exists(path) and not args.refresh:
            records.append(json.load(io.open(path, encoding="utf-8")))
            skipped += 1
            continue
        parent = pre_damage_revid(item_edits)
        rev = revision_by_id(parent) if parent else None
        if rev is None:
            print("  {}: their first edit CREATED the item; nothing precedes it".format(qid))
            failed += 1
            continue
        rev["authored_by_watched_user"] = is_own_creation(item_edits, rev)
        rec = build_record(qid, item_edits, rev)
        records.append(rec)
        s = rec["summary"]
        own = " [pre-damage rev by them]" if rev.get("authored_by_watched_user") else ""
        print("  {}  {:<28} {:>2} statements, {:>2} labels  (rev {} by {}){}".format(
            qid, (s["en_label"] or s["ja_label"] or "?")[:28], s["statement_count"],
            s["labels"], rev["revid"], rev["user"], own))
        if not args.dry_run:
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                json.dumps(rec, ensure_ascii=False, indent=2))
        time.sleep(0.4)

    if not args.dry_run and records:
        write_index(records)
    theirs = sum(1 for r in records
                 if r["pre_damage_revision"].get("authored_by_watched_user"))
    print("\n{} archived ({} newly captured, {} already held, {} created by the "
          "destructive edit itself)".format(
              len(records), len(records) - skipped, skipped, failed))
    print("{} have a pre-damage revision authored by them — either an item they created "
          "and then blanked, or an additive edit of theirs immediately before the "
          "removal. The parent revision is still the last undamaged state.".format(theirs))
    print("-> {}".format(ARCHIVE_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
