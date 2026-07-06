# Backlog board — resolution analysis (2026-07-05 session)

Emma-requested input for the next session: for each of the 8 `BACKLOG_ITEMS`
(`site/generate_pages.py`), where it stands after the 2026-07-05 session and what
is left. Sources: the backlog board, `todo.md`, and the DEVLOG 2026-07-05 entries.
Status is one of **RESOLVED** / **PARTIAL** / **NOT STARTED**; "what's left" tags
autonomous-buildable work vs. inherent human review / decisions.

Bottom line up front: **#1 and #2 are fully resolved.** **#3, #4, #6, #7 are
shipped automation whose only residual is inherent human review or the remote
cloud routine — not build tasks.** **#5 and #8 hold the genuinely-buildable
remainder.** Of those two, **#5 (Japanese category names) is the single
highest-value autonomous thread** — #8's recreation step is gated on per-target
research plus Emma decisions and is out of scope until then.

---

## #1 retire-terminating-scripts — RESOLVED (this session)

All four July-gated terminating scripts confirmed inert, unwired from
`wiki-cleanup.yml`, and deleted (`57bcb140`): `reimport_from_enwiki` and
`migrate_talk_pages` were drained input/rebuild jobs; `normalize_category_pages`
and `remove_legacy_cat_templates` were ported to orchestrator ops
(`ops/normalize_category_page.py`, `ops/remove_legacy_cat_templates.py`) and
deleted as standalones. The two dead local launchers that still invoked them
(`cleanup_loop.sh`, `cleanup loop.bat`) were also removed. **Nothing left.**

## #2 audit-legacy-scripts — RESOLVED (this session)

The keep/fix/retire verdicts have lived in `docs/program_audit_2026-06.md` §3/§8
since 2026-06-05. The one open empirical gap — "are the July-gated terminating
scripts actually inert?" — was closed by #1. Re-audited `wiki-cleanup.yml`: every
uncommented `python3 …` step resolves to an existing script; the only
reimport/overwrite references left are inside commented-out blocks. The stale
header comment (still listing the 4 deleted scripts as "kept here") and the stale
`queue.md` bullet were cleaned up (`6d56f4a1`); item removed from the board and
`todo.md`. **Nothing left.**

## #3 ill-missing-wikidata (ILLs without `WD=` / "Unknown") — PARTIAL (shipped automation; residual = human review)

Detection and fix both **shipped and running in CI**: the `unresolved_ill_qid`
orchestrator op populates `[[Category:Pages with unresolved QID in ill template]]`
as it sweeps mainspace, and `fix_ill_destinations.py` (wired into
`wiki-cleanup.yml`, `--apply --max-edits 50`) confidently resolves and fills
`WD=` per page, leaving low-confidence cases in the category by design. **What's
left:** inherent per-page human review of the deliberately-skipped low-confidence
targets (incl. Shikinaisha ILLs pointing at "Unknown"). No autonomous build work
— just let the loop keep draining.

## #4 duplicate-qid-tail — PARTIAL, effectively drained (nearly resolved)

The ~621-member historical-figure bulk is long gone. As of 2026-05-30:
`[[Category:Double category qids]]` = **7** members;
`[[Category:Duplicated qid category redirects]]` = **0**.
`resolve_double_category_qids.py` auto-handles same-target cases in the cleanup
loop. **What's left:** the 7-page genuinely-different-target review tail —
inherent human review, low priority. No build work.

## #5 japanese-category-names → English — PARTIAL (the real buildable backlog; advanced this session)

THE substantive remaining backlog (1189 subcategories as of 2026-06-05). Phases
(a)+(b) shipped 2026-06-05 (`generate_category_translation_moves.py`, wired
monthly before `move_categories`): deterministic dated-maintenance transform
(~2 cats) + Wikidata-anchored resolver (1067/1189 carry `{{wikidata link|Q…}}`;
the Wikimedia-category item's enwiki sitelink is the authoritative English
`Category:` name). **This session** added phase (c) — the place-name gazetteer
for `<place>の歴史` / `<place>の建築物` content cats (214 of the 578-entry
residual): resolves on the place stem (strip suffix → jawiki article →
Wikidata → enwiki sitelink), gated by a P31 Japanese-administrative-division
check, 90% hit rate on a 60-cat sample, 8 unit tests, verified E2E. **What's left
(autonomous-buildable — the highest-value thread):**
- other productive suffixes not yet handled: `の神社` (no cat-QID cases),
  `の重要文化財` / `の国宝`, the `の旧県社` / `の旧郷社` / `の旧村社`
  shrine-rank-by-place family, `の画像提供依頼` maintenance, bare `<place>郡`
  districts;
- gazetteer misses (non-place stems, disambiguated prefecture-prefixed stems)
  that currently fall to the residual report (`docs/category_translation_residual.md`);
- (d) the genuinely-unresolvable human queue.

## #6 multiple-wikidata-links — PARTIAL (shipped automation; residual = human review)

Detection and surfacing both **shipped and running in CI**: the
`multiple_wikidata_links` orchestrator op populates
`[[Category:Pages with multiple wikidata links]]`, and
`report_multiple_wikidata_links.py` (wired into `render-duplicate-qids.yml`)
renders each member's competing QIDs + Wikidata labels/descriptions side-by-side
to the `[[Multiple wikidata links]]` review page. The op self-heals a page out of
the category once it is back to one link. **What's left:** inherent per-case human
review (pick the correct QID / split the page). No build work.

## #7 duplicated-content + need-translation — PARTIAL (remote routine + human review)

Whole-body duplication to merge, plus pages still tagged for translation. Mostly
worked by the **claude.ai cloud-queue routine** (`remote_queue.json`,
`docs/remote_queue_pipeline.md`) — bulk LLM-grunge, not local-work-loop build
work. Manual review only for the hard cases: canonical-title choice, history
merge, and the 9 large kokuzō articles. **Guardrail:** never strip
`[[Category:Need translation]]` without verifying the body is actually English —
the sync deletes the local file when the category goes. No local build work.

## #8 recreate-deleted-wikidata — PARTIAL (info-gathering generator shipped; recreation deferred/out of scope)

**Shipped this session:** `recreate-deleted-wikidata/generate_recreate_quickstatements.py`
(isolated dir, NOT auto-submitted, 7 unit tests, CI-wired). Walks
`[[Category:Pages with deleted QID in ill template]]` (144 pages) → **304 distinct
deleted ill targets** → info-rich `CREATE` blocks in `recreate_quickstatements.txt`
+ human-review `review.md`. Design correction that mattered: the deleted QIDs are
the ill **targets** (sub-topics), NOT the pages (which already carry their own
items), so it does **not** emit `P11250|"shinto:…"` (that would duplicate the
page's item and reproduce the re-deletion). 36 old QIDs recovered as `#`
provenance comments (incl. 5 from the QID-written-into-the-label-slot data-loss
bug). Only **7/304** currently have a safe jawiki sitelink (the notability
anchor). **What's left (deferred — recreation itself is out of scope per Emma):**
- per-target content research so each item survives Wikidata's deletion churn
  (304 targets, only ~36 with recovered QIDs — small enough to research
  individually); **NEEDS-INVESTIGATION**, overlaps the queued "agentic RAG on
  deleted Immanuelle-created items" and the context dump;
- a minimum-viable-claim-set-per-type decision (person / shrine / facility /
  concept) that survives deletion review; **NEEDS-DECISION (Emma)**;
- only after review: feed vetted blocks through the QuickStatements pipeline,
  human-gated, respecting the Wikidata-editing rules in `CLAUDE.md`.

Related open threads (not board items but adjacent): the 26 interlanguage-cohort
pages with no Wikidata item (`todo.md`) and creating WD items being off-limits
autonomously.

---

## Where the next session should spend effort

1. **#5 phase (c)/(d) continuation** — the only substantial *autonomous* build
   work left. Extend `generate_category_translation_moves.py` to the next
   productive suffix family (candidates above), each behind the same
   authoritative-not-guessed anchor + P31 gate + unit tests, appending to
   `category_moves.csv`.
2. **#8 research tier** — bounded (304 targets) but gated on Emma's
   minimum-claim-set decision and on the deleted-item RAG source (the context
   dump); do the info-gathering RAG, but do not recreate until the decision
   lands.
3. **#3 / #4 / #6 / #7** — no build work; let the loops drain and leave the
   human-review tails alone.

For context, the multilingual label / translation tier tracked separately in
`queue.md` is COMPLETE (transliteration matrix shipped + drip-delivered; every
confidently-actionable translation done); what remains there is remote-routine
drift and the deliberate 2027-05-23 delivery ramp — not backlog-board work.
