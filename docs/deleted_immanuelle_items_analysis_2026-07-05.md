# Deleted Immanuelle-created Wikidata items — context-dump analysis (2026-07-05)

Processing of the `context dump/` committed 2026-07-05 (`911bbfb`), for the queue item
"context dump review + agentic RAG on deleted Immanuelle-created Wikidata items". Feeds
backlog #8 (recreate-deleted-wikidata).

## What the dump contains

| File | What it is |
|---|---|
| `context dump/deleted.txt` | XTools export (2026-07-05) of **every deleted page created by `User:Immanuelle` on wikidata.org**. A MediaWiki wikitable: row # · QID · deletion timestamp (+ admin `Special:Undelete` link) · original byte size · public `Special:Log` link. |
| `context dump/chat dump.md` | Transcript of the interrupted prior session — its subject is backlog #1/#2/#8 (terminating-script retirement), **not** deleted-item content. |
| `context dump/Claude Code.html` + `_files/` | Saved rendering of that same Claude Code session page. |

## Extracted facts (deleted.txt)

- **455 distinct deleted Q-items** (all Main namespace; no properties).
- Byte-size distribution of the deleted content:
  - `<400 B`: **264 (58%)** — near-empty Wikidata stubs (a ~360-byte item JSON is essentially a label or two, no meaningful claims).
  - `400–1000 B`: 83
  - `1000–3000 B`: 107 (the substantive ones)
  - `>3000 B`: 1
- **Overlap with backlog #8's recovered set: 35.** Of the 36 old QIDs backlog #8 recovered from `[[Category:Pages with deleted QID in ill template]]` (the ill-target provenance comments), **35 are confirmed present in this deleted-Immanuelle list** — validating the queue's predicted overlap between "deleted Immanuelle items" and "the 304 deleted ill targets".

## The RAG blocker — stated explicitly (per the queue instruction, not fabricated)

**The dump gives the LIST of deleted QIDs but NOT their content.** Each row carries only the
QID, a deletion timestamp, a byte size, an admin-only `Special:Undelete` link (EmmaBot /
a non-admin cannot read deleted revisions), and a `Special:Log` link (public, but shows only
the deletion log entry — who/when/comment — never the content).

Agentic RAG cannot reconstruct a deleted Wikidata item from its QID alone: the QID number is
semantically opaque, and once deleted the item content is not publicly retrievable. The only
public inference channel is **cross-wiki references** — what other pages pointed at the QID —
and the one relevant corpus (the shinto-wiki `{{ill}}` templates) has **already been mined by
backlog #8**, which recovered exactly the 35 overlapping items above. Chasing the remaining
~420 via web archives / caches is near-zero-yield (58% are sub-400-byte stubs that were never
substantial) and RAG-expensive.

**Therefore:**
- The substantive-subset reconstruction is **BLOCKED-ON-USER-ACTION**: it needs an actual
  *content* export of the deleted items (an admin `Special:Undelete` dump / XTools content
  export), which only Emma (with adminship) can produce. The current dump is a *listing*, not
  a content dump.
- The ~264 sub-400-byte stubs are effectively **OUT-OF-SCOPE**: near-empty, low recreation
  value, and unlikely to survive Wikidata's deletion review even if recreated.
- The already-actionable path is unchanged: the 35 overlapping (and the broader 304 ill
  targets) are handled by backlog #8's shipped, human-gated generator — content sourced from
  the shinto-wiki ills, never from the opaque deleted QIDs.

## Incidental finding folded out of the chat dump

The `cleanup-loop.yml` scheduled-run failures on 2026-07-03 / 07-04 were a
**category-orchestrator step timeout (~160 min)** — the long-known category-sweep slowness
flagged in CLAUDE.md, not a code error and unrelated to the #1 deletions. The 2026-07-05 run
succeeded. No action needed beyond the existing category-catch-up awareness.

## What next session should do with this

1. If Emma wants the ~420 non-overlapping deleted items recreated, she must provide their
   **content** (admin undelete export) — the listing alone is insufficient. Flagged on
   `[[Open questions]]`.
2. Otherwise, treat backlog #8 (the 304 ill targets, content-recoverable from the shinto
   wiki) as the whole actionable surface, and let the stub majority stay deleted.
