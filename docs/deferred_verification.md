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

- [ ] **Q4 — `{{wikidata link}}` self-categorization** (shipped 2026-05-30, `34fcfefc`).
  Verify via `action=parse`: a page invoking `{{wikidata link|Q…}}` renders exactly as
  before (the tmbox + interwikis); a page with a blank `{{wikidata link}}` renders
  nothing visible AND gains `[[Category:Pages without wikidata]]` — but ONLY in ns 0/14.
  Confirm NO `[[Category:Pages without wikidata]]` cascade onto pages that merely
  transclude a template containing the blank call. If the render is broken, fix the
  template (`miraheze_unique/` + `fandom_unique/` `Template%3AWikidata link.wiki`).
- [ ] **Q4 — op appends blank `{{wikidata link}}`** (shipped 2026-05-30, `34fcfefc`).
  Verify a mainspace/category page lacking a wikidata link gets a single blank
  `{{wikidata link}}` appended (NOT re-appended each cleanup cycle — idempotency).
- [ ] **Q3 — enwiki parent-category enrichment** (shipped 2026-05-30, `f2b36a86`).
  Verify `enrich_enwiki_categories.py` adds `[[Category:<enwiki parent>]]` links to
  pages in `[[Category:Emmabot categories with enwiki]]`, red parents land in
  Special:WantedCategories, and the create→triage→enrich recursion proceeds. (~8h to
  show; Emma may confirm directly.)
- [ ] **propagate retirement drain** (shipped 2026-05-30, `0714ce70`).
  Verify `miraheze_unique/` churn-candidate count (files lacking the literal
  `[[Category:Independently git synced pages]]` tag) drains to ~0 and the 6 legit
  templates were NOT orphan-deleted. (Check with `check_lowercase_collisions.py`-style
  read or by recounting the repo files.)
- [ ] **sync conflict resolution → most-recent-edit-wins** (shipped 2026-05-30, `179eaebd`).
  Verify no spurious overwrites: when wiki and repo both changed, the side with the more
  recent edit wins (watch sync edit summaries — should no longer say "wins on revision
  count"; the logic now reads timestamps).
- [ ] **kana qualifier backlog** (status checked 2026-05-30: 5340 candidates remain).
  After the Wikidata freeze lifts (2026-06-06), confirm the QS pipeline drains these
  (`modern-quickstatements/check_kana_qualifier_status.py`).

## Verified (kept briefly, then prune)

*(empty — move Open items here with the date + what you observed once confirmed.)*
