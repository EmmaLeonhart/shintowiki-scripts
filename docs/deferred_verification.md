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
* **Writing "still unverified" into `DEVLOG.md` does not count as logging it here** — that
  is what happened to the 2026-08-25 churn fix, and it made the Open list read empty for
  eleven days while a real item was outstanding. The DEVLOG entry is the narrative; the
  Open list is the thing the monthly sweep walks. If a change ships unverified, it needs a
  line in **both**.
* **An empty Open list is not a finished sweep.** Before recording "nothing to test", grep
  the DEVLOG since the last sweep for unverified-ship language (`unverif`, `not yet
  verif`, `will manifest`, `the next … run is the test`) and enter anything found.

## Open (shipped, not yet verified)

(none — see the 2026-10-02 sweep log entry)

## Verified (kept briefly, then prune)

* **2026-10-02 — the WDQS pacing and backoff changes of 2026-09-20 (`a29bf5cf`, `f66ec730`,
  `2fbf1f00`) hold.** `Generate shrines-missing-en-label list` had failed 5 of 6 runs on 429.
  After them: 09-21 → 10-01, 11 scheduled runs, 10 green. Read the step outcomes, not the
  conclusions, on 10-01, 09-30 and 09-29: all 8 steps `"outcome": "success"`, no
  `RateLimitError` in any log, ~3m50s wall clock against the 20-minute timeout. The one red
  run, 09-24 (`35985318461`), was a real `429 Too Many Requests` from
  `generate_identical_name_en_labels`. So 429s are rare now, not impossible. The remaining
  levers (a `BATCH` under 150, a slower throttle) were not needed.

## Sweep log

* **2026-10-02** — the one Open item (WDQS pacing, 09-20) was tested and closed. Grepped the
  DEVLOG since 09-20 for unverified-ship language: the only hit is the orphan-removal ↔
  rebuild loop, which is a suspicion already carried by the Engishiki review item in
  `queue.md`, not a shipped change, so it is not entered here. Pruned the 09-05 and 09-20
  Verified entries (past the week expiry; git has them).

* **2026-09-20** — the one Open item was tested and closed, and the list did **not** come
  out empty, because the grep this file mandates found two entries in the same day's DEVLOG
  shipping unverified ("not claimed to fix it", "the next scheduled run is the measurement").
  Those are now the single Open item. The 09-05 lesson held exactly as written: the sweep
  that matters is the grep, not the list. ⚠ This one caught **my own** entries from hours
  earlier, which is the case for running the grep even when you believe you know what is
  outstanding.

* **2026-09-05** — the Open list was empty, and that was the finding rather than the
  result. A real deferred verification had been written into `DEVLOG.md` on 2026-08-25
  ("Still unverified: …the next scheduled regeneration is the test") instead of being
  added here, so the one item this file existed to hold was the one item it did not have.
  Two consecutive empty sweeps (08-03, and this one before checking) were the visible
  symptom. Swept by grepping the post-08-03 DEVLOG for unverified-ship language rather
  than by trusting the Open list; 9 of the 10 churn-fixed files verified, the tenth logged
  Open behind the Wikidata lockout. **An empty Open list is a claim to test, not a result
  to record.**

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
