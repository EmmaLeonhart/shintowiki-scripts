# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, shrine-disambig content strip) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.


## Duplicated-content pipeline — remaining follow-ups (2026-05-23)

Big fixes shipped this session (see DEVLOG 2026-05-23): consumer instruction
rewritten (macro paragraph-merge, NOT param dedup), sync conflict policy set to
**wiki-wins** for duplicated_content + need_translation, queue builder now
shuffles + only queues files that still carry the category, 134 dup pages
re-pulled from the wiki, cursor reset. Still open:

- [ ] **The cloud consumer still uses a cursor.** The claude.ai scheduled
  routine walks `consume_remote_queue.state` through `remote_queue.json`. Emma
  wants statefulness to be purely file-presence + category (no cursor): each run
  should scan `duplicated_content/` for files still tagged
  `[[Category:Pages with duplicated content]]` and pick at RANDOM. The routine's
  PROMPT defines this — it can't be edited from the repo. Reword the routine
  (via claude.ai schedules) to drop the cursor and pick category-tagged files at
  random. (Repo-side mitigations already in place: `remote_queue.py` shuffles +
  category-filters, cursor reset to 0.)
- [ ] **Verify after the next cleanup-loop run** that `sync_duplicated_content`
  resolved the conflicts wiki-wins (pulled, not skipped) and that the consumer,
  with the corrected instruction, actually merges the macro duplication on a
  sample page (e.g. Take Minato Shrine — currently triplicated) and the merged
  result reaches the wiki.

## Wikidata: カミノヤシロ kana — manual-review leftovers (bot request 2026-02-26)

Both bot jobs shipped (see DEVLOG 2026-05-23). Part 2's katakana gate left
behind cases that need a human (the move/append bots skip + report them):

- [ ] **18 Q135038714 items the part-2 bot won't touch.** From the dry-run census:
  2 items with >1 ojp-hani P1448 (ambiguous attachment), 1 with a katakana
  standalone kana but no ojp-hani P1448, and 15 whose standalone P1814 is a
  *modern hiragana* reading (e.g. `いめじんじゃはちまんぐう`) needing a modern `ja`
  official name, not the ojp-hani path (must NOT get カミノヤシロ). QIDs print in
  the workflow log / via `--dry-run`.


## shinto-label-generator — remaining piece (2026-05-23)

Subtree merged + generator workflow relocated + 20/day label drip-feed wired
(see DEVLOG 2026-05-23). Still open:

- [ ] **Pages consolidation + redirect** (from the original subtree spec): publish
  the label-generator `docs/` report as a subpage of
  emmaleonhart.github.io/shintowiki-scripts/ (wire into generate-pages.yml), then
  turn the standalone shinto-label-generator repo's GitHub Pages (`docs/index.html`)
  into a redirect to that subpage. Not yet done.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
