# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).


## 🚦 Wiki-editing gate — WORK-LOOP READS THIS FIRST
<!-- WIKI_GATE: WAIT -->
**Status: ⏸ WAITING** (Miraheze 403, checked 2026-07-13 00:14 UTC) — wiki editing is blocked. The hourly `wiki-editing-gate.yml` CI job runs `check_wiki_login.py` and flips the marker above to **`WIKI_GATE: GO`** the moment the login works again.
`wiki-editing-gate.yml` CI job runs `check_wiki_login.py` and flips the marker above to
**`WIKI_GATE: GO`** the moment the login works again.

**Work-loop, every tick:** SYNC (pull remote) first, then read the marker.
- Marker says **GO** → wiki editing is live: start working through the **❓ DECISIONS** below,
  one at a time, in order, each with the explain-first option. This is your signal to actually run.
- Marker says **WAIT** → do only **▶ DO / 🤖 AUTO** items and wait. Do NOT fire the decisions; we're
  just holding until the gate opens (no more spinning on "nothing actionable").

**How this queue executes (Emma 2026-07-11).** Every item is either executable now or clearly
blocked — no item just sits with a buried question. Each is tagged:

- **❓ ASK** — needs Emma's decision. The exact AskUserQuestion is written under the item. The
  work-loop FIRES it (don't silently skip) and then does the chosen branch. Clear these top-down.
- **▶ DO** — obvious, no question; just execute.
- **🤖 AUTO** — runs itself (CI / a collector / the drip); no action beyond letting it run.
- **⏸ BLOCKED** — waiting on a named external thing; skip until that clears.

**Login gate.** The 🚦 marker at the very top is the signal — CI keeps it current. When it says GO,
the decisions run; when WAIT, only DO/AUTO items run. Wikidata / read-only work is unaffected either
way.

---

## ❓ DECISIONS — fire the AskUserQuestion, then do the branch (clear these first)

**Standing rule: EVERY decision below also carries a "walk me through it first / let's chat"
option.** Emma often doesn't have the context to pick A vs B cold, and that's fine — she picks
"explain it first", the bot lays out the situation in plain terms in chat (or on the Open questions
page once the wiki unblocks), they talk it through, THEN decide. So each AskUserQuestion the
work-loop fires must include that option alongside the concrete branches. Never treat a decision as
"blocked on Emma" and skip it — fire the question (with the chat option) so it can actually move.
Fire ONE decision at a time, in order, not a batch.

### D1. Sequential-misc: where does a pair's ADD live?
The one-line-per-day file (`sequential_misc.txt`) is built + tested but empty. To populate a
remove-then-add pair we need to know where the ADD goes.
- **ASK:** "For a sequential-misc pair, put the ADD in both the atomic drip and the sequential
  file, or move it into sequential only?" → *sequential only* (single ordered home) / *both*
  (redundant, idempotent).

### D2. The 84 duplicate shrine pairs — link or merge?
84 living-shrine items duplicate their 927-register-entry twin (same Kokugakuin id / name).
Table: https://emmaleonhart.github.io/shintowiki-scripts/shikinaisha-orphans.html
- **ASK:** "Link each pair with 'said to be the same as', or merge them?" → *link* (I generate
  QuickStatements, add-only) / *merge* (manual/browser, I hand you the list) / *case-by-case*.

### D3. The 66 orphan Shikinaisha — mis-tagged, or missing entries?
66 confirmed-Shikinaisha with no twin: either modern shrines wrongly tagged as 927 entries, or
real entries the lists are missing. Same table as D2.
- **ASK:** "How do I treat the 66?" → *investigate case-by-case* / *treat as mis-tagged* (drop the
  class) / *treat as missing entries* (add to the list).

### D4. The 18 missing Kokugakuin ids — auto-fill or eyes?
18 register entries lack a Kokugakuin database id; the strict matcher found ZERO safe to add (two
adjacent DB entries can share a name). Table:
https://emmaleonhart.github.io/shintowiki-scripts/kokugakuin-missing-ids.html
- **ASK:** "Is exact name-matching good enough to auto-fill, or do the 18 need per-item eyes?" →
  *per-item eyes* / *auto-fill the exact matches*.

### D5. The ~66 items with two Kokugakuin ids — how to assign the section?
Each is a candidate for two different 927 entries, so its parent-link needs a "which entry" (P958)
qualifier. Emma earlier ruled all ambiguous. Table (parent entry vs the item's two entries):
https://emmaleonhart.github.io/shintowiki-scripts/kokugakuin-multi-p13677.html
- **ASK:** "Go through these with me per-item now, or leave them for you to work off the table?" →
  *per-item with you* / *leave for you*.

### D6. The Awa list fix — how to delete the wrong statement?
Awa entry 3 should be 天神社 (add already queued); the wrong 下立松原 statement must be deleted, but
it can't be a QuickStatement (下立松原 sits at ordinals 3 AND 5, same value).
https://emmaleonhart.github.io/shintowiki-scripts/awa-entry-3.html
- **ASK:** "Sequential-misc unit (remove BOTH 下立松原 has-parts, re-add the correct #5), or you
  hand-delete the one statement?" → *sequential unit* (I build it) / *you hand-delete*.

### D7. Kokugakuin P13677 matcher — what did you actually want here?
Emma 2026-07-09: *"I don't even understand what this actual thing even is."* The matcher
(`match_kokugakuin_ids.py`) cut the missing-id set 94→18 (same set as D4).
- **ASK:** "This is the same 18 as D4 — is D4 the whole of it, or is there a separate thing you
  wanted from the matcher?" → *D4 covers it, drop this* / *there's more (you explain)*.

### D8. Empty-items — which to restore?
New report (from Special:Export): 285 emptied items, 217 lost their P31 — restoration candidates,
sorted by how much was lost. https://emmaleonhart.github.io/shintowiki-scripts/empty-items.html
- **ASK:** "Do you want me to generate restore-QuickStatements for a slice of these (e.g. the ones
  that lost their P31), or is this a browse-and-you-pick report?" → *generate restores for <slice>*
  / *browse-only for now*.

---

## ▶ DO / 🤖 AUTO — running, no decision

- 🤖 **Label-typo collector** — re-run `collect_label_typo_answers.py` whenever a remote-routine
  commit lands (cloud fills answers a trickle at a time; 1 collected 07-11, 156 pending).
- 🤖 **Description-enrichment + ronsha-ranking + category-translation collectors** — same pattern;
  run when their cloud answers land. `docs/description_enrichment_pipeline.md`.
- 🤖 **Engishiki list membership** — script 1 (adds, `list_membership_rebuild.txt`) + script 2
  (removals, `list_membership_removals.txt`, 2,236 pure removals) both registered; drip when the
  pause lifts. The 22 duplicate `part of` are report-only (value-match-unfixable). Detail:
  `docs/ronsha_list_membership_2026-07.md`.
- 🤖 **Province exclusions** — `province_exclusions.txt` (382 ADD-only lines) registered, drips.
  Province work is ADD-ONLY, no removals ever. `docs/province_exclusion_residual_2026-07.md`.
- 🤖 **Bruno archiver** — `archive_destroyed_items.py` runs in CI, auto-captures new damage.
- 🤖 **Wiki-editing week-long lockout** (built 2026-07-11, Emma's directive). `wiki-editing-lockout.yml`
  runs ~1AM PDT: checks whether EmmaBot edited in the past 8h (a 403 counts as 0 edits, fail-closed).
  No edits → writes a 7-day lockout to `shinto_miraheze/wiki_editing_lockout.state`; every leaf wiki-
  writer (git-synced-sync, fandom-sync, strip-property-dumps, update-shikinaisha-lists, wiki-cleanup,
  the orchestrators, untransclude) calls `wiki_edit_allowed.py` and bails while locked. Lockout
  auto-expires on its date; nothing to do. Audit that motivated it: `docs/wiki_403_audit_2026-07-11.md`
  (finding: block began in a quiet window, most likely Miraheze-side, but our baseline volume had
  crept up and we kept hammering the 403 — the lockout stops both).

---

## ⏸ BLOCKED — waiting on a named thing, skip until it clears

- ⏸ **Wiki editing (Miraheze 403).** `git-synced-sync` has failed EVERY run today
  (03:44–20:25 UTC 2026-07-11, ~17h) — mwclient can't log in through the anti-DDoS challenge. So the
  Open-questions responses (committed to `git_synced/Open questions.wiki`) and all cleanup/orchestrator
  edits are stuck in the repo. NOT fixable from CI. Clears when Miraheze stops challenging the runners,
  or Emma addresses it wiki-side. [[reference_miraheze_antiddos_challenge]]
- ⏸ **The whole Wikidata drip is paused** by `conflict_gate` until ~2026-08-08 (or 7 days after
  ブルーノ・プラス goes quiet). So every registered atomic file (citations, list-membership, province,
  reisai) is staged-but-not-delivered by design. Emma's caution gate; not a stall.
- ⏸ **Reisai** — 3,239 P837 lines staged (`reisai.txt`); live coverage still 195, unchanged.
  Reassess (Mie prefectural scraper?) once the drip resumes and the real gap is measurable.
  `docs/reisai_prefectural_feasibility_2026-07.md`.
- ⏸ **Repurposed-item damage** — Q123044569 (Kamo), Q134886554 (Chikadono), Q134736575 (見光寺),
  Q140476265 (junk). Emma: *document, don't touch; no contact* until we understand the editor. The
  Kikuna restoration is already queued to OUR item Q134926804. `docs/bruno_plus_analysis_2026-07.md`.
- ⏸ **Bunrei paper sources** — 神社本庁『全国神社祭祀祭礼総合調査』(1995) etc.; needs a library, not
  scrapeable. Online 総本社 sources are exhausted (~10,650 cited edges).
- ⏸ **Category-orchestrator speed-up** *(this is "the category thing")* — a POSSIBLE future
  optimization to make wiki category-page processing faster (skip some ops on ~3k enwiki-junk cats,
  or shard the namespace). Only worth doing IF the Japanese-category-translation drain proves too
  slow. It isn't a problem now → nothing to do; dormant.

---

## Pinned tail (keep last)

- [ ] Ensure the five session-local crons are running (this session: work-loop d6754ae5 :03,
  auto-flush 3d3cd832 :15, status-report 0df6273e :42, briefing 257eeecc 08:03, debrief ee782e80
  23:57). SYNC fast-forwards onto origin/main each tick.
- [ ] Run the status-report action once more independently as an end-of-session summary.
