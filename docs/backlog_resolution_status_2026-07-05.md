# Backlog board — resolution status after the 2026-07-05 session

Emma-requested hand-off analysis: for each of the 8 `BACKLOG_ITEMS`
(`site/generate_pages.py`), how far it got this session and what is left. Sources:
the board itself, `todo.md`, `queue.md`, and the 2026-07-05 `DEVLOG.md` entries.

**Status legend:** RESOLVED (nothing buildable left) · SHIPPED-AUTOMATION (build
done; residual is inherent human review or a remote routine, not a build task) ·
PARTIAL (buildable work remains) · DEFERRED (scoped out this session by Emma).

Highest-value thread for the next session: **#5 phase (c) tail** (the only item with
concrete, authoritative-not-guessing build work left) and **#8 per-target research**
(largest, but gated on content research + Emma-approved recreation).

---

## #1 retire-terminating-scripts — RESOLVED

All four July-gated terminating scripts (`reimport_from_enwiki`, `migrate_talk_pages`,
`normalize_category_pages`, `remove_legacy_cat_templates`) confirmed inert and deleted
from the repo (`57bcb140`); the two cycling ones were already ported to orchestrator
ops, the two enwiki-driven ones drained. Follow-up same day removed the dead local
launchers (`cleanup_loop.sh`, `cleanup loop.bat`) that still invoked them.
**Left:** nothing.

## #2 audit-legacy-scripts — RESOLVED

Keep/fix/retire verdicts have lived in `docs/program_audit_2026-06.md` §3/§8 since
2026-06-05; the one open empirical gap (were the terminating scripts actually inert?)
was closed by #1. Re-verified no other actively-wired `wiki-cleanup.yml` step is a
silently-inert deleted-file reference (every uncommented `python3 …` step resolves to an
existing file; the rest are cycling ops / SPARQL generators / deletion sweeps /
date-gated no-ops). This session's follow-up cleared the residual the earlier close
missed: rewrote the stale `wiki-cleanup.yml` header comment (still listed the 4 deleted
scripts as "kept here, review July 2026") and removed the dangling queue.md bullet.
**Left:** nothing.

## #3 ill-missing-wikidata — SHIPPED-AUTOMATION

Detection + fix both shipped and running in CI: the `unresolved_ill_qid` orchestrator op
populates `[[Category:Pages with unresolved QID in ill template]]`, and
`fix_ill_destinations.py` (`wiki-cleanup.yml`, `--apply --max-edits 50`) confidently
resolves and fills `WD=` per page, self-healing pages out of the category. Low-confidence
and genuinely-unresolvable targets (incl. Shikinaisha ILLs pointing at "Unknown") are
left in the category by design.
**Left:** inherent per-page human review of the deliberately-skipped low-confidence
cases — not a build task. Let the loop drain it.

## #4 duplicate-qid-tail — SHIPPED-AUTOMATION (near-drained)

`[[Category:Double category qids]]` was down to ~7 members (verified 2026-05-30; the
~621 historical-figure bulk long gone); `[[Category:Duplicated qid category redirects]]`
= 0. `resolve_double_category_qids.py` auto-handles same-target cases in the cleanup
loop.
**Left:** the ~7-page genuinely-different-target review remnant — inherent human review,
not a build task. Low priority.

## #5 japanese-category-names — PARTIAL (the highest-value remaining thread)

THE real remaining backlog (1189 subcategories as of 2026-06-05). Phases shipped:
- **(a)** deterministic dated-maintenance transform;
- **(b)** Wikidata-anchored resolver — 1067/1189 carry `{{wikidata link|Q…}}`; the
  Wikimedia-category item's enwiki sitelink is the authoritative English `Category:` name;
- **(c) this session** — place-name gazetteer for `<place>の歴史` / `<place>の建築物`
  (214 of the 578-entry residual): strip topic suffix → look the place stem up as a
  jawiki article on Wikidata → take its enwiki sitelink → apply the fixed English
  convention ("History of X" / "Buildings and structures in X"). Authoritative, never
  guessed; P31-gated to Japanese administrative divisions. 90% sample hit rate (54/60).
  Rows append to `category_moves.csv` (monthly `move_categories.py`); misses → residual.

**Left (buildable):** later gazetteer phases deliberately out of scope in (c) —
`の神社` (no cat-QID cases), `の重要文化財` / `の国宝`, `の旧県社` / `の旧郷社` / `の旧村社`
(shrine-rank-by-place), `の画像提供依頼` (maintenance), bare `<place>郡` districts; plus
gazetteer misses (prefecture-prefixed disambiguated stems like `埼玉県美里町`). Then (d)
the genuinely-unresolvable human queue. Residual auto-maintained at
`docs/category_translation_residual.md`.

## #6 multiple-wikidata-links — SHIPPED-AUTOMATION

Detection + surfacing shipped and running in CI: the `multiple_wikidata_links`
orchestrator op populates `[[Category:Pages with multiple wikidata links]]`, and
`report_multiple_wikidata_links.py` (`render-duplicate-qids.yml`, `--apply`) renders each
member's competing QIDs + labels/descriptions to the `[[Multiple wikidata links]]` review
page; the op self-heals a page out of the category once it's back to one link.
**Left:** inherent per-case human review (pick the correct QID / split the page) — not a
build task.

## #7 duplicated-content-need-translation — SHIPPED-AUTOMATION (remote routine)

Mostly worked by the claude.ai cloud-queue worker (`docs/remote_queue_pipeline.md`).
**Left:** manual review only for the hard cases — canonical-title choice, history merge,
the 9 large kokuzō articles. NEVER strip `[[Category:Need translation]]` without verifying
the body is actually English (the sync deletes the local file when the category goes).
Not local-work-loop work.

## #8 recreate-deleted-wikidata — DEFERRED (info-gathering shipped)

Info-gathering generator shipped this session:
`recreate-deleted-wikidata/generate_recreate_quickstatements.py` (isolated dir, NOT
auto-submitted, 7 unit tests, CI-wired). Walks `[[Category:Pages with deleted QID in ill
template]]` → **304 distinct deleted ill targets** → info-rich `CREATE` blocks +
human-review `review.md`. Design-corrected: the deleted QIDs are the ill *targets*, not
the pages (which already have items), so it emits NO `P11250|"shinto:…"`. 36 old QIDs
recovered as `#` provenance comments (incl. 5 from the QID-in-title data-loss bug). Only
7/304 currently have a safe jawiki sitelink.

**Left (deferred, out of scope this session per Emma):** per-target content research so
each item survives Wikidata's deletion churn; a minimum-viable-claim-set-per-type decision
(person / shrine / facility / concept); then human-gated submission through the
QuickStatements pipeline (respecting the CLAUDE.md Wikidata-editing rules). Overlaps the
"agentic RAG on deleted Immanuelle-created items" queue item — the context dump is the
source, not a live API pull.

---

## One-line scoreboard

| # | Item | Status |
|---|------|--------|
| 1 | retire-terminating-scripts | RESOLVED |
| 2 | audit-legacy-scripts | RESOLVED |
| 3 | ill-missing-wikidata | SHIPPED-AUTOMATION (residual = human review) |
| 4 | duplicate-qid-tail | SHIPPED-AUTOMATION (~7-page review remnant) |
| 5 | japanese-category-names | PARTIAL — **next-session build thread** |
| 6 | multiple-wikidata-links | SHIPPED-AUTOMATION (residual = human review) |
| 7 | duplicated-content-need-translation | SHIPPED-AUTOMATION (remote routine) |
| 8 | recreate-deleted-wikidata | DEFERRED (info-gathering shipped; recreation gated) |
