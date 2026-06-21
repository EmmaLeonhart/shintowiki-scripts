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

- [ ] **A1. Stage 1 — deterministic kana→English generator (highest priority).** For shrines with a `ja` label + kana (P1814/P5461) but no `en` label: build the English label by deterministic rules from the kana using the romanization conventions above. Emit `Qxxx|Len|"…"` (+ `Lan` aliases for jingu/taisha). Do NOT use the inaccurate pykakasi/Indonesian library. Output to an atomic `.txt` wired into `submit_daily_batch.py`. Verify on a sample before wiring.
- [ ] **A2. Stage 2 — identical-Japanese-name reuse generator.** For shrines with `ja` but NO kana and no `en`: SPARQL for other shrines sharing the identical `ja` label that DO have an `en` label. Rules: if one English label is dominant → use it, add the less-common reading as an alias; if tie → pick one at random; only add an alias when there is exactly one other distinct reading. Adds-only (no removals). Emit `Len` + `Lan`.
- [ ] **A3. Stage 3 — non-CJK transliteration fallback.** For shrines with no `en`, no kana, no identical-name match, but a label in some non-CJK script (Latin/Cyrillic/etc.): transliterate with a standard library, drop the second word, replace it with "Shrine". Expected to be a rare edge case — keep it simple.
- [ ] **A4. Stage 4 — LLM remote-queue fallback.** Everything still without an `en` label after A1–A3 goes to the existing claude.ai Sonnet remote routine for translation (5/day drip). Confirm this fires only on the residual set and is correctly last in priority order. Mostly exists — verify ordering and the worklist hand-off (`select_shrines_to_translate.py`).
- [ ] **A5. Wire the four stages into one ordered run** so each stage's worklist excludes shrines already handled by an earlier stage, and the daily submitter draws from all of them.

## STAGE B — downstream language generators seeded from the English label

- [ ] **B1. Repoint the non-CJK multilang generator to the English label.** `shinto-label-generator/generate_multilang_quickstatements.py` currently sources from Indonesian labels (its docstring says so) for tr/de/nl/es/it/eu/lt/ru/uk/fa/ar/arz/hi/fr/pt. Make it derive from the `en` label going forward, WITHOUT deleting existing Indonesian-derived output. Toki Pona (`tokiponizer`) should also flow from English.
- [ ] **B2. Confirm CJK + Korean derive from the Japanese label directly.** zh and its sublanguages (zh-hant, zh-hk, zh-hans, zh-tw, zh-cn, zh-sg, yue, nan, wuu, hak, lzh…) copy characters from the `ja` label; Korean uses its hangul/hanja special case. These do NOT route through English — verify and document.
- [ ] **B3. Institutionalize one generator per language using `query.csv`.** Build a registry covering every language column in `query.csv`; each language gets a generator whose job is to fill that column toward the top. Many exist (the 15 in B1 + zh/ko/tok); add generators for the long tail that lacks one. For low-sample languages whose existing Wikidata convention looks clearly wrong (e.g. Tibetan `bo` was noted as bad), inspect the actual existing labels and either continue a good pattern or invent a sane convention rather than copying the bad one.
- [ ] **B4. Add new-language generators: Bengali (`bn`), Vietnamese (`vi`).** Then verify the pipeline status of Indonesian (`id`), Malay (`ms`), Japanese (`ja`), English (`en`) — Mistral may have muddied which of these are already covered; confirm against the code.

## STAGE C — edge case (low priority, do not fret)

- [ ] **C1. CJK-name-but-no-Japanese-label backfill.** If a shrine has no `ja` label but has a name in another CJK language, copy that CJK name onto the `ja` label (via QuickStatements). Rare edge case — keep minimal.

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
