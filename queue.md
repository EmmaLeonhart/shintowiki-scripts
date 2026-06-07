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

- [ ] **10 QID-overlap MERGE cases — BLOCKED on Emma's merge-route call (decision B).** Examined all 10: both sides are substantial real articles (e.g. Kehi Shrine = 100k, Izanagi Jingū = 60k), NOT stub+article — blind redirect would destroy content. Partner pages now pulled into `git_synced/` + tagged (both sides synced). Awaiting Emma: route to duplicated-content cloud-queue merger, or per-pair manual? **prefer the "Jingū" / proper title over "…Shrine" / romanised variant**; several have ambiguous canonical (two romanisations). Do NOT auto-redirect substantial articles. Cases: `Kehi Jingū`↔`Kehi Shrine` (Q11129346), `Izanagi Jingu`↔`Izanagi Jingū` (Q10884977), `Iwaki no Kuni no Miyatsuko`↔`Ishikami no Kuni no Miyatsuko` (Q11585422), `List of Kuni no Miyatsuko`↔`Kuni no miyatsuko` (Q2483673), `Mukuda…`↔`Makuta Kuni no Miyatsuko` (Q11667981), `乎止与命`↔`Otoyo no mikoto` (Q97706258), `无邪志国造`↔`Musashi no Kuni no Miyatsuko` (Q11504612), `椎根津彦`↔`Saonetsuhiko` (Q11120574), `道奥菊多国造`↔`Michinoku Kikuta Kuni-no-Miyatsuko` (Q11641674), `List of Shikinaisha in Awa Province`↔`List of Shikinaisha in Awa Province (Chiba)` (Q11450714).
- [ ] **26 no-hit — no Wikidata item found.** Biographies, sect-specific docs, shinto-coined terms, list/disambiguation pages. These need an article created first (overlaps backlog item 8, deleted-QID recreation) or should stay unconnected. Leave for now; don't force.
- [ ] **Cleanup when the operation completes:** delete the one-off scripts `pull_unresolved_wikidata_to_git_synced.py`, `build_wikidata_resolution_csv.py` (+ `.out.csv`), `fill_resolved_wikidata_qids.py` once Part 3 is finished (repo-discipline: don't leave one-offs around).

## git-synced clobber recovery (Emma, 2026-06-07)

Bug fixed + audit done (6 clobbers / 5 pages, all Emma's edits — see DEVLOG). `Open questions` (06-07) + `Main Page` recovered; `Open questions` (05-27) superseded. Remaining:
- [ ] `Yang Water Monkey` / `Yin Metal Pig` / `Yin Metal Snake` (2026-05-11) — each lost `[[Category:qqqqqqqqqqqqqqqqq]]`, a junk/test category (likely Emma testing whether wiki edits survive). NOT recovered — confirm with Emma these were tests; else recover. Asked on [[Open questions]].
- [ ] Delete `audit_git_synced_clobbers.py` (+ `.out.json`) once recovery is confirmed done.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
