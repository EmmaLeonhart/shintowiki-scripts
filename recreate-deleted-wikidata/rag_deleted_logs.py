#!/usr/bin/env python3
"""Agentic-RAG enrichment of the deleted Immanuelle-created Wikidata items.

Emma's correction (2026-07-05): the deleted-item *content* is admin-gated, but the
deletion *logs are public*. This script cross-references the weak-but-real signals we
actually have:

  1. ``context dump/deleted.txt`` — the XTools listing (QID, deletion timestamp, byte size).
  2. The public Wikidata deletion log for each QID (deleting admin + deletion reason).
  3. Backlog #8's recovered ill-target labels (``recreate_quickstatements.txt``) — the
     shinto-wiki ``{{ill}}`` templates that referenced the QID, which carry per-language
     labels for the subset that overlaps.

Output: ``deleted_log_rag.md`` — an enriched, bucketed report telling the next session
which deleted items are worth recreating (have recoverable labels / a substantive size /
a non-"empty" deletion reason) versus which are genuinely-empty stubs deleted for being
empty (leave deleted).

READ-ONLY against public Wikidata APIs. No wiki writes; no Wikidata edits. Bails on HTTP
429 (per CLAUDE.md). Throttles reads at 0.3s.
"""
import io
import os
import re
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DELETED_TXT = os.path.join(REPO_ROOT, "context dump", "deleted.txt")
RECREATE_TXT = os.path.join(HERE, "recreate_quickstatements.txt")
OUT_MD = os.path.join(HERE, "deleted_log_rag.md")

UA = ("EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:Immanuelle; "
      "immanuelleleonhart@gmail.com) rag_deleted_logs")
READ_THROTTLE = 0.3


def api(params):
    params = {**params, "format": "json"}
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("HTTP 429 from Wikidata — bailing immediately (CLAUDE.md policy).")
            sys.exit(2)
        raise


def parse_deleted(text):
    """Yield (qid, timestamp, size_bytes) from the XTools wikitable."""
    rows = re.split(r"\n\|-\n", text)
    for row in rows:
        qm = re.search(r"\[\[:(Q\d+)\]\]", row)
        if not qm:
            continue
        tm = re.search(r"timestamp=(\d{14})", row)
        sm = re.search(r"FORMATNUM:(\d+)", row)
        yield (qm.group(1),
               tm.group(1) if tm else "",
               int(sm.group(1)) if sm else None)


def load_ill_recovered():
    """QID -> the ill provenance/label context from backlog #8 output."""
    if not os.path.exists(RECREATE_TXT):
        return {}
    text = open(RECREATE_TXT, encoding="utf-8").read()
    # Old deleted QIDs are carried as '# ... Qxxx ...' provenance comment lines,
    # grouped under each CREATE block. Map every Qref on a comment line to the
    # nearest preceding label line for a little context.
    recovered = {}
    block_labels = []
    for line in text.splitlines():
        if line.startswith("CREATE"):
            block_labels = []
        m = re.search(r'LAST\s+L\w+\s+(\w+)\s+"([^"]+)"', line)
        if m:
            block_labels.append(f'{m.group(1)}:{m.group(2)}')
        for q in re.findall(r"Q\d+", line):
            if line.lstrip().startswith("#"):
                recovered.setdefault(q, list(block_labels[:3]))
    return recovered


def reason_bucket(comment):
    c = (comment or "").lower()
    if "empty" in c:
        return "empty-item"
    if "improperly created" in c or "per request" in c or "project_chat" in c or "project chat" in c:
        return "batch-improperly-created"
    if "duplicate" in c or "merge" in c:
        return "duplicate/merge"
    if "test" in c or "vandal" in c or "nonsense" in c:
        return "test/vandalism"
    if not c:
        return "no-reason-given"
    return "other"


def main():
    text = open(DELETED_TXT, encoding="utf-8").read()
    deleted = list(parse_deleted(text))
    ill = load_ill_recovered()
    print(f"Parsed {len(deleted)} deleted QIDs; {len(ill)} carry recovered ill context.")

    records = []
    for i, (qid, ts, size) in enumerate(deleted, 1):
        r = api({"action": "query", "list": "logevents", "letitle": qid,
                 "leprop": "user|timestamp|comment|action|type", "lelimit": 5})
        evs = r.get("query", {}).get("logevents", [])
        dele = next((e for e in evs if e.get("type") == "delete"
                     and e.get("action") == "delete"), None)
        comment = dele.get("comment", "") if dele else ""
        admin = dele.get("user", "") if dele else ""
        records.append({
            "qid": qid, "size": size, "del_ts": ts,
            "admin": admin, "comment": comment,
            "bucket": reason_bucket(comment),
            "ill_recovered": qid in ill,
            "ill_labels": ill.get(qid, []),
        })
        if i % 50 == 0:
            print(f"  ...{i}/{len(deleted)}")
        time.sleep(READ_THROTTLE)

    # Buckets
    from collections import Counter
    buckets = Counter(r["bucket"] for r in records)
    admins = Counter(r["admin"] for r in records if r["admin"])
    ill_n = sum(1 for r in records if r["ill_recovered"])
    substantive = [r for r in records if (r["size"] or 0) >= 1000]

    lines = []
    lines.append("# Deleted Immanuelle-items — public-log RAG cross-reference\n")
    lines.append("Auto-generated by `rag_deleted_logs.py` (read-only, public Wikidata "
                 "deletion logs). Emma 2026-07-05: the *content* is admin-gated but the "
                 "*logs are public* — this cross-references log reason + size + backlog #8 "
                 "ill-recovery to triage what is worth recreating.\n")
    lines.append(f"- Total deleted Immanuelle Q-items: **{len(records)}**")
    lines.append(f"- With recovered ill labels (backlog #8 overlap): **{ill_n}**")
    lines.append(f"- Substantive (>=1000 bytes at deletion): **{len(substantive)}**\n")
    lines.append("## Deletion-reason buckets\n")
    for b, n in buckets.most_common():
        lines.append(f"- `{b}`: {n}")
    lines.append("\n## Deleting admins\n")
    for a, n in admins.most_common(10):
        lines.append(f"- {a}: {n}")

    # The actionable subset: NOT plain "empty-item", OR has ill labels, OR substantive.
    actionable = [r for r in records
                  if r["ill_recovered"] or r["bucket"] != "empty-item"
                  or (r["size"] or 0) >= 1000]
    lines.append(f"\n## Candidate-for-recreation subset ({len(actionable)})\n")
    lines.append("Excludes items that are *both* deleted-as-empty AND sub-1000-byte AND "
                 "not ill-recovered — those are genuine empty stubs, leave deleted.\n")
    lines.append("| QID | bytes | reason bucket | admin | ill? | comment |")
    lines.append("|---|---|---|---|---|---|")
    for r in sorted(actionable, key=lambda r: -(r["size"] or 0)):
        c = r["comment"].replace("|", "\\|")[:70]
        lines.append(f"| {r['qid']} | {r['size']} | {r['bucket']} | {r['admin']} "
                     f"| {'Y' if r['ill_recovered'] else ''} | {c} |")

    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\nWrote {OUT_MD}")
    print("Buckets:", dict(buckets))
    print(f"Actionable subset: {len(actionable)} / {len(records)}")


if __name__ == "__main__":
    main()
