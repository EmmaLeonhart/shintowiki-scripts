# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

## 🚦 Wiki-editing gate — WORK-LOOP READS THIS FIRST
<!-- WIKI_GATE: GO -->
**Status: 🟢 GO** (weekly edit-test passed, 2026-08-23 09:48 UTC) — wiki editing is live for the week; work-loop, start clearing the ❓ DECISIONS.
The Sunday `weekly-wiki-edit-test.yml` job re-tests a real edit and flips this to **`WIKI_GATE: GO`** when it lands.

> ✅ **THE BLACKOUT IS OVER — ended 2026-08-19T01:54 UTC, and this paragraph is the record, not the
> rule.** Emma's 2026-07-27 full blackout (no requests to shinto.miraheze.org of any kind, reads
> included) ran its course; the 403 that had been up since 07-11 was a Cloudflare bot challenge, and
> it ended when she sent the farm the bot's User-Agent and they allowlisted it. The weekly edit-test
> then passed and landed a real edit on `[[User:EmmaBot/edit-test]]`.
>
> **Read `shinto_miraheze/wiki_editing_lockout.state`, not this prose.** It is `locked: false`. This
> paragraph said "until 2026-08-09" for ten days after that date passed, while the marker above it
> said GO — a work-loop reading top-to-bottom would have stopped on a blackout that had already
> ended. Retired 2026-08-19.
>
> **⚠ The OTHER two gates are still closed and are NOT this one:** Wikidata editing is locked until
> **2026-09-18** (`wikidata_editing_lockout.state`, Emma 2026-08-18), and the enwiki-mention
> condition is still unmet (7 mentions on the AI noticeboard, 2 on WikiProject Japan). Wiki work is
> live; Wikidata writes are not.

**THE QUEUE IS SPLIT IN TWO (Emma 2026-07-27).** Read this before picking work:

- **§A — NOT gated on shintowiki.** Wikidata, external DBs, repo/CI work. **Runnable right now,
  today, regardless of the 403.** The work-loop starts here, every tick, always.
- **§B — GATED on shintowiki access.** Nothing in §B can start until the marker says **GO**.
  Do not fire §B decisions, do not "prepare" §B work, do not touch the wiki to check something.

**Work-loop, every tick:** SYNC (pull remote) first, then read the marker.
- Marker **WAIT** → work §A only. §B does not exist for you.
- Marker **GO** → §A still comes first; then §B unlocks and the decisions fire one at a time.

**⏳ TIME-GATED WORK DOES NOT LIVE IN THIS FILE (Emma, 2026-08-20).** If the only thing standing
between an item and being done is a DATE, it goes in `scheduled/scheduled_items.json`, not here
wearing a PARKED label. Her words: *"waiting means you write a script that injects it by a json into
the queue or open questions at a certain date … because it being visible in the queue as 'parked'
adds clutter, and other time gated stuff also goes into this, github actions injects on that day
into open questions and the queue."*
- `scheduled/inject_due_items.py` runs daily from `inject-scheduled-items.yml` and appends the item
  to `queue.md` and/or `[[Open questions]]` on its due date — the first day anyone could act on it.
- Idempotent via an `<!-- scheduled:<id> -->` marker in the target, **not** the json's `injected`
  flag: the json is a tracked file someone can revert or merge-resolve, and the guard has to live in
  the file it protects.
- **Only for DATE gates.** A gate on a *signal* — a watcher going quiet, an external condition
  clearing — is not this, and dating it would misrepresent Emma's condition as a calendar wait. Those
  stay here with a named blocker. `_not_moved` in the json records which ones and why.
- Currently held: the `continue-on-error` decision (2026-09-21) and two Wikidata-lockout items
  (2026-09-18).

**Item tags.** ❓ ASK = needs Emma's decision, the exact AskUserQuestion is written under the item;
fire it, don't skip it. ▶ DO = just execute. 🤖 AUTO = runs itself.

**⏸ PARKED IS GONE — Emma, 2026-08-19: *"Anything 'parked' should be addressed with an
AskUserQuestion now."*** The tag was retired then and the last two uses were cleared 2026-08-23 (A5
was finished work mislabelled; B9 is a real condition, so it is OUT-OF-SCOPE with the condition
named). Parking is not a disposition. Anything that cannot proceed gets a named blocker from the
taxonomy above, or goes to her directly.

---

# ═══════ §A — NOT GATED ON SHINTOWIKI · RUN THESE NOW ═══════

## A-KANA. ▶ kana-from-jawiki, FULL BUILD — Emma's call 2026-08-23; guessing is wired, draining is not

Her decision via AskUserQuestion: the full version, not the bounded one — pull the kana from the
jawiki article, feed the naming pipeline, **and guess where no kana can be found**. She was shown
her own 2026-08-18 objection (it extends the programme's runtime, against the finite ending) and
chose the full build anyway.

**⛔ pykakasi is OUT and that is settled.** A mechanical guesser was built and measured against the
342 readings already extracted from articles: **47.7% exact, 52.3% wrong, 0% close** — the failures
were different words, not spelling slips (江島 えのしま→えじま, 三吉 みよし→さんきち, 一宮 いっく→
いちのみや). Emma: *"Pykakasi is horrible don't use it lol"* / *"This is a settled issue."* Deleted.
Do not reintroduce it; `test_name_in_kana_guess_answer.py` asserts the file stays gone.

- ✅ **`GUESS:` is now an answer kind** on the same work-file/ANSWER path that produced the 342
  correct readings. `collect_name_in_kana.py` accepts it and puts it through the identical hiragana
  gate. The builder's TASK asks for a derived reading — from the place-name it is named for, from
  other shrines of the same name, from the infobox — and names the three measured failure modes so
  the same error class does not come back. `NO_KANA` remains the right answer when nothing can be
  derived: a wrong reading is worse than none.
- ✅ **A `GUESS` carries NO source.** `S143`/`S4656` asserts *"the jawiki article states this"*,
  true of `KANA` and false of a guess. A sourced-looking wrong reading is worse than an unsourced
  one because nothing downstream can distinguish it.
- ✅ **Ten tranches built and drained — 862 answered, 0 rejected, 0 pending.**
  Answers in `shinto_miraheze/local_answers/name_in_kana_2026-08-23{,b,c,d,e,f,g}.tsv` and
  `…_2026-08-24{,b,c}.tsv`.
- **A third `GUESS` sub-shape: a PAIRED shrine whose lead gives each half separately.**
  `Q11633774` 豊榮神社・野田神社 — the lead reads 豊榮神社（とよさかじんじゃ）と野田神社（のだじんじゃ）,
  so both halves are sourced but the **combined string is not**. Staged as `GUESS`, no source.
  The contrast is in the same batch and is worth keeping: `Q11643733` 都波岐神社・奈加等神社's lead
  states the combined つばきじんじゃ・なかとじんじゃ outright, so that one is `KANA` **with**
  `S143`/`S4656`. Two paired shrines, two different answers, decided by whether any article states
  the value being written.
- ✅ **The "lead names a different shrine" case is now DETECTED BY THE BUILDER, not by
  whoever happens to notice.** `subject_mismatch()` compares the item's ja label to the name the
  lead actually opens on and writes a warning above the ANSWER marker telling the answerer not to
  copy the reading. **It caught 2 real cases on its first live tranche** — `Q11595844`
  秋葉神社・三座宮稲荷神社 (lead is about 秋葉神社 and 三座稲荷) and `Q11596881` 柳原稲荷神社 (lead is a
  bare 稲荷神社). Neither is visible from the answer format.
  - Tuned against 11 real cases from this session, because a first cut got two wrong in each
    direction: it passed 千住氷川神社 (the lead's name is a *substring* of the item's, which plain
    containment reads as a match) and flagged 利雁/利鴈 and 尾崎/尾﨑, which are one shrine with a
    variant kanji.
  - ✅ **One false positive on the SECOND tranche, fixed the same tick.** `Q11613492` 舊府神社 is
    led as 舊府**（旧府）**神社（ふるふじんじゃ） — the first parenthetical is a kanji gloss *inside*
    the name, so stopping at it yielded 舊府. `lead_subject()` now drops parentheticals carrying no
    kana. **A warning that cries wolf is worse than no warning**, so this mattered more than the
    miss rate. 18 tests, every case taken from a real work-file.
  - ⚠ **This is the highest-severity error the pipeline can make**, which is why it gets a builder
    check rather than a note: the lead states a reading cleanly, so a `KANA` answer looks
    well-sourced and the collector attaches `S143`/`S4656` — asserting jawiki backs a reading of a
    name the article never mentions.
- **`GUESS` has two shapes, and the second is the common one.** 11 guesses in 562 answers:
  - **No lead at all** (redirect / disambig / empty) — the case the builder now writes a work-file
    for. 6 so far.
  - **The lead names a DIFFERENT shrine.** The article is titled and led as a bare 氷川神社 while the
    item is 千住氷川神社 or 南沢氷川神社; or, worst, `Q11556511` 洲崎濱宮神明神社 whose lead is about
    海山道神社 entirely. Taking the lead's reading here yields a **sourced** answer about the wrong
    name — which is more dangerous than no answer, because `S143`/`S4656` would assert the article
    backs it. 5 so far, and this shape is invisible unless the item label is compared to the lead.
- **The target set is not purely shrines, and that is correct.** Emma's 2026-08-05 rule is *"is it a
  nameable place"*, not *"is it a shrine"*, and it has now admitted: a sea cave (`Q11488835`
  御厨人窟), two Kumano 王子 sites one of which no longer exists (`Q11480731`, `Q11483087`), a
  Kōyasan Shingon temple (`Q11545320` 歓喜院) and a park (`Q11548302` 水分れ公園). All have real
  readings in their own leads. **What DOES get excluded is a different class** — people,
  disambiguation pages, festivals, texts and organisations — and two of those reached the set anyway
  and were answered `NO_KANA` (`Q11435648` a Muromachi text, `Q11443187` a religious organisation).
- ✅ **The permanent skip loop is CLOSED 2026-08-23.** `Q11391058`, `Q11391059`, `Q11391060`
  (three Okazaki 八幡社) and `Q11396252` (刈田嶺神社 (七ヶ宿町)) were re-fetched and re-skipped by
  every tranche — three in a row printed an identical four — because the builder wrote no file
  "so a later run retries them". Their articles are redirects/disambig/empty, so the extract never
  arrives; it was a loop, not a retry.
  - The builder now writes a work-file with the LEAD replaced by `NO_LEAD`, which states that the
    extract will never come and names what is left to derive from. All four answered as `GUESS`:
    八幡社 → はちまんしゃ; 刈田嶺神社 → かったみねじんじゃ, taken from siblings `Q11396254` /
    `Q11396255`, which state it in their own leads and were answered from them the same day.
  - **Verified by re-running the builder**: 613 targets excluded as already answered and the four
    are gone from the front of the set. `test_name_in_kana_no_lead.py` (5 tests) pins both the
    behaviour and the prompt, including that the old `continue` cannot come back.
- ▶ **The remaining work is coverage, and it is the bulk of the programme.** Real counts from the
  builder itself: **2,633 targets** (bucket a 2,576, bucket b 57), of which 601 also carry an
  ojp-hani P1448 and are queued anyway because the two pipelines write disjoint values. **1,216
  resolved, 0 pending → ~1,417 still unqueued** (`_resolved.log`: 1,186 KANA · 15 GUESS · 8 KATAKANA
  · 5 NO_KANA · 1 NOT_A_SHRINE · 1 ALREADY_STAGED; `name_in_kana.txt` 1,211 lines). Keep rebuilding in
  tranches with
  `build_name_in_kana_queue.py --limit N`, answer locally in batches
  (`apply_local_answers.py --queue name_in_kana`, fixed 2026-08-23), then collect. The remote routine
  delivers ~5/day, so local batches are the road.
  ⚠ Generation only. **Nothing is delivered** — the Wikidata lockout holds to 2026-09-18.

## A-OQ. ▶ Metabolised off `[[Open questions]]` 2026-08-23 — both were ASKs that should have been DOs

Emma, on the page, about exactly this shape: *"OH MY GOD IS THIS DONE OR NOT YOU CUNT"*. Neither of
these needed her; both had been sitting as questions.

- ✅ **CAUSE FOUND 2026-08-24 by Emma: an erroneous merge. No new item is needed — undo it.**
  `Q135040908` was merged into `Q135040786` at **2026-05-23T21:28:33Z**
  (`wbmergeitems-to` + `wbcreateredirect` in its history). `Q135040908` *was* the entry-39 item:
  created 2025-06-24, ja 坐韓国伊**太**弖神社 (the 太 spelling = entry 39's register name), with
  `P155`→`Q135040907` (38), `P156`→`Q135040909` (40), `P361`→list at ordinal **39**, national
  ordinal **2264**, and both ronsha `P460`→`Q135070107`/`Q135070108`.
  - **The list has exactly one wrong cell**, measured live: 28→`Q135040786` ✅, 29→`Q135040787`
    筑陽神社 ✅, **39→`Q135040786`** ❌ (follows the redirect), 40→`Q135040909` ✅. **No ordinal is
    used twice.**
  - ⛔ **Two of my own readings were wrong and are corrected here, not left in chat.** I told her
    (a) the 大/太 spelling separates entries 28 and 39 — the 08-19 devlog had already retired that,
    because entry 28's *modern shrine* is spelled 太; and (b) ordinal 29 also held `Q135040786`
    while 39 was empty — a parse error on my own query. Neither is true of the live data.
  - ▶ **Restore the merge rather than create an item.** Un-merging returns the QID the list already
    points at, plus the 38/40 sequence, the 2264 ordinal and the ronsha links — all of which a fresh
    item would need rebuilt by hand and would still not match what other statements reference.
    Then delete the two `part of`→list rows the merge pushed onto `Q135040786`: ordinal **39** and
    the **bare** one. Keep 28.
  - BLOCKED-ON-USER-ACTION: undoing a merge is a manual Wikidata action and her lockout holds to
    2026-09-18. She is doing it herself; nothing to stage.

- ⛔ **RETRACTED 2026-08-23. Both the "41 of 42 verdicts are wrong" finding and the "773 staged
  removals would strip a real membership" finding were MINE and both were WRONG**, on the same
  mistaken premise: that a register naming a shrine means the shrine belongs to the list. It does
  not. Emma, shown the second one: *"pretty sure this is intended behaviour."* It is.
  - **List membership belongs to the ENTRY item.** `Q135040491` 出雲神社 (the Engishiki entry) holds
    `P361 → Q11368560` with `P1545: 1`, `P155`, `P156`. `Q10896675` 出雲大神宮 (the modern shrine)
    holds `P460 →` that entry plus two bare `P361` — which is the piped-link import damage the
    removal drip exists to strip. Checked on five more of the "41": all five are modern shrines with
    `P460` to a `Q135…` entry item. The pattern is uniform.
  - **The guard reading `P527` is reading the right source.** The list's members are the entry items,
    so a modern shrine is correctly absent. I called that a "partial transcription"; it is not.
  - **Her 2026-07-09 decision already settled this** — "Reading A: list membership belongs to the
    entry item, so the candidate loses it." The rule is now in `CLAUDE.md` so it is not re-derived.
  - `recheck_orphan_memberships.py` is **deleted**: it answered "does the register name this shrine",
    which is not the question, and keeping it would invite the same wrong inference again.

## A-CI. The 08-22 CI repair is VERIFIED. A separate, older defect remains.

Run `32615320387` (2026-08-23) settles the first half and rediagnoses the second.

**✅ Both 08-22 defects are fixed, measured on the run rather than on the diff.** All four jobs
that were red on 08-19 → 08-22 came back green or better:

| job | 08-22 | 08-23 |
|---|---|---|
| `generate-pages / build` | failure (`MIRAHEZE_EMAIL is not set`) | **success** |
| `generate-pages / deploy` | skipped | **success** |
| `cleanup / cleanup` | failure (`ModuleNotFoundError`) | **success** |
| `untransclude-crud-templates` | failure (`ModuleNotFoundError`) | **success** |
| `generate-quickstatements / generate` | failure in ~90s | **cancelled at the 75m cap** |

Every other job in the run is green. `secrets: inherit` and the 69 unbootstrapped imports are
done; nothing further to check there.

## A-CI2. ▶ The SUNDAY path does not fit in `generate-quickstatements`' timeout — and did not before this week

⚠ **I got this wrong in the 05:10 status report** and am correcting it rather than leaving it: I
guessed the 08-22 bootstrap fix had doubled the runtime by reviving 17 dead scripts. It had not.
The pattern is Sunday-only and it predates the fix:

- **2026-08-16 (Sunday) — cancelled.** Before the bootstrap bug even existed (`8ac7d8a2`, 08-19).
- **2026-08-23 (Sunday) — cancelled.**
- **08-17 (Mon), 08-18 (Tue) — success, 31m28s and 31m50s.**

So the Sunday-gated steps are the overrun, and the header comment above them says they were gated
*"so the daily job stays inside its timeout"* — which worked for the daily path and quietly failed
for the weekly one. My fix did make it worse (`generate_description_adds.py` is Sunday-gated, was
one of the 17, and now actually runs) but it is not the cause.

Where the budget went on 08-23, from the log's own timestamps — ~55 minutes in four steps:

    1060s  select_label_proposals    2,642,704 label proposals loaded
     867s  description fixes         1,267 collision groups
     723s  fetch [[QuickStatements/P11250]] from shintowiki
     655s  P459 qualifiers, phase 1

**The generators FINISHED.** It was cancelled inside the *commit* step, with the modified files
already listed — so a full Sunday regeneration was computed and then thrown away. That is why
`description_label_pairs.txt` has not moved since **2026-08-02** across three Sundays, and why it
still holds **5 `Did` against 3,514 `Duk`**.

- ✅ `timeout-minutes: 75` → **150**, with the measurement recorded in the workflow.
- ▶ **Still to verify on the next Sunday run:** `submit-quickstatements` non-skipped, and `Did` in
  the thousands. If `Did` does not move, the label-only fix did not take and the branch to re-read
  is the `new == desc` arm of `generate_description_fixes.py`.
- ⚠ **BLOCKED-ON-EXTERNAL and the wait is a WEEK, not a night — corrected 2026-08-24.** The run
  this was written against, `32615320387`, fired on **Sunday 2026-08-23** and was cancelled at the
  cap. It is now Monday, so tonight's run and the five after it take the `else` branch — *"not
  Sunday — keeping committed description_label_pairs.txt"* — and exercise none of this. **The next
  Sunday run is 2026-08-30.**
  - So a green nightly run in the meantime proves the timeout raise for the *daily* path only, which
    was never the failing one. Do not read it as verification of this item.
  - Stated as a fact about the cron, not as a due date: `date -u +%u = 7` is in
    `generate-quickstatements.yml`, and 2026-08-30 is simply when that next evaluates true.
- ▶ **If it overruns again, split rather than raise.** The Sunday-only steps belong in their own
  weekly workflow — the repo already does this with `weekly-wiki-edit-test.yml` — instead of
  riding the daily job's budget. Raising the cap is the small fix, not the right shape.
  ⚠ Generation only. **Nothing is delivered** — the Wikidata lockout holds to 2026-09-18.

## A0. 🖥️ name-in-kana → label pipeline — BUILT 2026-08-03; bucket (b) DONE, bucket (a) draining

**Status.** Builder `shinto_miraheze/build_name_in_kana_queue.py` + collector
`collect_name_in_kana.py`, on the same work-file/ANSWER-marker pattern as the other cloud queues;
`name_in_kana.txt` registered in `direct_daily_edits.ATOMIC_FILES`; the queue is registered in
`remote_queue.py` so the routine fills answers unattended.
- ✅ **Bucket (b) is FINISHED** — all 54 done locally: 50 P1814 lines + 43 en labels (via
  `kana_english.label_for`). 4 produced no statement: 3 legitimately mixed-script readings and 1
  two-shrine disambiguation page.
- ⏳ **Bucket (a): 2,582 targets; 281 done locally 2026-08-04**, **2 work-files left** in this
  tranche, both on purpose (below). `name_in_kana.txt` is at 343 lines.
  **The remote routine is not the bottleneck and never was** — every one of the 34 pending
  work-files still had an EMPTY answer marker, and so did all 222 description / 143 label-typo /
  34 ronsha / 354 category ones. Answering locally is the road. New tool for it:
  `shinto_miraheze/apply_local_answers.py --queue <q> --answers <tsv> --apply` fills the markers
  from a TSV, then the normal `collect_*.py` runs unchanged and applies its own gates. Answers
  kept in `shinto_miraheze/local_answers/`. It refuses to overwrite a marker the routine already
  filled.
- ✅ **The non-shrine leak is FIXED 2026-08-05 — and our P31 filter was never the cause.**
  Measured, not assumed: all three items genuinely carry `P31 = Q845945` on Wikidata alongside
  their real class. Q7137401 水谷川忠起 is `P31 = Q5` (human) **AND** `P31 = Q845945`. It is an
  upstream data defect, so no tightening of the shrine query can exclude them — the only handle is
  the OTHER class the item carries.
  - A survey of the whole target set found **135 distinct co-classes over 2,684 (item,class)
    pairs**, almost all legitimate shrine subtypes (Shikinaisha 442, Kokuhei-sha 440, Shikinai
    Ronsha 226, Hachiman 170). The non-shrine tail is **8 items**: the person, 4 disambiguation
    pages (浮島神社, 天山神社, 八海神社, 海神社 — each names several shrines, so a reading attaches
    to none), 2 festivals (御柱祭, 住吉の御田植), a book (住吉大社神代記), and an organization
    (鹿児島県神社庁). `NOT_A_SHRINE` in the builder excludes them and **prints each drop** — a
    silent one would read as the query merely missing them.
  - **The rule is "is it a nameable place", NOT "is it a shrine"** — Emma's ruling that the
    place-ish ones stay in. A forest, a mountain, a sea cave, a kofun and a building complex all
    have real readings, and `_resolved.log` already carries 東京十社 → とうきょうじっしゃ, so
    groups-of-shrines are settled as answerable too. A literal "must be a shrine" gate would have
    thrown all of that away. 8 tests pin both halves.
  - Q7137401's work-file is retired and logged `NOT_A_SHRINE` in `_resolved.log`.
- ✅ **機殿神社 (Q11544511) ANSWERED 2026-08-19 — it was never hard, and "deliberately unanswered"
  was the wrong call.** Emma: *"You have to come up with a reading... this is a pair of Shinto
  shrines... just get the reading of the combined ones from the readings on the items of the two of
  them. I feel like you're significantly overcomplicating this."* She is right. The jawiki lead gives
  both readings outright — 神服織機殿神社（かんはとりはたどのじんじゃ）and
  神麻続機殿神社（かんおみはたどのじんじゃ）— so the shared tail is unambiguous, and the article
  states the collective name itself: *両社を合わせて両機殿（機殿神社）と呼ぶ*.
  **P1814 = はたどのじんじゃ**, staged in `name_in_kana.txt` sourced to the jawiki article.
  The pipeline now has **zero** unanswered work-files.
  - ✅ **Q135186223 RESOLVED 2026-08-20 — it IS the modern shrine, and it was already staged.**
    Two things were wrong in the note this replaces. It said the item was "not staged"; it is, at
    line 299 of `name_in_kana.txt`, with かんはとりはたどのじんじゃ. And it read "(Ronsha 1)" in the
    description as evidence of a register-entry item. That is a **role**, not an item type, and the
    two are separate QIDs:
    - The register entry is **Q135098921** 服部麻刀方神社 二座 — no coordinates, no website, no
      sitelink, `P2670` two seats, and `P460` out to its three 論社 candidates ranked `P1352` 1/2/3.
    - **Q135186223 is candidate 1**, and carries what only a physical place carries: `P625`
      coordinates, `P856` the jingukaikan 125-shrine page, `P131` two municipalities, a
      `shinto:` wiki page. Its siblings are equally physical — Q135186224 a co-enshrinement,
      Q135186227 a former site. The reading belongs on it.
    - The `P1814` it already held is a **qualifier** on `P1448` (ハトリノマトカタ, `P1264` = Heian
      period) — the ancient reading of the historical name. Top-level `P1814` was and is empty, so
      this is an add, not a contest with the kana-qualifier cleanup.
    - Its reference URL resolves: `神服織機殿神社` is a **redirect** to `機殿神社`, the article the
      lead was read from.
  - ⚠️ **The collector could stage a DUPLICATE, and did have one live case — fixed 2026-08-20.**
    `already_handled()` fixed this from the BUILDER's end on 2026-08-04. The collector had no such
    guard at all and appends to `name_in_kana.txt` unconditionally, so the same hazard survived from
    the other end: a line staged BY HAND leaves the work-file sitting in `name_in_kana/`, and
    whoever fills its ANSWER marker next gets a second identical `P1814` statement.
    - The live case was **Q11544511** (機殿神社), hand-staged 2026-08-19, work-file never retired —
      so "the pipeline now has **zero** unanswered work-files" was not true; it had one, sitting with
      an empty marker, which is precisely why nothing noticed.
    - `already_staged()` in `collect_name_in_kana.py`, checked **before the answer is parsed** —
      an answer-first order counts these pending forever and never retires them. Keyed on the staged
      file only, since the question is narrowly "does a statement already exist to be duplicated".
    - Run: `pending=0 resolved=1 qs-lines=0 already-staged=1`; work-file retired to `_resolved.log`
      as `ALREADY_STAGED`, `name_in_kana.txt` **unchanged at 352 lines**. 5 tests, and most pin what
      it must NOT match — a QID as a statement *value*, a `Q1234560`/`Q123456` prefix, a `-Qxxx`
      removal line.
  **Anchor the lead match at position 0**: 機殿神社 is a substring of the first name in its own
  lead, so an unanchored search silently hands the pair-item the wrong shrine's reading
  (田上大水神社/大水神社 and 河原神社/川原神社 are the same shape).
- ⚠️ **The builders re-queued finished work, and both are fixed.** Skipping only on work-file
  existence is wrong: the collector DELETES the file when it answers, and the SPARQL/category target
  set cannot see the staged line either, because the freeze holds delivery until 2026-08-10. So a
  rebuild re-created 12 name-in-kana files (and, earlier, 14 Beppyo ones) for work already done —
  answering them would have written a second identical statement each. Both builders now consult the
  staged `.txt` + `_resolved.log` via `already_handled()`. **Until the freeze lifts, local staging is
  the only record of what has been done; do not trust the target query to know.**
  **The cloud routine is one path, not the only one** — these can be extracted locally in batches
  exactly like bucket (b), and waiting on the routine is not a blocker. It addresses only a handful
  of items per run across all 2,252 queue entries, so local batches are the faster road. Rebuild more
  work-files with `--limit N` once the current 177 are drained.
- ✅ **The Engishiki collision does not exist** (checked in the cleanup's own code, not assumed):
  `generate_kana_qualifier_add.py` guards both branches with `is_katakana()`, `_remove.py` emits
  value-matched removals, and this builder only queues items that already have no top-level P1814.
  The 601 are queued normally; `--hold-engishiki` restores the old blanket hold.
- ⛔ **4 ブルーノ・プラス husks are hard-excluded** (`REPURPOSED` in the builder): Q123044569,
  Q134886554, Q134736575, Q140476265. They reach the target set legitimately — the repurposing
  stripped their P1814 — and writing to one would be editing the husk. A5 says document, don't touch.
- ✅ **RULED 2026-08-05 (Emma): allow the mixed-script readings. Done, and the 8 lost ones are
  recovered.** The hiragana-only gate was rejecting readings that are legitimately part-katakana
  because the name carries a foreign place-name or loanword — and it was **8**, not 7
  (ハワイいづもたいしゃ and アメリカつばきおおかみやしろ were also sitting in the log).
  - **Emma's argument is the load-bearing part, and it checks out in the cleanup's own code:**
    *"The thing that removes the katakana readings, I'm pretty sure it uses a qualifier too. If that
    qualifier is not present, then it shouldn't be running on it."* Correct —
    `generate_kana_qualifier_remove.py` only ever touches items carrying an **ojp-hani P1448** with
    a confirmed カミノヤシロ qualifier, and its removals are **value-matched**. An overseas shrine
    has no ojp-hani P1448 at all, so the cleanup could never reach it. The collision this gate was
    built to prevent was never possible for these items; the blanket rejection was pure over-gating.
  - **The shape separates the two cleanly**, so the new rule needs no judgement: a shrine name ends
    in 神社/神宮/宮, which read as hiragana, so a legitimate case is always MIXED — while the
    ancient-reading error values are ALL katakana (アスキ-, ツキタノ-, カミノヤシロ).
    `acceptable_reading()` = all kana **and** at least one hiragana. All-katakana is still refused.
  - `restage_katakana_readings.py` recovered all 8 from `_resolved.log` (their work-files were long
    deleted), fetching each jawiki sitelink so a restaged line carries the same S143/S4656
    provenance a normally-collected one would. `name_in_kana.txt` 343 → **351**. Idempotent — the
    re-run is a clean no-op. 14 + 7 tests.

**Original brief follows.**

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

## A1. ▶ Cloud-answer collectors — the routine is ALIVE but delivers ~5 items/day

**Corrected 2026-08-05: "answered NOTHING since 2026-07-28" was stale.** The routine fired again
today (`988c2e5c`, 5 items) and all five collectors were re-run: 2 were collectable —
`Category:奥六郡 → Category:Okurokugōri` (good), and a description for Q135289475 which
**turned out to be destructive and has since been withdrawn** (see the overwrite guard below).
The other three returned `resolved=0`.
**The conclusion the old wording reached is still right, for a different reason:** ~5 items/day
against 2,252 queue entries is ~15 months. Local batches remain the road; the routine is a trickle,
not a stall.
- ✅ **A prompt bug found while checking that answer, and it contradicted itself.** The TASK text
  said descriptions take a "lowercase start" while its own worked example read "**S**hinto shrine
  in Maebashi…". Settled by measuring the corpus rather than picking a rule: of 14,300 en
  descriptions on shrine items, **11,487 begin "Shinto" against 1 beginning "shinto"**. The
  routine's capitalized answer was correct and the instruction was wrong — following it literally
  would have produced the 1-in-11,488 form. Fixed in `build_description_enrichment_queue.py`,
  `remote_queue.py`, and rewritten in all 221 pending work-files (TASK comment only; each file's
  ANSWERS block was asserted byte-identical before the write).
- ✅ `collect_label_typo_answers.py` — **128 of the 143 answered locally 2026-08-04**; 71 became
  `Len` lines in `label_typo_fixes.txt` (79 total). **15 left**, all of them items with no jawiki
  article (below). Answers + reasoning in `shinto_miraheze/local_answers/label_typo_2026-08-04*.tsv`.
- 📐 **STANDING RULE, Emma 2026-08-04: MACRONS.** A long vowel is written Ōmi, Kōnomine — not
  Oomi/Omi. **The macron rule and the morpheme rule are the same rule seen twice:** a macron marks
  one long vowel, so two identical vowels meeting across a morpheme boundary are not it. 飯玉
  いいたま is Iitama; 男乃宇刀 お・の・う・と is Onouto; but 神峯 こうのみね is Kōnomine.
  It does NOT rename places that have an established English form — Kobe stays Kobe, the same way
  ちりふ stays Chiryū. ⚠️ **The queue's own `KANA_ROMANIZED` column does not know the morpheme
  rule** — it collapses every o+u, reporting Kotoura as "Kotora" and Horinouchi as "Horinochi",
  and then flags the correct label as divergent. 13 items were "wrong" only in that column.
  - **The dominant defect is one machine error, not 143 separate ones.** A romanizer collapsed a
    doubled vowel into a macron *across a morpheme boundary*: 飯玉 いいたま → "ītama", 飯塚 →
    "īzuka", 幣石 へいいし → "Heīshi", 二荒 ふたあら → "Futāra", 堀出 ほりいで → "Horīde". 飯 is
    い plus the next morpheme's い, not a long vowel. **Eleven also came out lowercase-initial**
    ("ītama Shrine"), which is wrong under any policy.
  - ✅ **It is NOT the live romanizer — checked, not assumed.** `kana_english.label_for` was run
    against the whole defect class and returns exactly the corrected forms (Iitama, Iizuka,
    Heiishi, Futaara, Horiide). The bad labels came from an earlier pass, so the pipeline is not
    still emitting them and nothing needs fixing there.
  - ✅ **The reading clashes were researched per-item, and they did NOT all fall the same way** —
    which is the case against ever having applied a blanket rule to them. `fetch_label_typo_
    evidence.py` pulls each shrine's own jawiki lead via its item's sitelink (never by guessing a
    title — 八幡神社 names hundreds). Three outcomes: the lead backs the KANA and the label is
    wrong (孕 はらうみ, 潮江 うしおえ, 鹽竈 しおがま); the lead backs the LABEL and the **P1814** is
    wrong (那古野 なごや not なごの, 鵜鳥 うのとり not うねどり, 四本木 よもとぎ not しほんぎ,
    波々伯部 ほほかべ not ほうかべ) — **4 items where "trust the kana" would have damaged a correct
    label**; or the lead gives BOTH readings and the label uses one, so nothing was wrong at all
    (敬満 けいまん/きょうまん, 洲崎 すさき/すのさき, 貴布禰 きふね/きぶね, 志賀理和気, 大祁於賀美).
  - ✅ **Descriptive labels left alone** per Emma 2026-08-04 (合氣神社 "Iwama Dōjō", 海底神社
    "Underwater Shrine", 釜石製鐡所山神社, 合祀：大津神社) — logged so they stop being re-queued.
  - ✅ **The last 15 are CLOSED 2026-08-05 — and they were never defects.** Emma asked the right
    question instead of picking a reading: *"it would probably be worth even investigating where
    the Kana readings come from… Did I accidentally add them with a bad script a year ago? Do they
    have sources?"* They have sources. **10 of the 15 carry a P854 reference to
    `houjin-bangou.nta.go.jp`** — the National Tax Agency's 法人番号 corporate register, which lists
    宗教法人 with their *registered* furigana. Not a bad script; an authoritative source.
  - **So the "clash" was two correct values being compared to each other.** The EN label is the
    conventional English name (Hachiman Shrine, Futarasan, Isonokami, Akiba, Ishii) and the P1814 is
    the shrine's registered legal reading (やはた, ふたあらやま, いしがみ, あきは, いわい). Emma:
    *"That is Hachiman. That is Hachiman as the reading."* Nothing to fix on either side — which is
    also why no QuickStatement could ever have recorded the outcome.
  - All 15 retired to `label_typo_review/_resolved.log` as `NOT_A_DEFECT`. **`pending=0`; the queue
    is fully drained.**
  - ⚠️ **The builder would have resurrected every one of them** — `build_label_typo_review_queue.py`
    skipped only on work-file existence, the third builder caught by that rule, and the collector
    deletes the file when it answers. Worse here than elsewhere: a "nothing is wrong" decision
    produces NO QS line, so a staged-file-only guard misses it too. `already_handled()` now reads
    **both** `_resolved.log` and `label_typo_fixes.txt`. Verified by re-running the builder: 0 new
    files. 6 tests.
  - Its module-scope `sys.stdout` rebinding was moved into `main()` (same fix as
    `generate_soja_only.py`) — importing it was replacing the caller's stdout.
  - ✅ **The fix is not English-only — 153 fr/id/de/tr labels too.** Emma 2026-08-04: *"replacing
    all of the wrong names … not just the english one. It's wrong in French and Indonesian too."*
    The non-English labels were built FROM the English ones, so every bad reading was copied
    outward — 寒川神社 carried "sanctuaire de Samugawa" and "Kuil Samugawa" beside the en label.
    **75 of the 79 corrected items had a foreign twin.** `generate_multilingual_label_fixes.py` →
    `multilingual_label_fixes.txt`, registered in `ATOMIC_FILES`, wired into
    `generate-quickstatements.yml` after the label step, 15 tests.
    - It rewrites only the NAME inside each foreign label, keeping that language's own phrasing,
      and it skips any label that does not carry the old name (a translated one has nothing wrong).
    - ⚠️ **French elision is the part that bites.** Four real bugs in the first run: Ō was not in
      the vowel set so `d’Oominakami` became `de Ōminakami`; Y was in it so `de Yagiri` became
      `d’Yakiri`; the article was rewritten whenever anything changed rather than only when the
      name's vowel class flips; and a generic suffix punctuated differently either side
      (`Okagagū` vs `Okada-gū`) dropped the gū entirely. All four have tests.
  - ✅ **"hikida" was NOT garbage — it is signal, exactly as `CLAUDE.md` warns.** The item's own ja
    aliases include **疋田神社**, read ひきだ, so Hikida is a genuine alternative name for
    調田坐一事尼古神社; it was only ever wrong as the *primary* label. Emma: *"Hikida capitalized
    should be an alias and the one in the different languages should be like that."* Added as an
    alias in en/fr/id. **This is a hand-kept list, not a rule** — aliasing every replaced label
    would preserve the misreadings too (Samugawa for 寒川 is simply wrong).
  - ✅ **`sequential_misc.txt` finally has the pair it was built for.** The same item's P1814 is
    also a wrong name: くだにますひとことねこ is the jawiki reading minus its first character. Correct
    value ADDED + truncated one REMOVED, on the same property — which the random atomic drip cannot
    do safely, since the removal could fire first and leave the shrine with no reading. The Open
    questions note said the mechanism was built but *"population is the open bit"*; this is the
    first genuine remove-then-add pair to turn up. Its other P1814, ツキタノ-, is left alone — that
    is the kana-qualifier cleanup's territory and two passes on one property is how values get lost.
  - ✅ **French elision is now a RULE with its own generator, not a queue.** Emma 2026-08-04:
    *"de Ō should be corrected to d'Ō across them with an additional pipeline thing that makes the
    quickstatements instantly if it is something that was universal."*
    `generate_french_elision_fixes.py` → `french_elision_fixes.txt`, registered, in CI, 12 tests.
    **Measured before writing anything** (23,892 fr-labelled shrine items):

    | pattern | count |
    |---|---|
    | `de` + true vowel (incl. Ō Ū) | **0** |
    | `d’` + true vowel | 4,675 |
    | `d’` + consonant | 0 |
    | `de` + H | **25** |
    | `d’` + H | 3,645 |

    So **the "de Ō" case does not exist in the corpus** — real vowels are already 100% elided, and
    there are no reverse errors. The only live class is **H**, where the corpus itself has ruled
    3,645 to 25: "sanctuaire d’Hachiman" and "sanctuaire de Hachiman" both exist for the same name.
    Those 25 (21 of them 白山神社) are what is staged. The generator stays general, so the first
    "de Ōmi…" a future label pass introduces is caught on the next fire.
    - ⚠️ **The measurement is the point, not decoration.** Elision before a true vowel is
      obligatory French and needs no judgement — but H is exactly where French grammar does *not*
      decide (mute h elides, aspirated h does not, and Japanese h- is neither by definition).
      Applying strict grammar would have "corrected" 3,645 correct labels into wrong ones.
    - ⚠️ **A broken query and a clean corpus look identical.** The first version asked for
      `wd:QQ845945` (the template had `wd:Q%s` and the constant already carried its Q). WDQS
      returns zero rows for a nonexistent entity with no error — it reported the corpus clean. A
      test now pins the query shape. **Do not trust a generator's silence.**
  - 🛑 **RULED 2026-08-05: leave 兵庫縣神戸護國神社 alone, and treat this as a warning.** Emma:
    *"I'm not expecting the pipeline to even be changing this one… It is definitely a bit worrying
    to me that you seem keen on changing the name of a shrine that should be established in the
    data at this point."* No label change, and **no corpus-wide place-name macron pass** — an
    established shrine label is not a romanization exercise. She did say macrons belong in
    established-name forms generally, but not at the cost of rewriting settled shrine names, so
    nothing is generated from this. **Do not re-open it as a "consistency" cleanup.**
- 🛑 **DESCRIPTION ENRICHMENT WAS DESTROYING DATA — caught 2026-08-05, nothing delivered.**
  `Den` **overwrites**; it does not add. **15 of the 22 staged lines would have replaced a
  hand-written Engishiki annotation with location boilerplate:**

  | existing (Emma's) | staged replacement |
  |---|---|
  | `The 1111th Shrine of the Engishiki Jinmyōchō (Ronsha)` | `Shinto shrine in Kōfu, Yamanashi Prefecture, Japan` |
  | `Ronsha 3 of Yaahino Shrine` | `Shinto shrine in Azai district, Ōmi Province, Japan` |
  | `A candidate shrine for Nakagawa Shrine` | `Shinto shrine in Japan, candidate for Nakagawa Shrine` |

  The left column records the shrine's position in the 927 register, **which** disputed entry it
  is a candidate for, and **which numbered** Ronsha it is. The right column records where it is.
  Nothing recovers the former from the latter. Only the Wikidata freeze stopped it going out.
  - **This is the exact failure `CLAUDE.md` names** — an unfamiliar pattern in this data is signal,
    not corruption — and the queue walked into it because the builder *displayed* each existing
    description as context and then asked for a replacement anyway.
  - **The 15 lines are stripped**; the 7 that target items with no description are kept.
  - **Two independent gates, because they fail differently.** `needs_a_description()` in the
    builder stops the ask being made; `protected_members()` in the collector stops an answer
    already sitting in a work-file from being emitted, reading the recorded description out of the
    work-file so it needs no network. 9 tests.
  - 🛑 **SCOPE CORRECTED by Emma 2026-08-05:** *"We were never supposed to enrich English
    descriptions that aren't equal to Shinto shrine in Japan."* My first gate allowed any
    `Shinto shrine in X`, treating a prefecture-level description as a placeholder worth
    improving. Wrong — naming the prefecture IS the information, and this pipeline does not get
    to overrule it. **That version put 11,369 items in reach.**
  - **Measured, and it decides what the rule means in practice: ZERO of the 14,300 English
    descriptions on shrine items are exactly "Shinto shrine in Japan"** (11,369 are some other
    `Shinto shrine in X`, 2,931 something else). So the exact-match arm is dead in the current
    corpus and the rule reduces to: **this pipeline may only give a description to an item that
    has none.** The arm stays because it is what the wording licenses; a test pins that a
    near-miss like `Shinto shrine in Japan, Kansai` does not match it.
  - **The queue was 67% work that must not be done: 221 → 73 work-files.** 216 protected members
    across the two passes; 148 files deleted outright (every member protected), 24 had the ask
    removed while keeping the member as context, since a new description still has to differ.
  - ⚠️ **"The 73 that remain are the real queue" is WRONG for 51 of them — measured 2026-08-21.**
    They are 73 files holding **63** unanswered QIDs, and the premise printed in every work-file
    is *"every member of this group shares the same label and would get the same standardized
    description — they need UNIQUE, informative ENGLISH descriptions."*

    | group size | files | |
    |---|---|---|
    | **1** | **51** | **no other member. Nothing shares the label, nothing needs distinguishing — the stated reason for the work does not apply** |
    | 2 | 9 | a real collision |
    | 3 | 3 | a real collision |

    So **12 files** carry the disambiguation work this pipeline was built for. The other 51 are
    ordinary items that merely lack an English description, presented under a justification that
    is not true of them.
  - **The groups are keyed on the INDONESIAN label, which is why they look arbitrary.** Emma,
    2026-08-21, on Q135503340: *"idk what this is and where it came from… I lean towards it being
    a shrine that exists but has no context and is someone else's problem."* She is right, and the
    grouping is why it reached her: Q135413481 (神殿, the imperial palace sanctuary) and Q135503340
    (神殿神社, a shrine) both romanise to `Kuil Shinden`, so the generator called them a collision.
    They are not the same kind of thing. Same shape for Q135195021 — her words, *"is just a ronsha?
    like looks really normal"* — whose single-member group collides only with a *proposed*
    Indonesian description for a different Oyama Shrine in Ishikawa. The famous 雄山神社
    (Q11659204) is not in the batch at all.
  - **Only 2 of the 63 have nothing distinguishing whatsoever** (no location, coordinates, deity,
    sitelink or list): Q97013988 and Q135503340. The other 61 carry real register context — 58 in a
    Jinmyōchō list, 60 with an ancient P131, 34 with coordinates. One bad member does not condemn
    the set.
  - **Q135503340's provenance, since it was asked:** Emma created it herself 2025-07-30, *"Created
    item for red-link present on 阿沼美神社, Anumi Shrine"*. One claim, `P31 = Q845945`. Nothing to
    describe beyond "Shinto shrine", which is the generic string the pipeline is not allowed to write.
  - **Evidence + review page, both committed:** `shinto_miraheze/fetch_description_evidence.py`
    (read-only, `wbgetentities` in batches of 50 — two requests for 63 items, not a SPARQL sweep) →
    `description_enrichment_en/_evidence.json`; `site/generate_description_review.py` →
    `_site/description-review.html`, one card per item with what/where/siblings and both candidate
    description strings.
  - ❓ **The shape question is OPEN and is Emma's** — asked 2026-08-21, she is reading the items.
    The pipeline's own worked example is `Shinto shrine in Maebashi, Gunma Prefecture, Japan`, a
    MODERN municipality, and these items' `P131` is ancient (Ōmi Province, Azai district), so that
    example cannot be produced from their data. Their already-described siblings use the register
    position — `Ronsha 2 of Itateno Shrine`, `The 1115th Shrine of the Engishiki Jinmyōchō (Ronsha)`
    — 11 of 13.
  - ⚠️ **CORRECTED 2026-08-21, and Emma caught it.** I wrote that none of the 63 carries the
    ranking the register form is built from, and named `P1352`. Both halves were wrong. Her
    question was simply *"what do you mean no standard number?"*
    - The number is the **`P958` qualifier on `P13677`** (the Kokugakuin section), not `P1352`.
      Q135186223's description *"(Ronsha 1)"* is built from `P958: "1"`.
    - **56 of 63 do carry `P958`** — so "none of them" was false. But **52 of those are `n/a`**,
      and only **4** hold a real number (two `1`, two `2`). So the *conclusion* stood by accident:
      `Ronsha N of X` is derivable for 4 items, not 0 and not 56. This is the same fact B10 already
      recorded — `n/a` and `0` distinguish nothing.
    - **The genuinely useful part I had missed: 58 of 63 carry `P1545`**, the ordinal in the
      Jinmyōchō list (Q135194637 is #52). That is what the sibling form *"The 1115th Shrine of the
      Engishiki Jinmyōchō (Ronsha)"* is built from — so **that** register description IS derivable
      for 58 of 63.
  - **Emma's read of the batch, 2026-08-21, after opening the items:** *"is just a random ronsha and
    nothing is wrong with it"* · *"Are we just discussing indonesian descriptions? Nothing serious?"*
    Correct on both. Nothing here is a defect; it is cosmetic metadata work on ordinary register
    items, surfaced under an Indonesian-label collision that is not real for 51 of them.
    **Not to be re-raised at her.** Whoever picks this up decides between the P1545 register form
    (58 derivable) and leaving them undescribed, and does it without another round of questions.
- ✅ **The same question asked of the LABEL pipelines 2026-08-05 — and the answer is clean.**
  `L<lang>` SETS a label exactly the way `Den` sets a description, so the ~12,150 staged label
  lines were audited rather than reasoned about. **No label pipeline overwrites hand-written
  content.**
  - A 240-line stratified sample across the six bulk generators (`temple_identical_name_en_labels`,
    `identical_name_en_labels`, `kana_en_labels`, `temple_en_labels`, `en_labels_sonnet`,
    `en_labels`): **239 ADD, 1 NO-OP, 0 OVERWRITE** — they target items with no label in that
    language. Zero overwrites in 240 bounds the rate at roughly 1.2% at 95%; it is evidence, not
    proof, and the audit script re-runs on demand.
  - Every overwrite in the corpus comes from a file whose *purpose* is correction, and each was
    already evidenced: `label_typo_fixes` (79, researched per item), `french_elision_fixes` (25,
    the measured 3,645-to-25 corpus ruling), `multilingual_label_fixes` (Ootsu→Ōtsu, ītama→Iitama
    — Emma's macron ruling propagated outward).
  - ⚠️ **Two that look contradictory and are both right** — which is why this was audited instead
    of reasoned about from filenames. `category_label_fixes` ADDS a `Category:` prefix to 42 items;
    `miscellaneous_edits` REMOVES one from Q138565446. The 42 are genuine `P31=Q4167836` Wikimedia
    categories whose **ja labels already carry the prefix** and whose sitelinks are jawiki
    `Category:` pages. Q138565446 is a **shrine** — jawiki sitelink `神明宮 (横浜市神奈川区)`, a
    mainspace article — that picked the prefix up from its *Commons* category sitelink.
  - `modern-quickstatements/audit_label_overwrites.py` is the durable artifact — run it before a
    drip resumes or when a new label generator is added. It cannot be a CI test (needs live
    Wikidata); 12 tests cover its parsing and classification, including that a `-Qxxx` REMOVAL is
    never read as an add.
  - ▶ **One real oddity, unfixed and minor:** Q125302213's *English* label is `6世紀日本の政治家`,
    Japanese text. The staged fix prefixes it to `Category:6世紀日本の政治家` — correct as far as it
    goes, but it stays untranslated. Not damage; the label was already Japanese.
- **All five collectors drained 2026-08-23** — the "0 answered" line above was three weeks stale.
  `docs/description_enrichment_pipeline.md`. Counts after the run:
  name-in-kana **0** · beppyo-P612 **0** · description-enrichment **69** · ronsha-ranking **32** ·
  category-translation **338**. Collected: **4** descriptions, **1** ronsha ranking, **15** category
  translations. Nothing delivered — the Wikidata lockout holds to 2026-09-18; this is staging only.
  - The four descriptions were live-checked against `wbgetentities` before applying, not trusted
    from the work-file snapshot: all four had **no en description**, so the pipeline's one licensed
    action (describe an item that has none) genuinely applied. A collected description was withdrawn
    as destructive once before; the snapshot in a work-file is not evidence about the item today.
  - ⚠️ **Ronsha ranking is NOT mechanical** — each work-file asks which of several candidates is
    the likeliest true Engishiki shrine, needing per-candidate jawiki/Kokugakuin research. Do not
    batch-answer it the way name-in-kana was batched.
  - **Q135040248 stays undecidable, and its stated blocker is a dead end** — the routine said it
    needed "Wikidata access to check P131". Checked: P131 is **identical** across all three
    candidates and the Engishiki item (Q1047144 + Q7402764), as are P31 and P17; none has
    coordinates or a jawiki sitelink, so the usual research path does not exist for them. Do not
    retry the P131 route. Reasoning in `ronsha_ranking_review/_undecidable.log`.
- ▶ **Do these locally, in batches, the way name-in-kana was done** (A0): dump each queue's
  work-files, answer them here, `apply_local_answers.py --queue <q> --answers <tsv> --apply`, then
  the collector. All repo-local — no Miraheze request — so it runs through the blackout.
  - ✅ **That road was BLOCKED for the two biggest queues until 2026-08-23, and silently.**
    `apply_local_answers.py` offered six `--queue` choices while implementing one shape (key = QID,
    file = `<key>.wiki`, marker = `ANSWER:`). `category_translation` is keyed by category TITLE with
    a `TRANSLATED:` marker — every row was dropped by a `^Q\d+$` filter that ran *before* any
    counter, so a real batch printed four zeros, the same output as a correct run on an empty batch.
    `description_enrichment` uses an `ANSWERS:` **block** (`ANSWER:` does not match `ANSWERS:`) and
    its files are named after the group's FIRST member while the answerable members are the others
    inside the block. Fixed per-queue; 15 tests; end-to-end round-trip verified on a real file
    (apply → collector reports Finished → reverted). Its module-scope `sys.stdout` rebinding also
    moved into `main()` — third instance of that bug here.
  - ▶ **Next rung, and it needs ONE decision made once, not per item:** the enwiki category-naming
    convention to translate into. Worked example: `Category:いなべの Municipal History` is a damaged
    `いなべ市の歴史` (jawiki `Q18716435`, real) — the `市の歴史` → ` Municipal History` replacement
    that CLAUDE.md's "signal, not corruption" rule describes. Q18716435 has **no enwiki sitelink and
    no en label**, so there is nothing canonical to copy and the convention has to be chosen:
    `Category:History of Inabe` vs `Category:History of Inabe, Mie` (enwiki disambiguates city
    categories where the article does). Settle it once, then batch. Do not answer them one at a time
    with different conventions.
- ▶ **Separately, find out why the routine is so slow.** ~5 items/day is a trickle, not a stall.
  `docs/remote_queue_routine_prompt.md`; the last known fix was the missing repo binding
  (`session_context.sources`).

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
  - ✅ **Aichi is DONE and the "not yet covered" line here was stale** — 3,179 rows are already
    in `crawled_shrines.csv`, harvested by `harvest_aichi` in a single POST to the site's search
    API. Only Osaka is still uncovered.
  - ✅ **Mie + Kagoshima harvested via their sitemaps (2026-08-03).** They were filed as
    "name-slug paths, not enumerable"; both are WordPress and both publish a sitemap that
    robots.txt points at and permits. Mie's shrine post type is one file (**822** URLs);
    Kagoshima's shrines are ordinary posts across 92 monthly sitemaps, filtered by
    `/shrine-search/`. Run: `python crawl_jinjacho_shrines.py --index mie|kagoshima
    --max-pages N` — capped, resumable by URL (not cursor), URL list cached in
    `index_urls.json`. Re-run `match_jinjacho_shrines.py` + `generate_jinjacho_p973.py` after
    each chunk, same as the id families.
  - ⏳ **Osaka is the last one** — `www.osaka-jinjacho.jp` is static HTML
    (`funai_jinja/dai1shibu/nose-cho/01020kusasajinja.html`), no robots.txt and no sitemap, so
    it needs its section index pages walked rather than a sitemap read. Not started.
  - Add-only; the daily editor skips statements that already exist, so re-runs are no-ops.
  - ⚠️ **Mie's low yield is NOT the parser — corrected 2026-08-03 after measuring.** The parser fix
    below was real and lifted the total 1,151 → **1,441**, but almost all of that went to Kagoshima
    (129 → 283) and Osaka (97 → 213). **Mie went 17 → 16.** The actual cause: of its 300 rows, 202
    match a shrine name, but **171 of those match only same-named shrines in other prefectures**
    (三宅神社 → 亀岡市, 一色神社 → 掛川市, 三宮神社 → 神戸). Mie's own shrines mostly have no
    Wikidata item, so the earlier "thin data" guess was right and the parser diagnosis was wrong
    for this prefecture. Nothing to fix here — the gate is correctly refusing to attach Mie URLs to
    Kyoto and Shizuoka shrines. Crawling Mie's remaining 522 pages will add little; deprioritise it.
  - ▶ **Separate, real defect found while measuring: candidate items with NO P131.** 180 of the
    2,832 candidate items for Mie names (6%) have no P131 ancestor ending in 市/区/町/村 — e.g.
    Q135039445, Q135186750. These can never pass the municipality gate no matter how good the
    address parsing is, because there is nothing on the item to compare against. Worth measuring
    across all prefectures and deciding: either accept a prefecture-level match for items with no
    P131 at all (weaker gate, only for that subset), or leave them and treat it as a P131 backfill
    task. Do not weaken the gate for items that DO have P131.
  - ✅ **Municipality parser fixed 2026-08-03** — three bugs, all failing CLOSED (row dropped,
    never mismatched):
    the prefecture-stripper was `^.{2,4}?[都道府県]`, unanchored, so any address through a 国府町 /
    道明寺 lost its city; the 郡-stripper was `^.{1,5}?郡`, so 霧島市国分郡田 lost its city; and the
    token rule stops at the first mark, truncating 四日市市 → 四日市. Fixed with the real 47-name
    prefecture list, a lookahead requiring a 町/村 after 郡, and an explicit override list for the
    ~10 municipalities whose names contain a mark. 51 rows corrected. See the counter-example tests
    before touching this: 近江八幡市 + 市井町 is the same string shape as 四日市市 + 三滝町, so no
    general rule separates them.
  - ▶ **Better idea, not built: gate on P131 ancestor LABELS instead of parsing the address.** We
    already fetch every candidate's P131* ancestor ja labels; testing whether any ancestor label
    ending in 市/町/村 occurs in the crawled address removes address parsing entirely. Caveat that
    needs solving first: 区 labels are ambiguous across cities (港区 exists in Tokyo, Osaka and
    Nagoya), so 区 must be excluded or paired with its 市. Do not ship it without that.
  - ✅ **CI was reverting generated files it never generated (fixed 2026-08-04).**
    `generate-quickstatements.yml` backed up `*.txt` wholesale, pulled, then copied the lot back —
    reverting any file another push had updated meanwhile. `jinjacho_p973.txt` lost 205 matched
    pairs this way (1,526 → 1,236 lines against a 1,441-row CSV). Now backs up only
    `git diff --name-only` + untracked. **If a generated file ever looks smaller than its input
    justifies, suspect this shape before suspecting the generator.**
  - ✅ **`generate_soja_only.py` import-safety FIXED 2026-08-04.** It had no `__main__` guard, so
    importing it (to read one constant during the endpoint migration) fired its migration queries and
    rewrote its two output files; it also rebound `sys.stdout` at import and wrote its outputs to
    bare relative paths, so they landed wherever cwd happened to be. Body wrapped in `main()`, stdout
    rebinding moved inside it, outputs now `HERE`-relative. A scan of every `generate_*`/`fetch_*`/
    `resolve_*`/`submit_*`/`select_*` module found this was the ONLY generator missing the guard —
    the other unguarded files are import-only helpers (`kana_english`, `romaji_phonology`,
    `user_agent`, …). `tests/test_no_work_on_import.py` now asserts the guard across all generators.
  - ✅ **SPARQL endpoint migration — FINISHED 2026-08-20. It was 21 files, not 9, and neither
    stated blocker was real.** `modern-quickstatements/` was done 2026-08-04 (15 files); the rest
    went today, each verified with a bounded `LIMIT 1` probe through its own constant read
    **textually** from the source, never by importing. **21 migrated, 21 probed, 0 failures.**
    - **Both halves of the blocker had stopped being true, and one never applied.** `mwclient` **is**
      installed (0.11.0). The Miraheze blackout ended 2026-08-19. And a Wikidata endpoint change
      never depended on the wiki blackout in the first place — the two were unrelated systems joined
      only in the prose.
    - **The count was an undercount from a hand grep of one directory.** 9 in `shinto_miraheze/`
      was right as far as it went; there were **12 more in `shinto-label-generator/`**, which is
      live — its own `label-generator-regenerate.yml` runs five of them on a schedule, each step
      `continue-on-error: true`, so an old-endpoint 503 fails silently and the workflow still goes
      green. That is the worst place for the miscount to have landed.
    - **The migration silently depended on an untested assumption:** `ua_for()` fails CLOSED on an
      unrecognised host, and `query-main.wikidata.org` is a *different host* from
      `query.wikidata.org`. It routes correctly (`.wikidata.org` suffix match) — now pinned by a
      test instead of assumed, since a raise there would have taken down every migrated script.
    - `tests/test_sparql_endpoint_migration.py` makes the hand count impossible to repeat: it walks
      the tree for the retired URL, and a second test asserts the walk actually reaches **both**
      migrated directories, so it cannot pass vacuously. Full CI suite: **1504 passed**.
    - **Verify these textually, never by importing.** 84 modules in this repo rebind `sys.stdout` at
      module scope — that is the documented script-template invariant in `CLAUDE.md`, not a defect,
      and it exists because these are CLI scripts needing UTF-8 output on Windows. Importing one
      replaces the caller's stdout and breaks it. Read the constant out of the source instead. (This
      is distinct from `generate_soja_only.py`, which additionally RAN ITS WORK on import — that was
      a genuine defect and is fixed.)
    **Why the move happened at all** (kept — it is the reason, not a status): the old endpoint
    threw repeated 503/504 during the 2026-08-03 rematch's 17,549-candidate P131 pass.
    `generate_genbu_ids.py` was moved and verified live, which also fixed
    `match_jinjacho_shrines.py` (it imports that module's `_sparql`). The `grep -rln` that tracked
    the remainder now returns only `tests/test_user_agent_segregation.py`, where the old URL is a
    routing assertion rather than a call.

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

## A5. ✅ Husk guard — DONE and self-sweeping; kept because CI keeps re-emitting the lines

- ⛔ **HUSK GUARD (2026-08-04).** Ten staged QuickStatements across five atomic files targeted the
  ブルーノ・プラス-repurposed items — including `Q123044569|Len|"Ōmiwa Shrine"`, which would have put
  an English label on the repurposed identity. They arrived honestly: the husk now IS the 大美和神社 /
  近殿神社 item on Wikidata, so any generator resolving a jawiki article to a QID by sitelink lands on
  one. Nothing went out only because the freeze was still on. Lines stripped; the durable guard is a
  refusal in `direct_daily_edits.item_is_editable()` — the single road to Wikidata — not in each
  generator, because the next generator written would miss it.
  `tests/test_repurposed_husks_never_edited.py` asserts both the gate and that no atomic file stages
  a husk edit. **Expect generators to keep re-emitting these lines on each CI regeneration; the gate
  is what makes that harmless.**
  - ✅ **The re-emission is now swept automatically (2026-08-05).** It happened exactly as predicted:
    CI regeneration `2dfb736f` re-added **6** husk lines (honzon_p825 ×1, saijin_p825 ×3,
    souken_p571 ×2) and turned that test red on `main`. Stripping by hand every regeneration is the
    wrong shape, so `modern-quickstatements/strip_husk_lines.py` now runs as the last step before
    the commit in `generate-quickstatements.yml`. **One chokepoint, not a filter in twenty
    generators** — the same reasoning A5 used to put the refusal in `item_is_editable()`.
  - It imports `REPURPOSED` from `direct_daily_edits` rather than copying it, so the sweep and the
    refusal can never disagree about what a husk is. Deliberately **not** `continue-on-error`: if
    the step cannot run, the lines stay staged and the test stays red, which is the visible failure.
  - 9 tests, and most of them pin what it must **not** delete — a husk QID appearing as a *value*
    (`Q42|P612|<husk>`) is a statement about another item, `Q1234560` must not match husk `Q123456`,
    and a `-Qxxx` removal line's dash is the command rather than part of the QID. An over-eager
    strip would quietly delete real staged work in files too large for anyone to notice.


## A5b. Repurposed-item damage — Emma's THREE per-item rulings, promoted out of the doc

**Corrected 2026-08-19.** The queue carried this as one line saying *"document, don't touch; no
contact"*. That was a flattening of Emma's actual position, and she called it: *"That was not
actually my ruling. That was your bad summary of my ruling... I'm pretty sure I gave individual
rulings on how to deal with every single one of them."* She did — they were in
`docs/bruno_plus_analysis_2026-07.md` §6, which is not where work lives. Promoted here:

Her words: *"we might want to, at some point, a week after they have stopped editing … re-add the
properties to fix that one. We might want to create a new item for the shrine that they
significantly repurposed. However, that one is a bit up for debate."*

1. **菊名神社 → `Q134926804`, ADD-only restoration.** Re-add the five `P825` deities, `P18`, `P856`,
   `P1329`/`P2900`, `P625`. *Sourced, not restored blindly.*
2. **Kamo Shrine (Odawara) — does it need a NEW item?** `Q123044569` no longer represents it.
   **She flagged this as debatable and it is still hers to settle.**
3. **`Q28069431` husk — the orphaned `fr`/`id` labels.** A removal on an item they are active on,
   so it waits on their activity, not on a date.

**Editor status, measured 2026-08-19** (`watch_conflicting_editor.py`, read-only): **still active —
last edit 2026-08-17**. Every venue clean; no noticeboard mention anywhere; talk page untouched since
2026-04-24. That satisfies her §5.1 exit condition (*"regular, going into August, and they don't have
any talk page activity or mentions"* = assimilated, not a threat), and the watcher reports the drip
gate OPEN.

**So the trigger for 1 and 3 is NOT met, and the reason is worth stating precisely:** both were
conditioned on *"a week after they have stopped editing"*, and they have not stopped. An open drip
gate is not the same signal — it says our pipeline is safe to run, not that their edits are finished.
Conflating the two would restore statements onto items someone is still working on.

- **✅ DECIDED by Emma 2026-08-19 — no longer a question.** Her words: *"Look I don't know what's
  going on with the editor we create new otems for the ones lost due to their messing with them."*
  So: **create new items for every shrine whose item was lost to the repurposing.** That settles the
  Kamo Shrine (Odawara) question she had previously flagged debatable, and generalises it to the
  others. Her sequencing, same message: *"This goes at the end of the queue to do any tooling or
  research on because you're doing the bunrei book shit."* → see **A5c**, last.
- **1 and 3** — BLOCKED-ON-EXTERNAL: the watcher showing a stopped editor plus seven clear days.
  Unblock signal is `conflict_watch.state`, not a calendar date. Also under the Wikidata lockout to
  2026-09-18 regardless.

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

## B2–B8. ❓ DECISIONS — fire ONE at a time, in order, once the gate opens

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

**What is actually unanswered** — and it is a data question, not a decision for Emma: why are 149
items tagged as Shikinaisha yet named as a part of no Jinmyōchō list? Anything that claims to answer
it needs evidence that establishes identity — the (P13677 + P958) composite is the only one available
so far, and it currently matches nothing. NEEDS-INVESTIGATION, this repo's job, no gate on it.

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

### B7. Kokugakuin P13677 matcher — examples DELIVERED 2026-08-19, one question left
Emma 2026-07: *"I don't even understand what this actual thing even is"* and *"I genuinely do not
have any idea what shrines this is referring to."* Both were asks for the shrines to be NAMED, not
linked. All 18 are now written out on [[Open questions]] itself.

**The finding that reframes it: five of the 18 are one cluster, not five cases.** 坐韓国伊大弖神社,
嘉羅久利神社, 佐久多神社 (意宇郡) and 韓國伊太弖奉神社, 天若日子神社 (出雲郡) are the Izumo knot.
佐久多神社 is two items for one shrine — Q135040907 holds id 182811, Q135070108 holds none — which is
the 佐久多/嘉羅久利 論社 split jawiki records. The two 野蚊神社 rows are likewise two distinct items
of the same name in one district, which is why the matcher refused to pick.

- [ ] **ASK on the board:** pull the Izumo five out and work them with the Izumo item, leaving 13
  genuinely separate no-anchor/no-match cases? Asked on the page 2026-08-19; awaiting her reply, not
  blocking on it.

### B8. Empty-items — which to restore?
285 emptied items, 217 lost their P31 — restoration candidates, sorted by how much was lost.
https://emmaleonhart.github.io/shintowiki-scripts/empty-items.html
- **ASK:** "Generate restore-QuickStatements for a slice (e.g. the ones that lost their P31), or is
  this a browse-and-you-pick report?" → *generate restores for <slice>* / *browse-only for now*.

## B1b. Duplicated "part of" statements — ANSWERED and RECORDED 2026-08-19; one gated remainder

Emma hedged that it might be resolved. It is not, and the answer to the actual question ("is an
unqualified `part of` always the leftover to strip?") is **no**.

**116 item/list pairs carry more than one `part of` into the same Jinmyōchō list.** Corrected counts
— an earlier pass in this session said 14/48/54, which was off by one in two classes:

| class | count | disposition |
|---|---|---|
| same ordinal repeated | **14** | the real defect |
| distinct ordinals | **47** | **LEGITIMATE, do not touch** — the 坐韓国伊大弖神社 shape |
| one side has no ordinal | **55** | not one thing — see below |

Checking the 55 against the **list side** is what settled it:

| of the 55 | the list says | meaning |
|---|---|---|
| **42** | names the item **nowhere** | removing the blank fixes nothing; it deletes one of two claims the list never confirmed |
| **10** | names it at the ordinal we already carry | **the blank really is a leftover** — safe |
| **2** | does not confirm the ordinalled side | unresolved |
| **1** | names an ordinal the item does not carry | a different repair — an **add**, not a removal |

**A blanket "strip the unqualified ones" would have been wrong for 45 of 55.** That is the same
over-matching error B2 was withdrawn for, caught before it produced a batch this time.

All three classes are committed per-item at `modern-quickstatements/p361_multi_part_of_audit.json`,
which is what makes the 47 legitimate ones durable — they were only in queue prose before, one
careless "cleanup" away from being destroyed.

- **The 14 true duplicates + the 10 confirmed leftovers** — moved to
  `scheduled/scheduled_items.json`, due **2026-09-18**. Which of two identical statements gets
  removed is not expressible in QuickStatements by value, so this is the sequential-misc mechanism's
  job (built, tested, empty). The per-item evidence stays committed at
  `p361_multi_part_of_audit.json`; only the waiting moved.
- **✅ The 42 — DECIDED by Emma 2026-08-19: work them with the orphan set.** They are an item
  asserting a list membership the list does not reciprocate, which is the orphan defect wearing a
  different name. Folded into the Kokugakuin/orphan work rather than kept as a duplicate-statement
  class, so the same shrines are not walked twice.

## B1c. ✅ Wiki-based queue — RESTORED 2026-08-19. Nothing open.

Emma decided *restore it* when asked directly, settling her July *"not 100% sure"*.

**What it actually was, and why the rebuild was small:** the "wiki-based queue" was never a separate
page — it was a **section of [[Open questions]]**, and this session's own 44% trim deleted it earlier
the same day. Every item it held was genuinely settled (the 403, the Q137721156 deity analysis, the
reports-on-the-page request, the page's bloat, un-parking), so deleting the *items* was right.
Deleting the **surface** was not: it removed the place Emma writes wiki-side work.

Restored as an empty section carrying only what it is for and how it round-trips. No second pipeline
was built — it rides the existing `[[Category:Git synced pages]]` sync, which is the hub's standing
rule and which has round-tripped this page several times today.

**The mirror-or-§B question is moot** and is deleted rather than left open: since it is a section of
a page Emma writes in, it mirrors nothing. Copying 942 lines of `queue.md` onto a wiki page was never
what she used it for.

## B1d. Swept and closed on 2026-08-19 — no action, recorded so they are not re-raised

- **Sequential misc** — settled. Emma: *"I can confirm that I'm perfectly fine with this thing"*;
  design question answered *"sequential only"*. Built, 14 tests, ships empty.
- **Province exclusions** — settled as ADD-ONLY, standing rule. *"you should never be removing
  anything from the provinces."* The removal generator was deleted outright.
- **Takano address merge** — Emma: *"I can confirm this is good. (resolved — safe to delete on the
  next pass.)"* Verified gone from Q11673131. **Her explicit permission to prune it from the page.**
- **Reports on the page** — Emma: *"Went great."*
- **Un-parking the parked items** — Emma: *"We will do this when needed."* Not now, by her words.
- **Queue bloat on the wiki** — Emma: *"Not sure about this one."* No disposition; left alone.
- **"Edits being rejected"** — self-closing, as she said: *"this one is kind of tautological because
  in the event that this does get resolved, it's not going to be here anymore."* It is resolved.

## B9. OUT-OF-SCOPE until the category drain is measured too slow — speed-up *("the category thing")*

A POSSIBLE future optimization to make wiki category-page processing faster (skip some ops on ~3k
enwiki-junk cats, or shard the namespace). Only worth doing IF the Japanese-category-translation drain
proves too slow. It isn't a problem now → dormant.

## B10. Individual QuickStatements to CORRECT wrong/missing P958 sections

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

- [ ] **The 57 derivable ones** — NEEDS-INVESTIGATION, one specific question: `generate_p958_qualifiers.py`
  already derives P958 from P1352 and is add-only, so these 57 are exactly what it produces. Find out
  whether it has simply not been re-run since these items appeared, rather than building a second
  generator beside it. If it has been run, find out why it skipped them.
- **The 228 with no ranking** — OUT-OF-SCOPE for automation, permanently: the value only exists on the
  Kokugakuin page. This is a reading job, and 228 pages is a real size — it belongs to Emma or to a
  deliberate reading sprint, not to a work-loop tick.

---

## A5c. Create new items for the shrines lost to the repurposing — LAST, by Emma's sequencing

**Emma's decision, 2026-08-19:** *"we create new otems for the ones lost due to their messing with
them."* This replaces the old "is it debatable?" framing entirely — it is decided, and it covers
every shrine whose item was taken over, not only Kamo.

**Her placement, verbatim:** *"This goes at the end of the queue to do any tooling or research on
because you're doing the bunrei book shit."* So no tooling and no research on this until the bunrei
attempt is finished or dropped.

Known losses, from `docs/bruno_plus_analysis_2026-07.md` §4:

| shrine | old item | what it is now |
|---|---|---|
| Kamo Shrine, Odawara | `Q123044569` | 大美和神社, different coords. No surviving item; none of the eight 加茂神社 items is Odawara |
| Chikadono Shrine, Kumagaya (熊谷市下増田749) | `Q134886554` | 近殿神社 in Kanagawa (Yokosuka). No item holds Chikadono any more |
| 見光寺, Hanno, Saitama | `Q134736575` | re-pointed to a different temple; the item asserts the wrong one |

- [ ] Build the CREATE batch — one new item per lost shrine, from the pre-damage archives
  (`Q134736575.json` was archived pre-damage; check what else was). Creations are a different
  QuickStatements shape from statements and Emma has previously turned creations OFF, so confirm the
  create-mode before generating.
- BLOCKED-ON-EXTERNAL for execution: Wikidata lockout to **2026-09-18**. Building the batch is not
  blocked; only submitting it is.
- **Do NOT touch the repurposed items themselves.** This is creating new items for the lost shrines,
  which is additive and independent of whatever the other editor is doing.

## Pinned tail (keep last)

- [ ] Ensure the five session-local crons are running (this session 2026-08-05: work-loop bd4cf062
  :03, auto-flush 73fd217e :15, status-report c6048135 :42, briefing acf528e2 08:03, debrief
  4c5db204 23:57). SYNC fast-forwards onto origin/main each tick.
- [ ] Run the status-report action once more independently as an end-of-session summary.
