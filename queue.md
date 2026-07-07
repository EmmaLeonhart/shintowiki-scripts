# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here. **Nothing here is "parked" or "out of scope" — every item gets done; ordering is
just priority.** Keep items TERSE (Emma 2026-07-06) — a checkbox + one or two lines; no essays, no
"LAST TASK"-style labels (there's always more). Numbers are priority order, not fixed identity.

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Category-orchestrator throughput (conditional, low priority)

- [ ] A full ns14 category cycle still takes ~many fires at ~1000 pages/145min. ONLY if the
  Japanese-category translation drain (cloud RAG → `category_moves.csv` → monthly `move_categories`)
  proves too slow: skip history_offload/fandom_mirror on the ~3k enwiki-junk cats, or shard ns14. No
  premature optimization. (Cleanup-loop reliability itself is DONE — run 28802688487 green end-to-end.)

## Statement-vocab label propagation for the 07-06 imports (Emma 2026-07-07)

The reisai (P837) + bunrei (P612) imports systematically use vocabulary whose labels need the
same multilingual propagation the QS values got (cf. Q134956795, Q55522291). Day-of-year items
already have ~216 langs (no work). Reisai Q11385469 already flows via misc-terms.

- [ ] Bunrei Q195793: route through the misc-terms transliteration path (explicit extra — BFS
  never reached it; P31 "religious concept" fails the shinto|matsuri filter).
- [ ] P612/P837/P1013/P3831: add to `generate_property_translations.py` hand-authored dict,
  confident languages only (the established rail: omit = "unclear, skip", never guess).

## SPARQL-heavy audits

These need a full SPARQL scan. `query.wikidata.org` is 429-outaged (2026-07-06+), but the SPLIT
endpoint **`query-main.wikidata.org/sparql` works** — use it (it serves everything except scholarly
articles). Heavy, so the 22:00 cron owns them; the hourly loop can also run them via query-main now.

- [ ] **Typo review — routed to cloud RAG 2026-07-06.** 161 kana-vs-label candidates are work-files in
  `label_typo_review/` (builder: `shinto_miraheze/build_label_typo_review_queue.py`), emitted by
  `remote_queue.py`; the cloud worker fills ANSWER (LABEL_TYPO/KANA_ISSUE/PREFIX_OK/OTHER).
  Collector BUILT (`shinto_miraheze/collect_label_typo_answers.py`, 5 tests; LABEL_TYPO →
  `label_typo_fixes.txt` in ATOMIC_FILES) — run it once answers land. Comma cleanup draining (189).
  2026-07-07 late-morning check: 159 pending, no new cloud answers yet.

## 11. Bunrei residual (harvest EXHAUSTED 2026-07-06 — 6 sources, ~10,550 cited edges)

Online 総本社 sources are tapped (jinja-kikou 9,971 / animism 128 / toranomaki 40 / ikkojin 129 /
shinwa-otaku 205 / nicovideo 77; xrea = jinja-kikou dupe; 護国神社 excluded — officially not bunrei).

- [ ] (low) The one unharvested online source: onkamui Rakuten blog (~50 networks with NAMED branch
  enumerations, hierarchical prose — would catch branches whose names don't match their network
  suffix). Heavy parse; do only if the suffix-method coverage proves insufficient.
- [ ] (low) Paper-only: 神社本庁『全国神社祭祀祭礼総合調査』(1995), 岡田荘司『事典 神社の歴史と祭り』—
  authoritative 系統 counts; needs Emma or a library, not scrapeable.

## Session state (2026-07-07 late morning): contained verification session, hard stop 13:00

Today runs on Emma's five one-shot time-gated crons (11:00/11:30 full pace; 12:00/12:30 wrap-up
gradient; 13:00 finished) — they replace the usual 3-cron work-loop for today and die with the
session. Remaining queue items wait on external systems (cloud RAG answers, cloud category drain,
conditional triggers, paper sources); the not-for-today conditionals are written up on
[[Open questions]] for Emma.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
