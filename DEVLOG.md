# Devlog — shintowiki bot operations

Running log of all significant bot operations and wiki changes. Most recent first.

---

## 2026-05-26

### `grokipedia_link` op + `Template:Wikidata link` grok categorisation
**Files:** `shinto_miraheze/orchestrators/ops/grokipedia_link.py` (new), `shinto_miraheze/orchestrators/mainspace_orchestrator.py`, `shinto_miraheze/configure_wikidata_link_grok_categories.py` (new), `.github/workflows/configure-wikidata-link-grok-categories.yml` (new)

Added a new PRE_HEAVY op to the mainspace orchestrator only (per Emma's
explicit "main space orchestrator (and only the main space orchestrator)"
directive) that cross-links shintowiki pages into
[grokipedia.com](https://grokipedia.com). On each visit:

1. HTTP-probe `https://grokipedia.com/page/<slug>`. Grokopedia is
   case-sensitive (verified: `Tokyo` → 200, `tokyo` → 404;
   `yamato_no_kuni_no_miyatsuko` → 200, `Yamato_no_Kuni_no_Miyatsuko` → 404)
   with no predictable casing convention, so the op tries the shintowiki title
   verbatim AND the all-lowercase form.
2. If any probe returns 200 → set `|grok=<canonical-slug>` as a **named
   parameter** on the page's `{{wikidata link|...}}` template.
3. If every probe returns 404 → set `|grok=` (empty value, parameter
   *present*). An empty-but-present grok param is the positive "we
   checked, nothing on Grokopedia" marker — distinguishable from
   "we haven't checked yet" (which is no grok param at all).
4. Transient errors (5xx, timeout, mixed) → no-op; re-probe next cycle.

The categorisation is **template-driven**, not stamped by the op:
`Template:Wikidata link` carries a conditional `<includeonly>` block that
reads the grok param state and emits one of three tracking categories
on every transcluding page:

* `grok=<slug>` → `[[Category:Pages with Grokipedia links]]`
* `grok=` (empty, present) → `[[Category:Pages without Grokipedia links]]`
* no grok param at all → `[[Category:Pages to be checked for Grokipedia]]`

The third state is the one the op handles implicitly: every mainspace
page with `{{wikidata link}}` but not yet visited by the op auto-falls
into the "to be checked" category — no mass-tag pass needed. As the op
sweeps mainspace, pages migrate into "with" or "without" as it learns
their state. So Special:Categories on those three pages gives the live
classification + remaining workqueue, for free, from MediaWiki
parser-functions. The wiring is installed by the new one-shot script
`configure_wikidata_link_grok_categories.py` (idempotent — markered with
`<!-- BEGIN_GROK_AUTO_CATEGORIES -->` so it can be re-run safely),
triggered via the new `configure-wikidata-link-grok-categories.yml`
workflow (workflow_dispatch only — fires once, never recurring).

Named-param shape (not a positional `lang|title` pair) is load-bearing:
Grokopedia is not a language wiki, and named params survive
`wikidata_lookup`'s Phase 2 sitelinks refresh untouched (verified — it
preserves `named` via `dict(named)` and only mutates `check_date` /
`consistent_qid`). A positional pair would be wiped every 6-month
sitelinks refresh.

Skip-gates run before the HTTP probe: page is a redirect; `grok` named
param already present (any value, including empty); OR there's no
`{{wikidata link}}` template at all (we'd have no place to cache the
result, and re-probing every cycle would hammer grokipedia.com — Emma's
explicit concern: "I think it'll be a bit of a problem if we like
hammer at grokopedia too much"). Per-page cost is 1–2 HTTPS probes on
the first visit and zero on every subsequent visit. Throttled at 0.3 s
per probe.

User-agent has a built-in owner-contact rotation: Mozilla-prefixed with
`owner=Emma Leonhart <emmaleonhart999@gmail.com>` until 2026-06-02, then
auto-switches to `contact@emmaleonhart.com` (the custom-domain address Emma
expects to be live by then). The switchover is unconditional — no flag, no
deploy step — so we don't have to remember to swap it back manually.

Placed in `OPS` immediately AFTER `wikidata_lookup`. Ordering no longer matters
for correctness (named params survive Phase 2), but we still place it after so
`check_date` is always present before we touch the template.

Touches mainspace only (ns=0). Templates, categories, talk pages, etc. are
deliberately out of scope.

---

## 2026-05-23

### Root cleanup & reorganization — decluttered the repo root
**Files:** moved `API.md` `HISTORY.md` `SCRIPTS.md` `SHINTOWIKI_STRUCTURE.md` `SYNCING.md` `VISION.md` `crashed_session_2026-05-20.md` → `docs/`; `generate_pages.py` → `site/generate_pages.py`; `import_commons_wantedfiles_to_fandom.py` `import_template_list_to_fandom.py` `"templates to import to fandom.txt"` → `fandom/`; `EmmaBot.wiki` → `shinto_miraheze/`; `import_to_fandom.py` `test_fandom_login.py` `process_dupl.py` → `archive/`; `wikidata_scripts_archive/` → `archive/wikidata_scripts/`. Deleted `_scratch_classify_round3.py` `err.log` root-orphan `"Main Page.wiki"` `p459_missing_qualifiers.txt` root `reports/`. Edited `site/generate_pages.py` (SITE_DIR → repo-root `_site/`), `fandom/import_template_list_to_fandom.py` (INPUT_FILE → `__file__`-relative), `shinto_miraheze/update_bot_userpage_status.py` (default template path → `__file__`-relative), `.github/workflows/{generate-pages,fandom-cleanup,import-templates-to-fandom}.yml`, `README.md`, `docs/SCRIPTS.md`, `CLAUDE.md`, `todo.md`, `archive/README.md` (new).

Emma flagged that crud had accumulated in the root, obscuring what's actually
live. Cleaned it up per her three calls: reference docs → `docs/`; pure
scratch/stale deleted, reusable retired tools archived; live CI-referenced
scripts moved into purpose-named dirs (`site/`, `fandom/`) with every reference
rewired (workflow invocation paths + internal `__file__`-relative path fixes).
`remote_queue.py` + `remote_queue.json` + `consume_remote_queue.state` stay in
root deliberately — the claude.ai remote routine reads the JSON at repo root and
its prompt can't be edited from here. Root is now down to core docs, the
remote-queue trio, and dotfiles. All file moves used `git mv` (history
preserved). Added a **"Repository layout & organizational discipline"** section
to `CLAUDE.md` mandating stricter file-structure discipline going forward:
defines what the root is reserved for, a where-things-live table, and rules
(new files into the right subdir, co-locate scripts with their data, grep+fix
references on every move, archive don't litter, ask if unsure).

### Kana qualifier work, redone the RIGHT way — as QuickStatements generators
**Files:** `modern-quickstatements/generate_kana_qualifier_add.py` (new), `modern-quickstatements/generate_kana_qualifier_remove.py` (new), `modern-quickstatements/{kana_qualifier_add.txt,kana_redundant_remove.txt}` (new), `modern-quickstatements/{submit_daily_batch,direct_daily_edits}.py`, `.github/workflows/generate-quickstatements.yml`, `CLAUDE.md`

Re-did the カミノヤシロ kana-qualifier work as **QuickStatements generators** (no
direct API, no edit summaries — through the single channel), replacing the
deleted bespoke editors. Two SEPARATE scripts, per Emma's literal add-first /
remove-after-SPARQL-confirms principle:
- `generate_kana_qualifier_add.py` → `kana_qualifier_add.txt` (ADD-only):
  APPEND `<kana>カミノヤシロ` to ojp-hani P1448 names that have a katakana P1814
  qualifier not ending in カミノヤシロ (4,687), and SEED `<top-kana>カミノヤシロ`
  where the official name has no qualifier but the item has a top-level katakana
  P1814 (653). Total 5,340 lines.
- `generate_kana_qualifier_remove.py` → `kana_redundant_remove.txt` (REMOVE-only):
  emits a removal ONLY for statements where SPARQL CONFIRMS the `<base>カミノヤシロ`
  qualifier is already present, removing the redundant raw `<base>` katakana
  (sibling qualifier and/or top-level statement). 0 lines now (correct — nothing
  has the カミノヤシロ qualifier yet); removals appear once adds land. The
  confirmation is in the SPARQL, so a remove can never precede its add.
Both files added to `ATOMIC_FILES` (submit + direct fallback) and both generators
wired into `generate-quickstatements.yml`. The edits flow out only via the single
QS submitter, and only after the Wikidata freeze lifts (2026-06-06).

Also added CLAUDE.md §"Follow Emma's instructions LITERALLY" — implement her
stated steps verbatim (don't optimize/merge/guess); the project's hostile APIs
need the deliberately unintuitive, literal procedure.

### Removed all bespoke direct-API Wikidata editors — QuickStatements is the only channel
**Files (deleted):** `modern-quickstatements/{test_wikidata_qualifier,seed_kana_qualifier,append_kaminoyashiro_kana,remove_redundant_kana_statement}.py`, `.github/workflows/{test-wikidata-qualifier,seed-kana-qualifier,append-kaminoyashiro-kana,remove-redundant-kana-statement}.yml`. **Modified:** `.github/workflows/cleanup-loop.yml`, `modern-quickstatements/{submit_daily_batch,direct_daily_edits}.py`, `CLAUDE.md`.

Building the P459 and カミノヤシロ kana work as standalone direct-API editors (with
descriptive edit summaries) was the wrong shape and violated the project's core
Wikidata invariant: **Wikidata is edited by exactly ONE channel — the daily
QuickStatements pipeline, with NO edit summaries.** A cleanup-loop run executed
the combined kana move op directly on Wikidata (25 clean add+remove pairs, no
data loss, account not blocked) before being cancelled, which surfaced the
problem. Deleted all four bespoke editors + their workflows, removed their jobs
from cleanup-loop (build-run-history now needs only submit-quickstatements), and
documented the rule in CLAUDE.md ("Wikidata editing — ONE path only, no edit
summaries"). The QuickStatements pipeline (generate → submit_daily_batch → the
direct_daily_edits fallback that runs the SAME generated lines) is intact and is
the sole Wikidata editor. The P459 qualifier work is already covered by the QS
generators (modern_shrine_ranking_qualifiers.txt); the kana-qualifier work must
be re-expressed as QuickStatements lines if still wanted (open follow-up).

**Two-week Wikidata freeze (only Wikidata; everything else keeps running).** Per
Emma: force-killed every active GitHub Actions run, and added a hard freeze to
`cleanup-loop.yml`'s window-gate — `wikidata-daily-fire` is forced false until
**2026-06-06**, so the QS submission (the only Wikidata editor) cannot run on any
trigger; it auto-resumes after that date. `cleanup-loop` and all other workflows
stay **enabled and running as normal** (orchestrators, syncs, QS generation) —
only Wikidata *editing* is held, by the gate. New documented principle (CLAUDE.md):
**being visible on Wikidata is worse than losing data** — when in doubt, don't
edit. Also documented the add-first/remove-later-via-SPARQL two-script rule.

### Split the kana "move" into two independently-safe ops (seed + remove)
**Files:** `modern-quickstatements/seed_kana_qualifier.py` (renamed from move_kana_to_official_name.py), `modern-quickstatements/remove_redundant_kana_statement.py` (new), `.github/workflows/seed-kana-qualifier.yml` (renamed from move-kana-to-official-name.yml), `.github/workflows/remove-redundant-kana-statement.yml` (new), `.github/workflows/cleanup-loop.yml`, `queue.md`

Emma flagged a data-loss risk: the combined move op (add qualifier + remove the
top-level statement in one action) could, under random/drip execution or partial
failure, strip the top-level reading before its qualifier exists. Audited
Wikidata first — the move op had **never run** (0 move edits; the only recent
removals were Emma's own manual P1448 fixes), so nothing was damaged. Fixed the
design before it ever fires.

The "move" is now three independently-safe, presence-based ops (per Emma's spec):
- **op A — `seed_kana_qualifier.py` (ADD-ONLY):** for Q135038714 items whose
  single ojp-hani P1448 has NO P1814 qualifier but a top-level KATAKANA reading,
  copy that katakana onto the official name as a P1814 qualifier (raw). Never
  removes. Dry-run: 107 items / 118 qualifiers.
- **part 1 — `append_kaminoyashiro_kana.py`:** appends カミノヤシロ to ojp-hani
  P1814 katakana qualifiers (seeded or pre-existing). Unchanged.
- **op C — `remove_redundant_kana_statement.py` (REMOVE-ONLY):** removes a
  top-level katakana statement ONLY when a matching katakana qualifier is
  confirmed present on the official name (match tolerates part 1's suffix: a
  top-level T matches a qualifier q where q == T or q == T+カミノヤシロ). Modern
  hiragana top-levels never match a katakana qualifier and are left untouched.
  Dry-run: of 48 candidates only 2 currently match (the rest have non-matching /
  hiragana top-levels) — it grows as A seeds and part 1 appends.

No single action both adds and removes, so the top-level reading can never be
lost before it's safely on the official name. Wired into `cleanup-loop.yml` in
order seed → append → remove (each daily-fire gated; order doesn't affect
safety). The old combined `move_kana_to_official_name.py` was renamed to the
seed op.

### Fixed part-2 kana move: defer to part 1 when a qualifier already exists
**Files:** `modern-quickstatements/move_kana_to_official_name.py`, `queue.md`

Emma reviewed the "18 part-2 leftovers" and they were a false alarm. Checked the
data: of the 154 Q135038714 items with a standalone P1814 + an ojp-hani P1448,
**48 already have a P1814 katakana qualifier** on that official name (e.g. Eno
Shrine Q135040432: P1448 江野神社 ojp-hani + qualifier エノ, plus a normal
top-level modern reading えのじんじゃ) — those are part 1's job
(`append_kaminoyashiro_kana.py` appends カミノヤシロ to the existing qualifier), and
the top-level modern hiragana reading is correct and should be left. The 15
"modern hiragana leftovers" were all in this set. Part 2 trying to "move" a
standalone into those 48 would have created duplicate qualifiers.

Fix: part 2 now **skips any item whose ojp-hani P1448 already has a P1814
qualifier** (defers to part 1) and only SEEDS a qualifier for the ~106 items that
genuinely lack one. Reporting de-alarmed: the buckets are now "ambiguous
(manual)", "left to part 1 (qualifier already exists)", and "modern-only (no OJ
reading)". Dry-run after the fix: 48 deferred to part 1, ~106 seeded, 0
modern-only, 1 genuinely ambiguous (Q135040786, no ojp-hani name). Emma fixed the
earlier 3 ambiguous items on the wiki by hand.

### Label-generator Pages consolidated; standalone repo redirects
**Files:** `.github/workflows/generate-pages.yml`; (other repo) `EmmaLeonhart/shinto-label-generator` `docs/index.html` + `.github/workflows/deploy-redirect.yml`

`generate-pages.yml` now copies `shinto-label-generator/docs/` into
`_site/shinto-label-generator/`, so the merged label-generator report is served
at emmaleonhart.github.io/shintowiki-scripts/shinto-label-generator/. In the
standalone `shinto-label-generator` repo, `docs/index.html` was replaced with a
redirect to that subpage and `regenerate.yml` (now redundant — regeneration runs
here via `label-generator-regenerate.yml`) was swapped for a minimal
`deploy-redirect.yml` that just serves the redirect. Pushed to that repo's
master (57603cb).

### New orchestrator op: straggler raw wikilink → {{ill}} (Wikidata-resolved)
**Files:** `shinto_miraheze/orchestrators/ops/straggler_link_to_ill.py` (new), `shinto_miraheze/orchestrators/{mainspace,category,template,user,project,file,help,talk}_orchestrator.py`, `queue.md`

Built the straggler-link → ill op directly in-session (the remote routine
for it was disabled 2026-05-23; Emma wanted it done as an op, not a scheduled
routine). It converts free-standing raw internal wikilinks into proper
`{{ill}}` interlanguage-link templates by resolving the target to a Wikidata
QID:

    [[四所神社 (豊岡市)|四所神社]]
      → {{ill|Shisho Shrine (Toyooka)|ja|四所神社 (豊岡市)|lt=Shisho Shrine|qid=Q11419885}}

- **Scope — stragglers only.** Matches `[[Target]]` / `[[Target|Display]]`;
  SKIPS any target containing a colon (File:/Image:/Category:/namespace +
  interwiki `en:`/`ja:`/`zh:`… links), section-only `[[#X]]` links, and any
  link sitting inside a `{{ … }}` template (ill/jalink/nihongo/infobox params).
  In-template masking uses a brace-depth scan so nested templates are covered
  as one outer span — a link inside any template is never touched.
- **Resolution, strict priority.** (1) shinto.miraheze.org first: if the
  target (following redirects) is a page carrying `{{wikidata link|Q…}}`, use
  that QID; (2) else search Wikipedias en→ja→zh→ko→fr→de→ru, first hit wins, take
  the article's Wikidata item. No QID anywhere → link left unchanged. (Order
  corrected 2026-05-23 to insert French — it had been missing.)
- **ill build mirrors the sibling ill ops.** First positional = P11250 value
  with the `shinto:` prefix stripped (fallback: en Wikidata label if no
  P11250); one `lang|sitelink-title` pair per Wikipedia sitelink (sorted,
  enwiki/sister projects filtered like `normalize_ill_wikidata`); `lt=` = en
  label, OMITTED when the item has no en label; `qid=` always. If neither
  P11250 nor an en label exists there's no usable canonical title, so the link
  is left alone.
- **Pacing.** PRE_HEAVY light op (so converted text is captured by
  `history_offload`'s fandom mirror / XML archive in the same cycle, like the
  other ill ops). Read-only calls (miraheze + Wikidata + Wikipedias) throttled
  0.3s and cached per-run by unique target/QID. `MAX_CONVERSIONS_PER_PAGE = 5`
  caps a single page visit; the rest get picked up next cycle. Any HTTP 429
  trips a module-level kill switch — all further lookups short-circuit to
  not-found, no retries (repo-wide 429-bail policy). A failed lookup is cached
  as not-found so the link is conservatively left unchanged for that run.
- **Standard always-on op** (strictly programmatic — NOT gated behind any env
  flag; the initial gating was wrong and was removed per Emma) registered on all
  8 wikitext-namespace orchestrators (mainspace, category, template, user,
  project, file, help, talk), placed right after `ill_category_to_link` in each
  OPS list, so it runs on every wikitext page visit.
- **Dry-run before committing.** The spec example reproduced the target ill
  exactly. Real shinto pages converted correctly, e.g. on *Airborne Parachute
  Unit*: `[[田中賢一 (軍人)|田中賢一]]` →
  `{{ill|Ken'ichi Tanaka|ja|田中賢一 (軍人)|lt=Ken'ichi Tanaka|qid=Q112239761}}`,
  and on *Aedo Hashihime Shrine*: `[[伊勢文化舎]]` →
  `{{ill|Ise Bunka-sha|ja|伊勢文化舎|lt=Ise Bunka-sha|qid=Q11379080}}`. `品部`
  resolves to Q11418456 (has both an enwiki sitelink and P11250) and correctly
  yields `{{ill|Shinabe clans|en|Shinabe clans|ja|品部|lt=shinabe|qid=Q11418456}}`.
  Verified File:/Category:/`en:`/`ja:`/section-only links and links inside
  `{{nihongo}}`/existing ills produce no change. A link whose item has no en
  label and no P11250 (e.g. `丸 (雑誌)`, Q11367924) is left unchanged.

### Merged shinto-label-generator as a subtree + wired a 20/day label drip-feed
**Files:** `shinto-label-generator/**` (subtree), `.github/workflows/label-generator-regenerate.yml` (new), `.github/workflows/generate-quickstatements.yml`, `modern-quickstatements/select_label_proposals.py` (new), `modern-quickstatements/label_proposals_drip.txt` (new), `modern-quickstatements/{submit_daily_batch,direct_daily_edits}.py`

`git subtree add --prefix=shinto-label-generator ... master` (NO --squash — full
separate history preserved) brought the standalone label-generator in:
per-language proposed-label QuickStatements (`quickstatements/<lang>.txt`, 19
languages, ~1.1M lines), the generators (Indonesian/Korean/Chinese/multilang/
Toki Pona), and `docs/`.

The Indonesian generator (`generate_indonesian_proposals.py`) already does
JA-only-shrine → Indonesian: it romanizes the kana (P1814/P5461) or ja label via
pykakasi (Hepburn), strips parens + Japanese suffixes (Jinja/Jingu/Taisha/…), and
prepends "Kuil " (shrines) / "Wihara " (temples), e.g. "Kuil Tomiokahachimangu".
It derives from the kana, NOT the English label, and targets items with a ja but
no id label. Per Emma ("don't make it more efficient because it's working") it's
left untouched.

Wiring:
- **Generator workflow relocated** to the repo root as
  `label-generator-regenerate.yml` (monthly + on `shinto-label-generator/*.py`
  push). The original's Pages-deploy job was DROPPED — this repo has its own
  Pages deploy and two would clash. The in-subtree `regenerate.yml` is inert
  (GitHub only runs root workflows).
- **20/day drip-feed:** `select_label_proposals.py` pools all non-comment lines
  from `shinto-label-generator/quickstatements/*.txt` (pool ≈ 965k), picks 20 at
  random, converts the tab-delimited QS to pipe form, and writes
  `label_proposals_drip.txt`. Added a step to `generate-quickstatements.yml` to
  refresh it each cycle, and added the file to `ATOMIC_FILES` in both
  `submit_daily_batch.py` and `direct_daily_edits.py` so the daily QS run pushes
  ~20 labels/day. Deliberately slow (Emma: labels should lag the other work). No
  state file — the monthly regen only emits still-missing labels (self-draining);
  re-submitting an existing label is a no-op.

### Shrine en-label translation pipeline (SPARQL list + 5/day remote Sonnet translator)
**Files:** `modern-quickstatements/generate_shrines_missing_en_label.py` (new), `.github/workflows/generate-shrines-missing-en-label.yml` (new), `modern-quickstatements/select_shrines_to_translate.py` (new), `modern-quickstatements/en_labels_sonnet.txt` (new), `modern-quickstatements/shrines_missing_en_label.json` (new), `modern-quickstatements/{submit_daily_batch,direct_daily_edits}.py`

Progressive, self-draining queue for adding English labels to Shinto shrines on Wikidata that lack one:
- **Synced worklist (24h):** `generate_shrines_missing_en_label.py` SPARQLs every Shinto shrine (P31=Q845945) with a `ja` label but no `en` label, plus the kana reading (P1814) when present, → `shrines_missing_en_label.json`. The `generate-shrines-missing-en-label.yml` workflow runs it daily (05:17 UTC) and commits the refreshed list. First run: **5,061** shrines (442 with kana).
- **5/day translator (remote Sonnet routine):** `select_shrines_to_translate.py` picks 5 random shrines not already pending, prints them as JSON. A daily claude.ai **Sonnet** routine reads those, translates each `ja` label → English using the kana reading, and appends `Qxxx|Len|"..."` lines to `en_labels_sonnet.txt`.
- **Submission:** `en_labels_sonnet.txt` added to `ATOMIC_FILES` in both `submit_daily_batch.py` and `direct_daily_edits.py`, so the existing daily QuickStatements run pushes the new labels to Wikidata.
- **No state file:** dedup is presence-based — the selector skips QIDs already in `en_labels_sonnet.txt`, and once a label lands on Wikidata the next 24h SPARQL refresh drops it from the worklist.

### Tested the dup-content merge with local sub-agents (3 pages) + refined instruction
**Files:** `remote_queue.py`, `remote_queue.json`, `duplicated_content/{Take Minato Shrine,Shisho Shrine (Toyooka),Amatsu-Mikaboshi}.wiki`, `shinto_miraheze/sync_duplicated_content.state`

Ran 3 local sub-agents (general-purpose) against the freshly-pulled dup pages, each given the exact corrected `DUPLICATED_CONTENT_INSTRUCTION`, to validate the merge behavior before the cloud routine runs at scale. Results were correct:
- **Take Minato Shrine** (body ×3 + a `==merged content==` Wikidata dump + an English translation variant): collapsed 332→145 lines, reconciled conflicting river/era/station names, folded the Wikidata-dump's unique facts into prose, removed markers + category.
- **Shisho Shrine (Toyooka)** (×2 via `==Merged second translation==`): merged two parallel translations 144→74, kept the union of facts (e.g. the 1925 quake / 1928 rebuild / 1981 renovation only in copy 2), category removed.
- **Amatsu-Mikaboshi** (control): correctly identified it as NOT duplication (English article + raw-Japanese `==Japanese Wikipedia content==`), left the Japanese alone, only removed the (mistaken) dup-content category.

Emma reviewed and chose: keep the 3 merges + let the cloud routine proceed, and handle Wikidata-autogenerated property dumps by **folding unique facts into prose** (drop rows already in the infobox). Added that guidance to `DUPLICATED_CONTENT_INSTRUCTION` and regenerated all 135 dup instructions in `remote_queue.json`. Aligned `sync_duplicated_content.state` for the 3 titles to the current wiki revid/sha so the next sync sees them as local-changed/wiki-unchanged and PUSHES the merges (rather than wiki-wins discarding them as conflicts).

### Duplicated-content pipeline overhaul (wrong concept + jammed sync + cursor flaw)
**Files:** `remote_queue.py`, `remote_queue.json`, `shinto_miraheze/sync_duplicated_content.py`, `shinto_miraheze/sync_need_translation.py`, `consume_remote_queue.state`, all of `duplicated_content/*.wiki`, `queue.md`

Emma reported the duplicated-content pipeline "did nothing" on the wiki and was
making "random edits." Investigation found three compounding problems:

1. **The consumer had the wrong concept of "duplicated content."** The
   `DUPLICATED_CONTENT_INSTRUCTION` told the cloud worker the duplication was
   "autogenerated wikidata boilerplate vs article body" and to "drop boilerplate
   / dedupe overlapping prose" — so it was removing duplicate infobox params and
   interwiki lines (copyediting). The real meaning: **macro-scale, whole-body
   paragraph duplication** — the entire article copied 2+ times (e.g. Take Minato
   Shrine has its body 3×, plus `==Accidentally Overwritten Content==` /
   `==merged content==` marker headings). The job is to MERGE the parallel copies
   into one coherent article, reconciling where they deviate. Rewrote the
   instruction accordingly, incl. Emma's note that duplicated *parameters* must
   be left alone (removed programmatically elsewhere; the duplication carries
   signal). Updated all 135 dup items in `remote_queue.json` from the new
   constant so the consumer uses it immediately (daily rebuild also picks it up).

2. **The sync was jammed on conflicts.** `sync_duplicated_content` ran fine
   (every wiki-cleanup step has `if: always()`, so the restart-notice theory that
   syncs "never ran" was wrong), but the last run reported **133 of 134 pages as
   CONFLICT** — both the wiki revid and the local sha had changed since the last
   baseline, so the conservative "skip on conflict" left every page unsynced;
   the agent's repo-side edits never reached the wiki. Per Emma's policy decision
   — **the wiki is the source of truth for the cloud-queue pipelines** — changed
   the conflict branch in both `sync_duplicated_content.py` and
   `sync_need_translation.py` to **wiki-wins** (pull, overwriting local). The
   long-term template syncs (`git_synced`, `fandom_unique`, `miraheze_unique`)
   were already repo-wins, which matches Emma's policy (repo authoritative there
   because templates are hard to edit on-wiki) — left unchanged. Did an immediate
   read-only poll of all 134 dup pages from the wiki → overwrote local, clearing
   the jam and discarding the consumer's bad edits.

3. **The consumer's cursor skipped pages permanently.** The claude.ai routine
   walks `consume_remote_queue.state` (was at 105) through a static
   `remote_queue.json`; once past an item it never revisits, so the 133 pages it
   "did" with the wrong instruction (category removed but never actually merged —
   e.g. Take Minato still triplicated) would never be reprocessed. Emma wants
   statefulness to be purely file-presence + category, no cursor. Repo-side
   mitigations: `remote_queue.py` now `random.shuffle()`s the queue and only
   includes dup files that still carry the category (`_still_has_dup_category`);
   reset the cursor to 0. The deeper fix — making the cloud routine cursor-less
   (scan category-tagged files, pick at random) — needs a change to the routine's
   prompt, which can't be done from the repo; tracked in `queue.md`.

Also cleared the resolved 2026-05-20 crash/restart bloat out of `queue.md`.

### Fixed: no Wikidata edits since 2026-05-16 (qppage casing + cleanup coupling)
**Files:** `shinto_miraheze/delete_unused_redirects.py`, `.github/workflows/cleanup-loop.yml`, `queue.md`

Wikidata edits (under user `Immanuelle`) stopped on 2026-05-16 (last edit
19:29Z, Uga Shrine). Root cause was two-layered:

1. **`delete_unused_redirects.py` querypage casing.** The script queried the
   MediaWiki `querypage` API with `qppage="Unusedredirects"`; the API requires
   the exact Special: alias casing `"UnusedRedirects"` (capital R) and started
   returning `('badvalue', 'Unrecognized value for parameter "qppage"')` around
   2026-05-16. Verified the correct value via
   `api.php?action=paraminfo&modules=query+querypage` (valid redirect querypages:
   BrokenRedirects, DoubleRedirects, **Listredirects** (no capital R!),
   UnusedRedirects — the aliases are inconsistent per page, so the script's old
   "camel-stripped canonical form" comment was simply wrong). Only this one of
   the repo's ~11 querypage callers was mis-cased; the others' steps weren't
   failing. Fixed the constant + comment.

2. **Cleanup → Wikidata workflow coupling (the real design flaw).** The failing
   redirect step is a *Shinto-wiki* (miraheze) operation with nothing to do with
   Wikidata — but the four Wikidata-edit jobs in `cleanup-loop.yml`
   (submit-quickstatements, wikidata-qualifier-edit, move-kana-to-official-name,
   append-kaminoyashiro-kana) were gated `if: ... needs.cleanup.result ==
   'success'`. So a Shinto-wiki cleanup failure silently skipped all Wikidata
   edits. Changed the gate to `needs.cleanup.result != 'cancelled'` on all four:
   they still sequence after the cleanup job, but a cleanup *failure* no longer
   blocks independent Wikidata work. (Per Emma: redirect cleanup "shouldn't even
   be applying for wikidata.")

Both fixes pushed to main, which re-triggers `cleanup-loop.yml`.

### Append カミノヤシロ to ojp-hani shrine kana qualifiers (Wikidata bot request 2026-02-26)
**Files:** `modern-quickstatements/append_kaminoyashiro_kana.py` (new), `.github/workflows/append-kaminoyashiro-kana.yml` (new), `.github/workflows/cleanup-loop.yml`, `queue.md`

Per the Wikidata bot request (2026-02-26): Old Japanese (`ojp-hani`) `P1448`
official names of shrines carry a `P1814` "name in kana" qualifier that omits
the reading of 神社, which in Old Japanese is カミノヤシロ (kami-no-yashiro).
Built a direct Wikidata API editor that appends カミノヤシロ to each such
qualifier value.

Data shape verified against live Wikidata before building: P1448 mainsnak is
monolingualtext (`ojp-hani`); the P1814 qualifier is the **string** datatype
(not monolingualtext, despite the property name); a single P1448 statement can
carry multiple P1814 qualifiers (alternate readings). The script edits each
qualifier *in place* via `wbsetqualifier` with the existing `snakhash`, so no
duplicate qualifier is created. Idempotent: a value already ending in カミノヤシロ
is skipped, and the SPARQL universe shrinks via a `!STRENDS(...)` filter
(4,706 matching statements at build time; 6 already done → 4,700 remaining,
confirmed by `--dry-run`).

Modelled on `test_wikidata_qualifier.py`: SPARQL → per-item `wbgetentities` →
`wbsetqualifier`. `MAX_EDITS=50`/run (sits alongside the existing 50 QS-submit +
50 P459-qualifier daily jobs under the once-per-day fire gate), `THROTTLE=1.5`,
429-bail (no retries), graceful skip when `MW_BOTNAME`/`BOT_TOKEN` absent, and a
`--dry-run` flag for local read-only verification. Wired into `cleanup-loop.yml`
as `append-kaminoyashiro-kana`, daily-fire-gated after `wikidata-qualifier-edit`;
`build-run-history` now also `needs` it.

**Open follow-up (in `queue.md`):** the request's secondary ask — items
`P31`=Q135038714 whose kana is a standalone `P1814` *statement* (not a
qualifier) need the kana *moved into* a P1448 ojp-hani qualifier before the
append. More invasive (statement restructuring); left for scoping with Emma.

### Move standalone P1814 kana into ojp-hani official-name qualifiers (secondary ask)
**Files:** `modern-quickstatements/move_kana_to_official_name.py` (new), `.github/workflows/move-kana-to-official-name.yml` (new), `.github/workflows/cleanup-loop.yml`, `queue.md`

Built the secondary task (Emma chose move + append, dashes verbatim). For
`P31`=Q135038714 (Disputed Shikinaisha) items carrying the kana as a standalone
top-level `P1814` *statement*, the script adds it as a `P1814` qualifier on the
single ojp-hani `P1448` official name (value = original + カミノヤシロ, dashes
preserved) and removes the standalone statement. Modelled on
`append_kaminoyashiro_kana.py`: SPARQL → per-item `wbgetentities` →
`wbsetqualifier` (no snakhash = add) + `wbremoveclaims`. Idempotent (removal
drops the item out of the `p:P1814` SPARQL universe; existing-qualifier check
avoids double-add). `MAX_EDITS=50`/run, `THROTTLE=1.5`, 429-bail, `--dry-run`.
Wired into `cleanup-loop.yml` as `move-kana-to-official-name`, daily-fire-gated,
ahead of `append-kaminoyashiro-kana`.

**Data hazard found in the dry-run — added a katakana gate.** The standalone
`P1814` set on these items is *mixed*: Old-Japanese katakana readings
(e.g. `タケミナカタトミノ-`) alongside **modern hiragana** readings
(e.g. `いめじんじゃはちまんぐう`, which already contains じんじゃ=神社). The bot request
says "the same katakana change," so カミノヤシロ (the *Old Japanese* reading of
神社) only belongs on the katakana ones — appending it to a modern reading, or
attaching a modern reading to an Old-Japanese official name, would be wrong.
`is_katakana_reading()` rejects any value containing a hiragana char (or no
katakana at all). Census of the 155 items: **137 movable** (~151 katakana
statements), 2 ambiguous (>1 ojp-hani name), 1 with no ojp-hani name, **15
modern-hiragana-only** left untouched. The bot reports all 18 untouched cases
to stdout each run; they're tracked in `queue.md` for manual handling.

---

## 2026-05-20

### Remote queue consumer moved from GHA workflow to claude.ai scheduled routine
**Files:** removed `.github/workflows/consume-remote-queue.yml`, removed `consume_remote_queue.py`

Initial wire-up of the remote-Claude consumer put it in GitHub Actions calling the Anthropic SDK with an `ANTHROPIC_API_KEY` secret. That's the wrong shape for this repo: GHA in shintowiki-scripts is for repo↔wiki sync (and similar plumbing), not for paying-API LLM grunge work. Replaced with a **claude.ai scheduled routine** (`trig_013F9aeKeL3hx8zo7weKj3Ed`) — runs every 2 hours at :47 UTC, executes inline on Claude infra (no key needed, no GHA), commits + pushes back to main. Uses the same `consume_remote_queue.state` cursor the script would have, just driven by the routine's prompt instead of an SDK call.

Deleted `consume_remote_queue.py` and `.github/workflows/consume-remote-queue.yml` — the routine doesn't need them. The cursor state file `consume_remote_queue.state` will be created on first run.

### Remote-Claude consumer wired up (`consume-remote-queue.yml`)
**Files:** `consume_remote_queue.py` (new), `.github/workflows/consume-remote-queue.yml` (new)

`build-remote-queue.yml` had been rebuilding `remote_queue.json` daily for at least three weeks (1,097 items at last build), but no consumer was committing back — zero non-CI edits to `duplicated_content/`, `need_translation/`, `fandom_unique/`, or `miraheze_unique/` since 2026-05-01. The "remote-Claude cron" referenced in `queue.md` either was never deployed or got decommissioned.

Wrote `consume_remote_queue.py` — an Anthropic SDK consumer that walks the queue via a cursor in `consume_remote_queue.state`. Each run picks N items (default 3, cap 20), sends each as `(per-item instruction + delimited file contents)` to `claude-opus-4-7`, and writes the returned text back to the file. System prompt is cached (`cache_control: ephemeral`) so multi-item runs amortize. The model is instructed to return ONLY the new file body — no preamble, no fences — and to return the input verbatim when the instruction doesn't apply. Skips empty responses, identical outputs, and missing files (race with the wiki-cleanup sync that deletes local files when their category leaves the wiki).

`consume-remote-queue.yml` fires every 2 hours at minute 17 with `cancel-in-progress: false`, `timeout-minutes: 30`. At N=3 / 2-hour cadence that's ~36 items/day — roughly 30 days to drain the current queue. Tunable via `workflow_dispatch.inputs.max_edits` or by editing the cron. The commit message uses the `[skip ci]` marker so it doesn't trigger further loops.

**Dependency:** the workflow needs `ANTHROPIC_API_KEY` as a repo secret. None of the existing secrets (`WIKI_PASSWORD`, `BOT_TOKEN`, `FANDOM_*`, `QS_*`, `MW_BOTNAME`, `ARCHIVE_REPO_DEPLOY_KEY`) are an Anthropic key, so the scheduled runs will error out at the SDK call until the secret is added — flagged in `queue.md` as the open follow-up.

### Queue discipline merged from cleanvibe; todo.md `[x]` purge
**Files:** `CLAUDE.md`, `todo.md`, `queue.md`, `DEVLOG.md`, `.gitignore`

User flagged that the workflow rules in `CLAUDE.md` (plan into `queue.md` first, delete on completion, mirror to TaskCreate) had not actually been followed — `queue.md` had been touched in only 2 commits ever since being introduced 2026-05-18, despite 71 commits landing in that window. To bring the discipline live: ran `cleanvibe clone --no-claude` into a fresh `.cleanvibe-scratch/sws/` (now gitignored) to see the latest opinionated `CLAUDE.md` cleanvibe injects. The new bit not already encoded here was the **DEVLOG.md-in-same-commit** rule — done items must be deleted from `queue.md` AND appended to `DEVLOG.md` in the same commit, instead of disappearing into `git log` alone. Merged that rule plus the `todo.md → queue.md → task tool → DEVLOG.md` flow diagram into this repo's `CLAUDE.md`.

Audited `todo.md` and removed the 7 `[x]` entries (`commit_state.sh` rebase fix, 300+ untranslated re-bucket, `replace_p1027_with_p459.txt`, template `<noinclude>` fix, erroneous-qid-category-links migration, legacy category-page fix templates removal, `commit_state.sh` rebase-bail). Section headers left empty by those removals were deleted. Populated `queue.md` with two concrete next actions: wire up the GHA remote-Claude consumer for `remote_queue.json`, and CronCreate an in-session self-paced worker as a stopgap.

While auditing the remote-workflow pipeline: `build-remote-queue.yml` is healthy (7 daily rebuilds in a row, latest today), but the consume side has been dead for at least three weeks — zero non-CI commits to `duplicated_content/`, `need_translation/`, `fandom_unique/`, or `miraheze_unique/` since 2026-05-01. The "remote-Claude cron" the queue plan references was either never deployed or was decommissioned. Filed as the top queue item.

---

## 2026-05-14

### `iter_category_with_revisions` pagination bug ported to the unique-pages syncs
**Files:** `shinto_miraheze/sync_miraheze_unique_pages.py`, `shinto_miraheze/sync_fandom_unique_pages.py`, `.github/workflows/fandom-sync.yml`, `.github/workflows/git-synced-sync.yml`

The same MediaWiki-API pagination bug that `sync_git_synced_pages.py` fixed on 2026-05-10 was still live in the two unique-pages syncs. Single-pass `generator=categorymembers` + `prop=revisions` + `rvprop=content` only returns ~50 pages with content per response; the rest come back without a `revisions` field and were silently skipped. With 515 tracked entries on miraheze, hundreds of pages per cycle looked like they had fallen out of `[[Category:Independently git synced pages]]`, fell through to the orphan-PUSH path, and overwrote genuine wiki edits with stale `miraheze_unique/<title>.wiki` content. User reported: "the Mirahaze unique stuff is just overwriting intended page edits."

Ported the two-pass helper verbatim from `sync_git_synced_pages.py` into both unique-pages syncs. Pass 1 lists every category member's title; pass 2 fetches revisions+content in batches of 50 via `titles=`, which has clean continuation semantics.

While in there, bumped the sync cadence — `fandom-sync.yml` was running once a day, `git-synced-sync.yml` was manual-only. Both now run every 15 minutes (~96/day) with `concurrency.cancel-in-progress: true` so overlapping fires can't pile up. Offset by 5 minutes so the two workflows don't hit miraheze at the same instant.

---

## 2026-05-12

### `{{ill}}` template normalization: qid is the authoritative signal
**Files:** `shinto_miraheze/orchestrators/ops/normalize_ill_positional.py`, `shinto_miraheze/orchestrators/ops/normalize_ill_wikidata.py` (new), `shinto_miraheze/orchestrators/mainspace_orchestrator.py`
**Status:** Both ops gated on qid; new op gated by `ENABLE_NORMALIZE_ILL_WIKIDATA=1`

The mainspace orchestrator gets two `{{ill}}` cleanup ops now. Both run PRE_HEAVY (so the cleaned text propagates into history_offload's fandom mirror and XML archive in the same cycle). Together they replace the previous half-done normalize_ill_positional with a complete pipeline:

1. **`normalize_ill_positional`** — cheap, no API calls. If a call has `qid=Q…` AND a `|1=X` named override, promote the last `1=` to the bare positional and drop every `1=` entry. The qid gate is new on this op: previously it ran unconditionally and would mangle calls that lacked a qid. The user's mental model is that **a qid is proof that the link has been reconciled against Wikidata**; an ill template without a qid is the deliberate human signal that something is unresolved (target ambiguous, no Wikidata entity yet, CJK sources conflict), and the previous behaviour of silently promoting a `1=` on those was overwriting human notes.

2. **`normalize_ill_wikidata`** (new) — expensive, hits Wikidata. If a call has `qid=Q…` and any junk (a named param other than `qid`/`lt`, or >1 positional), rewrite the entire call into a clean form: positional[0] + sorted `lang|title` pairs from the Wikidata sitelinks (enwiki excluded — already the positional, sister projects excluded, underscored codes like `zh_classical` kept) + `qid=` + optional `lt=`. The last `1=` value (if any) wins as the new positional[0], same last-wins rule as MediaWiki uses. Gated by `ENABLE_NORMALIZE_ILL_WIKIDATA=1` so the API churn isn't on by default. Per-run cache means each unique QID costs at most one API call per orchestrator run.

**The "redirects to" exception got walked back.** An earlier scoping pass had `normalize_ill_wikidata` refuse to touch calls whose body contained `redirects to` (case-insensitive) — the worry was that human notes like `ja_comment=jawiki redirects to スクナビコナ` flagged a real conflict the bot shouldn't paper over. After a closer look, the user reversed this: **if a qid is present we trust it.** The historical reason for caution about redirects was that during the early enwiki/jawiki import wave, some auto-attached interlanguage links pointed at redirect pages that landed in the wrong place — and the fix was to manually attach the correct QID via replaced text. Now that those manual QIDs are in place, the qid is the canonical signal: a redirect-target note in the body is just legacy commentary, and the rebuild from sitelinks is the right thing to do.

Order in `mainspace_orchestrator.OPS`:

```
strip_html_comments,           # PRE_HEAVY
ill_category_to_link,          # PRE_HEAVY
normalize_ill_positional,      # PRE_HEAVY  ← promotes 1= to positional, drops 1=
normalize_ill_wikidata,        # PRE_HEAVY  ← rebuilds from Wikidata when qid + junk
interlang_consolidate,         # PRE_HEAVY (gated)
wikidata_lookup,               # PRE_HEAVY (gated)
history_offload,               # heavy
…
```

Pages already touched by old `normalize_ill_positional` are unaffected. Pages that hadn't been visited yet (e.g. [[Agata Shrine (Gero City)]] which still carried the full junk form on 2026-05-12) will get the full clean-up next time they come up in the alphabetic sweep — the orchestrator runs ~100 pages per cycle with a 1000-page state-growth cap, so it can take many cycles to walk the whole namespace.

### Duplicated content: sync wired, agentic resolution scheduled
**Files:** `.github/workflows/wiki-cleanup.yml`, `SYNCING.md` (new)
**Status:** Live

`sync_duplicated_content.py` was implemented for `[[Category:Pages with duplicated content]]` months ago but never invoked by any workflow — the local `duplicated_content/` directory didn't exist because the script had never been run with `--apply`. Wired it into `wiki-cleanup.yml` in a new Duplicated Content Sync block between the Translation Sync and Git-Synced Pages sections. Same pattern as `sync_need_translation`: pull → commit `duplicated_content/` → commit state.

Resolution loop is two-stage: CI sync pulls wiki pages into `duplicated_content/`, then a series of scheduled remote agents (six one-shot routines, 12 hours apart starting 2026-05-13T21:18Z) reorganize the paragraphs into single coherent merged articles and strip the `[[Category:Pages with duplicated content]]` line from each file as it finishes. The next CI sync cycle sees the missing cat line, pushes the cleaned content to the wiki (which removes the category there too), and deletes the local file.

`SYNCING.md` at the repo root documents this and every other wiki↔repo / wiki↔wiki sync pathway.

### `categories_to_bottom` op — move stray cats to page bottom on non-template namespaces
**File:** `shinto_miraheze/orchestrators/ops/categories_to_bottom.py` (new)
**Status:** Live, registered on mainspace, user, project, file, help, and talk orchestrators

`noinclude_wrap` already does this for template pages (wraps stray cats inside `<noinclude>`). `normalize_category_page` already does it for category pages (rebuilds the whole page into a canonical templates/interwikis/categories block). For every other wikitext namespace there was no equivalent — own-line `[[Category:…]]` tags imported into the middle of pages from enwiki/jawiki stayed where they were.

The new op finds own-line cat tags whose page position is NOT inside the trailing category block (walks backwards from EOF over consecutive cat lines + whitespace to identify the trailing block, anything before that is stray) and moves them to the bottom in original order. Inline cats inside a sentence / ref tag / template parameter are deliberately not matched — moving those could wreck the surrounding wikitext.

---

## 2026-05-05

### Wiki shutdown threat from yesterday did not materialize — exiting desperation mode
**Status:** Context note

The miraheze-side warning that triggered the 2026-04-24 archive-push window (bias mainspace+template orchestrators to 1000-edit budgets, push aggressively into the fandom mirror + GitHub XML archive) was supposedly going to result in the wiki being shut down on 2026-05-04. That deadline came and went without action. We are not abandoning the archive backstops — fandom mirror + XML archive are still maintained best-effort — but we are no longer in "save what we can before the lights go out" mode.

Practical effects landing in subsequent commits:

* Archive-push edit-limit window in `cleanup-loop.yml`'s `window-gate` reverts to the 2026-05-05 → 2026-06-01 catchup baseline (uniform 500 per orchestrator) starting today, then to default 100 on 2026-06-01. (Implementation already in `window-gate`; today is the date the table inflects.)
* The `Currently double category qids` review buffer (added below) and the Japanese-cat drain logic become the long-running cleanup pattern, replacing one-shot bulk migrations.
* `status.md` archive-push window section is removed — the work it was tracking is done or no longer relevant.

### Resolver was actually hanging on a 1MB / 19,320-link audit page that contaminated the source category (timeout fix wasn't enough)
**Scripts:** `shinto_miraheze/resolve_double_category_qids.py`
**Status:** Fixed (the real bug)

The `site.connection.timeout = 120` fix from a prior commit didn't help — runs still ran for hours with one wiki edit (the stage marker) and nothing else. After the timeout fix landed, run `25410343874`'s resolver step started 02:00:23 UTC and stayed `in_progress` ~3.5+ hours with the same signature.

Real cause: the FIRST page in `[[Category:Double category qids]]` alphabetically is `[[Double category QIDs audit]]` — a 1MB page with **19,320** `[[:...]]` links. It was written there at some point by the disabled `audit_double_category_qids.py` script, before that script was disabled for being unbounded. My resolver iterated this page first, ran `LINK_RE.findall()` (got 19,320 hits), then called `resolve_final_target` on each — 2+ API calls × 0.3s sleep × 19,320 ≈ 2.7 hours per resolver call, all on one page, never reaching `--max-edits` because zero edits were being made.

Three layered fixes:

1. **QID-only filter in `collect_pages`.** Real dab pages are by definition `Q\d+` named (the generator script writes them at QID titles). Filter to `^Q\d+$`; everything else is contamination. The audit page's title `Double category QIDs audit` doesn't match and is dropped at enumeration time.

2. **`MAX_LINKS_PER_PAGE = 20` defensive cap.** Real dab pages have 2–5 links. Anything with hundreds is misplaced content. Skip-and-add-to-state on overflow so we never try to resolve thousands of links again.

3. **State file (`resolve_double_category_qids.state`).** Tracks titles already resolved (or skip-decided), so subsequent runs don't re-iterate the alphabetically-first pages of the source cat. Same pattern as the other legacy scripts; picked up by `commit_state.sh` automatically.

Multi-target/drain pages are deliberately *not* added to state — they need re-visiting on subsequent cycles to detect when the unused-cat sweep has finally cleaned up the Japanese cat.

### Resolver hung on first push-triggered run — missing `site.connection.timeout`
**Scripts:** `shinto_miraheze/resolve_double_category_qids.py`
**Status:** Fixed

Symptom: cleanup-loop run `25408189695` (the first push-triggered run with the re-enabled resolver from commit 6c1bc3d) had its `Structural: resolve_double_category_qids` step start at 23:44:55 UTC and stay `in_progress` for 47+ minutes. EmmaBot's wiki contributions log showed exactly one edit at 23:44:57 (the `run_step.sh` "stage" marker), then nothing. The script wasn't crashing, wasn't making progress, just hung silently — as did the queued cleanup-loop runs behind it.

Root cause: `mwclient.Site(...)` was constructed without setting `site.connection.timeout`. The library's default is no timeout, so a single slow miraheze response can hang the underlying HTTP request indefinitely. Every other long-running script in this repo sets `site.connection.timeout = 120` (audit_double_category_qids, find_duplicate_page_qids, fix_merged_qids, generate_p11250_quickstatements, propagate_independent_category, reimport_from_enwiki, rename_fandom_sync_category, strip_translated_char_count_cats, sync_duplicated_content, …) — the resolver simply did not, and it bit us on the first run.

Fix: `site.connection.timeout = 120` after construction. Force-cancelled the stuck run via `POST .../force-cancel` (regular cancel is cooperative — won't propagate while the script is mid-API-call) so queued runs could move.

### Resolver: drain edit now also posts a merge notice on the Japanese cat page; *do not* redirect the dab page in the same cycle
**Scripts:** `shinto_miraheze/resolve_double_category_qids.py`
**Status:** Complete (corrects an over-aggressive earlier change in this same session)

Two intertwined changes:

1. **Merge notice on the Japanese cat page.** The drain edit now prepends a human-readable banner above the `[[Category:crud categories]]` tag: *"This Japanese-named category is being merged into [[:Category:English]]. EmmaBot is moving members to the English-named category; this page will be cleaned up once empty."* Idempotent via a marker comment (`<!-- bot-jp-cat-merge-notice -->`), so subsequent runs don't re-post. Notice + crud-cat tag land in a single save per JP cat (one edit instead of two).

2. **Reverted the post-drain redirect.** A preceding commit in this session had the resolver redirect the dab QID page to the English target as the final step of the drain branch. That was too aggressive — the intended workflow is deliberately slow:

   * **This run:** drain Japanese cat (notice + crud + double-categorize members). Dab page stays as-is, just retagged from legacy to `Currently double category qids`.
   * **Subsequent runs over the next ~week:** the `crud categories` cleanup sweep deletes the now-empty Japanese cat.
   * **Once the Japanese cat is gone:** the dab page falls into the single-existing-target branch on its next visit and gets redirected to the English cat automatically.

   The forced multi-cycle pacing isn't because human review is required — it's because the slowness gives a human a clear window to intervene if any individual case is wrong, without requiring them to. The end state is the same redirect; the intermediate state is more readable.

### fandom-sync: pulled .wiki files were never committed — workflow missing the content-commit step
**Scripts:** `.github/workflows/fandom-sync.yml`
**Status:** Fixed

Symptom: `fandom_unique/` had only 8 files in the repo despite the workflow running daily and pulling ~1000 pages each run. User flagged it as "the fandom unique directory has fuck all pages in it."

Root cause: when the new Independent Pages Sync workflow was added on 2026-05-05 (commits 3496352 + 73a7982), it was modeled on the existing `git-synced-sync.yml` but missed its content-commit step. `git-synced-sync.yml:71-81` has an explicit "Commit: git_synced/ changes" step that does `git add -A git_synced/` before invoking `commit_state.sh`. The new workflow only invoked `commit_state.sh` directly — and that script's globs (`*.state`, `*.log`, `*.errors`, `reports/`) don't match `.wiki` files in the unique/ directories.

The compounding failure: `commit_state.sh` rebases against origin before pushing. With unstaged `.wiki` files in the working tree, `git rebase` aborted with "you have unstaged changes," so even the state-file commit never reached origin. Every daily run pulled 948 fandom pages + 106 miraheze pages, then the runner tore down and lost everything. Same loop the next day.

Confirmed via the 2026-05-05 12:45 UTC run log:

```
sync_miraheze_unique:    Wiki: 107 in category, Local: 1 .wiki files. Pulled (wiki -> repo): 106
bootstrap_seed_fandom:   Seeded into fandom_unique/: 101
sync_fandom_unique:      Wiki: 1042 in category, Local: 109 .wiki files. Pulled: 948
commit_state.sh:         error: cannot rebase: You have unstaged changes.
                         WARN: rebase failed on attempt 1; aborting.
```

Fix: add the missing "Commit: miraheze_unique/ + fandom_unique/ changes" step to `fandom-sync.yml`, modeled exactly on the git-synced-sync equivalent (`git add -A` over the dirs, commit if non-empty, pull-rebase, push). Runs before `commit_state.sh` so the state-file commit's rebase has nothing unstaged to choke on. Next scheduled run (2026-05-06 11:30 UTC) will land all ~1050 pulled pages.

### resolve_double_category_qids: drain Japanese-named categories into the English equivalent
**Scripts:** `shinto_miraheze/resolve_double_category_qids.py`
**Status:** Complete

Follow-up to the resolver re-enable below. For multi-target dab pages — where two or more *existing* categories share a QID — the previous behaviour was just to migrate the page off the legacy review category and leave it for human triage. Most of these pages are actually a Japanese-script category (e.g. `Category:遺跡`) duplicated against an English equivalent (`Category:Archaeological Sites`); the user's preference is to drain the Japanese one into the English one rather than merge in a single edit.

When exactly one of the existing targets is English-named (contains an ASCII letter) and one or more are Japanese-script-only (no ASCII letters in the name), the resolver now:

1. Tags each Japanese-named category page with `[[Category:crud categories]]` (idempotent — skips if already present).
2. Iterates members of each Japanese category and appends `[[Category:English]]` to any page that doesn't already have it.

Idempotent under repeated runs. Members already double-categorized are skipped. As the Japanese categories drain to empty over subsequent cleanup-loop cycles, the unused-categories sweep deletes them, and the dab page falls into the single-existing-target branch and gets auto-redirected — no separate cleanup needed.

Edits are bounded by the same `--max-edits` budget that governs the rest of the resolver run; if the budget is hit mid-drain, the run halts and resumes next cycle.

### resolve_double_category_qids: re-enabled with missing-target branch + bounded scope
**Scripts:** `shinto_miraheze/resolve_double_category_qids.py`,
`shinto_miraheze/create_japanese_category_qid_redirects.py`,
`.github/workflows/wiki-cleanup.yml`
**Status:** Re-enabled

`resolve_double_category_qids.py` had been disabled with the note "0 edits across 3 runs" — root cause was that the resolver only handled the all-chain-to-same-target case, but the dominant pattern in `[[Category:Double category qids]]` is "one of the two listed categories was renamed and emptied without leaving a redirect," i.e. only one target *exists*. The old `resolve_final_target` returned the title unchanged for missing pages, so a `[[:Category:Foo]]` (exists) + `[[:Category:Bar]]` (missing) page produced two distinct targets and was skipped.

Three changes shipped together:

1. **Resolver: missing-target branch.** `resolve_final_target` now returns `(final_title, exists)`. The main loop counts *distinct existing terminal targets*. If exactly one exists, redirect to it (subsumes the old all-same-target case). Multi-target pages are left untouched but moved to a separate review category (below).

2. **New "currently" category swap.** The generator (`create_japanese_category_qid_redirects.py`) now writes new dab pages into `[[Category:Currently double category qids]]` instead of the legacy `[[Category:double category qids]]`. The resolver iterates both source categories; for any page with multiple distinct existing targets that still carries the legacy tag, it strips the legacy tag and adds the "currently" tag. Effect: the legacy category drains to empty as the resolver visits its pages, and the "currently" category becomes the rolling buffer of dabs awaiting human review.

3. **Bounded per-run scope.** `MAX_PAGES_PER_RUN = 200` caps page visits per run, and `THROTTLE_API = 0.3s` spaces out reads inside the redirect-chain follower. This is the safeguard that was missing on `audit_double_category_qids.py` (un-throttled, 11+ hours, hung the cleanup loop on 2026-04-24); without it the same fate would befall this script when iterating the ~2000-page legacy backlog.

The audit script stays disabled — once the resolver drains the easy cases, the residual review set is exposed by the "currently" category itself, no separate report needed.

---

## 2026-05-03

### cleanup-loop: every 6h fire actually runs again
**Status:** Fix

Symptom: scheduled run at 13:19 UTC completed in 7 seconds with every downstream job reporting "in 0s". The earlier 08:05 UTC fire showed the same shape (window-gate ran, everything else skipped). User flag: "last run literally did absolutely nothing."

Root cause: on 2026-05-02 (commit 52eac59) the catch-up window was removed and `should-proceed` was kept as the cron cadence gate — only the 00:00 UTC fire proceeded. The catch-up branch that previously overrode that gate (`CATCHUP=true → proceed=true`) went away with it, so 3-of-4 cron slots silently no-op'd. The cron-line comment still claimed "every fire runs the full pipeline" — code and comment had drifted.

Fix: removed the off-hour gate entirely. `window-gate` now publishes only the per-orchestrator edit limits; every downstream `if:` lost its `should-proceed` predicate (`if: always()` where the job had other reasons to keep `always()`, removed otherwise). Every 6h cron fire now runs the full pipeline. `submit-quickstatements` gained `cleanup` in its `needs:` list — it was already referencing `needs.cleanup.result` without declaring the dependency.

If a future pause is needed, disable individual jobs explicitly rather than re-introducing the gate.

---

## 2026-04-24

### Session summary — archive-push plan, timeline, and everything that shipped today
**Status:** Context note

Big session. Today the story is "how do we cram as much of shintowiki into a preserved form (fandom mirror + GitHub XML archive) before the miraheze situation potentially forces our hand." Everything below was in service of making the orchestrator pipeline reliable, bounded, and biased toward the content we most care about saving.

**Timeline plan (all dates UTC):**

| Window | Mainspace | Template | Category | Misc | Notes |
|---|---|---|---|---|---|
| **2026-04-24 → 2026-05-05** (archive-push) | **1000** | **1000** | **10** | **10** | Bias hard toward the two namespaces we most want archived. |
| **2026-05-05 → 2026-06-01** (catchup baseline) | 500 | 500 | 500 | 500 | Uniform budget while the outer catchup window stays open. |
| **2026-06-01 onward** (default) | 100 | 100 | 100 | 100 | Normal operating schedule; daily instead of 6-hourly. |

Mid-window tweaks pending decision (not yet coded — see STATUS.md):
* If template finishes a full cycle during the push window, shift mainspace to **1500** and keep category/misc at 10.
* Once mainspace is fully imported, drop everything to uniform 500 (matches the outer catchup baseline early).

**What landed today, roughly in causal order:**

1. **Misc orchestrator scope**: restricted to subject-side namespaces (2/4/6/8/12/420/828/860/862); talk namespaces (odd-numbered) excluded. `history_offload` extended to cover non-wikitext namespaces (Module/GeoJson/Item/Property) with banner suppression — Lua and JSON content get archived + delete + recreate without a `<!-- History offloaded -->` comment that would corrupt the content model.
2. **Git-synced sync split out of wiki-cleanup**: now its own `git-synced-sync.yml` reusable workflow, invoked from cleanup-loop independently of the catch-up gate. `git_synced/` ↔ wiki mirror keeps moving even while the broader legacy cleanup is paused.
3. **Template orchestrator state push — fixed (the big one)**: zero state commits had ever landed on origin for the template orchestrator. Root cause: each orchestrator job used `actions/checkout@v4` without an explicit ref, so it checked out the push SHA instead of tip-of-main. When the 2nd / 3rd / 4th orchestrator committed `duplicate_qids.state`, rebase onto origin hit `add/add` conflict because their local version didn't include the 1st orchestrator's commit. `commit_state.sh` bails on rebase conflicts, so all downstream state was lost. Fix: `ref: ${{ github.ref_name }}` on the checkout across all four orchestrator workflows. Template state now lands.
4. **Offloading-priority scheduling**: new `DEFER_IF_PRIOR_MODIFIED` op flag. `template_mainspace_usage` opts in — when `history_offload` modifies a template in the same visit, categorization defers to the next cycle. Edit budget goes to offloading first; categorization fills in on pages that already offloaded.
5. **State-growth cap + apfrom resume**: `MAX_STATE_GROWTH_PER_RUN = 1000` bounds any single run at ~1000 page-visits, preventing multi-hour no-op walks. `iter_allpages` now accepts `start_from` (MediaWiki `apfrom`) so a run with 10k prior titles in state doesn't enumerate the already-done prefix just to discard via `done` set lookup.
6. **Template state seeded**: fetched all 805 templates from Template:! through Template:Company-stub via Special:AllPages and wrote them into `template_orchestrator.state`. Cycle-scoped — they come back into rotation on the next cycle clear.
7. **Fandom mirror is now best-effort**: retries once (so 2 attempts per page); on both fail, logs "giving up, proceeding via GitHub archive" and continues. The GitHub XML archive is the authoritative backup. Fandom outages no longer stall the offload queue.
8. **Fandom failure diagnostics**: the opaque `Expecting value: line 1 column 1 (char 0)` JSONDecodeError now includes HTTP status code and the first 200 chars of the response body, so the next 429 / 403 / 503 / login-redirect case is distinguishable at a glance.
9. **wikidata_link template namespace fix**: on templates, uses `[[Category:Templates missing wikidata]]` placed inside `<noinclude>` (not the generic mainspace category at top level, which was cascading through transclusion into every page using the template). Strips stray generic tags left over from prior runs.
10. **git-synced conflict policy changed**: repo is now the source of truth. Both-sides-changed conflicts resolve by pushing local → wiki with an audit summary. The previous "skip on conflict" behaviour was indefinitely blocking repo edits behind any concurrent wiki edit.
11. **Archive-push edit-limit window wired up**: `window-gate` now emits per-orchestrator edit-limit outputs computed from today's date, implementing the timeline in the table above.
12. **Force-cancel documented**: added CLAUDE.md note that `POST .../actions/runs/{id}/force-cancel` is the right escalation for runs where standard `gh run cancel` doesn't propagate within ~1 minute (the regular cancel is cooperative; the runner only notices between steps, and an orchestrator mid-walk with 2.5s throttles between saves may not respond for minutes).

---

### Orchestrator walks: apfrom resume + 1000-append state-growth cap per run
**Scripts:** `shinto_miraheze/orchestrators/common.py`
**Status:** Complete

Two perf/safety knobs added to `run_orchestrator`:

* **Server-side walk resume via `apfrom`.** `iter_allpages` now accepts a `start_from` arg (maps to MediaWiki's `apfrom`). Before the loop, `run_orchestrator` computes the alphabetically-max title in the current namespace's state entries (strips the namespace prefix; misc's mixed-namespace state is handled by prefix-filtering first). That value is passed as `apfrom`, so a run with 10,000 prior titles in state doesn't pay 20 allpages API batches just to discard each title via the in-memory `done` lookup — it starts at the right position directly.

* **`MAX_STATE_GROWTH_PER_RUN = 1000` cap.** Each run can append at most 1,000 titles to state before breaking with `finished_all=False`. Without this cap, a run where every visited page is a no-op (nothing to edit, but each visit still appends to state) would walk the entire namespace — potentially 20,000+ pages — in a single CI run, taking hours. The cap bounds one run at roughly "fetch 1,000 pages worth of content" and lets the next scheduled run pick up where this one left off. All in-loop `append_state(path, title)` calls now go through a `_mark_done` helper that bumps a counter, so the cap applies uniformly across outcomes (edited / no-op / error / interwiki skip / page-missing).

Combined with the earlier checkout + push-priority fixes, these two make per-run work visible, bounded, and auto-resuming across the full lifecycle of a cycle.

### Template orchestrator state never landed — checkout SHA stale + rebase bails on add/add
**Scripts:** `.github/workflows/{mainspace,category,template,miscellaneous}-orchestrator.yml`
**Status:** Fixed

Symptom: zero `chore(state): update state after Template Orchestrator` commits had ever landed on origin, while mainspace / category / miscellaneous had each landed several. Noticed because the template walk seemed to "restart" every run instead of resuming mid-walk.

Root cause: each orchestrator job in the cleanup-loop chain does its own `actions/checkout@v4`, and the default ref is the SHA that triggered the workflow — NOT the current tip of `main`. So the sequence is:
1. Cleanup-loop triggers at push SHA X (no `duplicate_qids.state` yet).
2. Mainspace checks out X, walks ns=0, creates fresh `duplicate_qids.state` + `mainspace_orchestrator.state`, commits, rebases cleanly onto origin (which is still X), pushes. Origin is now Y.
3. Category checks out X (not Y!), walks ns=14, **also creates a fresh `duplicate_qids.state`** (because it didn't see mainspace's commit), commits, rebases onto Y → `CONFLICT (add/add)` on `duplicate_qids.state` because both sides added the file from scratch. `commit_state.sh`'s rebase step aborts with `WARN: rebase failed; aborting. State will retry next run.` State for this orchestrator is lost.
4. Template has the same problem.

For category and misc the conflict sometimes resolved into a normal modify/modify and rebase survived, but for template it consistently failed. Template's state had literally never reached origin.

Fix: set `ref: ${{ github.ref_name }}` on `actions/checkout@v4` in all four orchestrator workflows, so each job checks out the tip of `main` at job-start and sees state commits from earlier orchestrator jobs in the same run. `duplicate_qids.state` is then a modify/modify edge for later orchestrators (each one appends its own titles to the existing dict), which git can auto-merge.

The underlying fragility in `commit_state.sh` (rebase-abort-on-first-failure, no handler for add/add on a JSON file) remains — flagged in `todo.md` — but the checkout fix removes the common path that triggers it.

### Template orchestrator: offloading-priority scheduling via `DEFER_IF_PRIOR_MODIFIED`
**Scripts:** `shinto_miraheze/orchestrators/common.py`, `shinto_miraheze/orchestrators/ops/template_mainspace_usage.py`
**Status:** Complete

With the new `template_mainspace_usage` heavy op added to the template orchestrator, each visited template could generate up to three edits per visit (history_offload save + template_mainspace_usage save + combined light-op save), burning `--max-edits 100` across ~33 pages instead of the prior ~50. Offloading (the higher-priority work) was getting throttled by categorization on the same page.

Added an opt-in per-op flag `DEFER_IF_PRIOR_MODIFIED = True`. In `common.run_orchestrator`'s heavy-op pre-pass, if an earlier heavy op modified the page in this visit, subsequent heavy ops with this flag set are skipped (printed as `deferred (prior heavy op modified this page)`). Only `template_mainspace_usage` sets the flag.

Effect: `history_offload` always gets first crack at the edit budget. `template_mainspace_usage` runs only on pages where `history_offload` was a no-op (already offloaded in a prior cycle, single-revision-so-skip, etc.) — so categorization fills in opportunistically as the offload backlog drains, without stealing budget from in-progress offload work.

### Template orchestrator: tag every template as transcluded-in-mainspace or not
**Scripts:** `shinto_miraheze/orchestrators/ops/template_mainspace_usage.py`, `shinto_miraheze/orchestrators/template_orchestrator.py`, `.github/workflows/template-orchestrator.yml`, `.github/workflows/cleanup-loop.yml`
**Status:** Complete (shipping in off state pending first observed run; enabled via `enable_template_usage_check: true` in cleanup-loop)

A very large fraction of Template-namespace pages were accidentally imported via the wanted-templates import pipeline and aren't actually used in any mainspace article — e.g. `Template:Coast guard`, which is transcluded only from non-mainspace pages and from other templates. We need to surface that set so we can review and prune it.

The new `template_mainspace_usage` op partitions every template into exactly one of two complementary maintenance categories, placed inside the template's `<noinclude>` block:
* `[[Category:Templates transcluded in mainspace]]` — at least one `prop=transcludedin&tinamespace=0` hit
* `[[Category:Templates not transcluded in mainspace]]` — zero hits

Heavy op (one API call per visited template via `tilimit=1`, so we detect "is there any mainspace use at all" without paging a full list). Self-correcting — when a template gains or loses its first mainspace transclusion, the tags swap on the next sweep. Env-gated by `ENABLE_TEMPLATE_USAGE_CHECK=1` so it can sit in the OPS list without acting until explicitly enabled; `cleanup-loop.yml` passes `enable_template_usage_check: true` to the template orchestrator.

Intent is to use the two categories as filter input for a later review/deletion workflow. Running it on every sweep keeps the partition fresh as mainspace content evolves.

---

## 2026-04-23

### Orchestrator state was silently never landing on origin — fixed with a push-retry loop
**Scripts:** `shinto_miraheze/commit_state.sh`
**Status:** Fixed

`commit_state.sh` was `git pull --rebase ... 2>/dev/null || true` followed by a single `git push`, and on rejection only printed a warning. Concurrent pushes from other workflow jobs in the same cleanup cycle consistently won the race, so `category_orchestrator.state`, `template_orchestrator.state`, `misc_orchestrator.state`, and the load-bearing shared `duplicate_qids.state` were being committed on the runner, push-rejected, and destroyed when the runner tore down. Only one `mainspace_orchestrator.state` commit (`9d4d5b6`) ever actually reached origin across many weeks.

Why nothing obviously broke: every orchestrator op is wiki-idempotent (each op detects the target state on the wiki itself and returns `(None, None)` if nothing needs to change), so a run without state still produced correct edits — it just wasted time re-reading already-processed pages to reach 100 pages that actually needed work. The first visible symptom was the `[[Duplicate page QIDs]]` report being perpetually out of date because `duplicate_qids.state` never persisted long enough for `find_duplicate_page_qids.py` to see it.

The fix replaces the silent-failure pattern with a fetch + rebase + push retry loop (up to 6 attempts, exponential backoff). First run under the fix landed `category_orchestrator.state`, `misc_orchestrator.state`, and the first-ever `duplicate_qids.state` commit.

### Migration-criterion correction — 3 "Deprecated:" scripts ported to ops; 8 cruft state files removed
**Scripts:** `shinto_miraheze/orchestrators/ops/{normalize_category_page,remove_legacy_cat_templates,shikinaisha_talk}.py`, `.github/workflows/wiki-cleanup.yml`
**Status:** Complete

Audit of the legacy `shinto_miraheze/*.state` files surfaced the real reason the orchestrator migration felt incomplete: the prior criterion ("port if the script finishes / drains its state") let per-page sweeps linger in legacy form as long as their state files were still growing. The correct criterion is structural, not behavioural: **port if the script is a per-page namespace sweep**; keep in legacy only if it's SPARQL-driven, a single-page write, a bidirectional repo↔wiki sync, or input-queue driven. This is now in `CLAUDE.md`.

Ported (previously `Deprecated:` steps in wiki-cleanup.yml, running Sunday or first-of-month):
* `normalize_category_pages` → `ops/normalize_category_page.py` (ns=14)
* `remove_legacy_cat_templates` → `ops/remove_legacy_cat_templates.py` (ns=14; runs before the normalizer so stripped templates don't re-appear in the normalized output)
* `tag_shikinaisha_talk_pages` → `ops/shikinaisha_talk.py` (ns=0, heavy op — edits the corresponding talk page when the visited mainspace page carries `[[Category:Wikidata generated shikinaisha pages]]`)

Removed 8 cruft state files (scripts disabled, ported, or fully abandoned; state files were dead weight): `migrate_talk_pages_jax.state`, `reimport_from_enwiki.state`, `tag_pages_without_wikidata.state`, `tag_deleted_qids_in_ill.state`, `strip_translated_char_count_cats.state`, `migrate_talk_pages.state`, `fix_template_noinclude.state`, `generate_p11250_quickstatements.state` (the last was an orphan from an older version of the script — the current renderer reads `orchestrators/duplicate_qids.state`).

Also removed `sync_main_page.py` + `sync_main_page.state` + `Main Page.wiki` (root). Main Page can sync via `sync_git_synced_pages.py` once `[[Category:Git synced pages]]` is added to the wiki's Main Page (one-time wiki edit).

### Misc orchestrator: share budget across sweep, combine state files, add push retry
**Scripts:** `shinto_miraheze/orchestrators/miscellaneous_orchestrator.py`, `orchestrators/common.py`
**Status:** Complete

The misc orchestrator took ~2h per cleanup cycle while the three main orchestrators each took ~11 min. Cause: `--max-edits 100` was being applied *per namespace* in a loop over 17 namespaces (effective cap ~1700 edits), and each namespace did its own full `allpages` walk with separate state files. Now a single shared `misc_orchestrator.state` tracks titles across the sweep, a `misc_orchestrator_cursor.state` records which namespace to resume, and the edit budget is shared across the whole sweep — so most runs hit only one namespace and cycle through to the next when that namespace is exhausted. `common.run_orchestrator` now returns `(edited, exhausted)` and accepts `clear_on_exhaust=False` so the misc orchestrator can own its own state clearing across the 17-namespace cycle.

Also fixed: the misc workflow step `Render: find_duplicate_page_qids` was failing with `run_step.sh: Permission denied` (exit 126) because the workflow only `chmod +x`'d `commit_state.sh`. Marked `run_step.sh` and `commit_state.sh` both executable in the git index (`git update-index --chmod=+x`) so every future checkout lands with the bit set.

### Merge legacy `tag_untranslated_japanese.state` into mainspace orchestrator state
**Scripts:** `shinto_miraheze/orchestrators/mainspace_orchestrator.state`
**Status:** Complete

`untranslated_japanese` was ported to `ops/untranslated_japanese.py` earlier but the standalone script's state file (`shinto_miraheze/tag_untranslated_japanese.state`, 18,556 lines / 14,620 unique titles) was left in the repo. Merged those titles into `orchestrators/mainspace_orchestrator.state` (12,909 new) and deleted the legacy file. The standalone script is still used by wiki-cleanup's `--category` rebucket mode but no longer owns a separate cycle state.

---

## 2026-04-18

### Server-load reduction effort
**Status:** Policy in force

Miraheze has raised server-load concerns. Actions taken:

* **Inter-edit throttle bumped from 1.5s to 2.5s** across all 43 scripts in `shinto_miraheze/` that write to `shinto.miraheze.org`. Sustained edit rate drops from ~40/min to ~24/min. Single constant `THROTTLE = 2.5`; reference enshrined in `status.md` pinned notes and the `EmmaBot` user page.
* **`--max-edits` caps stay where they are** — all long-walking scripts are already stateful and resume from state, so Miraheze is not paying for repeat namespace scans.
* **No new full-namespace walks** without a state file and a justification. Anything new added to `wiki-cleanup.yml` has to answer to this constraint.
* **Bail-on-429** for Wikidata/SPARQL (policy 2026-03-28) remains in force; the narrow exponential-backoff exception for QS generators (2026-03-29) also remains.

`todo.md` carries a "Server load" section; `EmmaBot.wiki` now documents the rate-limiting stance publicly so editors see the intent.

### Queue-style `status.md` adopted (Sutra-pattern)
**Status:** Complete

Replaced the ad-hoc `status.md` with a queue-style file modeled on `EmmaLeonhart/Sutra`'s `STATUS.md`: items have concrete context, and when finished they are deleted rather than checkmarked. Purpose is to bound session scope and curb scope creep. The long-horizon backlog stays in `todo.md`; `status.md` is strictly the active queue.

### `need_translation/` repair after a bad category strip
**Status:** Complete

An earlier batch edit in this session stripped `[[Category:Need translation]]` from ~140 files by ASCII-filename heuristic. That heuristic was wrong — most of those files had an auto-generated English top section but a full Japanese body under `== Japanese Wikipedia content ==`, and removing the category is destructive because `sync_need_translation.py` deletes the local file on the next CI sync when the wiki page loses the category. Recovery:
- Reverted the 83 files that still had the `== Japanese Wikipedia content ==` heading; prepended `[[Category:Pages with duplicated content]]` + `[[Category:Need translation]]` before the heading (commit `e02003d`).
- Re-added `[[Category:Need translation]]` to 15 files with 200–18k CJK characters inline but no heading (commit `bc39c53`).
- Appended `[[Category:Need translation]]` unconditionally across all 304 files in the directory to guarantee the repo version is newer than the wiki version on next sync — duplicate category tags are harmless on MediaWiki render (commit `41b3e90`).
- Tagged 13 fully-English pages with `[[Category:Translated pages]]` (commit `1a58022`).
- Added minimal stub content to 6 essentially-empty pages (Ancestor worship, Anrakugawa River (Mie), Engishiki funding categories, three Jawiki resolution tracking pages).

No files were lost — `git log --diff-filter=D -- need_translation/` confirms CI had not run between the bad commit and the reverts.

Lessons captured in `.claude/.../memory/feedback_judgment_shortcuts.md` and `project_need_translation_ci_sync.md`.

---

## 2026-04-04

### Fix GitHub Pages reverting to weeks-old content on pipeline failures
**Workflows:** `generate-pages.yml`, `generate-quickstatements.yml`
**Status:** Complete

**The bug:** When `generate-quickstatements` failed (usually SPARQL timeouts), no artifact was uploaded. The `generate-pages` workflow would then fall back to *regenerating everything from SPARQL*, which also tended to time out (10-minute limit). When that fallback also failed, no pages deployed — but when it *partially* succeeded, it deployed with incomplete data. Either way the site got stuck showing whatever last succeeded, which could be weeks old.

The subtle part: `_site/` was in `.gitignore`, so the repo never had a copy of the built pages. Every deployment had to generate them from scratch. If SPARQL was having a bad day (which was frequent — the pipeline makes 20+ queries), the pages simply couldn't be built at all.

**The fix (three parts):**
1. **Committed `_site/` to the repo** after running all generators locally. Removed `_site/` from `.gitignore`. The repo now always has a known-good copy of every page.
2. **CI commits `_site/` after each successful build.** Both `generate-quickstatements.yml` (commits generated `.txt` files, only non-empty ones so partial failures don't overwrite good data) and `generate-pages.yml` (commits the built `_site/`) push back to the repo with `[skip ci]`.
3. **Replaced the SPARQL fallback with the committed repo files.** When the artifact isn't available, `generate-pages` now just uses whatever's already checked out — no more re-querying SPARQL. Timeout increased from 10 to 30 minutes as a safety margin.

The net effect: pages can never go stale. Worst case, a failed run leaves the previously-committed version in place. Each successful run (even partial) ratchets forward.

### Add Shikinaisha removal from Shikinai Ronsha items
**Script:** `generate_modern_shrine_ranking_qualifiers.py`
**Status:** Complete

New generator: removes P31=Q134917286 (Shikinaisha) from items that have P31=Q135022904 (Shikinai Ronsha). Shikinai Ronsha is more specific and replaces the generic Shikinaisha class. Found 2,329 items needing cleanup. Output: `remove_shikinaisha.txt`, added to both `submit_daily_batch.py` and `direct_daily_edits.py`.

### Include P11250 Miraheze article ID in daily operations page
**Script:** `generate_modern_shrine_ranking_qualifiers.py`
**Status:** Complete

P11250 lines were being submitted via the daily batch but weren't shown on the HTML dashboard or daily operations page. Now included in both, with a dedicated section on the shrine ranking dashboard. Also moved the `fetch_p11250_from_wiki.py` step to run before the main generator in the workflow so the file exists when the HTML is built.

### Fix migration progress bar showing 100% with thousands of lines remaining
**Script:** `generate_modern_shrine_ranking_qualifiers.py`
**Status:** Complete

The Engishiki ranking migration showed "100% complete" while still generating 4,359 add lines. Root cause: the `total` SPARQL query counts old P31 statements still present, but as migration progresses and old P31 values get removed, `total` shrinks below `remaining`. This gave `completed = total - remaining = -931`, which the progress bar clamped to 100%. Fixed by using `corrected_total = max(total - remaining, 0) + remaining` so the bar always reflects actual work remaining.

---

## 2026-03-29

### Re-add retry with exponential backoff for SPARQL 429s
**Scripts:** `generate_modern_shrine_ranking_qualifiers.py`, `generate_p958_qualifiers.py`
**Status:** Complete

The bail-immediately-on-429 policy (2026-03-28) turned out to be too aggressive for the QS generators. The `generate-quickstatements` job makes 20+ SPARQL queries across all phases/migrations; by the Ritsuryō migration phase, the endpoint reliably returns 429. A single transient 429 would kill the entire pipeline.

Reverted these two scripts to retry with exponential backoff (30/60/120/240s waits, 4 retries max) and increased the base throttle from 5s to 10s between SPARQL requests. `test_wikidata_qualifier.py` still bails immediately on 429 since it hits the Wikidata API (not SPARQL) and retrying API writes is riskier.

The fix (355582e) hasn't been tested in CI yet — the run that used it (23704115295) was cancelled before reaching the SPARQL-heavy phases. The prior failure (23703150061) ran on the pre-fix commit.

### Fix stale artifact in pages build
**Workflow:** `generate-pages.yml`
**Status:** Complete

The pages build was downloading a stale artifact from the generate job instead of regenerating QS files fresh. Fixed to always regenerate in the pages build step.

---

## 2026-03-28

### Stop submit-quickstatements from regenerating SPARQL queries
The submit job was re-running all SPARQL generators (22+ queries) even though the generate job already produced the `.txt` files. This doubled SPARQL load and caused a `ReadTimeout` on the second run. Fixed by uploading generated files as artifacts from the generate job and downloading them in the submit job. No more redundant SPARQL queries.

### Submit P11250 QuickStatements via daily batch
**Script:** `fetch_p11250_from_wiki.py`
**Status:** Complete

P11250 (Miraheze article ID) QuickStatements were previously only written to a wiki page (`QuickStatements/P11250`) but never submitted automatically. Added `fetch_p11250_from_wiki.py` which reads the wiki page (public, no auth) and writes a local `p11250_miraheze_links.txt` for `submit_daily_batch.py` to pick up. Added to both the pre-flight generation and submission workflows.

### Bail-on-429 for all Wikidata scripts
**Scripts:** `test_wikidata_qualifier.py`, `generate_p958_qualifiers.py`, `generate_modern_shrine_ranking_qualifiers.py`
**Status:** Complete

We've been seeing 429 Too Many Requests from Wikidata. The root cause is unclear — may be cumulative load from multiple scripts hitting the SPARQL endpoint and Wikidata API in the same pipeline run, or external factors.

Previously, `generate_p958_qualifiers.py` and `generate_modern_shrine_ranking_qualifiers.py` would retry on 429 with backoff (30-90s waits), and `test_wikidata_qualifier.py` had **no** 429 handling at all. Retrying 429s can worsen rate-limit situations.

Changed all three scripts to match the `generate_p11250_quickstatements.py` pattern: on any 429, raise `RateLimitError` and terminate immediately. This lets us see the failure cleanly in CI logs and do diagnostics, rather than burning through retry budgets and potentially deepening the rate limit.

Wikidata chunk steps are already at 50 edits/run and paused until May, so the main exposure is `test_wikidata_qualifier.py` (100 direct API edits) and the QS generators (`generate_p958_qualifiers.py`, `generate_modern_shrine_ranking_qualifiers.py`) which query SPARQL.

---

## 2026-03-26

### Increase Wikidata step edit limits to 300
**Workflow:** `wiki-cleanup.yml`
**Status:** Complete

Raised the per-run edit limit for all four Wikidata steps from 100 to 300: `generate_p11250_quickstatements`, `clean_p11250_quickstatements`, `tag_pages_without_wikidata`, and `clean_wikidata_cat_redirects`. The global `WIKI_EDIT_LIMIT` (used by all other steps) remains at 100. This speeds up Wikidata convergence without increasing load on the wiki itself.

### Regenerate P459 missing qualifier quickstatements
**File:** `p459_missing_qualifiers.txt`
**Status:** Complete

Regenerated the P459 qualifier quickstatements from a live SPARQL query. Down to 244 remaining unqualified P13723 statements (from 382 when the file was first created on 2026-03-25).

### Fix case-sensitive TODO.md path for Linux CI
**Script:** `update_bot_userpage_status.py`
**Status:** Complete

The bookkeeping step was failing on CI (Linux) because the script defaulted to `TODO.md` but git tracks the file as `todo.md`. Windows is case-insensitive so this worked locally but broke in CI. Fixed the default path to match what git tracks.

---

## 2026-03-22

### TEMPORARY: Create shrine ranking article pages
**Script:** `create_shrine_ranking_pages.py`
**Status:** Added to workflow — remove after all pages are created

Creates article pages for all 21 subcategories of [[Category:Shrine rankings needing pages]] that don't already have articles. Uses the Gō-sha page as a template.

- 5 articles already exist: Gō-sha, Myōjin Taisha, Shikinai Shōsha, Shikinai Taisha, Son-sha
- 16 articles to create across three types:
  - **Modern system ranks** (Bekkaku Kanpeisha, Kanpei Taisha/Chūsha/Shōsha, Kokuhei Taisha/Chūsha/Shōsha, Fu-sha, Ken-sha, Fuken-sha, Unranked shrines)
  - **Engishiki offering classifications** (Hoe and Quiver, Hoe offering, Quiver offering, Tsukinami-sai+Niiname-sai, Tsukinami-sai+Niiname-sai+Ainame-sai)
- For categories with a `{{wikidata link}}`, queries Wikidata P301 (category's main topic) to get the article's QID
- 9 of 21 categories have Wikidata links; the other 12 get articles without wikidata
- Each article gets: nihongo template (where applicable), system link, See Also with category link, wikidata link (if available), and [[Category:Shrine rankings]]

**To remove after completion:** Delete the workflow step marked `(TEMPORARY)` in `cleanup-loop.yml` and optionally delete the script.

### Triage single-member categories from Secondary category triage
**Script:** `triage_secondary_single_member.py`
**Status:** Added to workflow

Walks [[Category:Secondary category triage]] and moves categories that have exactly one member into [[Category:Triaged categories with only one member]]. Early-exits member counting after 2 to avoid scanning large categories unnecessarily.

---

## 2026-03-21

### Extended untranslated Japanese character thresholds + translation pipeline plan
**Script:** `tag_untranslated_japanese.py`
**Status:** Thresholds updated; translation pipeline planned

The bucketed thresholds for tagging untranslated Japanese content previously capped at 300+, meaning pages with 500, 1000, or even 5000+ untranslated characters were all lumped into the same "300+" bucket. Extended the thresholds to: 50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000.

**Next steps (blocked on pipeline cycle completing):**
1. Let the tagging script run through the pipeline to re-bucket pages with the new thresholds
2. Triage pages starting from [[Category:Secondary category triage]] and the highest untranslated character buckets (300+, 500+, etc.)
3. Run an AI translation agent against the heavily-untranslated pages to properly translate them
4. Feed translated pages back through the pipeline for re-categorization

Added `--category` flag to `tag_untranslated_japanese.py` so it can target a specific category's members instead of walking all mainspace pages. This enables quick re-bucketing runs like:
```
python tag_untranslated_japanese.py --category "Pages with 300+ untranslated japanese characters" --apply --run-tag "..."
```
Category mode ignores the state file (always processes all members) and doesn't clear state on completion, so it won't interfere with the normal full-scan pipeline runs.

The goal is to identify the pages with the most untranslated Japanese content, translate them, and then verify via re-tagging that the translations stuck. Pages in the 300+ range and above are the priority targets since they represent substantially untranslated articles rather than minor leftover fragments.

---

## 2026-03-16

### Workflow reliability: chunked state commits and bounded runtime
**Scripts:** `cleanup_loop.sh`, `.github/workflows/cleanup-loop.yml`, `tag_pages_without_wikidata.py`
**Status:** Complete

The pipeline was failing and losing all state progress because it only committed state files once at the very end. If any script crashed midway (which was happening due to 502s and timeouts — see 2026-03-15 entry), every earlier script's state progress was thrown away.

**Chunked state commits:** The workflow now commits state/log/error files after each logical chunk instead of once at the end. Six commit points:
1. Import & Categorization
2. Structural Fixes
3. Wikidata
4. Final Core
5. Cleanup Loop
6. Deprecated (weekly)

A `commit_state()` helper in `cleanup_loop.sh` handles this — finds all `*.state`, `*.log`, `*.errors` files, stages them with `git add -f`, and commits if there are changes. Git config is now set up before the cleanup loop runs (moved out of the final push step). The final workflow step is now a fallback commit + push for anything the chunks missed.

**Bounded runtime for tag_pages_without_wikidata:** Previously `--max-edits 100` counted only pages that were actually *tagged*, meaning the script could scan thousands of pages (each with an API call) just to find 100 that needed tagging. Most pages already have `{{wikidata link}}`, so the hit rate was low and the runtime was unbounded. Changed to count pages *checked* instead of pages *edited*, so the script now stops after examining 100 pages regardless of how many needed tagging. This keeps the runtime predictable and prevents the pipeline from timing out on this single script.

Also fixed `.gitignore` which was blocking `*.log` files from being committed (the state commit step needs to track these), and added `Help:Link color` to `erroneous_transclusion_pages.txt` for reimport.

---

## 2026-03-15

### Pipeline failures: 3 consecutive CI failures diagnosed and fixed
**Script:** `shinto_miraheze/generate_p11250_quickstatements.py`, `.github/workflows/cleanup-loop.yml`
**Status:** Fixed

The pipeline failed 3 times in a row between 2026-03-14 and 2026-03-15. Root causes:

1. **Run 23081580192 (Mar 14, 05:40):** `git push` rejected — the remote had newer state file commits that the runner didn't have locally. The workflow was doing `git push` without pulling first, so when two runs produced state commits close together, the second one failed.

2. **Run 23081942775 (Mar 14, 06:02):** `502 Bad Gateway` from `shinto.miraheze.org` during recursive category traversal. The script was deep inside `get_category_pages_recursive` fetching subcategories of `天白区の歴史` (history of Tenpaku ward) when the Miraheze server returned a 502. No retry logic existed, so the entire run crashed.

3. **Run 23100572874 (Mar 15, 01:24):** `ReadTimeoutError` — same recursive category traversal, this time the server took longer than 15 seconds to respond. Again, no retry logic, immediate crash.

**Fixes applied:**

- Added `requests.Session` with automatic retry (5 retries, exponential backoff) for 500/502/503/504 errors. Timeout increased from 15s to 30s.
- Added `git pull --rebase` before `git push` in the workflow to handle state file divergence.
- 429 (Too Many Requests) is deliberately **not** retried — it triggers immediate termination with a FATAL log entry to avoid worsening rate-limit situations.
- Added `error.log` file (`shinto_miraheze/error.log`) where all errors are logged with timestamps and severity. The workflow now commits log files alongside state files, and runs the commit step with `if: always()` so logs are preserved even on failure.
- Added `*.log` to `paths-ignore` in the push trigger to avoid re-triggering the pipeline from log commits.

### ⚠️ Open concern: recursive category traversal depth
**Script:** `shinto_miraheze/generate_p11250_quickstatements.py`
**Status:** Under review

The `get_category_pages_recursive` function traverses the full subcategory tree of `[[Category:Pages linked to Wikidata]]` with no depth limit. The stack traces from the failures showed 12+ levels of recursion, reaching into deeply nested Japanese geographic/historical categories like `天白区の歴史`.

This is potentially problematic because:
- **No depth limit:** The recursion goes as deep as the category tree allows. A single deeply-nested branch can generate dozens of sequential API calls before returning.
- **No throttling on category API calls:** The script sleeps 0.3s between Wikidata checks in the main loop, but the category traversal itself makes rapid-fire requests with zero delay between them.
- **Multiplicative API load:** Each category level spawns N subcategory fetches, each of which spawns N more. A category tree 12+ levels deep with branching at each level means hundreds of API calls just to build the page list.
- **The function was part of the original script design** (commit 9d75771, 2026-03-13) — it was not added later. But the category tree has likely grown since then.

The retry logic added above makes the script more resilient to individual request failures, but does not address the underlying load pattern. If the category tree continues to grow, this could become a recurring source of 502s and timeouts — or worse, trigger rate limiting.

Possible mitigations (not yet implemented):
- Add a `max_depth` parameter to cap recursion depth
- Add throttling (e.g. `time.sleep(0.5)`) between category API calls
- Cache the page list between runs instead of rebuilding it from scratch every time
- Switch to a flat category member query if deep subcategories aren't actually needed for P11250 coverage

---

## 2026-03-13

### Orphaned talk page deletion added to cleanup loop
**Script:** `shinto_miraheze/delete_orphaned_talk_pages.py`
**Status:** Complete (pipeline integration)

Added `delete_orphaned_talk_pages.py` to the cleanup loop. Queries `Special:OrphanedTalkPages` via the querypage API and deletes talk pages whose corresponding subject page does not exist. 500+ orphaned talk pages identified at time of addition. Runs after `delete_unused_categories.py` and before `remove_crud_categories.py`.

### Enwiki XML reimport workflow automated
**Script:** `shinto_miraheze/reimport_from_enwiki.py`
**Status:** Complete (pipeline integration, bug fixed)

Automated the long-standing manual workflow of reimporting pages from enwiki to fix erroneous transclusions. The script:
1. Reads page titles from `erroneous_transclusion_pages.txt` (129 pages extracted from `[[Category:Erroneous transclusions of X]]` categories)
2. Downloads XML via enwiki `Special:Export` with `templates=1` and `curonly=1` (pulls full dependency tree)
3. Replaces `timestamp` with `timestam` in the XML to force overwrite regardless of local revision age
4. Imports into shintowiki via `action=import` with `interwikiprefix=en`

Processes 1 page per pipeline run (low priority, high cost operation). Runs as the first step of the Core Loop. Auto-retries non-namespaced titles with `Template:` prefix (e.g., "Country data X" → "Template:Country data X").

**Bug fix:** First pipeline run failed on all 129 pages — MediaWiki requires the `interwikiprefix` parameter for XML imports. Also fixed the loop to count attempts (not just successes) against `--max-imports` so it stops after 1 attempt per run.

**Historical context:** This workflow was originally performed manually and was one of the most important maintenance operations. Shintowiki was built by mass-importing templates/modules from enwiki. Categories were manually added to imported pages because of a Miraheze indexing quirk (imported pages had non-functioning categories until one was added manually). This caused crud categories to leak onto templates, modules, and structural pages, breaking template dependency chains in hard-to-diagnose ways. The indexing quirk has since been fixed on Miraheze, but the damage remains and needs cleanup.

### Secondary category triage added to core loop
**Script:** `shinto_miraheze/triage_emmabot_categories_secondary.py`
**Status:** Complete (pipeline integration)

Added `triage_emmabot_categories_secondary.py` as a third pass in the category triage pipeline, after the enwiki and jawiki passes. Handles remaining categories in `[[Category:EmmaBot categories without enwiki or jawiki match]]` using additional heuristics.

---

## 2026-03-12

### Uncategorized category fixer added to core loop
**Script:** `shinto_miraheze/categorize_uncategorized_categories.py`
**Status:** Complete (pipeline integration)

Added `categorize_uncategorized_categories.py` to the core loop. Fetches `Special:UncategorizedCategories` via the querypage API and appends `[[Category:Categories autocreated by EmmaBot]]` to each page that has no category membership.

Many category pages were created in earlier bulk workflows (consolidation, QID redirects, etc.) without any categorization. This retroactively fixes that by bringing them under the `Categories autocreated by EmmaBot` umbrella — the same category used by `create_wanted_categories.py` for newly created stubs.

### Erroneous QID category link fixes completed
**Script:** `shinto_miraheze/fix_erroneous_qid_category_links.py`
**Status:** Complete (task finished)

`Category:Erroneous qid category links` has been fully cleared. Removed from the active tasks list on `User:EmmaBot`.

### EmmaBot category triage script added to core loop
**Script:** `shinto_miraheze/triage_emmabot_categories.py`
**Status:** Complete (pipeline integration)

Added `triage_emmabot_categories.py` to the core loop. Processes up to 100 subcategories of `[[Category:Categories autocreated by EmmaBot]]` per run:
- Batch-checks English Wikipedia for a category with the same name
- If enwiki match exists: recategorizes to `[[Category:Emmabot categories with enwiki]]`
- If no match: recategorizes to `[[Category:Emmabot categories without enwiki]]`
- Removes the original `[[Category:Categories autocreated by EmmaBot]]` tag in both cases

This is the first step in a larger normalization pipeline for the many categories that were bulk-created in earlier workflows without proper documentation or categorization.

### Per-script stage declarations on User:EmmaBot
**Scripts:** `shinto_miraheze/cleanup_loop.sh`, `shinto_miraheze/update_bot_userpage_status.py`
**Status:** Complete

Added `--stage` flag to `update_bot_userpage_status.py`. When used alone (without `--status`), it performs a lightweight in-place edit of the status block on `User:EmmaBot` to update only the "Current stage" line — no full page rebuild from template.

The cleanup loop now calls `declare_stage` before every script invocation, so `User:EmmaBot` always shows exactly which script is currently running (e.g. "Core Loop: create_wanted_categories", "Cleanup Loop: migrate_talk_pages"). This makes it trivial to identify where the pipeline stalls.

### Uncategorized category fixer added to core loop
**Script:** `shinto_miraheze/categorize_uncategorized_categories.py`
**Status:** Complete (pipeline integration)

Added `categorize_uncategorized_categories.py` to the core loop. Fetches `Special:UncategorizedCategories` via the querypage API and appends `[[Category:Categories autocreated by EmmaBot]]` to each page that has no category membership. Many category pages were created in earlier bulk workflows without proper categorization — this retroactively fixes them under the same umbrella category used by `create_wanted_categories.py`.

### Run tag interwiki prefix fixed
**Script:** `shinto_miraheze/cleanup_loop.sh`
**Status:** Complete

Changed edit summary run tags from `[[git:...]]` to `[[github:...]]` to match the wiki's actual interwiki prefix configuration.

### Cleanup loop restructured into Core Loop + Cleanup Loop
**Scripts/Workflow:** `shinto_miraheze/cleanup_loop.sh`, `shinto_miraheze/create_wanted_categories.py`, `shinto_miraheze/update_bot_userpage_status.py`
**Status:** Complete

Restructured the flat cleanup loop into clearly separated phases with echo banners:

1. **Bookkeeping: START** — `update_bot_userpage_status.py --status active` marks the workflow as active on `User:EmmaBot`.
2. **Core Loop** — structural changes that later scripts depend on:
   - `create_wanted_categories.py` (new to loop) — dynamically fetches Special:WantedCategories and creates stub pages
   - `fix_double_redirects.py`
   - `move_categories.py`
   - `create_japanese_category_qid_redirects.py`
3. **Cleanup Loop** — category cleanup + talk pages (all 7 existing scripts, unchanged order).
4. **Bookkeeping: END** — `update_bot_userpage_status.py --status inactive` marks the workflow as done.

### create_wanted_categories.py rewritten to use dynamic API query
**Script:** `shinto_miraheze/create_wanted_categories.py`
**Status:** Complete

Replaced the hardcoded list of ~150 category names with a live query to `Special:WantedCategories` using the `querypage` API (same pattern as `delete_unused_categories.py` uses for `Unusedcategories`). Added standard CLI args: `--apply`, `--max-edits`, `--run-tag`.

The parent category was changed from `[[Category:Categories made during git consolidation]]` to `[[Category:Categories autocreated by EmmaBot]]`. These are effectively the same thing — the "git consolidation" category was an earlier iteration of the same concept (auto-creating wanted categories), just with a name tied to a specific cleanup phase. The new name is permanent and self-describing.

### update_bot_userpage_status.py gains --status flag
**Script:** `shinto_miraheze/update_bot_userpage_status.py`
**Status:** Complete

Added `--status active|inactive` flag. When set, the status block on `User:EmmaBot` includes a `Workflow status: '''active'''` or `'''inactive'''` line. Called at both start and end of the cleanup loop to show whether the bot is currently running.

---

## 2026-03-01

### Double redirect fixer added to cleanup loop
**Script:** `shinto_miraheze/fix_double_redirects.py`
**Status:** Complete (pipeline integration)

Added `fix_double_redirects.py` to the cleanup loop as the first cleanup step. Queries `Special:DoubleRedirects` and updates each redirect to point directly to the final target, eliminating intermediate hops. Runs before all other cleanup scripts so downstream steps see correct redirect targets.

---

## 2026-02-28

### Category move script and Japanese→English translations
**Scripts:** `shinto_miraheze/move_categories.py`, `shinto_miraheze/category_moves.csv`
**Status:** Complete (pipeline integration)

Added `move_categories.py` which reads a CSV of (source, destination) category pairs and performs moves: recategorizes all members then moves the category page. Skips sources that are already redirects or have `{{category move error}}`; tags conflicts where both source and destination already exist.

Added `category_moves.csv` with ~295 Japanese→English category translations covering:
- Building and history categories for various Japanese municipalities
- Japanese cultural and historical categories (shrines, temples, ancient relations)
- Taiwan-related historical and cultural categories
- Year/century-based categories, regional categories, template categories, WikiProject categories

### Japanese category QID redirect script added to cleanup loop
**Script:** `shinto_miraheze/create_japanese_category_qid_redirects.py`
**Status:** Complete (pipeline integration)

Added `create_japanese_category_qid_redirects.py` to handle a race condition where Japanese-named categories may not have proper QID redirects. For every category in `[[Category:Japanese language category names]]` with `{{wikidata link|Q...}}`: creates `Q{QID}` mainspace redirects, and handles duplicate QIDs by creating disambiguation pages tagged with `[[Category:double category qids]]`. Runs in the cleanup loop immediately after `move_categories.py`.

---

## 2026-02-27

### Legacy category template remover added to cleanup loop
**Script:** `shinto_miraheze/remove_legacy_cat_templates.py`
**Status:** Complete (pipeline integration)

Added `remove_legacy_cat_templates.py` to the cleanup loop. Strips `{{デフォルトソート:…}}` and `{{citation needed|…}}` artifacts from Category: namespace pages, with state file resumability and standard `--apply`/`--max-edits`/`--run-tag` interface.

Also fixed run-tag format in the same commit: switched from external link syntax `[https://... text]` to interwiki syntax `[[git:path|text]]` so edit summary links render correctly on the wiki.

---

## 2026-02-27

### CI-first operating policy declared
**Status:** Active policy

Operational policy is now explicit across docs and bot-page content:
- Emma Leonhart will not run normal mass-edit jobs from a local machine.
- Routine and major bot operations are to be executed via GitHub Actions by editing repository code/workflows.
- Local manual script execution is reserved for emergency intervention only.

### GitHub Actions bot-password pipeline rollout
**Scripts/Workflow:** `.github/workflows/cleanup-loop.yml`, `shinto_miraheze/cleanup_loop.sh`, `shinto_miraheze/update_bot_userpage_status.py`
**Status:** Complete (pipeline implementation)

Implemented full Ubuntu GitHub Actions execution for the active cleanup loop with bot-password credentials:
- Trigger modes: push, daily schedule (`00:00 UTC`), and manual dispatch
- Authentication model: `WIKI_USERNAME` variable (`MainUser@BotName`) + `WIKI_PASSWORD` secret
- Persistent state: `*.state` files are committed back to the branch after successful runs
- Loop protection: state-only commits do not retrigger the workflow (`paths-ignore: **/*.state`)

Added run-start status reporting:
- Bot updates `[[User:EmmaBot]]` at run start
- Uses `EmmaBot.wiki` as baseline content and appends/replaces a machine-managed status block
- Records UTC start time, trigger cause (push/schedule/manual), and workflow run URL

Added run-size limiting for timeout control:
- `WIKI_EDIT_LIMIT=1000` configured in workflow
- Active cleanup scripts now support `--max-edits` and stop after reaching the cap
- Cap is passed by `cleanup_loop.sh` into:
  - `normalize_category_pages.py`
  - `migrate_talk_pages.py`
  - `tag_shikinaisha_talk_pages.py`
  - `remove_crud_categories.py`
  - `fix_erroneous_qid_category_links.py`

Operational note:
- `remove_crud_categories.py` and `migrate_talk_pages.py` are expected to require multiple daily runs over several days due to scale.

### Unused category deletion added to active loop
**Script:** `shinto_miraheze/delete_unused_categories.py`
**Status:** Complete (pipeline integration)

Added automatic deletion of categories from Special:UnusedCategories as the first cleanup task in the CI loop.

Safeguard:
- If a category page contains `{{Possibly empty category}}`, the bot skips deletion.

Rationale:
- With crud categories being trimmed, unused category pages now need active cleanup to complete the consolidation phase.

### Active script credential override migration
**Scripts:** `shinto_miraheze/*.py` (active scripts)
**Status:** Complete for active scripts

Migrated active scripts from fixed credentials to environment-variable override pattern:
- `USERNAME = os.getenv("WIKI_USERNAME", ...)`
- `PASSWORD = os.getenv("WIKI_PASSWORD", ...)`

This keeps legacy fallback behavior locally while enabling secure CI credential injection.

### Local cleanup loop orchestration baseline
**Scripts:** `shinto_miraheze/cleanup loop.bat`, `shinto_miraheze/fix_erroneous_qid_category_links.py`
**Status:** Complete

Added a Windows launcher (`cleanup loop.bat`) that opens separate command sessions for the active cleanup jobs and now serves as the local orchestration baseline for the later bot CI/CD pipeline.

Also added `fix_erroneous_qid_category_links.py`, which processes pages in `Category:Erroneous_qid_category_links` and converts pages to simple redirects when all listed category targets are the same.

### Category:Q{QID} pages in wrong namespace resolved
**Status:** Complete — ~77 pages

Approximately 77 pages existed in the Category namespace as `Category:Q{QID}` (wrong namespace). These were resolved by deleting or moving them to mainspace as `Q{QID}` redirects pointing to the correct category.

---
## 2026-02-26

### Category page wikitext normalization
**Script:** `shinto_miraheze/normalize_category_pages.py` (new)
**Status:** Complete â€” **23,571 edited, 474 skipped, 0 errors**

Normalized all 24,045 non-redirect category pages to a clean three-section structure:

```
<!--templates-->
{{wikidata link|Qâ€¦}} etc.
<!--interwikis-->
[[ja:â€¦]] [[en:â€¦]] etc.
<!--categories-->
[[Category:â€¦]]
```

Strips all free text, stray headings, Japanese prose, and any other content accumulated from previous automated passes. Added state file (`normalize_category_pages.state`) and JSONL log (`normalize_category_pages.log`) so the script is safe to re-run without re-processing completed pages.

### Deletion of Category:Jawiki_resolution_pages
**Script:** `shinto_miraheze/delete_jawiki_resolution_pages.py`
**Status:** Complete â€” **10,239 pages deleted**

Deleted all pages in `Category:Jawiki_resolution_pages`. These were stub pages created during earlier jawiki import passes that served no ongoing purpose. Deletion was performed in bulk via the bot account. Category is now empty.

### Imported Kuni no Miyatsuko pages
I imported all of the Kuni no Miyatsuko pages from jawiki, this is something that needed to be complete, and leaving it partway filled was causing issues. They still need to be translated and normalized and deduplicated.

---

## 2026-02-23

### History merge â€” `{{moved to}}` / `{{moved from}}` pairs
**Scripts:** `shinto_miraheze/merge_move_histories.py` (new), `shinto_miraheze/tag_move_link_quality.py` (new), `shinto_miraheze/tag_move_intersection.py` (new)
**Status:** Complete â€” **184 pairs merged, 0 errors**

Completed the full-history merge for all matched move pairs. For each pair (A = old name, B = new name):
1. B's content saved (with `{{moved from}}` stripped)
2. B deleted â†’ revisions enter the deleted archive
3. A moved to B's title â†’ B's title now holds A's revision history
4. B's content pasted onto the page at B's title
5. B's archived revisions undeleted â†’ histories merge chronologically at B's title

Also introduced three maintenance categories populated by bot:
- `Category:moved from a redlink` â€” `{{moved from|X}}` where X doesn't exist
- `Category:moved to a redlink` â€” `{{moved to|X}}` where X doesn't exist
- `Category:moved from a non-redirect` â€” `{{moved from|X}}` where X exists but is not a redirect
- `Category:Move targets âˆ© destinations` â€” pages with both templates (edge cases needing manual resolution)
- `Category:move templates that do not link to each other` â€” pages whose templates form a contradictory/mismatched pair (7 pages; needs manual review)

History fully preserved for all 184 merged pages. Marginal exceptions: the 7 pages in the error category, plus the pre-existing âˆ© cases that were cleared manually.

---

## 2026-02-20

### ja: interwiki category merge and QID linking
**Script:** `shinto_miraheze/merge_by_ja_interwiki.py` (new)
**Status:** Complete â€” **22 linked, 40 merged, 0 errors**
Scans all 834 categories in [Category:Categories missing Wikidata with Japanese interwikis](https://shinto.miraheze.org/wiki/Category:Categories_missing_Wikidata_with_Japanese_interwikis). Builds a map of jawiki target â†’ shintowiki categories, then:

- **Single match** â€” queries jawiki API for the QID, creates a `Q{QID}` redirect page and adds `{{wikidata link|Q...}}` to the category (same flow as `resolve_missing_wikidata_categories.py`)
- **One CJK + one Latin sharing same jawiki target** â€” merges: recategorizes all members from the CJK category into the Latin one, redirects the CJK category, then adds the wikidata link to the Latin category
- **Two or more Latin sharing same jawiki target** â€” tags all with `[[Category:jawiki categories with multiple enwiki]]` for manual review

Results: 754 singles (22 linked, 732 skipped â€” no jawiki QID), 40 shared-target groups (all clean CJK+Latin pairs, all merged). 0 tagged-multi cases, 0 errors.

---

## 2026-02-19

### Tagging categories missing Wikidata but with Japanese interwikis
**Script:** `shinto_miraheze/tag_missing_wikidata_with_ja_interwiki.py` (new)
**Status:** Complete â€” **834 categories tagged**, 4209 skipped (no ja: interwiki), 0 errors
Scans all members of Category:Categories_missing_wikidata for `[[ja:...]]` interwiki links in their wikitext. Tags any that have one with `[[Category:Categories missing Wikidata with Japanese interwikis]]`. This intermediate categorization step makes it easy to later batch-process that subset: the ja: link provides a direct path to the jawiki category, from which the QID can be retrieved.

### Missing Wikidata link resolution
**Script:** `shinto_miraheze/resolve_missing_wikidata_categories.py` (new)
**Status:** Complete
For every category in [Category:Categories_missing_wikidata](https://shinto.miraheze.org/wiki/Category:Categories_missing_wikidata): queries the English or Japanese Wikipedia API (enwiki for Latin names, jawiki for CJK names, with fallback to the other) for `Category:{name}` and retrieves the `wikibase_item` QID from pageprops. If found:

- **Q page doesn't exist on shintowiki** â†’ create `Q{QID}` as `#REDIRECT [[Category:Name]]` and add `{{wikidata link|Q...}}` to the category page
- **Q page redirects to this same category** â†’ just add `{{wikidata link|Q...}}` to the category page
- **Q page redirects to a different English category** â†’ merge (recategorize members + redirect this category), same logic as `merge_japanese_named_categories.py`
- **Q page is a disambiguation list** â†’ skip

Result: **2425 actionable** out of 5054 checked â€” 2410 Q pages created + wikidata links added, 4 wikidata links added to existing Q-linked categories, 11 merges into English equivalents. 2629 skipped (no Wikipedia equivalent found). 0 errors.

### Japanese-named category merges
**Script:** `shinto_miraheze/merge_japanese_named_categories.py` (new)
**Status:** Complete
For every category in [Category:Japanese_language_category_names](https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names): finds the `{{wikidata link|Q...}}` on the category page, looks up the Q{QID} mainspace page, and if that Q page is a simple `#REDIRECT [[Category:EnglishName]]` to a non-CJK category, recategorizes all members from the Japanese-named category to the English one and redirects the Japanese category page.

Skips if: no wikidata link, Q page doesn't exist, Q page redirects back to a CJK name (no English equivalent on this wiki yet), or Q page is a disambiguation list (handled separately by `resolve_duplicated_qid_categories.py`).

Result: **1274 categories merged** out of 2417 checked (ran in two passes â€” first pass crashed at 84 on edit conflict with concurrent crud script; second pass completed remaining 1190 cleanly with 0 errors).

### [[sn:...]] interwiki link removal
**Script:** `shinto_miraheze/remove_sn_interwikis.py` (new)
**Status:** Complete
Strips all `[[sn:...]]` links from every page on the wiki. These were accidentally used as a note-storage mechanism during earlier bot passes â€” e.g. `[[sn:This category was created from JAâ†’Wikidata links on Fuse Shrine (Sanuki, Kagawa)]]`. The `sn` language code produces meaningless interwiki links and serves no purpose. Uses `insource:"[[sn:"` full-text search to find affected pages (the `list=alllanglinks` API module is not available on Miraheze), then strips the pattern from each.

Result: 1 page affected ([Help:Searching](https://shinto.miraheze.org/wiki/Help:Searching)), 3 links removed. The minimal footprint confirms these were all added during a single earlier pass.

### Crud category cleanup
**Script:** `shinto_miraheze/remove_crud_categories.py` (new)
**Status:** Running (two instances â€” original + second pass for subcategories added during runtime)
Fetches all subcategories of [Category:Crud_categories](https://shinto.miraheze.org/wiki/Category:Crud_categories) and strips those category tags from every member page. Goal is to leave all the crud subcategories empty. These were leftover maintenance/tracking categories accumulated from various automated passes that serve no ongoing purpose.

21 subcategories identified in the original run. The script caches the subcategory list at start and fetches members live per subcategory. A second instance was started to catch any new subcategories added to Category:Crud_categories during the first run's execution. By far the slowest script this session â€” the first subcategory alone (Category:11) had 1568 members. The individual-edit-per-page approach is suboptimal for bulk cleanup but is intentional and generative; the slow pace is not considered an error.

### Duplicate QID category resolution
**Script:** `shinto_miraheze/resolve_duplicated_qid_categories.py` (new)
**Status:** Partially complete â€” 146/221 processed; needs re-run for remainder
Processes all Q{QID} pages in [Category:Duplicated qid category redirects](https://shinto.miraheze.org/wiki/Category:Duplicated_qid_category_redirects). These are QID redirect pages where two categories â€” one with a Japanese name and one with an English name â€” share the same Wikidata QID, meaning they are the same category under two names.

Logic:
- **CJK name + Latin name pair** (e.g. `Category:ä¸Šé‡Žå›½` + `Category:KÅzuke Province`): recategorizes all members from the CJK category to the Latin/English one, redirects the CJK category page to the Latin one, and converts the Q page to a simple `#REDIRECT [[Category:LatinName]]`.
- **Both Latin names**: cannot auto-resolve â€” tags the Q page with `[[Category:Erroneous qid category links]]` for manual review.

Run crashed at Q8976949 (Category:ä¸€å®® â†’ Category:Ichinomiya, 36 members) with an edit conflict â€” concurrent editing with the crud cleanup script. 146 Q pages were fully resolved before the crash. Re-run will skip already-resolved pages since they no longer appear in the category.

### Wanted categories created
**Script:** `shinto_miraheze/create_wanted_categories.py` (new, ran this session)
**Status:** Complete
Created 153 category pages that had members but no page (showed up in Special:WantedCategories). Each got `[[Category:categories made during git consolidation]]`. [Category:Duplicated qid category redirects](https://shinto.miraheze.org/wiki/Category:Duplicated_qid_category_redirects) got special documentation explaining the Q-page format and how to resolve entries. Parent category [Category:categories made during git consolidation](https://shinto.miraheze.org/wiki/Category:Categories_made_during_git_consolidation) also created.

### Repository consolidation
- Moved all root-level scripts into `shinto_miraheze/`
- Deleted `aelaki_miraheze/` (project abandoned)
- Deleted `archive/` directory (544 files; all preserved in git history)
- Added `todo.md`, `HISTORY.md`, `DEVLOG.md` to repo
- Cleaned up README (removed speech-to-text dump, replaced with proper docs)

---

## 2026-02-19 (earlier â€” previous Claude session, interrupted by system crash)

### DEFAULTSORT removal from shikinaisha pages
**Script:** `shinto_miraheze/remove_defaultsort_digits.py`
**Status:** Complete
Removed `{{DEFAULTSORT:â€¦}}` from all pages in `Category:Wikidata generated shikinaisha pages`. These were auto-generated by an earlier script and served no purpose.

### Category Wikidata link addition
**Script:** `shinto_miraheze/resolve_category_wikidata_from_interwiki.py`
**Status:** Complete (full pass Feb 2026)
Added `{{wikidata link|Qâ€¦}}` to all category pages that had interwiki links but no Wikidata connection. Used interwiki links to look up QIDs.

### QID redirect creation for categories
**Script:** `shinto_miraheze/create_category_qid_redirects.py`
**Status:** Complete (ran concurrently with above â€” possible race condition artifacts, scope unknown)
Created `Q{QID}` mainspace redirect pages for all categories with `{{wikidata link}}`. Where two categories shared a QID, created a numbered disambiguation list and tagged with `[[Category:Duplicated qid category redirects]]`.

### Duplicate category link fix
**Script:** `shinto_miraheze/fix_dup_cat_links.py`
**Status:** Complete (one-off)
Fixed `[[Category:X]]` â†’ `[[:Category:X]]` in the dup-disambiguation Q pages. An earlier run of the QID redirect script had accidentally created category tags instead of category links in those pages.

---

## 2025 â€” Shikinaisha project

### Mass shikinaisha page generation
**Script:** `shinto_miraheze/generate_shikinaisha_pages_v24_from_t.py` (and earlier versions)
Generated wiki pages for shikinaisha (å¼å†…ç¤¾ â€” shrines listed in the Engishiki) from Wikidata. Earlier versions used ChatGPT translation; later versions used Claude. Pages were generated with Japanese Wikipedia content imported and translated.

### Shikinaisha data upload to Wikidata
Multiple scripts (now in git history) ran in Juneâ€“July 2025 to:
- Import shrine ranks from Japanese Wikipedia categorization into Wikidata
- Import shikinaisha entries from Japanese Wikipedia list pages (via Excel intermediary)
- Import from Kokugakuin University shrine database (caused many duplicate entries â€” significant WikiProject Shinto backlash, but data was not removed)

### ILL destination fixing
**Script:** `shinto_miraheze/fix_ill_destinations.py`
Multiple passes to fix `{{ill}}` template `1=` destinations using the QID redirect chain. See `SHINTOWIKI_STRUCTURE.md` for the resolution priority order.

---

## 2024â€“2025 â€” Category and interwiki passes

Various scripts (archived in git history) ran to:
- Add interwiki links to categories and main namespace pages from Wikidata
- Add Wikidata labels in multiple languages (Dutch, French, German, Indonesian, Turkish, etc.)
- Sync category interwiki links across Wikipedia editions (ja, de, zh, en)
- Add P31 (instance of) categories in bulk
- Generate and update shrine descriptions

---

## 2024 â€” Wiki restoration

Wiki was suspended by Miraheze and then reinstated. Restored from XML export obtained via Archive.org. Only most recent revision of each page was imported (not full history). Full history import is pending on Miraheze's side.

`{{moved to}}` and `{{moved from}}` templates introduced to preserve attribution across the two waves of page moves that occurred around this time.

---

## 2023â€“2024 â€” Wiki founding and initial imports

Wiki founded at shinto.miraheze.org. Initial pages imported from:
- English Wikipedia drafts (user was permanently blocked from enwiki December 2023)
- Simple English Wikipedia user pages (used as temporary holding space)
- Everybody Wiki

Early content workflow: ChatGPT translation of Japanese Wikipedia pages, with `{{ill}}` templates added for all links. All links on the wiki use `{{ill}}` â€” no bare wikilinks to other wikis.

Repository initially created for Wikidata edits. First major project: documenting Beppu shrines and Association of Shrines special-designation shrines.


