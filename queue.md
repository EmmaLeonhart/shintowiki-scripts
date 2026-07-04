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
(BLOCKED-ON-EXTERNAL until the 2026-07-05 ~06:00 UTC run: the 07-04 run's
generate job finished 06:20 UTC, before the fix landed at 09:03 UTC (f88f3a9c) —
tonight's run is the first that carries it.)

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
scheduled cleanup-loop run (~06:00 UTC daily), read the category-orchestrator
job log, find the dumped stack, fix the named line.
(2026-07-04 run checked: it wedged 160 min with zero output AGAIN, but that run
predated the instrumentation — its workflow ref pinned at 05:56 UTC and its
checkout dd8174b1 both exclude 63926a81 (pushed 09:18 UTC). Verified: no
faulthandler in that checkout's common.py, no `-u` in its workflow step. So the
zero-dump run is expected, not a watchdog failure. First instrumented run =
2026-07-05 ~06:00 UTC; read that log. One inference already banked: IF tomorrow
also dumps nothing, the wedge is before `run_orchestrator` entry — i.e. import
time or argparse/env, since the watchdog is armed at the function's first line
and writes straight to fd 2.)

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

Remaining rungs (DONE 2026-07-04: "3 manual items" by Emma f27c354f
[MANUAL_OVERRIDES, unmatched empty]; "citation backfill" shipped same day —
generate_address_citation_backfill.py, 151 lines first run, drips via
address_citation_backfill.txt, converges as refs land; see devlog):
1. **Generalize beyond 出雲国** if other provinces' imports carry 同上 (none
   found in the current 51, all Izumo — re-check with the SPARQL in
   resolve_doujou_addresses.py after the drip converges).
2. **Shinto-wiki list pages** — INVESTIGATED 2026-07-04, premise fails,
   NEEDS-DECISION (Emma): the List-of-Shikinaisha pages do NOT regenerate.
   They are hand-authored {{ill}} tables (afc comment, 2026-02-16) living in
   `git_synced/` — sync_git_synced_pages mirrors edits ~half-hourly but no
   generator rebuilds content; `site/generate_pages.py` is only the GitHub
   Pages status site. Only 2 such pages are in git_synced (both Awa); wiki
   enumeration blocked by the 07-04 Miraheze 503 outage. Columns today:
   District/Name/Funding/Rank/Candidates/Notes/Co-ords/DB — no Address.
   Decision needed: (a) new script that INSERTS an Address column into the
   existing hand-authored tables by matching each row's qid= to Wikidata
   P6375 (one-shot per page, non-regenerating, preserves hand content), or
   (b) build a true generator that rebuilds these pages from Wikidata (big:
   replaces hand-authored pages), or (c) drop the idea. (a) is the cheap
   fit but edits her authored tables, so not done autonomously.

## Temple & Shrine Standardization (decomposed 2026-07-04; Emma's rule: temple-only langs use the temple name for shrines)

Emma's original note (kept): "My expectation here is that likely a massive
amount more languages have the infrastructure to have shrine names than temple
names or shrine names. I want to standardise it a bit so that the languages
with no shrine infrastructure, but just temple infrastructure, basically you
just kind of guess at them or use the temple name or whatever, so that we are
properly propagating all the names in that way."

Measured 2026-07-04 (query.csv vs temple_query.csv vs format_label): the
asymmetry is real and it runs temple-heavy — **221 langs have temple labels,
116 have shrine labels; 112 langs are temple-only, just 7 shrine-only** (all
7 at count=1, ignore). format_label covers 38 langs and ALL 38 already emit
both kinds (25 distinct words, 13 shared — the shared ones ARE Emma's
"use the temple word" rule, already live for ar/fa/he/hi/bn/tr/la/sv/az/…).
The gap is coverage, not fallback logic. Rungs:

1. ~~temple-only langs~~ PARTIAL 2026-07-04: **nn, ceb, mai, as, ur shipped**
   into format_label + ALL_LANGS + language_registry with tests (sampled
   conventions: ceb "Templong <Name>"; nn mirrors nb; mai=hindify+मंदिर;
   as=bengalify+Assamese-ৰ+মন্দিৰ; ur=farsify+مندر — temple word serves both
   kinds per Emma's rule). Remaining split:
   a. **gan (91 labels!), cdo, zh-mo → the CJK path** — their sampled labels
      are verbatim kanji (trad variants), so they belong in
      generate_chinese_quickstatements.py (opencc variant conversion), NOT
      format_label. Wire them there.
   b. **pa/km/lo/dz/new/mad/shn deferred** — no script converter exists
      (Gurmukhi/Khmer/Lao/Tibetan/Newa/…) and 0-2 observed labels each;
      counts ≤16. Only worth it if a converter arrives or Sonnet does them.
2. **Both-kind langs missing from format_label** (pl 35/196, th 33/135,
   cs 31/135, fi 18/46, sl 29/97, ro 9/33 …): same sampling method, but these
   get DISTINCT shrine/temple words where the observed conventions differ.
   (ja/en/id/zh/ko/tok are fine — own paths per DEVLOG 2026-06-23.)
3. **Regenerate + eyeball a small batch** for the 5 new langs before the drip
   picks them up (tests are in tests/test_temple_only_tier.py, done).


## Monthly verification sweep (<!-- monthly-verify-sweep --> 2026-07-01) — PARTIAL 2026-07-04, wiki-dependent remainder only

Ran 2026-07-04: repo-local halves done and moved to Verified (retirement drain
3/642, essentially converged; no sync_*.state reappearance). The three
wiki-read items (Q3 enwiki bucket counts, conflict-resolution edit summaries,
sync churn inspection) were blocked AGAIN by a Miraheze 503 outage — second
sweep in a row. Remaining: run just those three when the wiki responds, then
delete THIS block.

## Temple drip verified NOT landing — QS path broken, BLOCKED-ON-USER-ACTION (Emma: one manual QS batch)

Checked 2026-07-04: 5/5 sampled temple QIDs from temple_en_labels.txt still have
NO en label; the file is unchanged since 2026-06-23 (359 lines pending;
temple_identical has 11,346). Root cause chain:
1. **The QuickStatements API path fails for EVERY batch** with: "Problem
   generating OAuth signature; user 'Immanuelle' needs to have submitted a
   batch manually at least once before" (see reports/2026-07-03_02-56-19).
   → **Emma unblocks it by logging into quickstatements.toolforge.org as
   'Immanuelle' and submitting any one batch manually in the web UI**; after
   that, API batches work again. This is THE fix — the QS path is the
   ~800-edits/day path.
2. The direct-API fallback (50/day) only fires when the submit job actually
   runs; during 06-22→07-01 the wedged cleanup-loop runs got the submit job
   CANCELLED (e.g. run 28499096140) → zero Wikidata edits for 10 days. It ran
   07-02 (manual dispatch, ~50 edits OK); 07-03 gate said already-submitted;
   07-04 run still in progress at check time.
3. Even a healthy fallback can't move temples: 50 random lines/day over
   ~25k pending lines ≈ 0.7 temple lines/day.
After Emma's manual batch: re-run this check (5 QIDs from temple_en_labels.txt
should gain labels within days, and the file should shrink on regeneration).
Cloud-prompt note kept: the Sonnet routine gets `"kind":"temple"` items and can
enforce the `<Stem>-<suffix> Temple` form.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
