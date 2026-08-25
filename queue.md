# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

- **The Kokugakuin reading job — corpus complete, 109 sections placed, residue characterised**

  Emma: *"work it now"*, *"grind it"*, *"generate the batch now"* — the three items this used to be
  are one job, and it is largely done.

  **The corpus is local.** All **2,846** entry pages Wikidata references are fetched and committed
  (`kokugakuin_pages/`, `fetch_all_kokugakuin_pages.py`), zero errors. Every reading job is now an
  offline parse: re-runnable, re-measurable, and auditable against the exact committed bytes.

  **`p958_by_entry.txt` — 109 sections**, exact match only, resolved one ENTRY at a time so a slot
  is claimed at most once and collisions are structurally impossible. Registered in `ATOMIC_FILES`.
  Held-out validation on 280 known sections: exact match **142/142**.

  **The residue is 263 holders and is NOT pending work.** 261 of them are typed `Q135022904`
  (Shikinai Ronsha) or `Q135038714` (Disputed Shikinaisha) — the two types
  `generate_p958_qualifiers.py` deliberately excludes from `n/a`, because their sections are
  genuinely unresolved and a default would erase that. The remaining 2 are already covered by that
  generator. **Nothing further should be assigned here without new evidence about specific items.**

  **✓ The loosen-the-matcher lever is CLOSED — measured, and it points the wrong way.** I had
  assumed the deferrals were mostly annotation noise a looser normaliser could absorb. Categorising
  all 46 ground-truth deferrals says otherwise:

  | why it deferred | share |
  |---|---:|
  | **the label matches SEVERAL slots** | **61%** |
  | genuinely different names (`厳原八幡宮神社` vs `八幡宮神社`) | 11% |
  | one name contains the other | 9% |
  | the slot is absent from the page | 9% |
  | **one variant character** (`高`/`髙`, `剣`/`剱`, `鬚`/`髭`) | **7%** |
  | slot name empty once its annotation is stripped (`（論社）`) | 4% |

  A variant-kanji fold — the only loosening with real evidence behind it — would fix **3 of 46**,
  and the pairs supporting it were each seen exactly once. Meanwhile the dominant cause is
  **ambiguity**, and loosening normalisation makes ambiguity *worse*: more strings compare equal, so
  more labels match several slots. The lever does not merely have low upside, it points backwards.

  The one sound direction is the opposite — **tightening, by using information currently thrown
  away**. Slot names carry disambiguators the matcher ignores: `（論社）山辺御県神社〈別所町〉` versus
  `〈西井戸堂町〉`. Matching on those would *separate* candidates rather than merge them, which is
  the right shape for a 61%-ambiguity residue. Not attempted; recorded so the next attempt starts
  from the measurement instead of the assumption.

- **Built and waiting on the lockout — no work left on any of them**

  BLOCKED-ON-EXTERNAL, one blocker: `wikidata_editing_lockout.state`, **2026-09-18**. All of these
  regenerate on every build and deliver through the normal drip when it lifts.

  | file | lines | what it does |
  |---|---|---|
  | `orphan_membership_removals.txt` | 829 | the 816 modern shrines whose `P361` belongs to their register entry |
  | `p958_by_entry.txt` | 109 | sections read off the Kokugakuin pages, resolved per entry |
  | `multi_ordinal_removals.txt` | 63 | `part of` statements carrying more than one series ordinal |
  | `tenjinsha_en_labels.txt` | 47 | 天神社 English labels derived from each item's own reading |
  | `lost_shrine_creates.txt` | 44 | the three shrines the repurposing left with no item — via `create_items.py`, not the drip |
  | `p958_from_kokugakuin.txt` | 40 | the earlier per-item read; superseded in method by `p958_by_entry.txt` |
  | `p958_corrections.txt` | 7 | wrong sections needing remove-then-add, incl. two the page proved wrong |

  The Awa entry 3 fix rides along as a requirement on item creation, per Emma's ruling — she
  hand-fixes the wrong 下立松原 statement the way she is handling the Izumo knot.

  - [ ] Emma asked to see one before it delivers. `_site/membership-removals.html` is built and
    wired into `generate-pages.yml`; it publishes on the next pages build.

- **⛔ Two standing corrections to how I read this repo**

  **The lockout gates WRITES, not work.** It covers `direct_daily_edits.py`, `create_items.py`,
  `substitute_source_shrine_proposal.py`, their CI guard steps, and the hand-run batches in
  `funding-and-networking`. Not SPARQL, not the API for reading, not any `generate_*.py`, not
  analysis or deciding. An item is blocked only if the thing left to do IS the write. Emma tested
  four of my labels and three were wrong.

  **Search the repo before asking her a data-model question, and measure what a value MEANS rather
  than how often it occurs.** I asked whether 75 items should get `n/a` or `0` on a frequency split;
  the semantics were already in `generate_p958_qualifiers.py`, and applying them reversed the
  answer. Same error as reporting a P958 coverage gap that came from subtracting two different units.

- **Pinned tail (keep last)**

  - [ ] Ensure the five session-local crons are running. **Verified live 2026-08-24**, this session:
    work-loop `0a52da5c` :03, auto-flush `aa735a3c` :15, status-report `f371ceee` :42, briefing
    `ff8886e6` 08:03, debrief `924d2b08` 23:57. SYNC fast-forwards onto origin/main each tick.
    (Crons are session-local, so a recorded ID is only ever evidence about the session that made it.)
  - [ ] Run the status-report action once more independently as an end-of-session summary.
