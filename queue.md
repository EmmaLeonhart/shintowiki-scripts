# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Verify the category-prefix fix after the next cleanup-loop run

The fix shipped 2026-07-04 (three legs, per Emma's spec): (1) both Len-emitting
generators (`generate_en_labels_quickstatements.py`, `generate_p11250_quickstatements.py`)
now keep the `Category:` prefix — the year-old strip was the bug; (2) new
`generate_category_label_prefix_fixes.py` renders corrective Len lines for
already-damaged items to [[QuickStatements/Category label fixes]], consumed by
`fetch_category_label_fixes_from_wiki.py` → `category_label_fixes.txt` →
`direct_daily_edits.py` (wbsetlabel overwrites; deliberately slow drip, multi-year
is fine); (3) queued Category: lines on [[QuickStatements/En labels]] are
auto-repaired to full titles by the generator's new repair pass each run.
After the next cleanup-loop + daily-edits cycle: confirm the fixes page populates,
the drip applies prefixed labels, and no bare category labels are re-emitted.

## Read the category-orchestrator stack dump after tonight's run (pipeline break, diagnosed to instrumentation stage)

Emma's "no run today" hunch verified 2026-07-04 and it's WORSE: cleanup-loop has
failed EVERY scheduled run since at least 2026-06-08 — always the
category-orchestrator job, timing out at 160 min with ZERO stdout/stderr and
ZERO state growth (never marks even one page done). Poison-page theory tested
and eliminated: every light + network op runs instantly on the first non-done
page (Category:Articles to be merged); no import-time side effects; login
retries are bounded and noisy. mwclient's silent-retry budget (25 retries ≈ 150
min of sleep) matched the timeout exactly and is now capped at 5, but the log
shows no retry warnings either, so the true wedge point is still unproven.
Instrumentation shipped: `python3 -u` + `faulthandler.dump_traceback_later(900,
repeat=True)` in `common.run_orchestrator` — the next wedge prints its own
thread stacks into the CI log every 15 min. NEXT ACTION: after the next
scheduled cleanup-loop run (02:23 UTC daily), read the category-orchestrator
job log, find the dumped stack, fix the named line.

## 同上 error — pipeline SHIPPED for Izumo (48/51); remaining rungs

The year-old import bug (P6375 = 同上@ja copied verbatim from jawiki
式内社一覧 per-district table templates, uncited) now has a standing corrective
pipeline (2026-07-04): `resolve_doujou_addresses.py` parses the 10 出雲国
district templates, resolves each 同上 to the nearest preceding real address
(exactly the table's semantics, incl. rowspan continuations and the |||同上
typo), matches items by ja label; `generate_doujou_address_fixes.py` re-derives
convergent self-contained QS lines from LIVE Wikidata state every run (phase 1:
add correct address with S143=Q177837 + S4656=list-article URL; phase 2: remove
同上 only once the good claim exists — order-safe under the drip's random
sampling); `direct_daily_edits.py` gained monolingual-text (`ja:"…"`) support.
Wired into generate-quickstatements.yml. Slow multi-year drip is by design.

Remaining rungs:
1. **3 manual items** the resolver refuses to guess (kanji-variant/cross-district
   ambiguity): Q135040786 坐韓国伊大弖神社, Q135070085 剣神社, Q135070108
   佐久多神社. Resolve by hand or LLM with the district tables open.
2. **Generalize beyond 出雲国** if other provinces' imports carry 同上 (none
   found in the current 51, all Izumo — re-check with the SPARQL in
   resolve_doujou_addresses.py after the drip converges).
3. **Citation backfill for non-同上 imported addresses**: same reference pair
   (S143 jawiki + S4656 list URL) for Shikinaisha P6375 claims that are
   unreferenced but correct. Reuse the resolver's row-matching; emit through the
   same drip. Bounded: query first, gate on row-address == claim-address.
4. **Shinto-wiki list pages**: include the Japanese addresses in the periodic
   regeneration of the List-of-Shikinaisha pages, regenerating ~daily (Emma).
   Investigate which generator owns those pages (site/generate_pages.py?) and
   whether they regenerate at all; wire addresses in from the same district
   tables or from Wikidata P6375 once corrected.

## Temple & Shrine Standardization

So I don't really know if this is the case or not. My expectation here is that likely a massive amount more languages have the infrastructure to have shrine names than temple names or shrine names. I want to standardise it a bit so that the languages with no shrine infrastructure, but just temple infrastructure, basically you just kind of guess at them or use the temple name or whatever, so that we are properly propagating all the names in that way. 


## Monthly verification sweep (<!-- monthly-verify-sweep --> 2026-07-01)

Walk `docs/deferred_verification.md` and actually TEST each Open item (the batched verification we skip in the moment because wiki/CI changes are slow lagging indicators). For each: run its check; if it works, move it to the doc's Verified section with the date + what you observed; if it's broken, fix it and note the fix. Then delete THIS block.

## Verify temple drip landed (residual of the shipped temple pipeline)

After the first drip cycles: confirm temple en-labels are landing on Wikidata and
downstream multilingual labels appear. Cloud-prompt note: the Sonnet routine gets
`"kind":"temple"` items and can enforce the `<Stem>-<suffix> Temple` form.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
## Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-06-22)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.
