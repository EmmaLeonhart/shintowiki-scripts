# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

_The English-label-first translation agenda (metabolized 2026-06-21) is complete: the 4-stage English-label pipeline (Stage 3 dropped per Emma), both downstream generators repointed to English, zh script variants, the per-language coverage registry (`shinto-label-generator/language_registry.py`, 44/116 covered), Vietnamese/Bengali/Greek/Hebrew + European/Latin affix batches, and the CJK→ja backfill all shipped. See `docs/english_label_pipeline.md` and `docs/language_coverage.md`. The remaining long-tail languages (Thai/Burmese/Georgian script maps, single-digit-label langs) were deliberately not hand-built — they failed the verification gate or are too low-value — and are left for the LLM/manual per Emma's scope decision._

---

## 2026-06-23 22:00 — Buddhist-temple label sprint (definitive close-out) [PRELIMINARY DOC; full run fires via cron at 10pm]

> This is the intended **definitive ending** of shintowiki-scripts: after this run the repo joins Aelaki as a finished, self-running bot (off Emma's active "compartment" board — tracked as a meta item in the `central-command` repo's `META-AGENDA.md`).

**Goal:** apply the same Japanese-name → English → all-languages label-propagation the repo already does for Shinto shrines to **Japanese Buddhist temples**, then actually edit the wiki/Wikidata.

**Scope — Japanese temples only.** Restrict to Buddhist temples *in Japan*: SPARQL `?item wdt:P31 wd:Q5393308 . ?item wdt:P17 wd:Q17 .` (Q5393308 = Buddhist temple, Q17 = Japan). Reason (Emma): the Japanese→other-language translation conventions only hold for Japanese temples; e.g. a Thai temple should be rendered Japanese→Thai by Thai convention, and its English name does not propagate cleanly to the other languages. Existing infra already targets this set — see `shinto-label-generator/fetch_shrines_tokiponize.py` (its SPARQL already unions shrines with `Q5393308 + P17 Q17`).

**Naming convention for temples:** `<name>-<suffix> Temple` — unlike shrines, temples are inconsistent, so **preserve the full Japanese reading**: the temple name, a hyphen, the suffix, a space, then the word `Temple`. (Confirm against existing prefix/suffix handling before generating.)

**Bracket rule (applies to everything, always):** strip bracketed content from the Japanese label *before* any search/translation. Brackets do not belong in Wikidata labels — they are a labelling error. All searching, dedup (identically-named temples), and the Claude translation step run on the bracket-stripped name.

**Steps for the 10pm run:**
1. Write a fresh SPARQL query for Japanese Buddhist temples (Q5393308 + P17 Q17) with source labels, run it locally (mirror `fetch_shrines_tokiponize.py`), save the dataset, and investigate coverage/gaps.
2. Audit what temple infra already exists vs. what's shrine-only; extend the multilang generators (`generate_multilang_quickstatements.py` + per-language) to temples using the `<name>-<suffix> Temple` convention and bracket-stripping.
3. Generate English labels first, then propagate to the covered languages (reuse `language_registry.py`).
4. Verify (tests + spot-checks), then **apply** to the wiki/Wikidata following the established patterns (mwclient / QuickStatements, `--apply`, rate-limit sleeps, UA + Unicode handling per the global rules). Real edits, not a dry run only.
5. Commit per repo convention (delete this queue item, append to `DEVLOG.md`); report outcome back into `central-command/META-AGENDA.md`.

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
## Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-06-22)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.

