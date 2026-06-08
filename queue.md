# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-06-08)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.

## Interlanguage-resolution operation (Emma, 2026-06-07) — Part 3 remaining

Parts 1+2 done (57-page cohort pulled into `git_synced/`, tagged into
`[[Category:Git synced pages]]` + `[[Category:Pages git synced to resolve
interlanguage and interwiki links]]`, sync dispatched). Part 3a done (CSV:
`shinto_miraheze/build_wikidata_resolution_csv.out.csv`). Part 3b done (14
exact-label non-overlap QIDs filled + pushed). Remaining:

- [ ] **26 no-hit — no Wikidata item found.** Biographies, sect-specific docs, shinto-coined terms, list/disambiguation pages. These need an article created first (overlaps backlog item 8, deleted-QID recreation) or should stay unconnected. Leave for now; don't force.
- [ ] **Cleanup (Part 3 now finished — merges done):** delete the one-off scripts `pull_unresolved_wikidata_to_git_synced.py`, `fill_resolved_wikidata_qids.py`, and `build_wikidata_resolution_csv.py` (+ `.out.csv`) — but KEEP the `.out.csv` until Emma finishes the QID spot-check (Open questions references it). Delete scripts now / CSV after the spot-check.

## git-synced clobber recovery (Emma, 2026-06-07)

Bug fixed + audit done (6 clobbers / 5 pages, all Emma's edits — see DEVLOG). `Open questions` (06-07) + `Main Page` recovered; `Open questions` (05-27) superseded. Remaining:
- [ ] `Yang Water Monkey` / `Yin Metal Pig` / `Yin Metal Snake` (2026-05-11) — each lost `[[Category:qqqqqqqqqqqqqqqqq]]`, a junk/test category (likely Emma testing whether wiki edits survive). NOT recovered — confirm with Emma these were tests; else recover. Asked on [[Open questions]].
- [ ] Delete the clobber-audit one-offs (`audit_git_synced_clobbers.py`, `measure_clobber_degree.py`, their `*.out.json`) once Emma has reviewed the clobber situation. Degree measured 2026-06-08: 116 events / 85 of 138 pages, but SMALL (≤41 lines/event, ~271 total); 6 human (26 lines, recovered) + 110 bot (orchestrator↔sync churn, self-healing, no permanent loss). No further recovery needed unless Emma wants the 110 chased.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
