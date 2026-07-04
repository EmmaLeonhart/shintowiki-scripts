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
2. **Shinto-wiki list pages — DECIDED (Emma 2026-07-04: full generator;
   pages were NEVER hand-authored, they're generated pages that stopped
   updating) and the generator is REVIVED**:
   `shinto_miraheze/update_shikinaisha_lists.py` (recovered from
   archive/engishiki_list_generator/update_shikinaisha_lists_v3.py in git
   history; the old progress file had marked every page done permanently —
   that's why they went stale). Revival adds the **Address column (P6375,
   ja preferred, 同上 refused)** between Notes and Co-ords, house flags
   (--apply/--max-edits/--run-tag/--pages), env creds (no hardcoded
   fallback), capped login retries. 5 offline tests. New dispatchable
   workflow `update-shikinaisha-lists.yml` (defaults to the two Awa list
   pages — Chiba + Tokushima; the bare "Awa Province" page is a
   disambiguation page and is not touched).
   Remaining rung:
   a. **Verify the first scheduled FULL sweep** (daily 18:37 UTC cron added
      2026-07-04 per Emma's original "regenerating ~daily" spec; first fire
      tonight): run green AND spot-check 2-3 non-Awa province pages carry
      the Address column. Both Awa pages already VERIFIED LIVE (Chiba
      16:11:09Z, 7 addr cells; Tokushima 16:22:03Z, 89 addr cells — after
      fixing the throttle failure with batched fetches + honest exit).

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
   a. ~~gan/zh-mo → CJK path~~ DONE 2026-07-04: wired into
      generate_chinese_quickstatements.zh_variants (gan = s2t generic
      traditional, matching all 15 sampled labels; zh-mo = s2hk, Macau
      follows HK convention). select_label_proposals globs the new
      quickstatements/gan.txt + zh-mo.txt into the drip automatically.
      **cdo DEFERRED with evidence**: zero cdo labels exist on Japanese
      shrines/temples even under a broad P31-subclass sweep — no observed
      convention, and cdo wiki mixes hanzi with romanized Bàng-uâ-cê.
   b. **pa/km/lo/dz/new/mad/shn deferred** — no script converter exists
      (Gurmukhi/Khmer/Lao/Tibetan/Newa/…) and 0-2 observed labels each;
      counts ≤16. Only worth it if a converter arrives or Sonnet does them.
2. ~~Both-kind langs~~ DONE 2026-07-04: **pl, ro, fi, cs, sl shipped** with
   distinct words from sampled conventions (pl Świątynia both kinds; ro
   Sanctuarul/Templul; fi -pyhäkkö/-temppeli; cs Svatyně/Chrám with the new
   Czech transcriber — Jasukuni/Meidži/Curugaoka Hačiman all reproduce; sl
   Svetišče/Tempelj with the Slovene variant — Jakuši-dži/Todai-dži).
   **th DEFERRED**: Thai script transliterator doesn't exist (vowel signs
   precede consonants — real work, not a map). ALL_LANGS 43→48.
3. **Verify the regeneration run** (dispatched 2026-07-04 ~17:05 after fixing
   why the last one silently died at lang 3/43: run_sparql had no retry and
   continue-on-error masked the crash — now retried 3×, per-lang fault
   isolation, nonzero exit on partial failure): confirm all lang files exist
   incl. the 10 new (nn/ceb/mai/as/ur + pl/ro/fi/cs/sl) and spot-check lines.


## Wikidata edits: direct path promoted to primary at 300/day (Emma decisions 2026-07-04)

QuickStatements is PERMANENTLY DEAD for this pipeline — its API requires a
one-time manual web-UI batch and Emma has said she will not do one. Decisions
taken in-session 2026-07-04: `direct_daily_edits.py` is the primary (only)
Wikidata editor at **MAX_EDITS=300, delays 30–90s** (Emma picked the 300/day
tier explicitly; ~25k pending lines ≈ 3 months). Still once-daily gated by
cleanup-loop. Historical context: 06-22→07-01 had zero Wikidata edits (wedged
runs cancelled the submit job), and at the old 50/day the temple files
(temple_en_labels 359 + temple_identical 11,346) moved ~0.7 lines/day.
VERIFY after 2-3 daily cycles: reports/ show ~300-line direct runs, and
sampled temple QIDs start gaining en labels. Consider retiring
submit_daily_batch's QS attempt entirely (it burns a failed API call per file
every day) — small cleanup, next tick.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
