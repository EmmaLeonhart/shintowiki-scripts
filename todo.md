# Todo

Long-horizon backlog — genuine, not-yet-done tasks ONLY. Active session work is in [queue.md](queue.md); finished work + history in [DEVLOG.md](DEVLOG.md); how the pipelines/orchestrators work lives in [CLAUDE.md](CLAUDE.md) and `docs/` (e.g. `docs/remote_queue_pipeline.md`). Reference/narrative and completed/dropped items do NOT belong here.

## Label-generator horizons (merged 2026-07-04 from the subtree's deleted todo.md)

> Long-term goal: every Shinto shrine, temple, deity, and related entity on
> Wikidata labeled in all supported languages (reference: Q687168 with every
> language column filled). Formal expansion roadmap:
> [`docs/mass-label-expansion-plan.md`](docs/mass-label-expansion-plan.md);
> the active BFS-driven work is in `queue.md`.

- [ ] **EN/FR/ID gap regularization:** some shrines have labels in one or two
  of English/French/Indonesian but not all three (old technical failures).
  Analyze the gaps, then a pipeline to fill missing ones where the others exist.
  _(2026-07-05 assessment — likely partly superseded: the BFS/multilang pipeline now
  generates fr + id fills for covered shrines INTO the drip, so a live-Wikidata gap
  query is confounded — it can't cleanly separate "genuinely unaddressed" from "queued,
  fills after the 2027 ramp". NEEDS-DECISION from Emma: is this still wanted as a
  distinct same-source cross-fill, or is it subsumed by the BFS drip? Don't build the
  fill-pipeline until that's clarified.)_
- [x] **QuickStatements provenance comments:** annotate output lines with the
  source label they derive from (id-label for most languages, ja kanji for zh,
  reading-vs-hanja for ko). _DONE 2026-07-05 — every transliteration generator emits
  a `# Source:`/`# <source>` comment (korean/indonesian/chinese/tokiponize already
  did; write_qs 4-tuple + all 8 category generators + multilang wired this day).
  N/A: shikinaisha_lists (frame-built titles) + hand-authored *_translations. See
  DEVLOG 2026-07-05 and queue.md "DONE — QuickStatements provenance comments"._
- [ ] **Long-tail language expansion:** `python language_registry.py` prints
  the uncovered languages by label count; th is the biggest (needs a real Thai
  transliterator — pre-posed vowel signs).

## Repo / script tasks

- **Full program audit:** [`docs/program_audit_2026-06.md`](docs/program_audit_2026-06.md) (2026-06-05) — the single read-through of the whole machine: CI invocation graph, orchestrators+ops, legacy CI scripts, the Wikidata QS path, the sync/cloud-queue loop, known kludges, in-flight migrations, keep/fix/retire verdicts.



## Wiki content tasks (manual / human review)

> **Scripting plans for everything in this section:** [`docs/wiki_content_scripting_plans_2026-05.md`](docs/wiki_content_scripting_plans_2026-05.md) — per-item design (trigger, state model, multi-cycle pacing, effort). Recommended build order: duplicate-QID tail + multiple-wikidata-link reports (small) → `fix_ill_destinations.py` (medium) → Japanese category translation (large, phased) → recreate-deleted-WD (gated on Emma + freeze).

- [ ] **ILLs without `WD=` / "Unknown" targets.** **Detection + fix SHIPPED and running in CI:** the `unresolved_ill_qid` orchestrator op populates `[[Category:Pages with unresolved QID in ill template]]`, and `fix_ill_destinations.py` (wired into `wiki-cleanup.yml`, `--apply --max-edits 50`) confidently resolves and fills `WD=` per page, leaving low-confidence/genuinely-unresolvable ones in the category by design. **Residual is inherent per-page human review** (the deliberately-skipped low-confidence cases, incl. Shikinaisha ILLs pointing at "Unknown") — not a build task. Nothing autonomous left here beyond letting the loop drain it.
- [ ] **Duplicate QID disambiguation pages** — mostly DRAINED (verified 2026-05-30: `[[Category:Double category qids]]` = **7** members, `[[Category:Duplicated qid category redirects]]` = **0**; the ~621 historical figure is long gone). `resolve_double_category_qids.py` auto-handles same-target cases in the cleanup loop; the 7-page tail is the genuinely-different-target review remnant. Low priority — nearly done.
- [ ] **Translate category names in `[[Category:Japanese language category names]]`** → canonical English titles. **THE real remaining backlog (1189 subcategories as of 2026-06-05).** Phases a+b SHIPPED 2026-06-05 (`generate_category_translation_moves.py`, wired monthly before `move_categories`): deterministic dated-maintenance transform (only ~2 cats) + **Wikidata-anchored resolver** (1067/1189 carry `{{wikidata link|Q…}}`; the Wikimedia-category item's enwiki sitelink/label is the authoritative English `Category:` name — first partial run resolved 205/483). **Remaining:** (c) place-name gazetteer for the residual content cats with no Wikidata-category anchor (`さいたま市の神社` → `Shinto shrines in Saitama`; the `<place>の神社`/`<place>市`/`<place>県` productive patterns — this is the guessing-risk part, build a JP→EN gazetteer bootstrapped from Wikidata place labels), and (d) the genuinely-unresolvable human queue. The residual list is auto-maintained at `docs/category_translation_residual.md`.
- [ ] **Multiple `{{wikidata link}}` on one page.** **Detection + surfacing SHIPPED and running in CI:** the `multiple_wikidata_links` orchestrator op populates `[[Category:Pages with multiple wikidata links]]`, and `report_multiple_wikidata_links.py` (wired into `render-duplicate-qids.yml`, `--apply`) renders each member's competing QIDs + Wikidata labels/descriptions side-by-side to the `[[Multiple wikidata links]]` review page; the op self-heals a page out of the category once it's back to one link. **Residual is inherent per-case human review** (pick the correct QID / split the page) — not a build task.
- [ ] **`[[Category:Pages with duplicated content]]` + remaining `need_translation/` pages.** Mostly handled by the cloud-queue worker (`docs/remote_queue_pipeline.md`); manual review only for the hard cases — canonical-title choice / history merge, and the 9 large kokuzō articles. NEVER strip `[[Category:Need translation]]` without verifying the body is actually English (the sync deletes the file when the category goes).



## Wikidata (social / high-care — respect the freeze to 2026-06-06; QuickStatements pipeline only)

- [ ] **26 interlanguage-cohort pages with no Wikidata item.** Leftover from the 2026-06-07 interlanguage-resolution op: biographies, sect-specific docs, shinto-coined terms, list/disambiguation pages that have no matching Wikidata item. They either need an article created on Wikidata first (overlaps the deleted-QID recreation item below — and creating WD items is off-limits autonomously) or should simply stay unconnected. Not forced; no autonomous action.

- [ ] **Recreate deleted Wikidata items.** Info-gathering generator SHIPPED 2026-07-05: `recreate-deleted-wikidata/generate_recreate_quickstatements.py` (isolated dir, NOT auto-submitted, CI-wired) walks `[[Category:Pages with deleted QID in ill template]]` → 304 distinct deleted **ill targets** → `CREATE` blocks + `review.md`. **Design correction:** the deleted QIDs are the ill *targets*, NOT the pages (which already have their own items), so it does NOT emit `P11250|"shinto:…"` (that would duplicate). Old QIDs kept as `#` provenance comments (36 recovered incl. the QID-in-title data-loss bug). **Remaining (deferred, see `queue.md`):** per-target content research so items survive Wikidata's deletion churn, a minimum-claim-set-per-type decision, and human-gated submission through the QS pipeline. Actual recreation is out of scope until researched.
