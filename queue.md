# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation
translation, fandom template fixup, shrine-disambig content strip)
lives in `remote_queue.json` and is worked by the remote-Claude cron
— not duplicated here.

## Active

- [ ] **Wire up the remote-Claude consumer for `remote_queue.json`.** The build side (`build-remote-queue.yml`) runs daily and the queue has 1,097 items, but the consume side is dead: zero non-CI commits to `duplicated_content/`, `need_translation/`, `fandom_unique/`, or `miraheze_unique/` since 2026-05-01. The original "remote-Claude cron" referenced in `queue.md` was either never wired up or has been decommissioned. Design a new GitHub Actions workflow (`work-remote-queue.yml`) that uses the Anthropic API (or the `claude-code` GitHub Action if available) to take the next N items from `remote_queue.json`, perform the per-file instruction, and commit results. Requires `ANTHROPIC_API_KEY` secret. Start with a small N (e.g. 3) and a generous `timeout-minutes`; pace via a cron schedule that respects the wiki's tolerance for downstream sync churn.
- [ ] **CronCreate: in-session self-paced work on `remote_queue.json`.** While the GHA consumer is being designed, set up an in-session `CronCreate` so I (current Claude) pick the next queue item every N minutes, do the local edit, commit, and push. Auto-expires in 7 days. Hand-off: once the GHA workflow above is shipping commits, this in-session cron can be deleted.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
