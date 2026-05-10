# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Action items

**TOP PRIORITY (2026-05-10): `sync_git_synced_pages.py` was silently
deleting wiki pages from the local mirror.** Discovered during the
git_synced annotation pass: only 67 of ~238 wiki-side category members
were present locally. Root cause: `iter_category_with_revisions` used
a generator+content query whose continuation semantics MediaWiki
caps at ~50 pages per batch — pages outside the current 50-slice came
back without a `revisions` field, the script's `if not revs: continue`
swallowed them, and the downstream "page no longer in category → delete
local file" branch then deleted them on the next run. Confirmed
casualties in `git log -- git_synced/`: `Shinto Wiki.wiki`,
`Christianity.wiki`, `Template%3AWikidata link.wiki`, and many others
were deleted across the recent sync commits.

  * **Fixed in commit on 2026-05-10**: switched the iter to a two-pass
    design — pass 1 lists every category member's title only, pass 2
    fetches revisions+content in batches of 50 using `titles=` instead
    of a generator. No silent drops.
  * **In-flight follow-up**: the user touch-edited every wiki page in
    the category right after the bug was found, so the next git-synced
    sync run will see `wiki_changed=True, local_changed=False` for the
    missing ~172 pages and pull them cleanly (no clash with the recent
    annotation work because that commit was reverted).
  * **Then**: a follow-up cron job (scheduled separately) re-runs the
    "annotate or instruction-apply" pass on the freshly-repopulated
    git_synced/ folder.

Go through the notes of the [[Category:git synced pages]]
Translate all of the [[Category:Need translation]]

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
