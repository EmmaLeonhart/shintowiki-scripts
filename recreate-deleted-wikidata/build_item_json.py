#!/usr/bin/env python3
"""Emit one JSON file per deleted Immanuelle Wikidata item, consolidating everything
we know about it (Emma 2026-07-05: "make json files on each deleted qid for the info
we have on them").

Merges, keyed by QID:
  * ``deleted_log_rag.json``  — the XTools listing + public deletion log (size, deletion
    timestamp, deleting admin, deletion comment, reason bucket, `content was:` label,
    ill-recovery flag/labels).
  * ``shinto_wiki_crossref.json`` — the fandom cross-reference (host page(s), per-language
    langlinks, current/recovered QID + source, jawiki sitelink, host-page categories,
    whether the recovered QID matches the RAG).

Writes ``items/<QID>.json`` (one per deleted QID) plus an ``items/_index.json`` manifest.
Pure local file merge — no network. Deterministic (sorted); safe to re-run.
"""
import io
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
RAG_JSON = os.path.join(HERE, "deleted_log_rag.json")
CROSSREF_JSON = os.path.join(HERE, "shinto_wiki_crossref.json")
OUT_DIR = os.path.join(HERE, "items")

SELF_DELETED_BUCKETS = {"author-request", "batch-improperly-created"}


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_record(rag, cross):
    """Consolidate one QID's RAG record + optional crossref record into a flat profile."""
    qid = rag["qid"]
    bucket = rag.get("bucket")
    rec = {
        "qid": qid,
        "deletion": {
            "timestamp": rag.get("del_ts"),
            "size_bytes": rag.get("size"),
            "admin": rag.get("admin"),
            "comment": rag.get("comment"),
            "reason_bucket": bucket,
        },
        # Recovered content: the label from the public 'content was:' deletion comment.
        "recovered_label": rag.get("content_was") or None,
        # Emma's own deletions (author-request / self-initiated batch) — confirmed not on
        # the wikis, out of recreation scope.
        "self_deleted": bucket in SELF_DELETED_BUCKETS,
        "ill_recovered": rag.get("ill_recovered", False),
        "ill_labels": rag.get("ill_labels", []),
        "fandom": None,
        "recreation_candidate": False,
    }
    if cross and cross.get("matched"):
        rec["fandom"] = {
            "label": cross.get("label"),
            "page": cross.get("fandom_page"),
            "host_pages": cross.get("host_pages", []),
            "langlinks": cross.get("langlinks", {}),
            "current_ill_qid": cross.get("current_ill_qid") or None,
            "recovered_qid": cross.get("recovered_qid"),
            "qid_source": cross.get("qid_source"),
            "qid_matches_rag": cross.get("qid_matches_rag", False),
            "ja_sitelink": cross.get("ja_sitelink"),
            "categories": cross.get("categories", []),
        }
        # A viable recreation candidate: matched a fandom ill with recoverable per-language
        # content, and NOT one of Emma's own deletions / an editor "no-evidence" call.
        rec["recreation_candidate"] = (
            bool(cross.get("langlinks"))
            and not rec["self_deleted"]
            and bucket not in ("rfd-no-evidence", "rfd-conflation")
        )
    return rec


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rag = load(RAG_JSON)
    cross_by_qid = {c["qid"]: c for c in load(CROSSREF_JSON)}
    if not rag:
        print(f"No RAG data at {RAG_JSON} — run rag_deleted_logs.py first.")
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    index = []
    candidates = 0
    for r in sorted(rag, key=lambda r: r["qid"]):
        rec = build_record(r, cross_by_qid.get(r["qid"]))
        path = os.path.join(OUT_DIR, f"{rec['qid']}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2, sort_keys=True)
        index.append({
            "qid": rec["qid"],
            "recovered_label": rec["recovered_label"] or (rec["fandom"] or {}).get("label"),
            "reason_bucket": rec["deletion"]["reason_bucket"],
            "self_deleted": rec["self_deleted"],
            "fandom_matched": rec["fandom"] is not None,
            "recreation_candidate": rec["recreation_candidate"],
        })
        candidates += rec["recreation_candidate"]

    with open(os.path.join(OUT_DIR, "_index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"Wrote {len(index)} per-QID JSON files to {OUT_DIR}/")
    print(f"  fandom-matched: {sum(1 for i in index if i['fandom_matched'])}")
    print(f"  recreation candidates: {candidates}")
    print(f"  self-deleted (out of scope): {sum(1 for i in index if i['self_deleted'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
