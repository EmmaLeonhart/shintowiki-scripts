# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## STANDING CONSTRAINTS for the label-translation agenda (read before any item below)

- **NON-NEGOTIABLE: never introduce any new direct-API Wikidata editing.** Wikidata is edited by exactly ONE channel: the existing daily QuickStatements drip pipeline, with NO edit summaries. Every item below produces QuickStatements lines into the atomic `.txt` files consumed by `modern-quickstatements/submit_daily_batch.py`. If something cannot be expressed as a QuickStatement, STOP and raise it on `[[Open questions]]` — do not route around the QS pipeline.
- **Do not remove or disrupt existing Indonesian-derived labels** already flowing through the pipeline. The migration is additive: new work derives from English, but the existing `id`-path output stays.
- **Follow Emma's instructions literally** — don't optimize/merge/guess the stages.
- **Add-first / remove-later via SPARQL (two scripts, never one)** whenever an item both adds and removes.
- **Romanization conventions** (the anglicise-but-preserve rules): `jinja → Shrine`; `jingu → Grand Shrine` (keep "jingu" as alias); `taisha → Grand Shrine` (keep "taisha" as alias); `daijinja → Daijinja`; `-sha → -sha Shrine`; `-gu → -gu Shrine`. CJK languages copy the characters; Korean is the special hangul case; everything else flows from the English label.

---

# AGENDA: English-label-first translation pipeline for Shinto shrines

**Vision (one paragraph):** Every run, SPARQL finds Shinto shrines lacking an English label and runs a 4-stage priority pipeline to give them one. The English label then becomes the seed from which all non-CJK downstream languages are generated (replacing the current roundabout Japanese→Indonesian→everything path), while CJK languages derive straight from the Japanese label. The end state is maximum linguistic coverage of every shrine name, drip-fed slowly through QuickStatements. `query.csv` is the coverage scoreboard (ja 30228, en 25171, id 24416, fr 23910, then a steep cliff to zh 1038 and a long single-digit tail) — the goal is to fill every language column toward the top with a dedicated generator.

## STAGE A — the 4-stage English-label generator (do in order; each stage only handles what earlier stages left)

## STAGE B — downstream language generators seeded from the English label

- [ ] **B3. Institutionalize one generator per language using `query.csv`.** Build a registry covering every language column in `query.csv`; each language gets a generator whose job is to fill that column toward the top. Many exist (the 15 non-CJK in `generate_multilang_quickstatements.py` + zh/ko/tok); add generators for the long tail that lacks one. For low-sample languages whose existing Wikidata convention looks clearly wrong (e.g. Tibetan `bo` was noted as bad), inspect the actual existing labels and either continue a good pattern or invent a sane convention rather than copying the bad one.
- [ ] **B4. Add new-language generators: Bengali (`bn`), Vietnamese (`vi`).** Then verify the pipeline status of Indonesian (`id`), Malay (`ms`), Japanese (`ja`), English (`en`) — Mistral may have muddied which of these are already covered; confirm against the code.

## STAGE C — edge case (low priority, do not fret)

- [ ] **C1. CJK-name-but-no-Japanese-label backfill.** If a shrine has no `ja` label but has a name in another CJK language, copy that CJK name onto the `ja` label (via QuickStatements). Rare edge case — keep minimal.

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
