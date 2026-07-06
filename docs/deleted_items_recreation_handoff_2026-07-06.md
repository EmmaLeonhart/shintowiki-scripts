# HANDOFF — deleted-Immanuelle-item recreation pipeline (2026-07-06)

**Read this first.** A session started on `main` prematurely while extensive related work was
happening on branch **`claude/work-queue-processing-ps5j2l`** (not yet merged). This document is
the bridge: what exists, where, why, and what to do next. Everything below lives on that branch
under `recreate-deleted-wikidata/` and `docs/`.

## 1. What this is

Immanuelle created ~455 Wikidata items that other editors later deleted (mostly as empty stubs
or at her own request). The goal: recover enough information on the genuinely-recoverable ones to
recreate them on Wikidata so they survive deletion review — **human-gated; nothing is submitted
to Wikidata autonomously** (CLAUDE.md Wikidata rules: QuickStatements pipeline only, no bespoke
editors, visibility is worse than data loss).

## 2. The pipeline (each script is isolated, tested, no auto-submit)

Run order, all in `recreate-deleted-wikidata/`:

1. **Source:** `../context dump/deleted.txt` — XTools export of the 455 deleted QIDs (QID +
   deletion timestamp + byte size + admin-gated undelete link). A LISTING, not content.
2. **`rag_deleted_logs.py`** → `deleted_log_rag.json` — pulls each item's PUBLIC Wikidata
   deletion log (admin, comment, reason). Recovers the English label from `content was:"X"`
   comments. Buckets: empty-item / author-request / batch-improperly-created / rfd-*.
3. **`crossref_deleted_labels.py --deep --apply`** → `shinto_wiki_crossref.json` — cross-refs each
   recovered label against **shinto.fandom.com** (fandom keeps page history and is NOT
   Cloudflare-blocked, unlike miraheze). Recovers per-language langlinks, host page(s),
   categories, and the ORIGINAL QID from `dd=` or fandom history (validated against the RAG QID).
4. **`build_item_json.py`** → `items/<QID>.json` (one per deleted QID) + `items/_index.json`.
   Merges 2×3 keyed by QID; sets `self_deleted` and `recreation_candidate` flags.
5. **`enrich_multilang.py`** → adds `enrichment.labels` (median 59 languages) using the project
   transliteration engine (`shinto-label-generator/translit_common.py`).
6. **`enrich_p31.py`** → adds `enrichment.p31` + `description_en` from the entity NAME.

`build_item_json.py` regenerates items from scratch (dropping enrichment), so after re-running it
you must re-run 5 and 6. All six are pure/deterministic except 2 and 3 (public read-only APIs,
throttled, 429-bail).

## 3. Data model — `items/<QID>.json`

```
deletion:        {timestamp, size_bytes, admin, comment, reason_bucket}
recovered_label: English label from the deletion log (or null)
self_deleted:    true = Immanuelle's own author-request/batch deletion (MOOT — see §5)
fandom:          {label, page, host_pages, langlinks, recovered_qid, qid_source,
                  qid_matches_rag, ja_sitelink, categories}   (null if unmatched)
recreation_candidate: true = matched a fandom ill + has langlinks + not self-deleted + not RfD
enrichment:      {romaji_reading, labels{lang:{label,source}}, label_count,
                  p31, p31_label, p31_property, description_en, type_confidence, type_source}
```

## 4. Current state (numbers)

- 455 deleted items → **213 recreation candidates** (215 fandom-matched; 2 dropped as RfD/dup).
- **203/215 QID-validated** against the RAG (original QID recovered from fandom history).
- All 213 candidates have **multilingual labels (median 59 languages)**.
- **134/213 have a P31** (kami 28, festival 26, Shinto shrine 42, human 19, Buddhist temple 9,
  kofun 6, dance 2, book 2). **79 left null for review** — see §6.
- 35 unit tests green (`recreate-deleted-wikidata/tests/`); CI-wired (`ci.yml`,
  `recreate-deleted-crossref.yml`).

## 5. Load-bearing decisions / gotchas (don't relearn these the hard way)

- **NEVER guess a P31.** Type comes from the entity NAME (Japanese suffix is definitional:
  祭→festival, 命/尊→kami, 社/宮→shrine, 寺→temple, 墳→kofun). A first pass that used the fandom
  HOST-PAGE categories was WRONG (mislabeled a kami as a "disambiguation page" because it sits on
  a shrine-dab page) — reverted. jawiki lookup is useless here (0/18 have articles — that's why
  they were empty-deleted).
- **Verify every type QID against live Wikidata.** Verification caught kami ≠ Q1751020 (a tennis
  match). Correct: kami Q524158, Shinto shrine Q845945, human Q5, festival Q132241, Buddhist
  temple Q5393308, kofun Q1141225, dance Q11639, book Q571.
- **The ~122 self-deleted items are MOOT** — confirmed not on the wikis (0/122 labeled, 0/15
  sampled QIDs referenced on fandom). They were standalone items Immanuelle made and removed. Do
  not recreate them.
- **Recreation itself is human-gated.** Wikidata creation is off-limits autonomously; go/no-go +
  the minimum-claim-set-per-type are Emma decisions (on `[[Open questions]]`).
- **miraheze is Cloudflare-blocked from the dev session; fandom and Wikidata are reachable.**

## 6. What's left (next work)

1. **The 79 unclassified P31s** (the #2 queue item). Genuinely ambiguous: Izumo-taisha branch
   *churches* (教会 — building vs congregation?), sacred-site/pilgrimage lists (霊場), geographic
   features (海 sea, 湯 hot spring), rank/系 systems, and person names without clan markers. Add
   rules only where a name signal is definitional; otherwise leave for human review. Do NOT guess.
2. **"A bit more data to really run"** (Emma) — beyond P31+description+labels: P17=Japan (Q17) for
   shrines/festivals/temples, P131 (located in admin territory) from the host-page place, maybe
   coordinates. Keep it authoritative.
3. **Human-gated recreation** — only after Emma's go/no-go + min-claim-set decision, feed vetted
   items through the QuickStatements pipeline (respect CLAUDE.md).

## 7. Branch / merge status

All of this is on `claude/work-queue-processing-ps5j2l`, **not merged to `main`**. The `main`
session that started prematurely should treat this branch as the source of truth for the
deleted-item work and avoid duplicating it. Full narrative: `DEVLOG.md` (2026-07-05/06 entries);
analysis: `docs/deleted_immanuelle_items_analysis_2026-07-05.md`; blockers/questions:
`git_synced/Open questions.wiki` + the "Blockers" section at the end of `queue.md`.
