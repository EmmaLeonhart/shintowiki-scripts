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


## Verified (kept briefly, then prune)

- [x] **Q3 — enwiki category enrichment + drain** (shipped 2026-05-30,
  `f2b36a86`; **closed 2026-07-04**). Live counts: ALL FOUR categories exist
  with **0 members** — the source (`Emmabot categories with enwiki`) went
  4788 → 0 since 06-06, and the three buckets (falsepos was 101, enwiki-only
  was 10, with-wikidata was 0) are also empty. The enrichment backlog is
  GONE; the 06-06 "with-wikidata bucket is 0" anomaly is moot (nothing left
  to enrich). Note recorded plainly: this observation doesn't distinguish
  "enrichment completed + buckets consumed downstream" from "the Emmabot
  category family was retired by a cleanup" — if the distinction ever
  matters, read the enrichment CI logs from mid-June; no defect signal
  either way.
- [x] **sync conflict resolution → most-recent-edit-wins** (shipped
  2026-05-30, `179eaebd`; **verified 2026-07-04**). 0/50 most-recent EmmaBot
  edit summaries mention "revision count"; no sync PUSH/DELETE churn in the
  window. (The Template:U* pages each edited 3× are the template-orchestrator
  running multiple ops per page — orchestrator summaries, not sync ones.)
- [x] **Sync `.state`-file removal — churn half** (**verified 2026-07-04**,
  completing the 06-05 partial): recentchanges window shows no runaway
  PUSH/DELETE and no same-page-every-cycle sync churn; `.state` files still
  absent (checked 07-04 earlier). Review CLOSED.
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

**2026-07-04 sweep, second pass:** the wiki recovered mid-afternoon (sync
workflows green from 15:30 UTC), so the wiki-read trio ran after all — all
three moved to Verified above. Nothing remains Open.
