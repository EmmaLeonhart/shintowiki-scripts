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

- [ ] **`migrate_ritsuryo_funding_remove.txt` — the 2026-08-24 sort-at-the-writer fix
  (`8c65d9b6`) is unverified for this one file of the ten.** Blocked by the Wikidata
  lockout, not by anything wrong: the file is written only by `submit_daily_batch.py`
  and `direct_daily_edits.py`, whose jobs (`submit-quickstatements`, `direct-daily-edits`)
  report **skipped** on every `cleanup-loop` run while
  `shinto_miraheze/wikidata_editing_lockout.state` is locked to **2026-09-18**. So it has
  not regenerated since 2026-08-25 and there is no post-fix build to measure.
  **Check, once the lockout date passes:** after a `cleanup-loop` run where those two jobs
  are no longer skipped, confirm the generator wrote the file in the run log, then confirm
  either no commit touched it, or that any commit is a small real delta rather than the
  ~2,494-line reshuffle it produced per build before the fix. The decisive form is
  `git show <c>~1:<f> | sort | md5sum` vs `git show <c>:<f> | sort | md5sum` — identical
  sorted content across a large diff is churn.

## Verified (kept briefly, then prune)

* **2026-09-05 — the 2026-08-24/25 sort-at-the-writer churn fix holds for 9 of its 10
  files.** The 08-25 DEVLOG entry deferred this explicitly (*"every `generate` step so far
  ran before these fixes landed… the next scheduled regeneration is the test"*) but the
  item was never entered here; found by reading the log rather than this list. What was
  observed:
  * `cleanup-loop` (daily, `cron: 23 2 * * *`) ran on all 12 days 08-25 → 09-05: ten
    successes, failures on 09-02 and 09-05.
  * In run [`33848078978`](https://github.com/EmmaLeonhart/shintowiki-scripts/actions/runs/33848078978)
    (09-04) the `generate` job's log shows each generator actually **writing** its file —
    `kana_qualifier_add.txt` "Wrote 4965 lines", `kana_redundant_remove.txt` "Wrote 252
    lines", `address_citation_backfill.txt` "Wrote 140 reference-backfill lines", plus
    `ronsha_ojp_name_removals`, `shikinaisha_kokugakuin_refs`, `multi_ordinal_removals`,
    `orphan_membership_removals`, `tenjinsha_en_labels`.
  * **Not one of those eight produced a commit in the 11 days since the fix**, against 2–22
    commits each in 08-01 → 08-24. Generator ran, rewrote the file, output byte-identical:
    that is the fix working, and the absence of commits is the evidence, not the doubt.
  * `daily_operations.txt` does still commit daily, which is correct — it is the only one of
    the ten that legitimately changes. All 8 commits 08-28 → 09-04 are **real** deltas
    (+51…+157 lines, sorted content differing every time), not the 2,483-line rewrite it
    produced per build before.
  * The tenth, `migrate_ritsuryo_funding_remove.txt`, is lockout-gated and stays Open above.

  **The check that made this conclusive** was reading the run log for the generators'
  "wrote" lines *before* reading anything into the zero commits. `generate-quickstatements.yml`
  documents its own trap in a comment: a generator that bails on HTTP 429 from WDQS is
  reported **green** by `continue-on-error: true` while the file silently does not
  regenerate. Under that failure a not-regenerating file and a deterministic one look
  identical from the commit history alone.

## Sweep log

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
