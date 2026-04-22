# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Minor stuff

The `interlang_consolidate` op is implemented (all four orchestrators) but deliberately gated behind `ENABLE_INTERLANG_CONSOLIDATE=1`, which is NOT set from cleanup-loop.yml. Flip that input to `true` on the four orchestrator calls in `.github/workflows/cleanup-loop.yml` once `Template:Wikidata link` has been updated to accept the new positional `|lang|title` pairs. Template edits go via `git_synced/` (tag `Template:Wikidata link` on the wiki with `[[Category:Git synced pages]]`, let the sync pull it to the repo, edit locally, push).

Also at least in this run https://github.com/EmmaLeonhart/shintowiki-scripts/actions/runs/24744680692/job/72417848749 there was a lot of redirect related flailing and idk why. I thought we solved the redirects problem several commits ago. (Observation so far: that run's `mainspace-orchestrator` hit the 2h timeout and got cancelled; the orchestrator skips redirects correctly in common.py, so the flailing is probably in `fix_double_redirects.py` — if Special:DoubleRedirects keeps producing the same pages run after run, that script is fighting itself. Run log isn't available until the run finishes, so this is deferred until a completed run with similar behavior can be inspected.)

## Queued work

0. **Retrofit the remaining cycling script into an orchestrator op.** Most of this item is done; what's left is `populate_namespace_layers.py` → `ops/namespace_layers.py` (mainspace only; creates/edits sibling pages in Data:/Export: namespaces; `HANDLES_SAVE = True`). It isn't currently wired into `wiki-cleanup.yml` (the docstring notes the Data:/Export: namespaces aren't created on the wiki yet), so porting it is blocked on the wiki-side namespace creation. Once those namespaces exist, port it and wire it into `mainspace_orchestrator` with `HANDLES_SAVE = True`.

4. **Translate the remaining untranslated `need_translation/` pages.** After tasks 1–3 clear: the `need_translation/` directory has ~290 files still carrying `[[Category:Need translation]]`. Nine of them are the large kokuzo articles that actually matter: `国造.wiki` (8669 CJK), `无邪志国造.wiki` (5141), `出雲国造.wiki` (4527), `千葉国造.wiki` (1763), `尾張国造.wiki` (1640), `倭国造.wiki` (1346), `廬原国造.wiki` (982), `斐陀国造.wiki` (854), `伊勢国造.wiki` (841). 83 files are shrine pages with `== Japanese Wikipedia content ==` sections (auto-generated English top + Japanese body). Translate using `{{ill|English|ja|Japanese|lt=Display|lt_ja=Japanese Display}}` per `feedback_translation_link_rules.md` in memory. Never remove `[[Category:Need translation]]` without verifying the body is actually English — CI deletes the file from the repo when the category is gone.


## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
