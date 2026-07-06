# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here.

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Resolve the 18 duplicate categories from the failed QS (`errors.txt`)

Of the 30 failed CREATEs: **12 (real jawiki target, no item) were re-run and all created
successfully** (done). The remaining **18 are shinto-wiki Japanese-named DUPLICATES** — the
`{{wikidata link||ja|Category:X}}` target X (`20世紀アジアの女性王族`, `19世紀のKokugakuist`, …)
is not a jawiki page but a *shinto* category duplicating the English-named one. All 30 English
pages are git-synced in `git_synced/Category%3A*.wiki`.

- [ ] Tag the 18 Japanese-named shinto duplicate categories into the deprecation pipeline
  (`[[Category:Japanese language category names]]`) so the cloud translates + `move_categories`
  merges them into the English survivor. (`19世紀のKokugakuist` is a bad-text-replacement dup of
  `19世紀の国学者` — same treatment; the target is signal, don't delete.) Drains only once the
  category orchestrator stops timing out — see the end-of-queue "Fix the pipeline" item. The 12
  already-created pages can be un-synced.

## 2. `Template:Wikidata link` consolidation (Emma issue 1)

Issue 2 (template invisible when QID empty) is FIXED — the interwiki chain now renders outside the
QID `#if` (miraheze copy; goes live next `sync_miraheze_unique_pages` run). Remaining:

- [ ] **Consolidation isn't running properly.** Multiple `{{translated page}}` / interwiki
  templates aren't being merged into the single `{{wikidata link}}` (e.g. Category:19th century
  Kokugaku scholars has 3 redundant `{{translated page}}` → `Pages using duplicate arguments in
  template calls`; Category:1988 books similar). Find the consolidation op (the 2026-04-29
  "consolidate interlanguage links into wikidata link" behaviour) and make it actively run / fix it.

## 3. Recreate deleted Wikidata items — continue (Emma is running the CREATEs)

Dataset in `recreate-deleted-wikidata/`; readiness `items/_recreation_readiness.md`. Emma creates
the items via QuickStatements (human-gated, minimal claim set); relinking ills to new QIDs is the
autonomous follow-up. **Repair is disposable — dumb direct text swaps, no durable pipelines.**

- [ ] **Finish P31 typing of the 24 still-untyped candidates** (186/210 typed). Type only where a
  name signal is definitional; verify each type QID live; NEVER guess; leave ambiguous ones for
  Emma. Tail: Shimabara Sea, court offices 御匙/御鑰, Kyoto's Three Kumano, Ōtsuki Hotel, Color
  Index, Inner Palace, Nakatomi Sakado clan, Kibi no Anaumi, Kimi-no-Mori, Shōkyō, Benten Chigo,
  rope attachment projections, Hozumi-Suzuki Clan Genealogy (+ verify JR Ise Sangū Line & rhyolitic
  welded tuff for existing-item duplicates).
- [ ] **Edit the ills on the 144 git-synced pages** (`[[Category:Pages with deleted QID in ill
  template]]`). Per `{{ill|…|qid=DELETED_QID}}`: sections → `[[Page#Section]]`; real entities →
  relink to created/live QID; duplicates → live QID. Un-sync each resolved page.
- [ ] **Optional per-item enrichment:** P131 (from host-page place) + coordinates — authoritative only.

## 4. `Template:Ill` wrongful-deletion fix (easy)

The fandom bot recurrently deletes `shinto.fandom.com/wiki/Template:Ill` ("no Shinto equivalent")
because the check doesn't count a miraheze **redirect** as an equivalent.

- [ ] **Mitigation (easy):** make `Template:Ill` git-synced on BOTH wikis so the sync restores it.
- [ ] **Root cause:** make the fandom delete-orphans check follow miraheze redirect targets first.

## 5. Long-tail language transliterators (build task)

- [ ] **Thai (`th`)** transliterator — pre-posed vowel signs (33/135 labels). `pa/km/lo/dz/new/mad/shn`
  (≤16 labels) + `cdo` have no converter — only if one arrives. `python
  shinto-label-generator/language_registry.py` lists uncovered languages by count.

## 6. Merged-QID redirect resolution op (LOW — very end; least time-dependent)

A Wikidata **merge** turns the old item into a *redirect* (NOT "missing"), so nothing
canonicalizes it — `deleted_qids_in_ill`/`wikidata_lookup` only act on `"missing"` entities.

- [ ] Orchestrator op: for each `{{ill|…|qid=Q…}}` (and `{{wikidata link}}`), query
  `wbgetentities`; if the entity is a redirect, rewrite the QID to the target (follow the chain).
  Light op; throttle + 429-bail; cache per run. Durable maintenance.

## Fix the pipeline

As seen here https://github.com/EmmaLeonhart/shintowiki-scripts/actions/workflows/cleanup-loop.yml It appears the entire cleanup look has just been broken for ages, this needs fixing

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
