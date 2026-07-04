# Deferred verification log

**Why this file exists.** Wiki/CI changes here are *lagging indicators* — a shipped
change can take many hours (sometimes a full cleanup-loop cycle, ~4-5h, or longer)
to actually manifest on the wiki, and the orchestrators are budget-bounded so a
wiki-wide change drains over many cycles. Waiting to confirm each change before
moving on would stall everything. So the working rule is: **ship it, then move on.**
Everything on the wiki is fixable after the fact; a wrong change is recoverable
(revert the repo, the next sync re-applies; content is in git history).

The cost of that rule is that things ship **unverified**. This file is where those
unverified-but-shipped changes get logged, so they aren't silently forgotten. The
`monthly-verification-sweep.yml` GitHub Action prepends a task to `queue.md` once a
month telling the agent to walk this list and actually test each open item — the
batched verification we skip in the moment.

## How to use this file

* **When you ship something you can't verify in the moment, add a `- [ ] ` entry
  here** under "Open" with: what shipped (date + commit), and *exactly how to verify
  it* (the command / API call / page to check).
* **During the monthly sweep:** go through every Open item, actually run its check,
  and either tick it done (move to "Verified", with the date + what you observed) or,
  if it's wrong, fix it and note the fix.
* Keep it honest: an item stays Open until someone has actually observed it working.

## Open (shipped, not yet verified)

- [ ] **Q3 — enwiki category enrichment + drain** (shipped 2026-05-30, `f2b36a86`).
  **Doc-description corrected 2026-06-06:** `enrich_enwiki_categories.py` does NOT
  add `[[Category:<enwiki parent>]]` (the original wording here was wrong). Per its
  own docstring it: looks up the matching enwiki Category; if absent → tags
  `Emmabot enwiki categories false positives`; if present w/o wikidata → adds
  `[[en:Category:Name]]` interlang link + tags `…with only enwiki category and no
  wikidata`; if present w/ wikidata → adds `[[en:Category:Name]]` +
  `{{wikidata link|QID}}` + tags `…with wikidata`; and in ALL cases REMOVES
  `[[Category:Emmabot categories with enwiki]]`. So the real test is whether the
  source drains into the 3 buckets.
  **2026-06-06 check — observed bucket state (live):**
  - `Emmabot categories with enwiki` (source): **4788**
  - `…with wikidata`: **0**
  - `…with only enwiki category and no wikidata`: **10**
  - `Emmabot enwiki categories false positives`: **101**
  So enrichment HAS run (111 categories moved into buckets) and the false-positive
  + enwiki-only paths fire. **Two anomalies to watch, NOT yet a confirmed defect:**
  (1) the source sits at **4788** vs ~111 drained — either slow/budget-bound drain,
  or triage adds new members faster than enrichment removes them; (2) the
  **with-wikidata bucket is 0** — suspicious (many enwiki categories DO have wikidata
  items), but could be that the ~111 processed so far happen to be the niche/no-wd
  ones. **Recheck criterion (rate over weeks):** if across the next sweeps the source
  shrinks and the buckets (esp. with-wikidata) grow → working-but-slow → Verify; if
  the numbers stay static → enrichment has stalled → investigate the wikidata-branch
  + the per-cycle edit count in CI logs. Left Open.
- [ ] **sync conflict resolution → most-recent-edit-wins** (shipped 2026-05-30, `179eaebd`).
  Verify no spurious overwrites: when wiki and repo both changed, the side with the more
  recent edit wins (watch sync edit summaries — should no longer say "wins on revision
  count"; the logic now reads timestamps).
  **2026-06-06 check: partial PASS.** 0 / 30 most-recent `User:EmmaBot`
  recentchanges summaries mention "revision count", and sync-push/delete entries
  were absent from that window (low churn). Consistent with the new timestamp
  logic; small window, so kept Open for a wider recheck, but no warning signs.

- [ ] **Sync `.state`-file removal (shipped 2026-05-30) — HIGHEST-PRIORITY REVIEW.**
  All 5 `sync_*.py` now run STATELESS: `load_state` returns `{}`, `save_state` is a
  no-op, and the 5 `.state` files were deleted. Conflict resolution is timestamp-based
  (most-recent-edit-wins), so any page whose wiki vs repo content DIFFERS is decided by
  whichever side was edited more recently; pages with equal content are no-ops. Orphan
  handling: git_synced + the unique dirs re-add via the category tag (repo-wins); the
  wiki-wins dirs (need_translation, duplicated_content) were re-gated on **wiki-page
  existence** (missing → push-create; exists-but-dropped-category → delete local) so a
  wiki-side category removal isn't churned back.
  '''Verify (8–24h after it hits a sync cycle):'''
  1. Watch sync edit summaries — should NOT see runaway PUSH/DELETE counts or churn
     (the same page edited every cycle). A few per cycle is normal.
  2. Spot-check git_synced/need_translation/duplicated_content pages aren't being
     spuriously deleted from the repo OR having categories re-added against a wiki-side
     removal. Recover any wrong deletion from git history; restore any wrongly-deleted
     wiki page via Special:Undelete.
  3. Confirm `.state` files do NOT reappear (save_state is a no-op).
  '''Known risk:''' timestamp comparison now drives EVERY differing page (was only
  conflicts) → more SPARQL/wiki reads + the per-dir static policy only breaks ties.
  Bounded by each script's `--max-edits`; everything is reversible. If it misbehaves,
  the fix is to refine the stateless orphan/winner logic, not to bring back the files.

## Verified (kept briefly, then prune)

- [x] **propagate retirement drain** (shipped 2026-05-30, `0714ce70`;
  **verified 2026-07-04**). Drained essentially to zero: **3 / 642**
  `miraheze_unique/*.wiki` lack the `[[Category:Independently git synced pages]]`
  tag (was 67/705 on 06-05; total also shrank 705→642 as untagged files were
  retired). Template files intact (Template%3A* population present — no
  orphan-deletion of the legit templates). Stragglers: Amenotaneko, Sanjō
  family, Ōhesoki — tail of the drain, not churn.
- [x] **Sync `.state` files do not reappear** (part 3 of the .state-removal
  review; **verified 2026-07-04**): zero `sync_*.state` files anywhere in the
  repo. The edit-summary churn half still needs a healthy wiki (see below).

- [x] **Q4 — `{{wikidata link}}` self-categorization** (shipped 2026-05-30,
  `34fcfefc`; **verified 2026-06-06**). Via `action=parse`: 6/6 sampled mainspace
  members of `[[Category:Pages without wikidata]]` render that category; 3/3
  sampled `[[Category:Categories missing wikidata]]` Category-ns members render
  THAT category — confirming the ns-aware `{{#switch:{{NAMESPACE}}|=Pages without
  wikidata|Category=Categories missing wikidata}}` else-branch fires only when the
  QID slot (`{{{1}}}`) is empty. (Template source re-read to confirm the condition.)
  *Probe note: `action=parse` returns category titles with underscores — an
  underscore-vs-space mismatch in the first probe gave false negatives; corrected.*
- [x] **Q4 — op appends blank `{{wikidata link}}` / idempotency** (shipped
  2026-05-30, `34fcfefc`; **verified 2026-06-06**). Every sampled member carries
  exactly ONE `{{wikidata link}}` template (no re-append each cycle); the appended
  blank gets pairs folded in by `interlang_consolidate` but keeps an empty QID, so
  it still self-categorizes. No runaway-duplicate-template pages (consistent with
  `[[Category:Pages with multiple wikidata links]]` sitting at 1).
- [x] **Backlog dashboard pages** (shipped 2026-05-30; **verified 2026-06-05**).
  `https://emmaleonhart.github.io/shintowiki-scripts/backlog.html` renders 8
  backlog cards with live counts: retire-terminating(4), legacy-script-audit(50),
  ILLs-without-WD(**849**), duplicate-QID-tail(4), Japanese-category(**1189**),
  multiple-wikidata-links(**1**), duplicated+need-translation(524), recreate-
  deleted-WD(144). Page fully functional, not empty/errored.
- [x] **Items 3 & 6 categories populating** (the `unresolved_ill_qid` /
  `multiple_wikidata_links` ops; **verified 2026-06-05**). Both populate — they do
  NOT read 0: the dashboard shows ILLs-without-resolved-QID at **849** and
  multiple-wikidata-links at **1** (a direct category-members count read
  `unresolved_ill_qid` = **873** the same day). The ops are tagging on the
  cleanup-loop sweeps as designed. (Over-tag spot-check still worth a glance but
  the fix_ill_destinations live test on 6 of these pages found genuine unresolved
  ills, consistent with correct tagging.)
- [x] **Sync `.state`-file removal — statelessness** (shipped 2026-05-30;
  **partially verified 2026-06-05**). All 5 `sync_*.py` confirmed stateless:
  `save_state` is `return` (no-op) in sync_duplicated_content, sync_fandom_unique_pages,
  sync_git_synced_pages, sync_miraheze_unique_pages, sync_need_translation. No
  `sync_*.state` files remain on disk. **Found + removed an orphan**:
  `sync_main_page.state` survived commit `feb2b678` (which deleted
  `sync_main_page.py`) — no script, no CI reference; `git rm`'d this session.
  ⚠ The churn-inspection half (watch sync edit summaries for runaway PUSH/DELETE)
  could NOT be run — shinto.miraheze.org was returning 502s / read-timeouts during
  the sweep. Recheck the recentchanges of `User:EmmaBot` next healthy sweep.

## Open (wiki-parse-dependent, deferred — wiki was 502/timeout during the 2026-06-05 sweep)

The remaining items (Q4 self-categorization render, Q4 blank-template idempotency,
Q3 enwiki parent-category enrichment, sync conflict-resolution edit summaries)
need live `action=parse` / recentchanges reads that the flaky wiki refused during
this sweep. Left Open; recheck on the next monthly sweep when the wiki responds.

**2026-07-04 sweep:** same story — shinto.miraheze.org served 503s throughout
(outage since ~11:30 UTC), so the three wiki-read items (Q3 bucket counts,
conflict-resolution summaries, sync churn inspection) could not be run again.
The two repo-local halves WERE run and moved to Verified above. Wiki-dependent
trio stays Open for the next healthy sweep.
