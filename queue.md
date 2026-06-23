# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

_The English-label-first translation agenda (metabolized 2026-06-21) is complete: the 4-stage English-label pipeline (Stage 3 dropped per Emma), both downstream generators repointed to English, zh script variants, the per-language coverage registry (`shinto-label-generator/language_registry.py`, 44/116 covered), Vietnamese/Bengali/Greek/Hebrew + European/Latin affix batches, and the CJK→ja backfill all shipped. See `docs/english_label_pipeline.md` and `docs/language_coverage.md`. The remaining long-tail languages (Thai/Burmese/Georgian script maps, single-digit-label langs) were deliberately not hand-built — they failed the verification gate or are too low-value — and are left for the LLM/manual per Emma's scope decision._

_Buddhist-temple deterministic en-labels shipped 2026-06-23 (see DEVLOG): `temple_english.py` + `generate_temples_missing_en_label.py` + `generate_temple_en_labels.py`, wired into the daily worklist workflow and `submit_daily_batch.ATOMIC_FILES`. 359/378 kana-bearing Japanese temples get a deterministic `<Stem>-<suffix> Temple` label; the daily drip applies them, and the multilingual generators propagate from English downstream once the en labels land._

---

## Temple close-out — remaining (NOT the deterministic part, which shipped 2026-06-23)

The deterministic kana→English temple step is done and self-running. What remains before the temple side is *fully* closed, deliberately left for a decision rather than done blind:
- **The kana-less majority (~14,515 of 14,893).** Stage 1 only handles temples that carry a kana reading (378). The rest have no `P1814` kana, so they need either the Stage 0 wiki-title lookup (only covers temples that have a shintowiki article — unverified coverage) or the Stage 4 LLM routine (currently shrine-scoped, `P31=Q845945`; extending it to temples means feeding 14k items through a 5/day throttle — a multi-year drip, Emma's call whether worth it).
- **Verify application + multilingual propagation** after the first drip cycles: confirm the 359 temple en-labels landed on Wikidata and that the `shinto-label-generator` multilang generators picked them up.

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
## Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-06-22)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.
