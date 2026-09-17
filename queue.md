# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **Miraheze: waiting for Cloudflare to stop challenging our runners. Nothing is owed by anyone.**
  Diagnosed 2026-09-12 (`shinto_miraheze/probe_miraheze_403.py`, `DEVLOG.md`): Cloudflare serves the
  GitHub Actions runners a managed challenge — 272 KB of `text/html`, *"Checking your connection…"* —
  on every request, reads included, while the identical script from Emma's connection gets 200. The
  control settles that it is not our UA: a deliberately generic UA from the same runner still gets
  Miraheze's own 193-byte `text/plain` policy refusal.
  - **Intermittent, not permanent.** `EmmaBot/3.1` passed from CI on 08-19, 08-23 and 08-30 and
    carried ~800 edits/day on 09-01..09-04. It began between 09-04 and 09-06.
  - **Probed DAILY since 2026-09-12** (Emma: *"Daily"*), `LOCK_DAYS` 8 → 2, so the day it lifts we
    know within 24 hours instead of up to eight days. The failure reason now records which 403 it is.
  - ⛔ **Emma has ruled out contacting Miraheze** (2026-09-12). Do not propose it again, and do not
    re-probe by hand — the daily test is the probe. There is nothing to decide and nothing to do;
    this item exists so the next session does not re-derive it.
  - ⚠ It also reframes `docs/fandom_vs_miraheze_2026-09-12.md`: that reliability table compares one
    host that challenges our runners against one that does not, which is not a comparison of the two
    wikis.

- [ ] WDQS transports: **69 callers, each hand-rolled.** All 8 that had a retry loop catching only
  `ReadTimeout`/`ConnectionError` are now covered (2026-09-14), and the whole dead-429 subclass is
  closed (2026-09-16, below). What is left is the rest, and it is per-file reading.

  ⛔ **DO NOT PUT A NUMBER ON HOW MANY ARE FRAGILE.** Three regexes gave three wrong answers:
  *"65 of 72"* missed every `except Exception` and `except (ValueError, KeyError)`, which already
  catch a JSON error; *"50"* counted a file fixed hours earlier whose clause puts the tuple in a
  variable; *"~41 with no retry loop"* matched only `for attempt in range` and missed the
  `for wait in (0, 15, 45, 135)` shape. Grounded, by reading: **34 have some retry construct, 35
  have none, 10 already use the 15/45/135 backoff.**

  ⚠ **Migration is NOT uniformly an upgrade.** Those 10 escalate harder than a flat backoff, and
  no two unmigrated transports share a body. The failure costs one day of one file — CI is
  `continue-on-error` and the next run repairs it — so this rides with each file's next real change.
  `modern-quickstatements/wdqs_transport.py` is the target, and it now carries the repo's 15/45/135
  so adopting it cannot downgrade anyone.

  **Adopters: 20.** The first six joined on the tick of their own reference fix — the intended
  cadence. `generate_court_rank_quickstatements.py` had **0.5s** spacing (the exact figure CLAUDE.md
  cites from the incident that set the 2.5s floor) and a 5/10/15 backoff; the saijin and honzon
  generators each had no retry, no throttle, and a 429 check placed after a *successful* urlopen.

  ✅ **The dead-429 subclass is CLOSED (2026-09-16) — 14 files, all migrated.** A file whose only
  429 handling was `if r.status == 429` inside a `with urlopen(...)` block. That branch is
  unreachable: urllib's default opener raises `HTTPError` on any non-2xx, so the body never runs and
  `r.status` is always a success code. Proved against a local server answering 429, and pinned as
  `test_a_429_check_after_a_successful_urlopen_can_never_fire`. None of the 14 had a retry construct
  around its WDQS call either, so the whole documented policy was absent from every one — no
  per-file judgement was left, which is what made migrating them as a batch right rather than a
  breach of the cadence above. `test_no_adopter_kept_the_unreachable_429_check` stops it coming back.
  - Eight of them also fetched ja.wikipedia, the Wikidata API, jmapps or rakuten through `urlopen`;
    each of those fetchers moved to `requests` too, because the transport test reads a raw urlopen
    anywhere in an adopter as evidence it regrew its own WDQS client.
  - ⚠ **Each of those conversions also turned a 429 into a bail.** Under `urlopen` a 429 raised
    `HTTPError` and `except Exception` swallowed it straight back into a 3× retry loop — the
    opposite of the repo's unconditional policy, and indistinguishable from a timeout.
  - `shinto_miraheze/build_ronsha_ranking_queue.py` needed an explicit `sys.path` entry, since the
    transport lives in `modern-quickstatements/`. Not a new cross-subproject dependency: that file
    already writes its output into that directory.
  - Five of the eight carried a byte-identical `_get` for the ja.wikipedia API. **It is still five
    copies.** A shared ja.wp transport is a second module and was not smuggled into this change.

  ✅ **The no-retry-construct population is CLOSED too (2026-09-16). Adopters: 26.** Same property
  that made the dead-429 subclass uniform — a bare request with nothing wrapping it — so migrating
  is the same strict upgrade. Six migrated: `audit_orphan_descriptions.py`,
  `generate_bunrei_quickstatements.py`, `fetch_shrines_tokiponize.py`,
  `generate_chinese_quickstatements.py`, `generate_korean_quickstatements.py`,
  `site/generate_orphan_label_fixes.py`. The last four are outside `modern-quickstatements/` and
  carry the `sys.path` entry `build_ronsha_ranking_queue.py` introduced.
  ✅ **And the CSV callers are in too (2026-09-16). Adopters: 33.** Not by converting them — by
  giving the transport a `query_csv`. Two of them say why in their own docstring: *"CSV, not JSON:
  the JSON body for these result sets comes back truncated."* Converting them to `query` would
  reintroduce, on the very result sets known to provoke it, the failure this module exists to
  survive. The CSV choice is load-bearing; what they were missing was the policy around it.
  `generate_list_membership_rebuild.py`, `generate_list_membership_removals.py`,
  `report_commons_label_accuracy.py`, `report_list_structure.py`, `report_orphan_shikinaisha.py`,
  `report_ronsha_list_membership.py`, `generate_p958_candidates_page.py`.
  - ⚠ **`query_csv` is NOT as protected as `query`, and the gap is real.** A truncated JSON body
    raises `JSONDecodeError` and is retried; a truncated CSV body is still valid CSV, just shorter.
    Only the truncations the transport itself notices — `IncompleteRead`, a dropped connection, a
    timeout — are catchable. A clean mid-stream close on a chunked response returns fewer rows and
    nothing raises. That was equally true of all seven hand-rolled versions; it is written down so
    nobody reads `query_csv` as making CSV safe.
  - ⛔ **`query` and `query_csv` share one `_run`, and the parse runs INSIDE the `with`.** Moving it
    out — read bytes in the loop, decode after — would put the one failure this module was built for
    outside the thing retrying it. Pinned by `test_the_parse_happens_inside_the_retry_loop`.
  - ⚠ **A caller is CSV or JSON by its Accept header, not by what its function is called.** This
    queue listed `generate_p958_candidates_page.py` as a JSON caller until it was read: its function
    is `fetch`, not `sparql_csv`, and it sends `Accept: text/csv`.

  ✅ **And the sub-floor pacers (2026-09-16). Adopters: 42.** Nine callers paced WDQS at **0.3–0.5s**
  against the 2.5s floor CLAUDE.md sets — 0.5 is the exact figure it cites from the incident that
  set the floor, and 0.3 is `READ_INTERVAL`, which `wd_pace.py` says in its own docstring not to
  pace a SPARQL caller at. All nine also backed off 5/10/15 against the documented 15/45/135, and
  one had no backoff at all.
  - ⛔ **Every one of them was a POST caller**, each carrying a VALUES clause, and the transport was
    GET-only. Its own note said *"if a caller ever needs one, add POST rather than chunking around
    it here"* — they needed one. `query(..., post=True)` puts the same encoded string in the body
    instead of the URL; pinned by `test_post_puts_the_query_in_the_body_and_not_the_url`.
  - `test_no_wdqs_caller_paces_below_the_documented_floor` now walks the tree for this shape. It
    **found a ninth file the hand survey missed** — `bfs/buddhist_deity_analysis.py` at 0.3s, whose
    `_get` is shared with the Wikidata API, so an AST scan looking for a WDQS-only function skipped
    it. Only the WDQS half moved; `_get` stays for the API.

  ✅ **And the catch-and-exit six (2026-09-16). Adopters: 48.** A `try` with no loop is not a retry —
  these caught the failure and exited, so a truncated body ended the run with nothing written, which
  is the failure the module exists for. They read as covered in any grep for `try`.
  `audit_duplicate_rankings.py`, `audit_model_adoption.py`, `generate_saijin_deity_research.py`,
  `investigate_property_modelling.py`, `generate_religious_building_labels.py`,
  `create_shrine_ranking_pages.py`.
  - ⚠ **Two of them are NOT a bare swap and must not be "tidied" into one.**
    `audit_model_adoption.wdqs` returns **None** when a query cannot be answered, deliberately — it
    is an audit, and a server-side timeout is a result it reports, not a reason to die. The swallow
    is kept, wrapped around the transport. `create_shrine_ranking_pages.query_wikidata_p301` degrades
    to `(None, None)` per category for the same reason.
  - ⭐ **Both get their 429 bail back for free**: `SystemExit` is a `BaseException`, so the
    transport's bail passes straight through `except Exception` while everything else still
    degrades. `query_wikidata_p301` had been swallowing 429s outright.
  - `audit_duplicate_rankings.run` also changed SHAPE — it returned the whole JSON document and both
    call sites indexed `["results"]["bindings"]` themselves. Both updated.
  - `test_no_adopter_builds_its_own_wdqs_request` walks the tree for regrowth across ALL adopters,
    not just `MIGRATED` — whose urlopen ban cannot tell a WDQS client from a legitimate API fetcher,
    which is why several of these files can never be listed there. ⚠ It matches a call that NAMES
    the endpoint; a `Request` built first and passed as a variable is not caught. Narrows the gap,
    does not close it.

  ✅ **And the HTTPError-only five (2026-09-16). Adopters: 53.** The subtlest class yet, because
  these read as fully compliant: correct `for wait in (0, 15, 45, 135)` backoff — the repo's own
  pattern — and a correct 429 bail. What they lacked was the retryable **set**. They caught
  `urllib.error.HTTPError` and nothing else, so a truncated body escaped the loop entirely and ended
  the run: **the exact 2026-09-13 incident this module was written for.** They also `continue`d on
  503/504 only, so a 500 or 502 was raised on the first attempt instead of retried.
  `audit_supershrine_collapse.py`, `generate_multi_ordinal_removals.py`,
  `generate_orphan_membership_removals.py`, `generate_tenjinsha_en_labels.py`,
  `report_en_label_without_kana.py`.
  - ⚠ **This is a DIFFERENT class from the one closed on 2026-09-14**, which was the eight catching
    only `ReadTimeout`/`ConnectionError`. Same defect, different narrow clause. The lesson is that
    *having* the right backoff is not evidence of having the right retryable set, and the backoff is
    the part a survey notices.
  - Each keeps its own "nothing measured / wrote nothing" exit, now naming the actual failure —
    the hand-rolled message asserted "kept timing out" unconditionally and would have printed it for
    a malformed query too.
  - ⚠ **`timeout` was hardcoded at 300 in the transport and the callers differ** — 600 in
    `site/generate_orphan_label_fixes.py`, 120 in `fetch_shrines_tokiponize.py`. Adopting without a
    parameter would not have broken visibly; it would have halved the longest query's budget and
    shown up as an occasional timeout. `query()` takes `timeout` now, pinned by
    `test_the_timeout_reaches_urlopen_and_is_not_silently_replaced`, and
    `generate_ontology_census_page.py` no longer accepts one and discards it.
  - A `try` with no loop is not a retry: `audit_duplicate_rankings.py`, `audit_model_adoption.py`,
    `generate_saijin_deity_research.py`, `investigate_property_modelling.py`,
    `generate_religious_building_labels.py`, `create_shrine_ranking_pages.py` catch and exit rather
    than try again. They read as covered in a grep and are not.
  - ⚠ **Do not re-derive the adopter count from a `wikidata.org/sparql` grep.** Migrating a file
    deletes its endpoint constant, so it drops out of that grep entirely — which made the adopter
    count read as 11 instead of 20 on the first pass of this scan. Count `import wdqs_transport`.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-16**: `6d83d5f0` :03, `15ff3f04` :15, `403be522` :42,
    `6730a8f1` 08:03. `CronList` again reported **no jobs at all** at the start of this session, as
    it has at the start of every session that has checked. Every recorded set this file has carried
    has been dead by the time the next session read it. Trust `CronList`, not this line.
    ⚠ `durable: true` does nothing — `CronCreate` says so in its own parameter description ("Has no
    effect — durable persistence is not available"). So the recreate-every-session step is the only
    mechanism there is, not a workaround for one that keeps failing.
    ⚠ The 08:03 briefing has **no skill in this repo** — `deep-briefing` lives in the hub and there is
    no `DAILY.md` here, so its prompt was written from what `DEVLOG.md` 2026-08-27 records of it:
    skip-check, push, then `AskUserQuestion` as the deliverable.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
