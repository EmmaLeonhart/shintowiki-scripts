# Todo

Long-horizon backlog — genuine, not-yet-done tasks ONLY. Active session work is in [queue.md](queue.md); finished work + history in [DEVLOG.md](DEVLOG.md); how the pipelines/orchestrators work lives in [CLAUDE.md](CLAUDE.md) and `docs/` (e.g. `docs/remote_queue_pipeline.md`). Reference/narrative and completed/dropped items do NOT belong here.

## Label-generator horizons (merged 2026-07-04 from the subtree's deleted todo.md)

> Long-term goal: every Shinto shrine, temple, deity, and related entity on
> Wikidata labeled in all supported languages (reference: Q687168 with every
> language column filled). Formal expansion roadmap:
> [`docs/mass-label-expansion-plan.md`](docs/mass-label-expansion-plan.md);
> the active BFS-driven work is in `queue.md`.

- [x] **QuickStatements provenance comments:** annotate output lines with the
  source label they derive from (id-label for most languages, ja kanji for zh,
  reading-vs-hanja for ko). _DONE 2026-07-05 — every transliteration generator emits
  a `# Source:`/`# <source>` comment (korean/indonesian/chinese/tokiponize already
  did; write_qs 4-tuple + all 8 category generators + multilang wired this day).
  N/A: shikinaisha_lists (frame-built titles) + hand-authored *_translations. See
  DEVLOG 2026-07-05 and queue.md "DONE — QuickStatements provenance comments"._
- [ ] **Long-tail language expansion — hand-building is CLOSED; the tail is an LLM
  job.** Re-measured 2026-07-29: 116 languages in `query.csv`, **54 covered, 59 todo**
  (the 2026-07-06 batch — th via wunsen, my/km/lo/dz via Aksharamukha, new/pa/mad, cdo —
  is what moved it from 47/66).

  This item used to read "Chinese topolects needing their own romanization tables like
  cdo did (nan/hak/wuu/yue/lzh) — do only if a real label count justifies it". Both
  halves were wrong, and [`docs/language_coverage.md`](docs/language_coverage.md)
  already said so:
  - **The label-count criterion cannot decide anything.** `cdo`, `km`, `new`, `pa` and
    `mad` are not in `query.csv` at all — they were built at **zero** existing labels.
    A count threshold would have blocked every recent build.
  - **These specific languages fail the verification gate**, which is why they were
    left, not low demand: `nan`/`hak`/`nan-latn-*` re-spell the name phonetically,
    `yue`/`wuu` mix traditional and simplified zh, `ka` keeps the Japanese suffix.
    A romanization table does not fix a convention we cannot verify.
  - `en-gb`/`en-us`/`en-ca` (11/8/7 labels, the largest uncovered counts after `nan`)
    must NOT be filled: language fallback already covers regional English, so they
    would be pure duplicates of `en`.

  So there is no hand-build left to do here. The gate-failing languages route to the
  LLM (the same RAG path the category translations use) or wait for Emma to change
  scope. Do not open a romanization-table build off the back of a label count.

## Repo / script tasks

- **Full program audit:** [`docs/program_audit_2026-06.md`](docs/program_audit_2026-06.md) (2026-06-05) — the single read-through of the whole machine: CI invocation graph, orchestrators+ops, legacy CI scripts, the Wikidata QS path, the sync/cloud-queue loop, known kludges, in-flight migrations, keep/fix/retire verdicts.



## Wiki content tasks (manual / human review)

> **Scripting plans for everything in this section:** [`docs/wiki_content_scripting_plans_2026-05.md`](docs/wiki_content_scripting_plans_2026-05.md) — per-item design (trigger, state model, multi-cycle pacing, effort). Recommended build order: duplicate-QID tail + multiple-wikidata-link reports (small) → `fix_ill_destinations.py` (medium) → Japanese category translation (large, phased) → recreate-deleted-WD (gated on Emma + freeze).

- [ ] **ILLs without `WD=` / "Unknown" targets.** **Detection + fix SHIPPED and running in CI:** the `unresolved_ill_qid` orchestrator op populates `[[Category:Pages with unresolved QID in ill template]]`, and `fix_ill_destinations.py` (wired into `wiki-cleanup.yml`, `--apply --max-edits 50`) confidently resolves and fills `WD=` per page, leaving low-confidence/genuinely-unresolvable ones in the category by design. **Residual is inherent per-page human review** (the deliberately-skipped low-confidence cases, incl. Shikinaisha ILLs pointing at "Unknown") — not a build task. Nothing autonomous left here beyond letting the loop drain it.
- [ ] **Duplicate QID disambiguation pages** — mostly DRAINED (verified 2026-05-30: `[[Category:Double category qids]]` = **7** members, `[[Category:Duplicated qid category redirects]]` = **0**; the ~621 historical figure is long gone). `resolve_double_category_qids.py` auto-handles same-target cases in the cleanup loop; the 7-page tail is the genuinely-different-target review remnant. Low priority — nearly done.
- [ ] **Translate category names in `[[Category:Japanese language category names]]`** → canonical English titles. Deterministic resolvers all SHIPPED (`generate_category_translation_moves.py`, wired monthly before `move_categories`): dated-maintenance transform + Wikidata-anchored resolver + phase-(c) place gazetteer (`の神社`→"Shinto shrines in X", `の寺院`/`の建築物`/`の歴史`/`の重要文化財`; jawiki→enwiki place + P31 gate; `の旧県社`/bare-`郡` verified as having no enwiki category convention → residual, 2026-07-06). **Everything the deterministic resolvers can't confidently name now routes to agentic RAG** (queue #5, 2026-07-06): `build_category_translation_queue.py` writes a work-file per residual category → the cloud remote routine researches the English name → `collect_category_translations.py` folds answers into `category_moves.csv`. So no "guessing-risk" gazetteer to hand-build and no dead human-only queue — the residual drains via RAG. Nothing left to build here.
- [ ] **Multiple `{{wikidata link}}` on one page.** **Detection + surfacing SHIPPED and running in CI:** the `multiple_wikidata_links` orchestrator op populates `[[Category:Pages with multiple wikidata links]]`, and `report_multiple_wikidata_links.py` (wired into `render-duplicate-qids.yml`, `--apply`) renders each member's competing QIDs + Wikidata labels/descriptions side-by-side to the `[[Multiple wikidata links]]` review page; the op self-heals a page out of the category once it's back to one link. **Residual is inherent per-case human review** (pick the correct QID / split the page) — not a build task.
- [ ] **`[[Category:Pages with duplicated content]]` + remaining `need_translation/` pages.** Mostly handled by the cloud-queue worker (`docs/remote_queue_pipeline.md`); manual review only for the hard cases — canonical-title choice / history merge, and the 9 large kokuzō articles. NEVER strip `[[Category:Need translation]]` without verifying the body is actually English (the sync deletes the file when the category goes).



## Wikidata (social / high-care — respect the freeze to 2026-06-06; QuickStatements pipeline only)

- [ ] **26 interlanguage-cohort pages with no Wikidata item.** Leftover from the 2026-06-07 interlanguage-resolution op: biographies, sect-specific docs, shinto-coined terms, list/disambiguation pages that have no matching Wikidata item. They either need an article created on Wikidata first (overlaps the deleted-QID recreation item below — and creating WD items is off-limits autonomously) or should simply stay unconnected. Not forced; no autonomous action.

- [x] **Recreate deleted Wikidata items — REFERENCED targets only (DONE 2026-07-06).** The deleted QIDs that were **referenced by `{{ill}}` templates** on wiki pages were recreated this session (Emma ran the QuickStatements) and their links relinked. **The ~213 UNREFERENCED deleted items are NOT to be recreated** (Emma 2026-07-06): they were deleted for a reason, they aren't breaking any links, and restoring them is explicitly unwanted. No open work here.

