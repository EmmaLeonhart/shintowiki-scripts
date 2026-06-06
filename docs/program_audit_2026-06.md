# Program audit — shintowiki-scripts (2026-06)

A single read-through of everything this repo does to the wiki(s) and Wikidata:
what runs, when, what state it keeps, what's stuck or orphaned, where the
in-flight wiki migrations are, and a keep/fix/retire verdict per item. Written
2026-06-05 during the wiki-content backlog barrel-through session.

> Scope note: this is an architecture-level audit, not a line-by-line inventory
> of all ~70 scripts. Per-page transforms are grouped by their orchestrator; the
> standalone CI scripts are grouped by their workflow chunk. The authoritative
> behavioural docs are `CLAUDE.md` (conventions) and `DEVLOG.md` (history).

---

## 1. The CI invocation graph (what actually fires)

### Top-level scheduled workflows (have their own `cron:`)

| Workflow | Schedule (UTC) | What it does | State |
|---|---|---|---|
| `cleanup-loop.yml` | `0 */6 * * *` + push | **The spine.** Orchestrates the whole pipeline: window-gate → generate-quickstatements → generate-pages → git-synced-sync + fandom-sync → wiki-cleanup → fandom-cleanup → untransclude-crud-templates → 12 orchestrators → render-duplicate-qids → random-wait → submit-quickstatements → build-run-history → direct-daily-edits. | per-sub-workflow |
| `git-synced-sync.yml` | `5,20,35,50 * * * *` | Bidirectional `git_synced/` ↔ wiki sync (also called by cleanup-loop). | stateless (timestamp) |
| `fandom-sync.yml` | `*/15 * * * *` | Bidirectional `fandom_unique/` ↔ shinto.fandom sync (also called by cleanup-loop). | stateless |
| `build-remote-queue.yml` | `0 4 * * *` | Rebuilds `remote_queue.json` (work-list for the claude.ai remote routine). | `remote_queue.json` |
| `generate-shrines-missing-en-label.yml` | `17 5 * * *` | Regenerates the shrines-missing-en-label QS report. | report file |
| `import-templates-to-fandom.yml` | `30 9 * * *` | Pushes template updates to shinto.fandom. | — |
| `delete-orphans.yml` | `7 5 1 * *` (monthly) | Deletes orphaned pages. | — |
| `label-generator-regenerate.yml` | `0 6 1 * *` (monthly) | Regenerates the multilingual shrine-label sub-project. | — |
| `monthly-verification-sweep.yml` | `23 7 1 * *` (monthly) | Prepends the deferred-verification sweep task to `queue.md`. | — |
| `weekly-open-questions-sweep.yml` | `17 6 * * 1` (Mon) | Prepends the `[[Open questions]]` analysis task to `queue.md`. | — |

### Called-only workflows (fired by `cleanup-loop.yml` via `workflow_call`)

`wiki-cleanup`, `fandom-cleanup`, `untransclude-crud-templates`,
`generate-quickstatements`, `generate-pages`, `submit-quickstatements`,
`direct-daily-edits`, `build-run-history`, `random-wait`,
`render-duplicate-qids`, the 3 dedicated orchestrators
(`mainspace`/`category`/`template`), and `ns-orchestrator-runner` (×9 for the
misc + talk namespaces).

### Manual-only workflows (`workflow_dispatch`, no cron, not called by anything)

`configure-wikidata-link-grok-categories`, `dedupe-duplicate-qids`,
`sunset-jp-char-count-cats`, `sunset-templates-not-transcluded-in-mainspace-cat`,
`tag-templates-not-transcluded-anywhere`. **These are one-off maintenance tools.**
→ **Verdict: keep as manual tools, but flag for July-2026 review** — if their
one-time job is done (sunset/tag scripts especially), retire the workflow + script
per the legacy-script audit. None of them fire automatically, so they cost nothing
sitting idle; the risk is only repo clutter.

---

## 2. The orchestrators (the load-bearing per-page model)

12 per-page orchestrators sweep every wikitext namespace once per cleanup-loop
fire, each running its `OPS` list against every non-redirect page. State: one
`<orchestrator>.state` each in `shinto_miraheze/orchestrators/`, plus the shared
`duplicate_qids.state` collector and the talk cursor. Budgets set in
`cleanup-loop.yml`'s window-gate (steady state post-2026-06-01: mainspace/category/
template 100 each, misc 10/ns × 9).

**Registered ops by orchestrator** (verified 2026-06-05 from the `OPS` lists):

- **mainspace (ns 0)** — strip_html_comments, canonicalize_template_case,
  strip_afc_templates, ill_category_to_link, straggler_link_to_ill,
  normalize_ill_positional, normalize_ill_wikidata, interlang_consolidate,
  wikidata_lookup, grokipedia_link, history_offload, shikinaisha_talk,
  duplicate_qids, remove_defaultsort, deleted_qids_in_ill, **unresolved_ill_qid**,
  untranslated_japanese, strip_char_count_cats, wikidata_link,
  **multiple_wikidata_links**, categories_to_bottom.
- **category (ns 14)** — strip_html_comments, canonicalize_template_case,
  strip_self_categorization, ill_category_to_link, straggler_link_to_ill,
  interlang_consolidate, wikidata_lookup, history_offload, duplicate_qids,
  remove_legacy_cat_templates, normalize_category_page, wikidata_link,
  **multiple_wikidata_links**.
- **template (ns 10)** — strip_html_comments, canonicalize_template_case,
  ill_category_to_link, straggler_link_to_ill, interlang_consolidate,
  enwiki_wikidata_link, wikidata_lookup, history_offload, duplicate_qids,
  noinclude_wrap, template_mainspace_usage, wikidata_link.
- **9 misc orchestrators** (user/project/file/help/geojson/module/item/property/
  talk) — share `ns-orchestrator-runner.yml`, lighter op sets, 10 edits/ns budget.

**Gated ops (off by default):** `normalize_ill_wikidata`
(`ENABLE_NORMALIZE_ILL_WIKIDATA`), `wikidata_lookup` (`ENABLE_WIKIDATA_LOOKUP`) —
enabled per-namespace in the workflow inputs where the per-cycle API churn is
acceptable.

→ **Verdict: keep.** This is the healthy core. State files advance each cycle.
The category orchestrator has historically never completed a full cycle (the
catch-up window 2026-04-23→2026-06-01); post-window it's back to 100/fire and
should settle.

---

## 3. Legacy standalone scripts wired into `wiki-cleanup.yml`

Category-/SPARQL-/state-driven scripts that are NOT per-page sweeps (so they stay
standalone per the migration criterion in `CLAUDE.md`). Run every cleanup-loop
fire unless date-gated. Grouped by chunk:

- **Sync (first, by Emma's directive):** `sync_need_translation`,
  `sync_duplicated_content` (stateless; the cloud-queue worker drains the content).
- **Import & categorization:** `create_wanted_categories`,
  `categorize_uncategorized_categories`, `triage_emmabot_categories`
  (+`_jawiki`/`_secondary`/`_single_member`), `enrich_jawiki_categories`,
  `enrich_enwiki_categories`, `create_shrine_ranking_pages` *(marked TEMPORARY)*.
- **Structural:** `delete_unused_templates`, `delete_unused_redirects`
  (paranoid — bails if Special: returns 0), `fix_double_redirects`,
  `resolve_double_category_qids` (bounded `MAX_PAGES_PER_RUN=200`).
- **Wikidata (QS generators — emit `.txt`, no direct edits):**
  `clean_p11250_quickstatements`, `fix_merged_qids`, `generate_p11250_quickstatements`,
  `clean_p6262_quickstatements`, `generate_p6262_quickstatements`,
  `generate_en_labels_quickstatements`, `clean_wikidata_cat_redirects`.
- **Final core:** `categorize_uncategorized_pages`, **`fix_ill_destinations`**
  (NEW 2026-06-05, 50/run), `rebucket_300plus_untranslated` *(TEMPORARY)*.
- **Cleanup:** `delete_unused_categories`, `delete_orphaned_talk_pages`,
  `delete_broken_redirects`, `add_/remove_wikidata_crud_categories` (date-gated
  2026-06-06 / 2026-12-06), `remove_crud_categories`,
  `delete_lowercase_template_collisions` (per-template safety-gated),
  `undelete_gaiad_date` + `undelete_immanuelle_common_js` (**kludges** — see §6).
- **Monthly (1st):** `fix_erroneous_qid_category_links`,
  **`generate_category_translation_moves`** (NEW 2026-06-05) →
  `move_categories`, `create_japanese_category_qid_redirects`.

→ **Verdict: mostly keep.** `create_shrine_ranking_pages` and
`rebucket_300plus_untranslated` are self-labelled TEMPORARY — confirm they're done
and retire (overlaps the July-2026 legacy-script audit in `todo.md`). The two
`undelete_*` kludges are papering over real bugs (§6) — fix the root cause, then
remove.

---

## 4. The Wikidata path (ONE channel only)

Per `CLAUDE.md`, Wikidata is edited by exactly one mechanism:

1. **Generators** (`generate_*` in `wiki-cleanup.yml` + `modern-quickstatements/`)
   emit QuickStatements lines (NO edit summaries) into atomic `.txt` files under
   `modern-quickstatements/`.
2. `submit-quickstatements.yml` → `submit_daily_batch.py` runs them via the QS API.
3. `direct-daily-edits.yml` → `direct_daily_edits.py` is the fallback (runs ~50 of
   the SAME generated lines via the API if QS submission failed).

Gating: `wikidata-daily-fire` (one fire/UTC-day) AND the **hard freeze to
2026-06-06** (window-gate forces it false). No bespoke direct-API editors exist
(the P459/kana ones were deleted 2026-05-23).

→ **Verdict: keep, do not touch the shape.** This is the most safety-sensitive
subsystem. The freeze auto-resumes 2026-06-06. Backlog item 5 (recreate deleted
WD items) is the only pending Wikidata work and is **blocked on Emma** (open
question posted 2026-06-05).

---

## 5. The sync subsystem & the cloud-queue loop

- **5 stateless sync scripts** (timestamp / most-recent-edit-wins):
  `sync_need_translation`, `sync_duplicated_content` (wiki-wins),
  `sync_git_synced_pages`, `sync_miraheze_unique_pages`,
  `sync_fandom_unique_pages` (repo-wins). Verified stateless 2026-06-05
  (`save_state` no-op); removed an orphan `sync_main_page.state`.
- **The cloud-queue loop:** `build-remote-queue.yml` (daily) writes
  `remote_queue.json`; the claude.ai remote routine consumes 5 random items/fire,
  does the LLM-grunge work (duplicated-content reorg, need-translation
  translation), and removes the gating category from a finished page; the next
  sync then pushes + deletes the local file. Statefulness = file-presence +
  category, no cursor.

→ **Verdict: keep.** The statelessness change (2026-05-30) is still under
deferred verification (churn-inspection half pending a healthy wiki — see
`docs/deferred_verification.md`).

---

## 6. Known-stuck / kludged / failing

- **`history_offload` delete-without-recreate glitch.** `User:Immanuelle/common.js`
  gets deleted by `history_offload` but its recreate stage glitches, leaving the
  page deleted. **Kludge:** `undelete_immanuelle_common_js` restores it every
  cycle. → **Fix:** diagnose the recreate glitch (open todo item), then drop the
  kludge.
- **`Template:GaiadDate` mis-deletion.** Swept up by deletion passes but must not
  be deleted. **Kludge:** `undelete_gaiad_date` every cycle. → **Fix:** exclude it
  from the deletion passes, then drop the kludge. **ROOT-CAUSE FIX LANDED
  2026-06-06:** `delete_unused_templates.py` now has a `KEEP_TITLES` never-delete
  set (with a loop-level unit test) protecting `Template:GaiadDate` — the
  Special:UnusedTemplates culprit. Kludge kept as a safety net until a CI cycle
  confirms GaiadDate stops being deleted, then retire `undelete_gaiad_date`.
- **`audit_double_category_qids` disabled** (2026-04-24) — un-throttled walk hung
  the loop for 11h. Superseded by the auto-fixer + the new
  `report_double_qid_tail.py`. → **Verdict: retire the script. DONE 2026-06-06**
  (script deleted; dead commented block in `wiki-cleanup.yml` replaced with a
  retirement note).
- **Wiki flakiness (observed 2026-06-05):** shinto.miraheze.org returned repeated
  502s / read-timeouts during this session. Not a repo bug, but it (a) truncated
  the category-translation generator's first run to 500/1189 subcats (now flagged,
  not silent), and (b) blocked the wiki-`action=parse` deferred-verification
  checks. CI runs on GitHub's network and retries; the new `_get_json` helper in
  the translation generator tolerates transient 5xx.

---

## 7. In-flight wiki migrations — where each one is

| Migration | Mechanism | Current state (2026-06-05) | Next observable step |
|---|---|---|---|
| Double-category-QID drain | `resolve_double_category_qids` (auto) + `report_double_qid_tail` (NEW) | `[[Category:Double category qids]]` = **4** dab pages (the genuinely-different-target tail) | render report; human picks winners → `move_categories` |
| Japanese category translation | `generate_category_translation_moves` (NEW) → `move_categories` | **1189** subcats; phases a+b resolve ~205/483 confident (Wikidata-anchored + dated); residual → `docs/category_translation_residual.md` | monthly CI: regenerate CSV → move 100/run; build gazetteer phase c |
| Unresolved ill qids | `unresolved_ill_qid` op (detect) + `fix_ill_destinations` (NEW, fill) | category at **849–873** | CI fills 50/run from enwiki/sitelinks; op self-heals pages out |
| Multiple wikidata links | `multiple_wikidata_links` op + `report_multiple_wikidata_links` (NEW) | category at **1** | render report; human resolves the disambiguation |
| Deleted-QID ills (recreate) | `deleted_qids_in_ill` op (mark) + future generator | **144** marked `DELETED_QID` | **BLOCKED on Emma** (open question) + freeze to 2026-06-06 |
| Wikidata-missing crud lifecycle | `add_/remove_wikidata_crud_categories` (date-gated) | inert until 2026-06-06 / 2026-12-06 | date-gated steps begin draining legacy literal tags |
| miraheze_unique retirement drain | category-tag re-add via sync | **67/705** files still lack the tag | next sync cycles drain toward ~0 |

---

## 8. Summary verdicts

- **Keep (healthy core):** cleanup-loop spine, 12 orchestrators + ops, the sync
  subsystem, the single Wikidata QS path, the dashboard/`generate-pages` build.
- **Fix:** the two `undelete_*` kludges (diagnose root causes), the category
  orchestrator's never-completing cycle (should settle post-catch-up-window).
- **Retire (confirm-then-delete, overlaps July-2026 legacy audit):**
  `create_shrine_ranking_pages` + `rebucket_300plus_untranslated` (TEMPORARY),
  ~~`audit_double_category_qids` (disabled, superseded)~~ **— RETIRED 2026-06-06**,
  and the 5 manual-only dispatch workflows once their one-time jobs are confirmed
  done.
- **Blocked on Emma:** backlog item 5 (recreate deleted Wikidata items) — go/no-go
  + minimum claim set (open question posted 2026-06-05).
- **Pending deferred verification:** sync-churn inspection + the 4
  wiki-`action=parse` items (a healthy wiki needed — see
  `docs/deferred_verification.md`).
