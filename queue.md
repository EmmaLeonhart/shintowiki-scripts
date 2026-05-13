# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Action items

TRY TO CLEAR THE BLOAT FROM THIS PAGE IT IS WAY TOO HIGH and involves already completed stuff

Go through the notes of the [[Category:git synced pages]] — each
git_synced/ page has a leading `<!--...-->` instruction comment, and
those instructions must actually be executed, not just present.
* **60 Sexagenary cycle pages**: fully standardized (commit 208006f
  on 2026-05-10).
* **~165 Shrine disambig pages**: migrated to the dual-sync model on
  2026-05-10 (commit c73d144). Pages now live in BOTH miraheze_unique/
  and fandom_unique/ instead of git_synced/. `generate_shrine_disambig_lists.py`
  runs as a step in the Independent Pages Sync workflow on every daily
  cleanup-loop cycle — pulls the Japanese kanji name(s) from each
  page, SPARQLs Wikidata for shrines with that label, writes the
  `== Shrines with this name ==` block to BOTH miraheze_unique/ and
  fandom_unique/, and the per-wiki syncs push to both wikis in the
  same cycle. Follow-ups:
  * 4 pages need manual kanji extraction (unusual lede formats:
    Kobe (disambiguation), Kōtai Shrine (disambiguation), Meiji,
    Nitta Shrine)
  * 15 pages had 0 exact-label SPARQL matches — extending the query
    with UNION over skos:altLabel + prefix matching would catch more
    but the broader query timed out at >60s; needs optimization

Translate all of the [[Category:Need translation]] —
`sync_need_translation.py` is a bidirectional file ↔ wiki mirror only;
it does not translate. As of 2026-05-11, 121 of ~167 files under
`need_translation/` still contain CJK awaiting English translation
(down from 215 on 2026-05-10; 94 cleared so far across multiple sessions).
Per-page LLM work, batchable but judgement-heavy.
The big remaining shape is genuine Japanese-prose kokuzo articles —
the simpler "swap template name + drop category" cases were done in
bulk via the maintenance-template renames in 40c519e.

Reorganize the pages in `duplicated_content/` to remove duplicated
content and turn each one into a single coherent article. This is an
agentic task — not scriptable. The duplicated-content sync (per
[[project_duplicated_content_not_wired]]) has already pulled each
listed page into the local repo as a `.wiki` file; the work is to
move paragraphs around, dedupe overlapping prose, drop boilerplate
inherited from the source-of-duplication, and end up with a
relatively organized article. When a page is done, the per-page
opt-out signal (remove `[[Category:Currently duplicated content]]`
from the file) lets the next CI sync push the cleaned version to the
wiki and delete the file from the repo. Process pages in batches;
commit and push after each batch.

Edit up the templates on the new independently-synced
miraheze_unique/ and fandom_unique/ disambig pages so they render
correctly on shinto.fandom.com. The dual-sync model (commit c73d144,
2026-05-10) pushes the same content to both wikis, but a number of
templates that work on miraheze haven't been ported to fandom — go
through each fandom_unique/ file and adjust template usage so it
renders. Commit and push once done.

## Stuff added by web during session

Here's stuff added by web during an autonomous agentic session

when resolving changes keep these at the end of the queue and execute on them

I want an action added that adds [[Category:crud categories]] 
to the end of all the untranslated Japanese character counting stuff and disables the actions that add them on September 1, 2027

Also set up remote claude cron jobs to go through a programmatically generated queue of agentic stuff it needs to do. Including pretty much all of the git synced pages. Moving the Japanese titled pages is a bit of a different additional thing that I think I will be doing manually. But apparently this is possible and will make it much easier for me to finally drop this project altogether and make it autonomous

Run a onetime script here https://shinto.miraheze.org/wiki/Category:Templates_not_transcluded_in_mainspace because basically an issue I have been having is essentially such: Templates transluded in categoryspace are ones worth preserving too. So the ideal here would be to run through all of the pages here and adding [[Category:Templates not transcluded in mainspace or categoryspace]] to the applicable ones. And then setting it up so that on July 1st 2027 we add that category to [[Category:crud categories]] to sunset it. 


## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
