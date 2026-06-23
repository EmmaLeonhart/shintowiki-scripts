# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

_The English-label-first translation agenda (metabolized 2026-06-21) is complete: the 4-stage English-label pipeline (Stage 3 dropped per Emma), both downstream generators repointed to English, zh script variants, the per-language coverage registry (`shinto-label-generator/language_registry.py`, 44/116 covered), Vietnamese/Bengali/Greek/Hebrew + European/Latin affix batches, and the CJK→ja backfill all shipped. See `docs/english_label_pipeline.md` and `docs/language_coverage.md`. The remaining long-tail languages (Thai/Burmese/Georgian script maps, single-digit-label langs) were deliberately not hand-built — they failed the verification gate or are too low-value — and are left for the LLM/manual per Emma's scope decision._

_Japanese Buddhist temples now run the FULL automatic pipeline, same as shrines (shipped 2026-06-23, see DEVLOG): **Stage 1** deterministic kana→`<Stem>-<suffix> Temple` (`temple_english.py` + `generate_temple_en_labels.py`, 359/378 kana temples) AND **Stage 4** the cloud Sonnet routine — `select_shrines_to_translate.py` now returns a shrine batch + a temple batch (kind-tagged) from `temples_missing_en_label.json`, so the kana-less majority (~14.5k) flows through the LLM automatically with no cloud-side change and no shrine starvation. The daily worklist workflow refreshes both lists (new temples added to Wikidata flow through), the drip applies, and the multilingual generators propagate from English downstream._

---

## Temple close-out — full pipeline shipped; verify-only residual

The temple en-label pipeline now runs every stage shrines have:
- **Stage 1** deterministic kana → `<Stem>-<suffix> Temple` (`temple_english.py`).
- **Stage 2** identical-name reuse from same-ja-name Japanese temples (`generate_temple_identical_name_en_labels.py`, sharing the parametrized `generate_identical_name_en_labels.run`).
- **Stage 4** LLM via the cloud Sonnet routine (`select_shrines_to_translate.py` returns a temple batch; `"kind":"temple"` tag).
All wired into `ATOMIC_FILES`, `EXCLUDE_FILES`, and the daily worklist workflow; new temples flow through on refresh.

Remaining (verify / cloud-side only, not coverage gaps):
- **Cloud-prompt note:** the Sonnet routine receives `"kind":"temple"` items; it can use the tag to enforce the exact `<Stem>-<suffix> Temple` form. Translation works regardless.
- **Verify after the first drip cycles:** confirm temple en-labels land on Wikidata and the `shinto-label-generator` multilang generators propagate them to other languages.

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
## Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-06-22)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.
