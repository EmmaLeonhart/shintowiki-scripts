# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Currently watching

1. **Resolver run on its first real cycle.** `resolve_double_category_qids.py` re-enabled in commit 6c1bc3d, drain branch added in 12eef5a, post-drain redirect added today. First push-triggered cleanup-loop run is `25408189695` (in_progress as of writing). Once it completes, check that:
   * Single-existing-target dabs got `#REDIRECT [[Category:Foo]]` (the missing-target branch).
   * Multi-target English+Japanese dabs got the drain (Japanese cat: merge notice + crud tag in one edit; members double-categorized into the English cat). The dab page itself stays in the `Currently double category qids` review buffer; the redirect lands on a future cycle automatically once the crud-categories sweep deletes the now-empty Japanese cat. This forced multi-cycle pacing is intentional — slow enough that a human can intervene on any one case, but doesn't require them to.
   * Run did not exceed the wiki-cleanup timeout (resolver step has 200-page cap + 0.3s read throttle, but each drain can blow `--max-edits` quickly).

2. **fandom-sync first run with the content-commit fix.** The next `Independent Pages Sync` run (either standalone 11:30 UTC or the cleanup-loop fan-out at 18:00 UTC) should land ~948 fandom + ~106 miraheze `.wiki` files into the repo. Confirm `fandom_unique/` count jumps from 8 to ~1000 after that run.

3. **Portable infobox conversion — needs hand-conversion, no viable auto-converter.** `fandom_unique/` has 255 `Template%3AInfobox*.wiki` files; 5 are already portable (the 4 broken-interwiki ones from commit `9b3b52b` plus `Template:Infobox Ancient Aristocrat`), 250 are not. Tried writing a converter (`convert_to_portable_infobox.py`, deleted after analysis) that maps the `{{Infobox | labelN | dataN}}` pattern to `<infobox><data source><label>`. Of 250 non-portable templates the script would only "convert" 4, and those 4 are `child=yes` sub-templates that should stay as MediaWiki children, not become standalone `<infobox>` blocks. Of the rest: 95 have Lua/parser-function-driven construction at the top level (`{{#invoke:WikidataIB|...}}`, `{{#invoke:InfoboxImage|...}}`, etc.) that can't be mechanically translated; 88 have no `{{Infobox}}` block at all (mostly `/doc` documentation subpages or redirects); 51 use a different MediaWiki infobox style without the `labelN/dataN` numbered-pair convention. Per-template hand-conversion is the only viable path. Earlier portable conversions in this repo (commits `9b3b52b`, `68f6fed`) were also done by hand.

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

## Stuff

  Watching now (status.md)

  1. Resolver first real cycle — resolve_double_category_qids first push-triggered run; check Japanese cats got drain notice + crud tag, single-target dabs got #REDIRECT.
  2. fandom-sync first content-commit run — confirm fandom_unique/ jumps from 8 to ~1000 files.
  3. Portable infobox conversion — 250 fandom infobox templates need hand conversion (no viable auto-converter; 5 already done).

  Open follow-ups

  4. Enable interlang_consolidate in cleanup-loop — flip enable_interlang_consolidate: true on the four orchestrator calls, once Template:Wikidata link is updated for new positional |lang|title pairs.
  do this, I thought it was already done
  5. 4667 placeholder XML files in xml/unknown/ — confirm none have real data, batch-delete.
  do this
  6. fix_double_redirects flailing — possibly fighting itself; needs a completed run to inspect.
  do this if it is happening

  Wiki content (manual / mostly blocked)

  7. Translate ~290 need_translation/ files — blocked on history_offload completion for those pages.
  most of these were done but postpone
  8. Manually undelete User:Immanuelle/common.js — needs steward/sysop hands; bot can't restore other users' JS.
  did it
  9. Audit other ns=2,3 .js/.css/.json deleted by EmmaBot before the guard landed.
  nah do not do this
  10. ILLs without WD= — fill in missing WD= values per local context.
  idk what this is, my thought is defer for later
  11. 621 duplicate-QID disambiguation pages — automated for easy cases; the rest need human review.
  I think we did this
  12. Translate Category:Japanese language category names — manual.
  I think we did this
  13. Pages with duplicated content — pick canonical title, history-merge case-by-case.
  I think we did this
  14. Recreate Category:Categories_missing_wikidata with split into "missing interwikis" vs "has interwikis but no QID".
  I think we did this
  15. Categories with interwikis but no {{wikidata link}} — re-run wikidata-link script.
  I think we did this
  16. Multiple {{wikidata link}} on one page — disambiguation review per case.
  I think we did this
  17. Fix Shikinaisha pages with broken ILL "Unknown" destinations.
  do this
  18. Audit category pages for race-condition artifacts from the old resolve_category_wikidata/create_category_qid_redirects run.
  do this
  19. Template:Talk page header edit for migrated talk page format.
  not doing this
  20. Investigate replace_p1027_with_p459.txt — purpose unclear; remove or integrate.
  do this
  21. Enrich autocreated stub categories with interwikis/wikidata/parents.
  not doing this
  22. Special:WantedPages / WantedTemplates — unscheduled, plan unclear.
  not doing this

  Repo / script

  23. Rewrite ~23 fandom Template:Infobox X to Portable Infobox XML (priority: Infobox religious building, Japanese Temple, Japanese Kofun, Officeholder, Noble).
  Fix all of these, but I think they are all done
  24. commit_state.sh rebase-conflict fix — add merge=union .gitattributes for line-based orchestrator state files.
  not sure whether to do this
  25. Drop sync_git_synced_pages.state / sync_need_translation.state — derive baseline from git log + wiki history.
  not worth changing
  26. Secret removal before open-source — rotate creds → git filter-repo --replace-text rewrite → force-push → coordinate clones.
  Finished
  27. Node 20 deprecation — bump actions/checkout@v4 and actions/setup-python@v5 before 2026-06-02.
  fix this script

  July 2026 audit

  28. Confirm + remove terminating cleanup scripts: reimport_from_enwiki, migrate_talk_pages, normalize_category_pages (Sun), remove_legacy_cat_templates (monthly).
  Wait until then

  External

  29. Wikidata item deletions — assess scope of items deleted by another editor; plan re-creation.
  Make a script that creates items for the deleted item qids

  Architecture (VISION.md)
On indefinite hold
  30. Namespace restructure (Data:/Meta:/Export:).
  31. Move {{ill}} data to Export:.
  32. Category name standardization via Wikidata.
  33. Pramana integration as canonical ID backend.
  34. Automated translation pipeline.
  35. Change-tracking bot across namespace layers.

  Anything you want me to start on right now?