# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here.

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Recreate deleted Wikidata items — continue (Emma is running the CREATEs)

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

## 2. `Template:Ill` wrongful-deletion fix (easy)

The fandom bot recurrently deletes `shinto.fandom.com/wiki/Template:Ill` ("no Shinto equivalent")
because the check doesn't count a miraheze **redirect** as an equivalent.

- [ ] **Mitigation (easy):** make `Template:Ill` git-synced on BOTH wikis so the sync restores it.
- [ ] **Root cause:** make the fandom delete-orphans check follow miraheze redirect targets first.

## 3. Long-tail language transliterators (build task)

- [ ] **Thai (`th`)** transliterator — pre-posed vowel signs (33/135 labels). `pa/km/lo/dz/new/mad/shn`
  (≤16 labels) + `cdo` have no converter — only if one arrives. `python
  shinto-label-generator/language_registry.py` lists uncovered languages by count.

## 4. Merged-QID redirect resolution op

A Wikidata **merge** turns the old item into a *redirect* (NOT "missing"), so nothing
canonicalizes it — `deleted_qids_in_ill`/`wikidata_lookup` only act on `"missing"` entities.

- [ ] Orchestrator op: for each `{{ill|…|qid=Q…}}` (and `{{wikidata link}}`), query
  `wbgetentities`; if the entity is a redirect, rewrite the QID to the target (follow the chain).
  Light op; throttle + 429-bail; cache per run. Durable maintenance.

## 5. Fix the cleanup-loop pipeline

The whole cleanup-loop has been failing for ~a week: the **category-orchestrator step times out
at 160 min** every run (its allpages(ns=14) walk can't finish), so the category deprecation /
translation / interlang-consolidation never drains. Everything else in the loop passes.

- [ ] Make the category orchestrator finish within the window — make it resumable via a cursor so
  each run processes a bounded slice and continues next run (never restarts from zero), and/or
  split the namespace across jobs, and/or raise the 160-min step timeout. Then the deprecation of
  the 18 tagged duplicate categories (and the interlang consolidation) drains.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
