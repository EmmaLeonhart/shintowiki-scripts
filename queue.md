# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

- **The two-Kokugakuin-id items — a reading job, worked off the table**

  Emma's ruling: leave them to be worked off the table rather than per-item with her. ~66 items each
  hold two Kokugakuin ids, so each is a candidate for two different 927 entries and needs a "which
  entry" `P958` qualifier. She earlier ruled all of them ambiguous.

  Table: https://emmaleonhart.github.io/shintowiki-scripts/kokugakuin-multi-p13677.html

  **NOT LOCKED — Emma's ruling, 2026-08-25: "work it now."** The lockout gates three credentialed
  scripts and the hand-run batches. It does not gate SPARQL reads, generators, or deciding, so the
  reading and the QuickStatements generation happen now; only delivery waits for 09-18.

- **The 228 sections that can only be read off the Kokugakuin page**

  `_site/p958-reading-queue.html` — 226 shrines across 140 Kokugakuin pages, one card per page showing
  every holder so the taken sections are visible while choosing, with the QuickStatements building
  live at the bottom. Emma chose the shape: *"One HTML page, all 228, work at your own rate."*

  **NOT LOCKED — Emma's ruling, 2026-08-25: "grind it."** "Out of scope for automation" was about
  automation and says nothing about the lockout; no Wikidata write happens until the batch is
  submitted. Worked at my own rate, accumulating QuickStatements.

- **The 13 Kokugakuin ids with no `P1352` on their link statement**

  Established 2026-08-24 (see `DEVLOG.md`): not a code defect and not a coverage gap. The `P958`
  generator requires a ranking qualifier on the `P460`/`P527` link statement, and these links do not
  carry one, so they are outside its input rather than dropped by it.

  **NOT LOCKED — Emma's ruling, 2026-08-25: "generate the batch now."** I had marked this
  BLOCKED-ON-EXTERNAL, which was wrong: the *output* is a write, but building the batch is not.

  **Measured 2026-08-25, and the job is READING, not derivation.** It is **24 links across 13
  items**, pointing at **23 distinct register entries**. The ranking says which numbered candidate
  (現社名など（１）（２）…) the shrine is on its Kokugakuin page, so it can only be derived when an
  entry has exactly one candidate — otherwise the page decides it.

  | | |
  |---|---:|
  | entries with several candidates → must be read | **18** |
  | entries with one or no resolvable candidate | **5** |

  Worst cases are heavily contested: [`Q135040009`](https://www.wikidata.org/wiki/Q135040009) has
  **five** candidates, [`Q135039676`](https://www.wikidata.org/wiki/Q135039676) and the two
  常宮神社 entries [`Q135040140`](https://www.wikidata.org/wiki/Q135040140) /
  [`Q135040141`](https://www.wikidata.org/wiki/Q135040141) have **four** each.

  Two hypotheses tested and dropped rather than left as theories: the item-level `has_p958` flag
  does not cause this (none of the 13 carries `P958` anywhere), and the `P527` links are **not**
  shrine-to-sub-shrine relationships where a ranking would not apply — all six targets carry
  Kokugakuin ids and are genuine register entries.

  So this is the same work as the 228-section reading queue below, in a different property. It
  belongs there rather than in a separate speculative batch, and generating one would mean guessing
  ordinals — which is what `resolve_multi_p13677` already refuses to do by design.

- **Built and waiting on the lockout — no work left on any of them**

  BLOCKED-ON-EXTERNAL, one blocker: `wikidata_editing_lockout.state`, **2026-09-18**. All of these
  regenerate on every build and deliver through the normal drip when it lifts.

  | file | lines | what it does |
  |---|---|---|
  | `orphan_membership_removals.txt` | 829 | the 816 modern shrines whose `P361` belongs to their register entry |
  | `multi_ordinal_removals.txt` | 63 | `part of` statements carrying more than one series ordinal |
  | `tenjinsha_en_labels.txt` | 47 | 天神社 English labels derived from each item's own reading |
  | `lost_shrine_creates.txt` | 44 | the three shrines the repurposing left with no item — via `create_items.py`, not the drip |
  | `p958_corrections.txt` | 3 | Kokugakuin page 181621, where a wrong `P958` needs remove-then-add |

  The Awa entry 3 fix rides along as a requirement on item creation, per Emma's ruling — she
  hand-fixes the wrong 下立松原 statement the way she is handling the Izumo knot. No sequential unit
  is built for it.

  - [ ] **Emma asked to see one before it delivers (2026-08-25).** Building a readable page for
    `orphan_membership_removals.txt` — the largest, and the only one that removes statements from
    816 items. A `.txt` of `-Q…|P361|Q…` is not reviewable.

- **⛔ I keep mis-scoping the lockout. It gates WRITES, not work.**

  Emma, 2026-08-25: *"do askuserquestion on everything there so that I can judge if they are or are
  not locked with wikidata since you often just defaulted to saying stuff was wikidata locked."*
  She put four items to the test and **three of my four labels were wrong.**

  What `wikidata_editing_lockout.state` actually gates: `direct_daily_edits.py`, `create_items.py`,
  `substitute_source_shrine_proposal.py`, their CI guard steps, and the hand-run QuickStatements
  batches in `funding-and-networking`. That is the whole list.

  What it does **not** gate: SPARQL queries, the Wikidata API for reading, any `generate_*.py`,
  analysis, deciding, or writing a batch to a `.txt`. **An item is blocked only if the thing left to
  do IS the write.** Everything upstream is available now, and marking it blocked is how a queue
  fills up with work that could already have been done.

- **Pinned tail (keep last)**

  - [ ] Ensure the five session-local crons are running. **Verified live 2026-08-24**, this session:
    work-loop `0a52da5c` :03, auto-flush `aa735a3c` :15, status-report `f371ceee` :42, briefing
    `ff8886e6` 08:03, debrief `924d2b08` 23:57. SYNC fast-forwards onto origin/main each tick.
    (Crons are session-local, so a recorded ID is only ever evidence about the session that made it —
    the IDs here before were the 2026-08-05 session's, dead since it ended.)
  - [ ] Run the status-report action once more independently as an end-of-session summary.
