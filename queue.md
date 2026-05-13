# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation
translation, fandom template fixup, shrine-disambig content strip)
lives in `remote_queue.json` and is worked by the remote-Claude cron
— not duplicated here.

## Action items

Shrine-disambig SPARQL extraction follow-ups: 4 disambig pages have
unusual ledes the kanji extractor can't parse (Kobe disambiguation,
Kōtai Shrine disambiguation, Meiji, Nitta Shrine — Nitta and Kōtai
already have the auto-generated block, Kobe and Meiji still don't).
15 pages had 0 exact-label SPARQL matches and need a broader query
(UNION over skos:altLabel + prefix matching; the broader query timed
out at >60s and needs WDQS optimization). Both follow-ups are
tooling/query work, not page-by-page LLM editing.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
