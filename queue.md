# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Interlanguage-resolution operation (Emma, 2026-06-07) — Part 3 remaining

Parts 1+2 done (57-page cohort pulled into `git_synced/`, tagged into
`[[Category:Git synced pages]]` + `[[Category:Pages git synced to resolve
interlanguage and interwiki links]]`, sync dispatched). Part 3a done (CSV:
`shinto_miraheze/build_wikidata_resolution_csv.out.csv`). Part 3b done (14
exact-label non-overlap QIDs filled + pushed). Remaining:

- [ ] **QID-overlap merges — GO (Emma 2026-06-08: "combine and redirect, Jingū always wins").** Both sides are substantial real articles (dup-content cloud-queue is within-page only, doesn't fit), so these are per-pair editorial merges — do ONE carefully per tick, reviewable, never blind. Status:
  - DONE (redirect-to-fuller, verified the canonical covers the cohort): `Izanagi Jingu`→`Izanagi Jingū`; `乎止与命`→`Otoyo no mikoto` (Q97706258); `道奥菊多国造`→`Michinoku Kikuta Kuni-no-Miyatsuko` (Q11641674 — canonical's Ancestry/Clan/Shrine/See-Also sections cover the cohort's Lineage/Tutelary-shrine prose + full-ja-history import).
  - Canonical clear but CONTENT-MOVE needed (the non-canonical holds MORE content, so move content into the canonical-title page first, then redirect): `无邪志国造` (16k) → `Musashi no Kuni no Miyatsuko` (7k, Q11504612); `Kehi Shrine` (100k) → `Kehi Jingū` (21k, Jingū wins, Q11129346); `List of Shikinaisha in Awa Province` → `…(Chiba)` (Q11450714).
  - AMBIGUOUS / verify before acting — flag for Emma if still unclear: `Iwaki`↔`Ishikami no Kuni no Miyatsuko` (Q11585422, two romanisations of 石城国造 — which title?); `Mukuda`↔`Makuta Kuni no Miyatsuko` (Q11667981, two romanisations); `椎根津彦`↔`Saonetsuhiko` (Q11120574 — WD label was "Shiinetsuhiko", name mismatch, verify it's the same person); `List of Kuni no Miyatsuko`↔`Kuni no miyatsuko` (Q2483673 — a LIST vs the CONCEPT page; may not be a real merge, the QID overlap could be wrong).
- [ ] **26 no-hit — no Wikidata item found.** Biographies, sect-specific docs, shinto-coined terms, list/disambiguation pages. These need an article created first (overlaps backlog item 8, deleted-QID recreation) or should stay unconnected. Leave for now; don't force.
- [ ] **Cleanup when the operation completes:** delete the one-off scripts `pull_unresolved_wikidata_to_git_synced.py`, `build_wikidata_resolution_csv.py` (+ `.out.csv`), `fill_resolved_wikidata_qids.py` once Part 3 is finished (repo-discipline: don't leave one-offs around).

## git-synced clobber recovery (Emma, 2026-06-07)

Bug fixed + audit done (6 clobbers / 5 pages, all Emma's edits — see DEVLOG). `Open questions` (06-07) + `Main Page` recovered; `Open questions` (05-27) superseded. Remaining:
- [ ] `Yang Water Monkey` / `Yin Metal Pig` / `Yin Metal Snake` (2026-05-11) — each lost `[[Category:qqqqqqqqqqqqqqqqq]]`, a junk/test category (likely Emma testing whether wiki edits survive). NOT recovered — confirm with Emma these were tests; else recover. Asked on [[Open questions]].
- [ ] Delete the clobber-audit one-offs (`audit_git_synced_clobbers.py`, `measure_clobber_degree.py`, their `*.out.json`) once Emma has reviewed the clobber situation. Degree measured 2026-06-08: 116 events / 85 of 138 pages, but SMALL (≤41 lines/event, ~271 total); 6 human (26 lines, recovered) + 110 bot (orchestrator↔sync churn, self-healing, no permanent loss). No further recovery needed unless Emma wants the 110 chased.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
