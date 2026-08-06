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

## A00. ✅ The 11 lineage cases — ALL ANSWERED AND APPLIED 2026-08-04

Emma saved the shintowiki 分霊 page to the repo (`lineage/bunrei_page_saved_2026-08-04.html`,
text via `lineage/read_bunrei_page.py`) so the blackout did not have to be waited out. **No
request was made to shinto.miraheze.org.** Its table "Some difficult bunrei to track" answers all
11. They are transcribed to `lineage/bunrei_page_rulings.tsv`, which
`build_p612_quickstatements.py` now applies **before** the article read — they are answers, not
more evidence, so where the page says autochthonous and the article named a source, the page wins.

- ✅ **3 new statements:** 佐嘉神社 → autochthonous (not 松原神社), 劔神社 → autochthonous (not
  the 伊部郷 kami), 坐摩神社 → **Q11453221 宮中** (*"it comes from the palace things in list of
  shikinaisha in the imperial palace"*) — the same target 石上神宮 and 菅生石部神社 already use.
- ✅ **6 confirmed already correct** — 度津神社, 石園座多久虫玉神社, 月讀宮, 風宮, 風日祈宮 are
  *"explicitly unknown"*, matching the staged `Q24238356`; 小俣神社 *"we figured this out from
  deity page"*, matching the staged 豊受大神宮.
- ✅ **瀧原宮 — "make wikidata for 磯宮"**: 磯宮 is now a CREATE block in `ise_jingu_creates.txt`
  (22 blocks). It cannot be one QuickStatement — `LAST` only names the item just created and
  瀧原宮 is an existing item — so `lineage/stage_takihara_p612.py` emits the 瀧原宮 line after the
  batch runs. Run it right after `create_items.py`; it no-ops until then and is idempotent.
- ✅ **忌部神社 is itself the head → `Q135508874` autochthonous.** The page said *"comes from the
  main inbe lineage. Not gosho shrine"*, refusing 五所神社 without naming a replacement. Emma first
  gave Q705547 安房神社, then corrected to **Q11490722** once the direction was raised: the 阿波忌部
  went *from* Awa/Tokushima, where this shrine stands, *to* Chiba — so 安房神社 is the offshoot and
  this is the head. Q11490722 is the row's own subject, and a shrine that heads its lineage has no
  mother house, so it takes the root marker. The 安房神社 line was dropped by `--supersede`;
  nothing had gone out, the freeze held it. (Unrelated and still correct: 安房神社's *own* P612 →
  天太玉命神社 Q11442508, from the article read.)

**The sheet, since it caused confusion (Emma 2026-08-04).** The Google Sheet has TWO tabs and
they are not the same thing. `to_fix` = exactly the rows that produced no statement. `all_444` =
every shrine read, 444 rows — the audit trail, not a worklist. The "11" was 5 PICK TARGET + 6
no-origin; the 6 left `to_fix` when they were staged as `P612 = Q24238356`, which is why it read
26 and not 32. Regenerated after the rulings: **`to_fix` is now 22 rows and every one of them is a
CREATE ITEM** — no judgement calls remain in it. `python lineage/build_sheets.py` rebuilds both.

**423 statements** staged in `modern-quickstatements/beppyo_p612.txt`.
Method: `docs/lineage_full_read_method.md`.

▶ **The whole of A00 now reduces to two runs, in this order, after the freeze lifts 2026-08-10:**
1. `python modern-quickstatements/create_items.py --batch ise_jingu_creates.txt --apply`
2. `python lineage/stage_takihara_p612.py --apply`

### ✅ The 21 Ise items — BUILT 2026-08-04, waiting only on the freeze

Emma: *"just make them … the English name, English language name, the P31 Shinto Shrine
Japanese language name, and a connection."* Done. `modern-quickstatements/ise_jingu_creates.txt`,
21 CREATE blocks, run via `create_items.py --batch ise_jingu_creates.txt --apply`.
Generator `lineage/build_ise_creates.py`; readings `lineage/fetch_ise21_readings.py` (21/21 out
of the parent articles). Gate `ise_jingu_gate.py` = Wikidata freeze (2026-08-10) AND
conflict_gate, fails closed. 11 tests.
- They had no item because each is a jawiki **redirect** into a neighbour's article (2 are
  section redirects) — no article, no sitelink. Not a lookup failure: `build_subject_map.py`
  also asked for an item whose jawiki sitelink is the redirect title, and one whose ja label
  is exactly the name. Both empty for all 21.
- Per block: Lja, Len, `P31=Q845945`, `P361=Q687168` (伊勢神宮 — the connection), `P1814`,
  and the `P612` with `P1013=Q195793`. **No descriptions** (Emma's standing note) and **no
  sitelinks** (legal on a redirect title, but the one field that can steal a link from a
  neighbouring item — left for a deliberate pass).
- Three labels are hand-written in `MANUAL_LABELS`, Emma's call 2026-08-04: 屋乃波比伎神 →
  Yanohahiki-no-kami, 宮比神 → Miyabi-no-kami (both kami names, no shrine suffix to
  romanize; 宮比神 has no shrine building), 瀧原竝宮 → Takiharanarabi-no-miya (reading is
  …のみや not …ぐう; matches its sibling 瀧原宮 = "Takihara-no-miya").
- ▶ **Run it after 2026-08-10.** Needs `MW_BOTNAME`/`BOT_TOKEN`; `create-items.yml` is the
  workflow that has them.

### ✅ create_items.py has no duplicate guard (Emma 2026-08-04)

*"I don't know why this duplicate guard should exist. Just none."* Removed. It searched
ENGLISH labels, which for shrines are generic transliterations — an unrelated 森神社 labelled
"Mori Shrine" would have blocked 毛理神社 — so it refused real work while catching nothing the
generator had not already checked more precisely on the ja label. Whether a batch's contents
already exist is now the generator's question, answered before the lines are written. This
also applies to the `vsa_libraries.txt` batch, which shared the tool.



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
- ⏸ **1 work-file deliberately unanswered:** Q11544511 機殿神社 (joint article for 神服織機殿神社 +
  神麻続機殿神社; its lead opens with those two names and the pair name carries no reading).
  Q7137401 水谷川忠起 is no longer among them — it is excluded at the source now, see above.
  The latest 54 are the whole 神宮125社 slice (A0c's "P1814 pass over the 54" — the real figure was
  55). `lineage/fetch_jingu125_kana.py` → `_jingu125_kana.tsv` → `lineage/stage_jingu125_kana.py
  --apply`. **53 of the 54 already had a work-file waiting for the cloud routine**, which would
  have written a second identical line each; staging locally now retires the work-file and logs it
  to `_resolved.log`, the same disposal the collector performs. Only 機殿神社 (Q11544511) is left —
  it is the joint article for 神服織機殿神社 + 神麻続機殿神社 and has no reading of its own.
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

## A0b. ✅ Mother house (P612) — ALL 444 READ IN FULL 2026-08-04 (345 Beppyo + 99 Ise)

**Done, and the 2026-08-03 keyword pass is superseded.** That pass judged from keyword-extracted
sentences, not full articles, which is why it produced 129 UNCLEAR. Emma called it: *"all 344 need
the same agentic full-read treatment."* Every one of the 444 articles has now been read in full by
an Opus agent and classified TRANSFER / NETWORK / AUTOCHTHONOUS / UNKNOWN —
**327 AUTOCHTHONOUS (74%), 78 TRANSFER, 33 NETWORK, 6 UNKNOWN.** Only six articles give no origin
at all; the lineage really is in the prose and essentially never findable by keyword.

**408 items staged** in `modern-quickstatements/beppyo_p612.txt` (one P612 line each, no subject
with two targets); the daily submitter delivers once the freeze lifts (2026-08-10).
Data: `lineage/agent_results.tsv`. Generator: `lineage/build_p612_quickstatements.py`
(`--supersede` drops an earlier line where the full read disagrees — 21 did, all still un-dripped
because the freeze has been on since before the file existed). Waves are restartable via
`lineage/wave.py`, which plans from what is missing rather than from session context.

Emma's two class rulings, 2026-08-04:
- **NETWORK → emit the inferred network head**, including where the article names only a deity
  (函館八幡宮 "八幡神" → 宇佐神宮, 笠間稲荷 勧請元不詳 → 伏見稲荷大社). `DEITY_HEAD` in the
  generator is the one place a value is not read off the article.
- **A non-shrine source still gets P612** — a palace, a place, a tomb (皇大神宮←笠縫邑,
  白峯神宮←白峯陵, 石上神宮←宮中). The edge is real; recording it beats losing it.
- Gates that stop a bad value: disambiguation-page targets are refused (京都の諏訪神社 resolves to
  the generic 諏訪神社 list), as are self-references (瀧原宮/瀧原竝宮 share one article and one QID).
  14 rows produce nothing and say why in `lineage/_p612_resolution.log`.

- **Membership comes from the jawiki CATEGORY, never Wikidata** (Emma 2026-08-03). One paginated
  `list=categorymembers` call; each QID from `pageprops.wikibase_item` in the same request. The
  builder issues zero SPARQL — see the "DO NOT HAMMER WIKIDATA" rule in `CLAUDE.md`.
- Two findings worth Emma's eye: 石清水八幡宮 → **宇佐神宮** (its own lead says so), and 宇佐神宮 →
  **大分八幡宮**, which its own 託宣集 calls 我本宮 — the head of ~44,000 Hachiman shrines naming a
  parent.
- The 178 autochthonous calls are the ones most likely to need correction; 護国神社 rest on
  三重県護国神社's own "靖国神社とは本社分社の関係にはない".
- ✅ **Suffix generator time-boxed** — `generate_bunrei_quickstatements.py` now stops on
  **2027-02-01** via a date gate (a rule, not a future commit-then-revert). It exits *before* the
  SPARQL and *before* opening the output, because `main()` writes with `"w"` and a post-sunset run
  would otherwise truncate `bunrei.txt` and destroy statements the drip had not yet delivered.
  4 tests, including one that the gate is not wired backwards.
- ✅ **enwiki re-read DONE 2026-08-04 — and it is close to exhausted.** Of the 129 UNCLEAR, only
  **81 have an enwiki article at all**, median 2,115 chars with 30 of them stubs. Scanning those 81
  for mother-house language found 12 candidates, and reading all 12 yielded **3 statements**:
  Q11381863 → 住吉大社 ("It is a branch shrine of Sumiyoshi-taisha"), Q500763 → 吉備津神社 (enwiki
  calls it "the parent shrine", matching 安仁神社's jawiki account), and Q335618 Kumano Hayatama →
  autochthonous (it is one of the three Kumano Sanzan heads). The other 9 were regex false
  positives — clan cadet branches, lists of a shrine's OWN outward branches — or claims that merely
  add a third competing tradition (Yasaka's Nunakuma origin) without settling anything.
  **~2% yield. Do not spend another pass on enwiki for this set.** 126 remain UNCLEAR and they are
  genuinely unsettled in both languages, not under-researched.
- ✅ **CORRECTED 2026-08-04 (Emma): a 勧請 in transit IS a real bunrei.** I had ruled the three
  shrines founded along 行教's 859 Usa→Iwashimizu journey UNCLEAR — 亀山八幡宮 (下関), 琴崎八幡宮,
  甲宗八幡神社. Emma: they are real bunrei. All three now point at 宇佐神宮 (Q715632). Named parents
  go 39 → 42 of 344 (12.2%).
- ▶ **Remaining:** Emma's review of the 327 autochthonous calls.
- **A more organized extraction technique is a job for Topaz, NOT this repo.**

## A0c. 🖥️ 神宮125社 — the Ise Jingū constituent shrines (Emma 2026-08-04)

**Emma's scope ruling:** every 別表神社 is notable enough to be worth high effort, and *"all of
these shrines are that way too"* — <https://ja.wikipedia.org/wiki/Category:神宮125社>.

**Measured 2026-08-04** (direct members only — never recurse a category, see `CLAUDE.md`):
- 99 ns-0 articles besides the list page; **76 have a Wikidata item**, so **23 articles have none**.
- **54 of the 76 lack P1814** — direct work for the A0 name-in-kana pipeline, and the obvious first
  pass. Includes 豊受大神宮, 荒祭宮, 風日祈宮 and 伊勢神宮 itself.
- **0 lack P361 (part of)** — every one is already linked as a constituent of the Jingū.

**✅ P612 question SETTLED 2026-08-04 — Emma: keep all 99.** The worry was that a 摂社/末社/別宮 is
a *constituent* (P361, already on all 76) rather than a branch. It is answered by how the read was
done: the agents were told explicitly that subordination is not lineage, so P612 here carries the
kami's origin and P361 carries membership — different claims, and they coexist. 80 of the 99 came
back AUTOCHTHONOUS (倭姫命 enshrining a local 国津神 in place; a river, well or stone that is itself
the kami), which is a statement no constituency relation can express. The 19 that name a parent
(瀧原宮←磯宮, 豊受大神宮←比沼麻奈為神社, 伊雑宮←皇大神宮) are staged with the rest. See A0b.

✅ **"23 with no item" was 21, and the correction is instructive.** 23 was `99 − 76 articles
carrying a `wikibase_item``. Two of the 23 — 大間国生神社 `Q135098908` and 神服織機殿神社
`Q135186223` — DO have items, found by exact ja label with **no sitelink at all**, so no
sitelink-based lookup can see them. The real figure is 21, and those are the CREATE batch
under A00.

✅ **The P1814 pass is DONE (2026-08-04)** — 54 staged, see A0. Nothing open in A0c.

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
  - ▶ **The 73 that remain are the real queue** — every one an item with no English description.
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
- Ronsha-ranking (34), category-translation (353) — 0 answered.
  `docs/description_enrichment_pipeline.md`.
  - ⚠️ **Ronsha ranking is NOT mechanical** — each work-file asks which of several candidates is
    the likeliest true Engishiki shrine, needing per-candidate jawiki/Kokugakuin research. Do not
    batch-answer it the way name-in-kana was batched.
- ▶ **Do these locally, in batches, the way name-in-kana was done** (A0): dump each queue's
  work-files, answer them here, `apply_local_answers.py --queue <q> --answers <tsv> --apply`, then
  the collector. All repo-local — no Miraheze request — so it runs through the blackout.
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
  - ▶ **SPARQL endpoint migration — 9 left, ALL of them blocked.** `modern-quickstatements/` is
    DONE (15 migrated 2026-08-04, every one verified with a bounded `LIMIT 1` probe through its own
    constant). The 9 remaining all sit in `shinto_miraheze/` and import `mwclient`, which is not
    installed in the dev environment — so they cannot be imported, and a live check is impossible
    until the blackout lifts. They stay on the old endpoint rather than being changed blind.
    - **Verify these textually, never by importing.** 84 modules in this repo rebind `sys.stdout` at
      module scope — that is the documented script-template invariant in `CLAUDE.md`, not a defect,
      and it exists because these are CLI scripts needing UTF-8 output on Windows. Importing one
      replaces the caller's stdout and breaks it. Read the constant out of the source instead. (This
      is distinct from `generate_soja_only.py`, which additionally RAN ITS WORK on import — that was
      a genuine defect and is fixed.)
    mid-migration to `query-main.wikidata.org` (32 scripts already there). The old endpoint
    threw repeated 503/504 during the 2026-08-03 rematch's 17,549-candidate P131 pass;
    `generate_genbu_ids.py` was moved and verified live, which also fixed
    `match_jinjacho_shrines.py` (it imports that module's `_sparql`). The remaining 24 are a
    mechanical one-line change each, but each needs a live run to confirm — do them in
    batches, not as one blind sweep. `grep -rln "https://query\.wikidata\.org/sparql"`.

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

- [ ] Ensure the five session-local crons are running (this session 2026-08-05: work-loop bd4cf062
  :03, auto-flush 73fd217e :15, status-report c6048135 :42, briefing acf528e2 08:03, debrief
  4c5db204 23:57). SYNC fast-forwards onto origin/main each tick.
- [ ] Run the status-report action once more independently as an end-of-session summary.
