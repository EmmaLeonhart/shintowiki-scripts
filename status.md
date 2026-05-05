# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Currently watching

1. **Resolver run on its first real cycle.** `resolve_double_category_qids.py` re-enabled in commit 6c1bc3d, drain branch added in 12eef5a, post-drain redirect added today. First push-triggered cleanup-loop run is `25408189695` (in_progress as of writing). Once it completes, check that:
   * Single-existing-target dabs got `#REDIRECT [[Category:Foo]]` (the missing-target branch).
   * Multi-target English+Japanese dabs got the drain (Japanese cat tagged crud + members double-categorized) AND the dab page itself ended as a redirect to the English cat.
   * Run did not exceed the wiki-cleanup timeout (resolver step has 200-page cap + 0.3s read throttle, but each drain can blow `--max-edits` quickly).

2. **fandom-sync first run with the content-commit fix.** The next `Independent Pages Sync` run (either standalone 11:30 UTC or the cleanup-loop fan-out at 18:00 UTC) should land ~948 fandom + ~106 miraheze `.wiki` files into the repo. Confirm `fandom_unique/` count jumps from 8 to ~1000 after that run.

3. **Hourly local loop converting non-portable infoboxes to Portable Infobox syntax.** `/loop 1h` scheduled (job `565ff75f`); fires hourly at :23. Once `fandom_unique/` has the bulk of pulled pages, each loop fire scans `Template%3AInfobox*.wiki` for non-portable templates and converts them to `<infobox>` syntax. Stops after 4 iterations or once all infoboxes are portable.

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
