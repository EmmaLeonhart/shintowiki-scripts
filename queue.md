# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

- **▶ Verify the WDQS throttle fix on the next scheduled run**

  Both 08-22 CI defects are fixed and verified (`secrets: inherit`, the 69 unbootstrapped imports) —
  all four red jobs green since 08-23, nothing further to check there.

  The "separate older defect" that item carried is also diagnosed, and the diagnosis was wrong three
  times before it was right. It was never a timeout: a forced run finished the whole path including
  both weekly steps in **41.8 minutes** against a 150-minute cap. The two description generators
  were **429ing themselves out of WDQS** — `time.sleep(1)` against this repo's own documented
  `WDQS_THROTTLE = 2.5`, in VALUES batches of 150 across the full target set — and
  `continue-on-error: true` reported the step green, so `description_label_pairs.txt` sat unchanged
  since 2026-08-02 behind a passing check.

  Both generators now use the 2.5s floor, and both emit a `::warning` naming the file that was not
  regenerated when they bail.

  - [ ] **Unverified: whether 2.5s is actually enough.** The next `cleanup-loop` fire (02:23Z daily)
    exercises it on a weekday, where the weekly steps do not run — so the real test is either a
    Sunday or another `force_weekly=true` dispatch. Check for the `::warning` annotation; its
    absence plus a changed `Did` count is the pass.
  - The 429 was ours the whole time and was reported as BLOCKED-ON-EXTERNAL in three status reports.
    A rate limit from our own scheduled job means our own pacing is wrong.

- **Individual QuickStatements to CORRECT wrong/missing P958 sections**

  Emma, 2026-08-19, last item by her sequencing: *"There were actually significant errors here that we
  caught, but you caught them in such a bizarre way. We should have individual quick statements here
  that set these things... specifically, put it at the end of the queue of the shinto wiki. We have to
  set up individual quick statements to change these things so that they get corrected."*

  **Why the existing generator cannot do it.** `generate_p958_qualifiers.py` is ADD-only — it derives
  the section from the parent list's P1352 ranking and adds it where absent. QuickStatements has no
  "overwrite a qualifier" verb, so a statement whose P958 is present but WRONG is invisible to it
  forever. A correction is necessarily two lines: remove the old qualifier, add the right one.

  **Built 2026-08-19:** `modern-quickstatements/generate_p958_corrections.py` → `p958_corrections.txt`.
  It reads live state first, so an already-correct item emits nothing rather than a churn pair.

  Kokugakuin page **181621** carries three shrines, and that is what surfaced the errors:

  | item | should be | live state | action |
  |---|---|---|---|
  | [Q111776816](https://www.wikidata.org/wiki/Q111776816) | `1` | **no P958 at all** | add |
  | [Q134925373](https://www.wikidata.org/wiki/Q134925373) | `0` | `n/a` — **wrong** | remove + add |
  | [Q135039671](https://www.wikidata.org/wiki/Q135039671) | `n/a` | `n/a` | correct, nothing emitted |

  Batch as it stands (3 lines, built and ready — **but GATED, correcting what this item first said**).
  `wikidata_editing_lockout.state` names the scope itself: *"Covers EVERY write path — the daily
  direct-API drip, item creation, the one-shot property-proposal talk edit, **and the hand-run
  QuickStatements batches**."* Emma's *"quickstatements are separate"* was about pacing, not about the
  lockout. So this batch waits for **2026-09-18** like everything else:

  ```
  Q111776816|P13677|"181621"|P958|"1"
  -Q134925373|P13677|"181621"|P958|"n/a"
  Q134925373|P13677|"181621"|P958|"0"
  ```

  - **Emma pastes the batch** — moved to `scheduled/scheduled_items.json`, due **2026-09-18** when
    the Wikidata lockout lifts. It is not listed here as a parked item on purpose (Emma, 2026-08-20);
    the injector puts it in this queue and on `[[Open questions]]` on the day it becomes pasteable.
    The unblock signal is still the state file, not a session deciding the batch is a small enough
    exception.
  **Widened 2026-08-19 — page 181621 is NOT special.** `modern-quickstatements/generate_p958_candidates_page.py`
    checks every Kokugakuin id held by more than one item. Of **900** such ids, 619 are fine and **281
    are candidates**:

    | count | shape |
    |---|---|
    | **0** | **collisions** — nowhere do two items claim the same (id, real section) |
    | **197** | a holder has NO section while its siblings do — **181621's exact shape** |
    | **66** | no holder on the page has any section |
    | **18** | every holder carries `0` or `n/a`, so none is distinguished |

    The **zero is the load-bearing result**: the failure mode is under-specification, not two shrines
    fighting over one entry. And the error Emma found on the one page she opened recurs on **197** pages.

    Report: `_site/p958-candidates.html` (281 cards, each linking the Kokugakuin page and every holder),
    data: `modern-quickstatements/p958_candidates_audit.json`. Report-only by design — the correct
    section can only be read off the Kokugakuin page, which is how 181621's values were established, so
    this narrows WHERE to look and never guesses WHAT the value is.

  **Derivability tested 2026-08-19 — and my own guess was wrong.** I had written that deriving the
    missing section from the parent's P1352 ranking "would turn most of them mechanical". It does not.
    Of the **321** items missing a section across the 197 pages:

    | count | share | disposition |
    |---|---|---|
    | **57** | 18% | exactly one parent ranking → **mechanically derivable** |
    | **36** | 11% | **conflicting** rankings from different parents → manual |
    | **228** | 71% | **no ranking anywhere** → must be read off the Kokugakuin page |

    Data: `modern-quickstatements/p958_derivability.json`.

    **Two things that bite whoever does this next:**
    - P1352 is a *quantity*, so SPARQL returns `2.0` / `1.0` / `0.0` while P958 values are the strings
      `"2"` / `"1"` / `"0"` / `"n/a"`. A derivation that does not format the float will write `2.0`.
    - A derived `0` is legitimate but distinguishes nothing — section 0 carries no uniqueness — so
      those add a value without resolving the ambiguity they appear to fix.

  **✅ The reading queue is BUILT (2026-08-19)** — Emma chose the shape: *"One HTML page, all 228,
  work at your own rate."* `modern-quickstatements/generate_p958_reading_queue.py` →
  `_site/p958-reading-queue.html`: **226 shrines across 140 Kokugakuin pages**, one card per page
  showing *every* holder so the taken sections are visible while choosing, a box per missing section,
  and the QuickStatements building live at the bottom with a copy button. (228 boxes, 226 shrines —
  two items sit on two pages each.) Nothing tracks progress and nothing chases; submission waits on
  the lockout to 2026-09-18.

  - [ ] **Re-measure the derivable 57 against a FRESH `p958_qualifiers.txt`.** I said on 2026-08-25
    that the existing generator already produces 44 of the 57 and misses only 7 items. Measured
    against the file on disk that is wrong: **33 of the 57 rows are covered and 24 are not**, across
    17 distinct items — more than double the gap I reported.

    But the artifacts disagree with each other, so neither number is trustworthy yet.
    `p958_qualifiers.txt` is **68 lines** (the queue said 2,480), while `p958_summary.json` from the
    same directory reports `generated: 167` and `p958_qualifiers: 0`. A file and its own summary
    cannot both be right, so they are from different runs and the coverage figure is measured against
    a stale artifact.

    `generate_p958_qualifiers.py` runs in `generate-quickstatements.yml` on every build, so a fresh
    pair settles it. Re-run the comparison against the regenerated file before deciding whether the
    remainder is structural.

    What does hold regardless: the generator **already queries P527** alongside P460, both with
    `P1352` qualifiers. So "Q135194158/Q135194159 are skipped because P527 is an unhandled route" is
    not the explanation — that route is handled, and their real cause is still unidentified.
    `Q1466105` 廣田神社 is genuinely structural: three Kokugakuin ids, all rank `0.0`, and section `0`
    carries no uniqueness, so there is nothing to derive from.

  - **The 228 with no ranking** — OUT-OF-SCOPE for automation, permanently: the value only exists on the
    Kokugakuin page. This is a reading job, and 228 pages is a real size — it belongs to Emma or to a
    deliberate reading sprint, not to a work-loop tick.

  ---



These are not waiting on Wikidata. They are waiting on a ruling, and each names what is being asked.
- **❓ DECISIONS — fire ONE at a time, in order, once the gate opens**

  **Standing rule: EVERY decision carries a "walk me through it first / let's chat" option.** Emma often
  doesn't have the context to pick A vs B cold — she picks "explain it first", the bot lays out the
  situation in plain terms, they talk, THEN decide. Never treat a decision as "blocked on Emma" and skip
  it; fire the question with the chat option so it can actually move.

  > These can't be decided blind — Emma reviews them against the Open questions page **plus** the
  > browsable tables. The tables are GitHub Pages and work right now, but the review pairs the two, so
  > they wait for the gate (Emma 2026-07-13).

  ### B2. ~~The duplicate shrine pairs — link or merge?~~ **WITHDRAWN 2026-08-19. Not a decision.**

  Table: https://emmaleonhart.github.io/shintowiki-scripts/shikinaisha-orphans.html

  **Emma settled this in JULY and the answer never reached the queue.** From [[Open questions]] on the
  wiki, unhandled because B1 (the sweep that reads that page) was itself gated behind the 39-day wiki
  blackout:

      "I am pretty sure right now that, for literally all of them, it's a matter of Japanese Wikipedia
       and the Kokugakuin database disagreeing with each other, and you're insisting that we should
       merge them. This actually is a thing that was done by the original import bot ages ago, and it
       was the source of a massive amount of problems!... If any of these ones are not a disputed
       shikinai-sha, then it's different, and I'm going to manually go through them to ensure that there
       aren't any. I am pretty strongly convinced that this thing here that you're talking about is just
       a non-issue."

  So merging is not merely undecided — she has already seen it do damage once, via the original import
  bot, and said so. **This is the standing ruling; treat it as decided.** She reserves the manual pass
  over any that are not disputed shikinaisha.

  **And it is not decidable on the evidence either, because the "duplicate" class never established
  identity.** Emma again, 2026-08-19, on being asked to pick link/merge/case-by-case:

      "I'm extremely confused. What are you even doing here? What are you doing with duplicate labels?
       What is the point of this? There's plenty of shrines with duplicate labels."

  She is right, and it kills both halves of the class:

  - **The Kokugakuin-id half was artifact.** It matched on bare P13677 while ignoring the P958 section.
    Identity is the *combination*, and neither section `0` nor `n/a` is uniqueness-protected. Fixed at
    source; the 36 "id disagreements" went to **zero** and none of the 11 id-matched pairs was real.
  - **The name half is not evidence either.** It matched equal ja labels among entries of a list the
    item already claims. That is narrower than "duplicate labels anywhere in Wikidata" — but not narrow
    enough: **杉山神社 alone accounts for 4 of the 48**, and that name is multiplied all over the
    Musashi region. Same-name-in-the-same-list is not the same shrine.

  **Corrected state: 149 orphans, and NONE is provably a duplicate of a listed entry.** The 48 are a
  list of name collisions; the report's own headline calls them duplicates, which overstates what it
  knows. Do not re-raise link/merge on this basis.

  **✅ ANSWERED 2026-08-24 — and there was no defect. They are the 宮中神, the palace shrines.**

  The question was: why are items tagged Shikinaisha named as a part of no Jinmyōchō list? Measured
  live, **it is 23 items, not 149** — the older figure counted something else or predates the list
  rebuilds.

  They are not listless. They are `part of` the palace groupings, which the Engishiki Jinmyōchō lists
  BEFORE it reaches the provinces:

  | part of | n |
  |---|---|
  | **八神殿** — the Eight Deities Hall (神産日, 高御産日, 玉積産日, 生産日, 足産日 …) | 8 |
  | **座摩神** — the 座摩巫祭神五座 (生井, 福井, 綱長井, 波比祇 …) | 5 |
  | **御門巫祭神 八座** | 2 |
  | **生島巫祭神 二座** | 2 |
  | modern shrines carrying `P460` — relocated or merged sites, correctly listless | 4 |
  | no `P361` at all | 2 |

  So the orphan query only catches them because those palace groupings are not themselves
  `part of` the Jinmyōchō item, while the province lists are. **The register's own structure, not
  damage** — nothing to merge, nothing to link, and the class dissolves the same way the
  "duplicates" did.

  - [ ] Optional and cosmetic: making 八神殿 / 座摩神 / 御門巫祭神 / 生島巫祭神 `part of` the Jinmyōchō
    would empty this report to the 2 genuinely bare items. Only worth it if the report is meant to be
    a zero-inbox; it is a Wikidata edit, so it waits for 2026-09-18 either way.

  **Housekeeping done 2026-08-19:** the generator called the class "living/entry duplicates &mdash; the
  same shrine under the same name &rarr; link or merge". It now calls them **name collisions**, says
  plainly that a shared name is not proof of identity, and carries the withdrawal note on the section
  itself. Headline reads `149 orphans: 48 name collision / 0 Kokugakuin-id disagreement / 101 no-twin`.

  ### B3. The orphan Shikinaisha — mis-tagged, or missing entries? **Re-read before deciding.**
  Was 66; now **101** after 36 members arrived from B2's id-disagreement class, which turned out not to
  exist. With B2 withdrawn the honest count is closer to all **149** orphans, since the 48 "duplicates"
  are only name collisions. 101 confirmed-Shikinaisha with no twin: either modern shrines wrongly tagged as 927 entries, or real
  entries the lists are missing. Same table as B2.
  - **ASK:** "How do I treat the 66?" → *investigate case-by-case* / *treat as mis-tagged* (drop the
    class) / *treat as missing entries* (add to the list).

  ### B4. The 18 missing Kokugakuin ids — auto-fill or eyes?
  18 register entries lack a Kokugakuin database id; the strict matcher found ZERO safe to add (two
  adjacent DB entries can share a name). **Same 18 as B7** — where five of them turn out to be the
  one Izumo cluster, so this is 13 rows plus a knot, not 18 independent lookups.
  Table: https://emmaleonhart.github.io/shintowiki-scripts/kokugakuin-missing-ids.html
  - **ASK:** "Is exact name-matching good enough to auto-fill, or do the 18 need per-item eyes?" →
    *per-item eyes* / *auto-fill the exact matches*.

  ### B5. The ~66 items with two Kokugakuin ids — how to assign the section?
  Each is a candidate for two different 927 entries, so its parent-link needs a "which entry" (P958)
  qualifier. Emma earlier ruled all ambiguous.
  Table: https://emmaleonhart.github.io/shintowiki-scripts/kokugakuin-multi-p13677.html
  - **ASK:** "Go through these with me per-item now, or leave them for you to work off the table?" →
    *per-item with you* / *leave for you*.

  ### B6. The Awa list fix — how to delete the wrong statement?
  Awa entry 3 should be 天神社 (add already queued); the wrong 下立松原 statement must be deleted, but it
  can't be a QuickStatement (下立松原 sits at ordinals 3 AND 5, same value).
  https://emmaleonhart.github.io/shintowiki-scripts/awa-entry-3.html
  - **ASK:** "Sequential-misc unit (remove BOTH 下立松原 has-parts, re-add the correct #5), or you
    hand-delete the one statement?" → *sequential unit* (I build it) / *you hand-delete*.

  ### B7. Kokugakuin P13677 matcher — examples DELIVERED 2026-08-19, one question left
  Emma 2026-07: *"I don't even understand what this actual thing even is"* and *"I genuinely do not
  have any idea what shrines this is referring to."* Both were asks for the shrines to be NAMED, not
  linked. All 18 are now written out on [[Open questions]] itself.

  **The finding that reframes it: five of the 18 are one cluster, not five cases.** 坐韓国伊大弖神社,
  嘉羅久利神社, 佐久多神社 (意宇郡) and 韓國伊太弖奉神社, 天若日子神社 (出雲郡) are the Izumo knot.
  佐久多神社 is two items for one shrine — Q135040907 holds id 182811, Q135070108 holds none — which is
  the 佐久多/嘉羅久利 論社 split jawiki records. The two 野蚊神社 rows are likewise two distinct items
  of the same name in one district, which is why the matcher refused to pick.

  **Emma's ruling, 2026-08-24: pull them out.** So this is not 18 cases. It is the Izumo knot, worked
  once against the Izumo item, plus **13** genuinely separate no-anchor/no-match cases. The two
  野蚊神社 rows stay inside the 13 — they are two distinct items of one name in one district, which is
  a different problem from the Izumo cluster and does not resolve with it.

  ### B8. Empty-items — which to restore?
  285 emptied items, 217 lost their P31 — restoration candidates, sorted by how much was lost.
  https://emmaleonhart.github.io/shintowiki-scripts/empty-items.html
  - **ASK:** "Generate restore-QuickStatements for a slice (e.g. the ones that lost their P31), or is
    this a browse-and-you-pick report?" → *generate restores for <slice>* / *browse-only for now*.

- **Wikidata batches built and waiting on the lockout (2026-09-18) — no work left on them**

  `multi_ordinal_removals.txt` (63 lines) is registered in `ATOMIC_FILES` in both submitters and
  runs in `generate-quickstatements.yml`, so it delivers itself once the lockout lifts.

  `lost_shrine_creates.txt` (39 lines, 3 CREATE blocks) is **not** registered, and that is the one
  open decision: a creation is a different QuickStatements shape and creations have been switched
  off before, so switching them on is Emma's call, not a side effect of the generator existing.

- **Pinned tail (keep last)**

  - [ ] Ensure the five session-local crons are running (this session 2026-08-05: work-loop bd4cf062
    :03, auto-flush 73fd217e :15, status-report c6048135 :42, briefing acf528e2 08:03, debrief
    4c5db204 23:57). SYNC fast-forwards onto origin/main each tick.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
