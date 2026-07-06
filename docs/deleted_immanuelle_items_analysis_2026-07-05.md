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

## RAG from the public deletion logs (corrected 2026-07-05 after Emma's note)

**Correction.** An earlier draft of this doc called content recovery "blocked, needs an admin
undelete export." That was premature — it flagged the admin-gated *undelete* link but never
probed the *public deletion log*. Emma: "the deletion logs are public just not the content …
we can agentic RAG stuff from it … cross reference the info we have." Correct. The public
`Special:Log` for each QID carries the deleting admin + a deletion **reason**, and for many
items the reason string even **preserves the item's label** (`content was: "X"`).
`rag_deleted_logs.py` pulls all 455 public logs (read-only, throttled) and cross-references
reason + byte-size + backlog #8's ill labels. Output: `deleted_log_rag.md` / `.json`.

### What the public logs actually yield

Deletion-reason buckets (455 items):
- **`empty-item`: 322** — deleted as "empty" (had a label but no statements). **273 of these
  carry a clean `content was: "X"` English label** recovered directly from the public log —
  kami (`Niwa-tsume no Mikoto`, `Mori-no-Kami`), shrines (`Morimasa Hachiman Shrine`), a whole
  cluster of `Izumo-taisha <place> Church` branch orgs, people, concepts. Median label length
  19 chars; all clean (no JSON/quote noise). This is the big RAG yield.
- **`author-request`: 96** — Immanuelle *herself* requested these deletions.
- **`batch-improperly-created`: 26** — the `[[Wikidata:Project chat/Archive/2025/08#Deletion
  of improperly created items]]` cleanup, which **Immanuelle initiated herself** (items she
  said were "created by mistake"; Addshore cleaned them up + their redirects).
- **`rfd-*`: 7** — RfD "no evidence for existence" / conflation; editors judged these
  non-existent → recreating invites re-deletion.

### The decisive findings for recreation

1. **273 of 455 deleted items have a clean recovered English label** from the public logs — a
   *large* actionable set, not a small one (an earlier draft of this doc wrongly called it
   small). These are the `empty-item` deletions that had a label but no statements — i.e.
   real Shinto entities that were deleted only for lacking claims. Give them proper sourced
   claims and they survive re-deletion. Full list: the "Recovered English labels" table in
   `deleted_log_rag.md` (+ `deleted_log_rag.json`).
2. **~122 were deleted at Immanuelle's OWN request** (96 author-request + 26 self-initiated
   batch). Recreating those undoes her own decision — leave unless she says otherwise. (These
   do NOT overlap the 273: author-request/batch comments carry no `content was:` label.)
3. **The labels can be combined with the shinto wiki** (Emma's point): each recovered label is
   very likely a shinto-miraheze page carrying real content (description, `{{ill}}`
   per-language labels, categories, jawiki sitelink) — the material to build a Wikidata item
   that survives review. **But this cross-reference needs a LIVE wiki search:** the repo mirrors
   only ~984 gated pages (need_translation/git_synced/duplicated_content/miraheze_unique/
   fandom_unique) and only **1 of the 273** labels matches locally; miraheze is also
   Cloudflare-blocked from the dev session. So "how much shinto-wiki content exists for these"
   **cannot be answered locally** — it needs a CI wiki-search pass (see next-step spec below).

**Therefore (revised):**
- Content recovery is **NOT hard-blocked** — public logs recover 273 clean labels with zero
  admin access. The earlier "needs an admin undelete export" call is withdrawn.

### What CI already stores + where the QID actually lives (investigated 2026-07-05, Emma-corrected)

- **wikidata-deleted** ills (had a QID, deleted): the `deleted_qids_in_ill` orchestrator op
  (every CI sweep) tags `[[Category:Pages with deleted QID in ill template]]` and rewrites the
  ill to `qid=DELETED_QID`. The original QID is **NOT lost** (an earlier draft wrongly said so):
  it is preserved discreetly in a `dd=` param on many ills, and — Emma's key point — it is in
  the **fandom wiki page HISTORY** for the rest (the shinto content was imported from fandom;
  fandom keeps history). Proven: the pre-overwrite fandom revision of `Niwa-tsume no Mikoto`
  carries `qid=Q135579706`, exactly matching the RAG's deleted QID for that label.
- **wikidata-less** ills (never created): `unresolved_ill_qid` op tags
  `[[Category:Pages with unresolved QID in ill template]]`, drained by `fix_ill_destinations.py`.
- CI **detects + categorises** both; the authoritative deleted-QID list + labels come from the
  Wikidata logs (the RAG). No `deleted_qids_report.txt` is committed; the #8 recreation
  generator is not scheduled (run once by hand).

### Built this session (Emma greenlit the cross-reference; corrected to use fandom)

- `crossref_deleted_labels.py` — for each RAG-recovered label, finds the **fandom**
  `{{ill|<label>|…}}` and pulls: the per-language **langlinks** (recreation content — they
  survive the `qid=DELETED_QID` overwrite), the current ill qid (`dd=` recoveries), the host
  page, and — with `--deep` — the ORIGINAL qid from fandom history, validated against the RAG.
  **Fandom, not miraheze**, because (a) miraheze is Cloudflare-blocked from dev (403) while
  fandom is reachable → this is verifiable locally, and (b) the original QID lives in fandom
  history. Pure ill-parsing/matching logic unit-tested (`tests/`, 8 cases, green); the fandom
  run was verified live (12-label sample → 9 matched, all with langlinks). Read-only; 429-bail.
- Also wired into `.github/workflows/recreate-deleted-crossref.yml` (weekly + dispatch) for
  periodic refresh, though — unlike miraheze work — it can also just be run locally.
- **Full `--deep` fandom run (2026-07-05):** 272 labels → **215 matched a fandom ill**, **213
  with per-language langlinks** (the recreation content), **203 with the original QID recovered
  from `dd=`/fandom history AND validated against the RAG deleted QID**, 13 with a jawiki
  sitelink. Each per-item record also carries the host page's categories (type signal) + its own
  wikidata item (relationship context). Per-item: `recreate-deleted-wikidata/shinto_wiki_crossref.md`/`.json`.
  This is the recreation surface, and 203 of them are QID-anchored (not just label-matched).
- **The ~122 self-deleted items are moot — confirmed not on the wikis** (Emma's guess, verified):
  0/122 carry a recovered label, and 0/15 sampled author-request/batch QIDs are referenced
  anywhere on fandom (`insource:"Q…"`). They were standalone Wikidata items Immanuelle created
  and removed — nothing references them, nothing to recreate from. Dropped from scope (no Emma
  decision needed).
- The truly-empty items with `content was: ""` (no label) + RfD-no-evidence items stay
  **OUT-OF-SCOPE**.
- **Net: the actionable recreation surface is the ~211 fandom-matched, langlink-bearing items**
  — feed vetted ones through backlog #8's human-gated generator (respecting the CLAUDE.md
  Wikidata rules). No standing open decision remains for Emma beyond that normal human gate.

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
