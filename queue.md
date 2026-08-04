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

## A0. 🖥️ DESKTOP HANDOFF (front of queue · later today 2026-08-03) — name-in-kana → label pipeline

**What it is.** Give shrines a correct *modern hiragana* P1814 (name in kana), extracted by Opus from the
jawiki lead, as a new stage of the **label** pipeline. Name-in-kana is in almost every jawiki article but
is NOT reliably regex-extractable (furigana / bold-reading parsing is fragile) — that fragility is exactly
why the LLM step earns its place. This feeds romaji/label generation and may overwrite the Indonesian-seed
labels and some queued labels → that's why it's front of queue. Not gated on Miraheze (jawiki reads +
Wikidata + local pipeline), so the 403 blackout doesn't touch it; it needs a **desktop** for the
all-article download + local pipeline run.

**⚠️ Do NOT confuse with the kana-*qualifier* cleanup.** `generate_kana_qualifier_add.py` / `_remove.py`
is Engishiki-only, undoing the ~1yr-old error where ancient-Japanese *katakana* readings (from the
Engishiki-chapter tables Emma put on jawiki) landed in top-level P1814 — wrong; P1814 wants modern
*hiragana*. That cleanup relocates the old reading onto the ojp-hani P1448 as a カミノヤシロ qualifier and
strips it from top-level, leaving those Engishiki items with NO modern P1814.
**Collision risk on the shared Engishiki items:** the new writer and the cleanup both touch P1814. Use
add-first / remove-later (two scripts; the remove only fires after a fresh SPARQL confirms the add landed —
CLAUDE.md rule), and gate the new writer so it never re-introduces what the cleanup is stripping. Get
Emma's eyes on this ordering before running the Engishiki subset.

**Target set (SPARQL).** Shinto shrines (`?item wdt:P31 wd:Q845945`) with a jawiki sitelink and NO
top-level P1814. Reuse the `all_shrines()` SPARQL shape in
`modern-quickstatements/generate_bunrei_quickstatements.py` (query-main endpoint, UA-compliant). Two
buckets:
- **(a) HAS en label** — most likely to carry romanization-derived errors (includes already-queued
  labels). Highest priority.
- **(b) NO en label but scheduled** — download the article, extract kana, and locally generate BOTH the
  P1814 and the new en label; enqueue both.

**Local pipeline (desktop):**
1. Download the jawiki **lead** for each target (lead is enough — the reading sits in the first sentence).
2. Opus extracts the kana reading.
3. **THE gate: exclude any katakana candidate** — P1814 wants modern hiragana; katakana signals the
   ancient-reading error. Otherwise do NOT over-gate on confidence (Emma): the LLM path is high-quality and
   *producing* kana is the priority. (If quality holds, the katakana exclusion may be all the gating we need.)
4. For bucket (b), also generate the en label — reuse `shinto-label-generator/` (`language_registry.py`,
   `generate_multilang_quickstatements.py`; `modern-quickstatements/kana_english.py` for kana→romaji) and
   drip via `select_label_proposals.py`.
5. Enqueue: P1814 line(s) into an atomic `.txt`; new en labels into the label-proposal drip.

**QS output.** `Qxxx|P1814|"<hiragana>"|S143|Q177837|S4656|"<jawiki url>"`, drained by the daily submitter.
Generation is NOT blocked by the 2026-08-10 Wikidata freeze — only submission is, so staging now is fine.

**CI/CD phase (items with no queued en label).** A new label-pipeline step BETWEEN "check P1814" and the
same-name/disambig step: save the jawiki article to Claude → extract kana → make P1814 → continue normally.
Model it on the `remote_queue.py` answer-marker + collector pattern (builder writes a work-file = lead +
`<!-- ANSWER: -->` marker; the remote routine fills it; a `collect_*` script turns answers into QS) — same
shape as `collect_label_typo_answers.py` / `collect_category_translations.py`.

## A0b. 🖥️ DESKTOP (later today 2026-08-03) — Beppyo Shrine Opus Pass: mother house (P612)

**What it is.** Mother house (P612) is actually **very common in jawiki *prose*** — of the articles Emma
has read, at least ~a third mention it, often most — but it's essentially NEVER in *structured* data (no
infobox field), so it's not cleanly regex-extractable. That mismatch (ubiquitous in prose, absent from
structured data) is the "weirdness," and it's exactly why this is an LLM job. **Emma is very confident an
LLM can extract it — but it's an *Opus* job specifically** (not a lesser model), and expect the results
to need some correction. Concrete plan: download every **Beppyo shrine** (別表神社) Japanese and/or English
article and run a **local Opus pass** to extract the mother house / 総本社 / 勧請 origin. **Large shrines
first, then move down** (may extend downward later). This produces the more-specifically-sourced, in-depth
*individual* P612 lines — the accurate, indefinite layer beneath the coarse suffix-network heads.

- **Output:** P612 QS lines, one statement per branch, `P1013 = Q195793` in the same statement + a
  jawiki/enwiki citation. Follow the P612 invariant in `docs/wikidata_shrine_festival_model.md` (ONE P612,
  criterion-used qualifier, never a bare P612). Drains via the daily submitter (freeze-gated on submission
  only).
- **Beppyo set:** SPARQL the 別表神社 membership — **confirm the exact Wikidata QID / route before
  running; do not guess it.**
- **Keep the suffix-based (name-based) generator (`generate_bunrei_quickstatements.py`) but time-box it to
  ~6 months, then STOP** (Emma). Rationale: it's **inaccurate but descriptive** — the suffix→network-head
  guess is only approximately right, but it's *close enough* that when it sits on an item a while, human
  editors are likely to notice and fix it. That's the point: it seeds/establishes the convention on
  Wikidata, and being approximately-right-and-visible is what invites better-equipped editors to correct
  it. Not perpetual maintenance; the individual Opus-extracted lines (above) are the accurate layer.
- **A more organized extraction technique is a job for Topaz (Emma's other tool), NOT this repo.**

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
- 🤖 **Shinmei DB (P14391)** — `generate_shinmei_ids.py` → `shinmei_ids.txt` (**77**). Audited
  2026-07-28 and the count went DOWN on purpose: the matcher had no class gate at all (its sibling
  `generate_genbu_ids.py` always had one), so three category errors were staged and would have gone
  out when the freeze lifts — 気比大神→`Q11129346` (the SHRINE 氣比神宮), 筑紫島→`Q13987` (the modern
  island 九州), 波比岐神→`Q10928586` (座摩神). A deity/non-shrine gate now runs AFTER uniqueness; it
  rejects, it never disambiguates (applying it during the lookup turned two safely-ambiguous names
  into confidently wrong ones). Rejections are listed in `_site/shinmei_unmatched.txt`.
  - ❌ **The fuzzy/alias pass is settled: NOT worth doing — do not re-attempt.** The old note here
    said "256 kami have no exact-label match"; the real figure is **129** (+19 ambiguous). Suffix
    variants (strip/append 神/命/尊/大神/之命) over all 129 resolve just 3, and 2 of the 3 are wrong
    (穴戸神→`Q907382` 長門国, a province; 大土神→`Q11571306` 犯土, a calendrical term). 1-in-3
    precision on a deity identifier is not a trade worth making. The 129 are obscure Kojiki names
    with no Wikidata item; the 19 ambiguous ones need Emma to choose.
- ▶ **Prefectural shrine-association IDs → P973.** Emma decided 2026-07-28: **P973 now** (not a
  property proposal, not the private repo). No new property needed.
  - **Correction to the old framing:** there is no "rest of the CSV" to cover.
    `generate_jinjacho_p973.py` already emits **all 88** rows of
    `jinjacho/shrines_and_websites.csv` — that CSV is a *sample*, not a backlog, so re-running the
    generator adds nothing. Coverage grows only by resolving MORE shrine→URL pairs.
  - ✅ **Pipeline BUILT 2026-07-28** (`f97c85b74`): `jinjacho/crawl_jinjacho_shrines.py` →
    `crawled_shrines.csv` → `jinjacho/match_jinjacho_shrines.py` → `crawled_shrines_matched.csv` →
    `generate_jinjacho_p973.py` (now reads that file *and* the original 88-row sample). 16 tests,
    wired into `ci.yml`. External sites only, so it runs through the blackout.
  - ✅ **Shiga and Saitama are COMPLETE** (2026-07-28): 1,388 + 1,284 records. Both ended on miss
    tolerance, and that was verified to be the real end of the id space, not a gap — Saitama 404s
    past 10397, Shiga serves empty pages past 1560.
  - ⏳ **Gifu still crawling** — cursor in `crawl_state.json`; that host answers in ~20s/request, so
    its 2,600 ids are ~12h of wall-clock. Resume with
    `python crawl_jinjacho_shrines.py --family gifu --max-pages 2400`. **After each chunk:** re-run
    `match_jinjacho_shrines.py` then `generate_jinjacho_p973.py` and commit the three outputs —
    both are idempotent and simply extend the file.
  - **Precision is deliberately expensive.** The match gate is the MUNICIPALITY from the crawled
    address, not the prefecture (prefecture-gating produced verified-wrong matches: a 大垣市 天満神社
    → 天満神社 (高山市)), plus a collision guard dropping any item claimed by two crawled shrines.
    Expect a low yield; a missed shrine costs nothing, a wrong P973 is a wrong statement.
  - **Not yet covered:** Aichi (UUID keys) and Mie/Osaka/Kagoshima (name-slug paths) are not
    id-enumerable — they need an index harvest before they can be added as families.
  - Add-only; the daily editor skips statements that already exist, so re-runs are no-ops.

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
- **Mother house (P612): active work is A0b** (Beppyo Opus Pass, individual lines). Suffix generator
  stays but time-boxed ~6 months (convention-establishment, not perpetual). Organized extraction →
  Topaz, not this repo.

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
