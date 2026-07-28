# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

## 🚦 Wiki-editing gate — WORK-LOOP READS THIS FIRST
<!-- WIKI_GATE: WAIT -->
**Status: ⏸ WAITING** (weekly edit-test failed, 2026-07-26 10:56 UTC) — wiki editing is locked.
The Sunday `weekly-wiki-edit-test.yml` job re-tests a real edit and flips this to **`WIKI_GATE: GO`** when it lands.

> ⛔ **FULL BLACKOUT until 2026-08-09** (Emma 2026-07-27). Not just "no writes": **no requests to
> shinto.miraheze.org of any kind, reads included.** The 403 has been up since 2026-07-11 and never
> lifted; Emma's read is that our continuing to read through the challenge is what kept us looking
> persistent, so it was never relaxed. Every Miraheze-touching workflow is now gated on
> `wiki_editing_lockout.state`, and `weekly_wiki_edit_test.py` holds its probe until `blackout_until`
> passes — so the first test after the blackout, Sunday 2026-08-09, lands on ~13 days of true silence.

**THE QUEUE IS SPLIT IN TWO (Emma 2026-07-27).** Read this before picking work:

- **§A — NOT gated on shintowiki.** Wikidata, external DBs, repo/CI work. **Runnable right now,
  today, regardless of the 403.** The work-loop starts here, every tick, always.
- **§B — GATED on shintowiki access.** Nothing in §B can start until the marker says **GO**.
  Do not fire §B decisions, do not "prepare" §B work, do not touch the wiki to check something.

**Work-loop, every tick:** SYNC (pull remote) first, then read the marker.
- Marker **WAIT** → work §A only. §B does not exist for you.
- Marker **GO** → §A still comes first; then §B unlocks and the decisions fire one at a time.

**Item tags.** ❓ ASK = needs Emma's decision, the exact AskUserQuestion is written under the item;
fire it, don't skip it. ▶ DO = just execute. 🤖 AUTO = runs itself. ⏸ PARKED = waiting on a named
external thing.

---

# ═══════ §A — NOT GATED ON SHINTOWIKI · RUN THESE NOW ═══════

## A1. 🤖 Cloud-answer collectors — live again, run them when a routine commit lands

The routine's push was fixed 2026-07-28 (it had no repo bound; `session_context.sources` is the field
— see `docs/remote_queue_routine_prompt.md`), so answers are landing again and these are no longer
idle. Ran the same day: 9 label typos, 1 ronsha ranking, 11 descriptions, 12 category moves. All four
are repo-local — no Miraheze request — so they stay runnable through the blackout.
- `collect_label_typo_answers.py` — 147 pending.
- Description-enrichment (224 pending), ronsha-ranking (34 pending), category-translation (361
  pending) collectors — same pattern. `docs/description_enrichment_pipeline.md`.

## A2. ⏭ Court-rank (P14005) people pipeline — pure Wikidata, finishable now

Tags PEOPLE with P14005 from the ja.wp [[Category:日本の位階受位者]] tree. Decisions settled: create
missing items, every rank held, primary-label rank map, skip 无位, no parent-rank double-tag.
- ✅ 26 sub-rank items created (Q140679480…Q140679509); base ranks already existed.
- ✅ Sub-rank parent links (P361) run; 外従五位 base created = **Q140679675** (part of 外位).
- ✅ Bidirectional category links run: 42 recipient categories linked rank↔category (P1792/P301);
  24 missing category items created (Q140685601…).
- ⏳ **Category English labels:** `court_rank_category_en_labels.txt` (42 lines), add-only. Emma runs it.
- ✅ **Wire-in done 2026-07-28** — the live rerun reported all **42 rank categories resolved** (the
  stated condition), so the generator is a step in `generate-quickstatements.yml` and
  `court_rank_people.txt` (12,605 lines, 12,326 people) is registered in `ATOMIC_FILES`, uncapped
  (~10% of the daily draw, same share as its size peers). Lands no earlier than the 2026-08-04 freeze
  lift.
- Note: base-rank items still carry sub-rank names as skos aliases (正四位 has "正四位上/下"); optional
  cleanup now that sub-ranks are their own items.

## A3. 🤖 Shrine external-ID entity resolution — Wikidata + external sites

- 🤖 **Genbu.net (P13930)** — `generate_genbu_ids.py` → `genbu_ids.txt` (**1257**, up from 1041 after the
  kyūjitai + province-disambiguation passes). Registered; drips. Only the *live-wiki citation* source
  is capped by the 403 — the genbu crawl itself is unaffected, so further coverage work runs now.
- 🤖 **Shinmei DB (P14391)** — `generate_shinmei_ids.py` → `shinmei_ids.txt` (**80**, up from 77 via alias
  + kyūjitai matching). 256 kami still have no exact-label match; a fuzzy/alias pass could recover more.
- ❓ **Prefectural shrine-association IDs** — two walls found 2026-07-24: no public repo to merge (the
  research is in Emma's PRIVATE repo), and no Wikidata property exists for prefectural jinjacho
  databases. Pragmatic path needing no new property: **P973 (described at URL)** using jinjacho URLs
  already cited in our articles — 88 already shipped.
  - **ASK:** "P973 now / propose dedicated properties / hand me the private repo?" — plus the standing
    *"walk me through it first"* option.

## A4. 🤖 Wikidata drip — staged, waiting on conflict_gate (NOT on the wiki)

All registered atomic files are staged-but-not-delivered by design until `conflict_gate` lifts
(~2026-08-08, or 7 days after ブルーノ・プラス goes quiet). Emma's caution gate, not a stall.
- **Engishiki list membership** — script 1 adds (`list_membership_rebuild.txt`), script 2 removals
  (`list_membership_removals.txt`, 2,236 pure removals). The 22 duplicate `part of` are report-only.
  `docs/ronsha_list_membership_2026-07.md`.
- **Province exclusions** — `province_exclusions.txt` (382 lines). ADD-ONLY, no removals ever.
  `docs/province_exclusion_residual_2026-07.md`.
- **Reisai** — 3,239 P837 lines staged (`reisai.txt`); live coverage still 195. Reassess (Mie
  prefectural scraper?) once the drip resumes and the real gap is measurable.
- 🤖 **Bruno archiver** — `archive_destroyed_items.py` runs in CI, auto-captures new damage.

## A5. ⏸ Parked — external, and not shintowiki either

- **Repurposed-item damage** — Q123044569 (Kamo), Q134886554 (Chikadono), Q134736575 (見光寺),
  Q140476265 (junk). Emma: *document, don't touch; no contact* until we understand the editor. The
  Kikuna restoration is already queued to our item Q134926804. `docs/bruno_plus_analysis_2026-07.md`.
- **Bunrei paper sources** — 神社本庁『全国神社祭祀祭礼総合調査』(1995) etc.; needs a library, not
  scrapeable. Online 総本社 sources are exhausted (~10,650 cited edges).

---

# ═══════ §B — GATED ON SHINTOWIKI · DO NOT START UNTIL `WIKI_GATE: GO` ═══════

Everything below needs the wiki. While the blackout is on, these are not just blocked — **touching
them means touching Miraheze, which is the exact thing the blackout exists to prevent.**

## B0. 🤖 The gate itself

- **Weekly wiki edit-test** — `weekly-wiki-edit-test.yml`, Sundays. CI attempts a REAL edit to
  `User:EmmaBot/edit-test`. Success → unlocks for the week + marker GO; failure → 8-day lock + marker
  WAIT. Currently held by `blackout_until: 2026-08-09`, so it makes no request at all before then.
  Nothing to do — the Sunday test is the sole decider.
  Audit: `docs/wiki_403_audit_2026-07-11.md`. The block is a Cloudflare zone challenge on shinto
  (aelaki works from the same IP).
- **All wiki edits are stuck in the repo** — Open-questions responses committed to
  `git_synced/Open questions.wiki`, plus every cleanup/orchestrator edit. Not fixable from CI.
  [[reference_miraheze_antiddos_challenge]]

## B1. Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-07-13)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki`
(the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every
actionable item or Emma disposition not yet handled: decompose it into concrete steps, or act on it now
and prune the resolved bullet. Then delete THIS block. **Needs the live page → §B.**

## B2–B8. ❓ DECISIONS — fire ONE at a time, in order, once the gate opens

**Standing rule: EVERY decision carries a "walk me through it first / let's chat" option.** Emma often
doesn't have the context to pick A vs B cold — she picks "explain it first", the bot lays out the
situation in plain terms, they talk, THEN decide. Never treat a decision as "blocked on Emma" and skip
it; fire the question with the chat option so it can actually move.

> These can't be decided blind — Emma reviews them against the Open questions page **plus** the
> browsable tables. The tables are GitHub Pages and work right now, but the review pairs the two, so
> they wait for the gate (Emma 2026-07-13).

### B2. The 84 duplicate shrine pairs — link or merge?
84 living-shrine items duplicate their 927-register-entry twin (same Kokugakuin id / name).
Table: https://emmaleonhart.github.io/shintowiki-scripts/shikinaisha-orphans.html
- **ASK:** "Link each pair with 'said to be the same as', or merge them?" → *link* (I generate
  QuickStatements, add-only) / *merge* (manual/browser, I hand you the list) / *case-by-case*.

### B3. The 66 orphan Shikinaisha — mis-tagged, or missing entries?
66 confirmed-Shikinaisha with no twin: either modern shrines wrongly tagged as 927 entries, or real
entries the lists are missing. Same table as B2.
- **ASK:** "How do I treat the 66?" → *investigate case-by-case* / *treat as mis-tagged* (drop the
  class) / *treat as missing entries* (add to the list).

### B4. The 18 missing Kokugakuin ids — auto-fill or eyes?
18 register entries lack a Kokugakuin database id; the strict matcher found ZERO safe to add (two
adjacent DB entries can share a name).
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

### B7. Kokugakuin P13677 matcher — what did you actually want here?
Emma 2026-07-09: *"I don't even understand what this actual thing even is."* The matcher
(`match_kokugakuin_ids.py`) cut the missing-id set 94→18 (same set as B4).
- **ASK:** "This is the same 18 as B4 — is B4 the whole of it, or is there a separate thing you wanted
  from the matcher?" → *B4 covers it, drop this* / *there's more (you explain)*.

### B8. Empty-items — which to restore?
285 emptied items, 217 lost their P31 — restoration candidates, sorted by how much was lost.
https://emmaleonhart.github.io/shintowiki-scripts/empty-items.html
- **ASK:** "Generate restore-QuickStatements for a slice (e.g. the ones that lost their P31), or is
  this a browse-and-you-pick report?" → *generate restores for <slice>* / *browse-only for now*.

## B9. ⏸ Category-orchestrator speed-up *("the category thing")*

A POSSIBLE future optimization to make wiki category-page processing faster (skip some ops on ~3k
enwiki-junk cats, or shard the namespace). Only worth doing IF the Japanese-category-translation drain
proves too slow. It isn't a problem now → dormant.

---

## Pinned tail (keep last)

- [ ] Ensure the five session-local crons are running (this session: work-loop d6754ae5 :03,
  auto-flush 3d3cd832 :15, status-report 0df6273e :42, briefing 257eeecc 08:03, debrief ee782e80
  23:57). SYNC fast-forwards onto origin/main each tick.
- [ ] Run the status-report action once more independently as an end-of-session summary.
