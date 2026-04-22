# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Minor stuff
One thing I really want us to work on is getting the interlanguage links more integrated with the Wikidata link template. I feel like we can do this, and once we do, we'll no longer have the interlanguage links randomly going around the page. This will be generally more efficient. I want this script that we make to be implemented on all namespaces, so it doesn't just iterate through the ones with the interlanguage link. Basically, what it will do is it will take something like this 

'''
[[vi:Ất Mão]]
{{wikidata link|Q904791}}
'''

and it will turn it into something like this

{{wikidata link|Q904791|vi|Ất Mão}}

Now, I think we might be able to at some point move away from positional parameters into something like 

{{wikidata link|Q904791|vi=Ất Mão}}

But I feel like an unfortunate reality is that the way that our links and stuff are structured makes it so that it's very difficult, because you can easily, with that one, do something like this. 

[[$2:$3]]

Whereas dropping the positional parameters in favour of having it so the languages all have their individual things is something that we might be able to do. But I think in order to do this, it'll be best for us to consolidate all of these things first and then focus on it later.

Our general rule here will be pretty simple, right? If we experience instances where we are putting them into the template regardless of where they are. If there is no wiki data but there is a thing, then we specifically have the wiki data but there are interlanguage links. We specifically have them so that the second parameter is empty and this will add these things into a category specifically indicating that they have interlanguage links but no wiki data. This is easier than running our own category thing constantly. 

Yeah, positional parameters are good, but my idea here would probably be we get all these things in here first to consolidate the mess, and then we work on that. One thing I'll say as well is basically the interlanguage links: if there are two of the same interlanguage link that contradict each other, then we can even have it so that they're two different positional parameters with the same information, and the template will somehow indicate it. We're switching everything towards using the template. However, if it's the same one, then we don't bother with it. Right now, we're not actually going to do anything of like 'are these consistent with a Wikidata item?' or anything like that. That is something for later. 


Also sync the category [[Category:Git synced pages]] based on how it is done in C:\Users\Immanuelle\Documents\Github\aelaki-wikibot2 you will need this for when we edit [[Template:Wikidata link]] to make it properly use the new parameters we have added to it

Also at least in this run https://github.com/EmmaLeonhart/shintowiki-scripts/actions/runs/24744680692/job/72417848749 there was a lot of redirect related flailing and idk why. I thought we solved the redirects problem several commits ago. Either way I am also gonna be interested in making something that we ADD TO ALL FOUR ORCHESTRATORS THAT CHECKS FOR DUPLICATE QIDS ON OUR WIKI. iF THERE ARE DUPLICATE QIDS THEN IT WILL ADD THEM TO A DUPLICATE QIDS PAGE.  tHIS MIGHT EVEN EXIST ALREADY BUT IF SO IT IS PROBABLY A ONE TIME OPERATION AND REALLY STALE, OUR EVENTUAL INTENTION IS TO MERGE THESE POSSIBLY SOMEWHAT AUTOMATICALLY BUT NOT SURE HOW TO DO IT AD THE MOMENT

## Queued work

0. **Retrofit all non-terminating cycling scripts into the namespace orchestrators.** The three namespace orchestrators (`shinto_miraheze/orchestrators/mainspace_orchestrator.py`, `category_orchestrator.py`, `template_orchestrator.py`) visit every page in their namespace once per cycle and run every registered op on it. `history_offload` is the first op in every orchestrator's OPS list (gated behind `ENABLE_HISTORY_OFFLOAD=1`). The following cycling scripts still have their own standalone state files and must be ported into `shinto_miraheze/orchestrators/ops/` as per-page ops (signature: `NAME`, `NAMESPACES`, `def apply(title, text) -> (new_text|None, summary_fragment|None)`), then their steps must be removed from `.github/workflows/wiki-cleanup.yml`:
   - `tag_untranslated_japanese.py` → `ops/untranslated_japanese.py` (mainspace only, `NAMESPACES=(0,)`)
   - `generate_p11250_quickstatements.py` → `ops/p11250_quickstatements.py` (mainspace only; writes QuickStatements to a wiki page, not the page being visited — needs special handling, likely `HANDLES_SAVE = True`)
   - `populate_namespace_layers.py` → `ops/namespace_layers.py` (mainspace only; creates/edits sibling pages in Data:/Export: namespaces — also `HANDLES_SAVE = True`)
   - `tag_deleted_qids_in_ill.py` → `ops/deleted_qids_in_ill.py` (mainspace only)
   - `fix_template_noinclude.py` → already ported as `ops/noinclude_wrap.py` ✔
   - `tag_pages_without_wikidata.py` → already ported as `ops/wikidata_link.py` ✔
   After all six are ported and their wiki-cleanup.yml steps removed, the only cycling scripts the workflow still invokes should be the terminating ones flagged for July 2026 review.

1. **Strip untranslated character-count categories from already-translated pages.** `[[Category:Pages with 50+/100+/.../5000+ untranslated japanese characters]]` was applied by `shinto_miraheze/tag_untranslated_japanese.py` based on CJK density. Pages that have since been translated still carry these categories. Write `shinto_miraheze/strip_translated_char_count_cats.py` that walks [[Category:Translated pages]](https://shinto.miraheze.org/wiki/Category:Translated_pages), removes any `[[Category:Pages with N+ untranslated japanese characters]]` tags found on each, and commits the edit. Must follow the repo script template: `--apply`, `--max-edits`, `--run-tag` flags; `mwclient`; 1.5s rate limit; UTF-8 stdout wrapper; state file under `shinto_miraheze/`.

2. **Remove DEFAULTSORT from all pages via a bot.** `{{DEFAULTSORT:...}}` is leftover from the enwiki/jawiki imports and has no semantic value on shintowiki (categories use direct sort keys). Write a script that walks mainspace, removes the `{{DEFAULTSORT:...}}` line, and commits. Same script-template requirements as task 1.

3. **Extend QuickStatements wikidata linking to templates and category pages.** `shinto_miraheze/generate_p11250_quickstatements.py` today only walks mainspace members of `[[Category:Pages linked to Wikidata]]`. Extend it (or add a sibling script) that also processes `Template:` and `Category:` namespace pages that carry `{{wikidata link|Q...}}`, emitting `Q...|P11250|"Template:Name"` / `Q...|P11250|"Category:Name"` lines. Confirm Wikidata accepts P11250 with a namespaced title first — that's the risk.

4. **Translate the remaining untranslated `need_translation/` pages.** After tasks 1–3 clear: the `need_translation/` directory has ~290 files still carrying `[[Category:Need translation]]`. Nine of them are the large kokuzo articles that actually matter: `国造.wiki` (8669 CJK), `无邪志国造.wiki` (5141), `出雲国造.wiki` (4527), `千葉国造.wiki` (1763), `尾張国造.wiki` (1640), `倭国造.wiki` (1346), `廬原国造.wiki` (982), `斐陀国造.wiki` (854), `伊勢国造.wiki` (841). 83 files are shrine pages with `== Japanese Wikipedia content ==` sections (auto-generated English top + Japanese body). Translate using `{{ill|English|ja|Japanese|lt=Display|lt_ja=Japanese Display}}` per `feedback_translation_link_rules.md` in memory. Never remove `[[Category:Need translation]]` without verifying the body is actually English — CI deletes the file from the repo when the category is gone.

5. **Audit `[[Category:Double category qids]]` for resolvable entries.** <https://shinto.miraheze.org/wiki/Category:Double_category_qids> lists QID disambiguation pages where two categories share the same QID. `shinto_miraheze/resolve_double_category_qids.py` already handles the easy case (one is a redirect to the other → replace the dab with a redirect). The remaining members are where both targets are *real, working, distinct* categories — these need manual inspection to decide which category should keep the QID (or whether they should be merged on the wiki side). Walk the category, for each member fetch the two categories it disambiguates, check if both have member pages and distinct scope, produce a report listing the pairs for human review. Do not edit — just report.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
