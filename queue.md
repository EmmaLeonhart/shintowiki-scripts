# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here. **Nothing here is "parked" or "out of scope" — every item gets done; ordering is
just priority.**

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Get the cleanup-loop reliably working (top priority — enables everything else)

TWO root causes found + fixed:
1. **Category timeout** (`1fa6c414`): ns14 ballooned to 28,176 pages × heavy per-page ops → blew the
   160-min step timeout. Added a wall-clock self-stop (`MAX_RUN_SECONDS=145min`). VALIDATED — the
   07-06 run's category-orchestrator step ran GREEN in 6m11s.
2. **Site-build push race** (`generate-pages.yml`): the "Commit updated _site to repo" step did a
   single `git push` with no retry; a sibling job pushed first → `! [rejected] main -> main` → the
   step exit-1'd and reddened the WHOLE cleanup-loop (the actual 07-06 failure). Fixed: fetch-rebase
   -retry loop (5 attempts) + non-fatal exit (mirrors `commit_state.sh`; _site is cosmetic — Pages
   deploys from the uploaded artifact, not the repo commit).

- [ ] Confirm on a live fire that the cleanup-loop now green-completes end-to-end (both fixes in).
  Next scheduled fire (`23 2 * * *`) validates, or a manual dispatch. If it still reds, diagnose the
  next-failing step.
- [ ] THROUGHPUT (separate, lower priority): a full category cycle still takes ~many fires at
  ~1000 pages/145min. Only if draining item 2 proves too slow: skip history_offload/fandom_mirror on
  the ~3k enwiki-junk cats or shard ns14. No premature optimization.

## 2. Drain the category-deprecation back-pressure (depends on #1)

Once the loop runs: the **18 Japanese-named duplicate categories** tagged this session into
`[[Category:Japanese language category names]]` get translated (cloud) + merged by
`move_categories`; the interlang consolidation (`{{wikidata link}}` merge) and the new
`merged_qids_in_ill` op sweep the wiki.

- [ ] Confirm the 18 tagged dups actually move/merge once the loop is healthy; spot-check a few.

## 3. Category-name translation — deterministic resolvers (done); residual → agentic RAG (item 6)

`[[Category:Japanese language category names]]` (~1186 subcats). The DETERMINISTIC resolvers are done:
dated-maintenance transform, phase-1 Wikidata-category-anchored (covers ~all QID'd cats incl. `の神社`
shrines via authoritative enwiki category sitelink), and phase-4 place gazetteer (`の建築物`/`の歴史`/
`の神社`/`の寺院`/`の重要文化財`, jawiki→enwiki place + P31 gate). These only handle patterns with an
authoritative Wikidata anchor or a verified enwiki convention.

- [ ] The remaining residual (`の旧県社`, bare `<place>郡` districts, `の画像提供依頼`, `<sect>の寺院`,
  etc. — auto-refreshed at `docs/category_translation_residual.md`) is NOT out of scope. It is exactly
  the agentic-RAG target in **item 5** — every one gets an English name via cloud RAG, not left for a
  human. (The deterministic resolvers just avoid GUESSING inside a mechanical script; RAG does the
  research the script can't.)

## 4. cdo (Min Dong) transliterator — maintenance only

Built + wired (gated `cdoify` in `generate_chinese_quickstatements.py`, registered, emits `cdo.txt`;
`cdo_readings.json` 1502 entries, 1502/2192 corpus-char coverage). No open task — the only ongoing
work is coverage growth:

- [ ] (low, recurring) Rerun `python fetch_cdo_readings.py --corpus --apply` after the zh corpus
  grows, to pick up new shrine-name chars. 690 chars currently have no Wiktionary `md=` reading
  (genuine gaps); gated cdo simply withholds labels containing them. Not a blocker.

## 5. Agentic RAG the ENTIRE category-translation residual — 100% all in

Emma 2026-07-06: the residual is NOT human-only / out of scope — RAG every one. The deterministic
resolvers (item 3) handle only Wikidata-anchored + verified-convention cases; everything else in
`docs/category_translation_residual.md` (~425 Japanese-script category names) goes through **agentic
RAG on the cloud** — the same remote-routine mechanism that translates `need_translation/` prose and
`duplicated_content/`. Go 100% all in: every residual category gets a canonical English name, none
left behind.

- [ ] Build a `remote_queue.py` source that emits each residual category as an agentic-RAG item:
  worker reads the category (its members + jawiki/Wikidata context), determines the canonical English
  `Category:` name (research, not a mechanical guess — the point of RAG), and appends
  `source,destination` to `category_moves.csv` (consumed by the existing monthly `move_categories`).
  Uncapped; the cloud consumer paces itself. Verify a sample of proposed names before wiring to move.

## 6. POLICY: deleted-QID ills → best EXISTING Wikidata item, never recreate

Emma 2026-07-06: recreation is a losing game — a recreated item (Q140447362 "Tropical decor",
南国趣味) got re-deleted, breaking its relink. **Do not recreate.** For any `{{ill|…|qid=DELETED_QID}}`
(or an ill whose QID is later deleted), search Wikidata for the BEST EXISTING item and set `qid=` to
it (or de-ill if there's no reasonable match). Best-effort; imperfect beats a dead link.

- Tropical decor (the ONLY current case, on Jungle bath) → RAG'd to **Q368949 "exoticism"** and
  relinked. Done.
- [ ] If deleted-QID ills accumulate again (the `deleted_qids_in_ill` op re-flags dead QIDs on its
  sweep), resolve each RAG→existing-item, not by recreation. Only worth a `remote_queue` RAG source
  (mirror the category_translation one) if the volume returns; a handful get done by hand.
  Retire `recreate-deleted-wikidata/generate_recreate_quickstatements.py` (superseded by this policy).

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
