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

*(empty)*

## Verified (kept briefly, then prune)

*(empty)*

## Sweep log

* **2026-08-03** — nothing Open to test: the 07-04 sweep closed every item and no
  new entry was added in the month since. Pruned the Verified section (all entries
  2026-06-05 → 2026-07-04, past the week-expiry rule in `CLAUDE.md`); git history
  retains them.
* **2026-07-04** — all remaining items verified and closed (two passes; the
  wiki-read trio ran after shinto.miraheze.org recovered mid-afternoon).

> Note for the next sweep: the Miraheze blackout (to 2026-08-09) means any newly
> added item whose check requires a wiki read cannot be tested until the gate in
> `queue.md` flips to `GO`. Log such items Open with the check written out; do not
> touch the wiki to test them.
