# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Archive-push window (2026-04-24 → 2026-05-05)

Per-orchestrator edit limits are biased to move mainspace and template to fandom / GitHub archive as fast as possible:

| Orchestrator | Edit limit during window | After 2026-05-05 (catchup) | After 2026-06-01 |
|---|---|---|---|
| mainspace | **1000** | 500 | 100 |
| template  | **1000** | 500 | 100 |
| category  | **10**   | 500 | 100 |
| miscellaneous | **10** | 500 | 100 |

**Why**: mainspace is the primary thing we want archived; template is the next biggest. Category and misc drop to 10 so they don't compete for runner minutes during the push. Implemented in `.github/workflows/cleanup-loop.yml`'s `window-gate` (per-orchestrator-edit-limit outputs).

**Mid-window tweaks (pending decision, not yet coded):**
* If the template orchestrator **completes a full cycle** inside this window (state clears, nothing left to offload), shift the freed budget to mainspace: bump mainspace to **1500**, keep category/misc at 10.
* Once mainspace has been **fully imported**, drop everything to a uniform 500 (matches the outer catchup baseline).

## Open follow-ups (from the history-offload rework)

1. **Enable `interlang_consolidate` in cleanup-loop.** The op is implemented on all four orchestrators and gated by `ENABLE_INTERLANG_CONSOLIDATE=1`. The original blocker was `Template:Wikidata link` not supporting the new positional `|lang|title` pairs; the template is now in `git_synced/` so edits can be made locally and CI-pushed. Flip `enable_interlang_consolidate: true` on the four orchestrator calls in `.github/workflows/cleanup-loop.yml` once the template has been updated. With this on, each page the orchestrator processes should get ~3 edits per run (fandom mirror + delete-recreate + interlang consolidate), up from ~2 currently.

2. **Review the 4667 files now sitting in `xml/unknown/`** in EmmaLeonhart/shintowiki-xml-archives. They were siteinfo-only placeholders from runs where Special:Export returned empty. Confirm none contain real data; delete as a batch once verified. The `history_offload` guard added in 845da03 prevents new placeholders from accumulating.

## Minor stuff

The `interlang_consolidate` op is implemented (all four orchestrators) but deliberately gated behind `ENABLE_INTERLANG_CONSOLIDATE=1`, which is NOT set from cleanup-loop.yml. Flip that input to `true` on the four orchestrator calls in `.github/workflows/cleanup-loop.yml` once `Template:Wikidata link` has been updated to accept the new positional `|lang|title` pairs. Template edits go via `git_synced/` (tag `Template:Wikidata link` on the wiki with `[[Category:Git synced pages]]`, let the sync pull it to the repo, edit locally, push).

Also at least in this run https://github.com/EmmaLeonhart/shintowiki-scripts/actions/runs/24744680692/job/72417848749 there was a lot of redirect related flailing and idk why. I thought we solved the redirects problem several commits ago. (Observation so far: that run's `mainspace-orchestrator` hit the 2h timeout and got cancelled; the orchestrator skips redirects correctly in common.py, so the flailing is probably in `fix_double_redirects.py` — if Special:DoubleRedirects keeps producing the same pages run after run, that script is fighting itself. Run log isn't available until the run finishes, so this is deferred until a completed run with similar behavior can be inspected.)

## Queued work

0. **Retrofit the remaining cycling script into an orchestrator op.** Most of this item is done; what's left is `populate_namespace_layers.py` → `ops/namespace_layers.py` (mainspace only; creates/edits sibling pages in Data:/Export: namespaces; `HANDLES_SAVE = True`). It isn't currently wired into `wiki-cleanup.yml` (the docstring notes the Data:/Export: namespaces aren't created on the wiki yet), so porting it is blocked on the wiki-side namespace creation. Once those namespaces exist, port it and wire it into `mainspace_orchestrator` with `HANDLES_SAVE = True`.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
