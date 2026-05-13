# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Action items

Shrine-disambig follow-ups (rest of `[[Category:git synced pages]]` work
is done — 60 sexagenary + 165 disambig pages migrated to dual-sync on
2026-05-10): 4 disambig pages have unusual ledes the kanji extractor
can't parse (Kobe disambiguation, Kōtai Shrine disambiguation, Meiji,
Nitta Shrine — Nitta and Kōtai now have the auto-generated block,
Kobe and Meiji still don't); 15 pages had 0 exact-label SPARQL matches
and need a broader query (UNION over skos:altLabel + prefix matching;
the broader query timed out at >60s and needs WDQS optimization).

Translate all of the [[Category:Need translation]] —
`sync_need_translation.py` is a bidirectional file ↔ wiki mirror only;
it does not translate. As of 2026-05-11, 121 of ~167 files under
`need_translation/` still contain CJK awaiting English translation
(down from 215 on 2026-05-10). Per-page LLM work, batchable but
judgement-heavy. The big remaining shape is genuine Japanese-prose
kokuzo articles — the simpler "swap template name + drop category"
cases were done in bulk via 40c519e.

Reorganize the pages in `duplicated_content/` to remove duplicated
content and turn each one into a single coherent article. Agentic
task — not scriptable. The duplicated-content sync (per
[[project_duplicated_content_not_wired]]) has already pulled each
page into the local repo as a `.wiki` file; the work is to move
paragraphs around, dedupe overlapping prose, drop boilerplate, and
end up with an organized article. When a page is done, removing
`[[Category:Pages with duplicated content]]` from the file is the
opt-out signal — next CI sync pushes the cleaned version and deletes
the local file. ~353 pages remaining; this is the largest LLM-time
sink on the queue and is the strongest candidate for the autonomous
remote-claude flow below.

Edit up the templates on the new independently-synced
miraheze_unique/ and fandom_unique/ disambig pages so they render
correctly on shinto.fandom.com. The dual-sync model (commit c73d144,
2026-05-10) pushes the same content to both wikis, but a number of
templates that work on miraheze haven't been ported to fandom — go
through each fandom_unique/ file and convert `{{ill|...}}` →
`[[...]]` etc. ~600 pages; mostly mechanical but each page needs
review.

## Stuff added by web during session

Stuff added by web during an autonomous agentic session. When
resolving changes keep these at the end of the queue and execute
on them.

Crud-cats sunset for untranslated-Japanese character-counter
categories. Add `[[Category:crud categories]]` to each
``Pages with N+ untranslated japanese characters`` category page so
the whole counter family enters the crud-deletion pipeline, and
disable the orchestrator op + the standalone `tag_untranslated_japanese.py`
sweep that adds them, on 2027-09-01.

Set up remote claude cron jobs that work a programmatically generated
queue of agentic page changes. `remote_queue.py` runs in GitHub
Actions, produces a queue (page + instruction list) covering most of
the git_synced/ work and the duplicated_content/ reorganization, and
a scheduled remote claude pulls items off and edits them. Moving the
Japanese-titled pages is a separate manual task and is **not**
covered by this. Goal: the wiki gets self-healing enough that I can
finally drop the project and have it stay in a decent state for the
archives, regardless of whether the wiki itself stays up long-term.

Run a one-time sweep over
[[Category:Templates not transcluded in mainspace]]: for each
template, check whether it's transcluded in category space too, and
if not add `[[Category:Templates not transcluded in mainspace or
categoryspace]]`. Then queue a 2027-07-01 step that adds the older
"in mainspace" category to `[[Category:crud categories]]` to sunset
it. Once the new category is settled, start deleting its members —
templates with no transclusions in mainspace or categoryspace are
wiki-space waste.

## More stuff

We need to add to the mainspace orchestrator for it to remove the {{AfC submission}} and {{AfC topic}} templates from pages. We also need to have it so that the quickstatements run wikidata editing checks whether a page exists before adding it. Fandom pages and miraheze pages both, but whether it exists on miraheze is the source of truth.

The pages in https://shinto.miraheze.org/wiki/Category:Shrine_disambiguations
need their content stripped harder — the old lists they inherited
from the source pages cause active confusion. Each should have a
generic-ish intro (a tiny amount of custom content per shrine name
is OK), and the old human-curated lists should be dropped; what
stays is the auto-generated `== Shrines with this name ==` block
that `generate_shrine_disambig_lists.py` writes. Process these from
miraheze_unique/ (canonical source per the dual-sync model) so the
next sync pushes the cleanup to both wikis.

## More More Stuff

Please cleanup the [[Action Items]] section here a lot of it appears to be quite outdated and I am not sure why it is still there. Stuff gets cleared from the queue.md as it is done and if iti s not clear enough claude.md should be edited to make this clear

Also edit the category orchestrator to remove any self-categorization of categories. That is a major issue that I think keeps a lot of categories from being cleared from the wiki

## More More More Stuff

I am adding a [[Category:crud templates]] and the idea is similar to crud categories. You remove all transclusions of the template from everywhere. Since this is a template you need to make sure that you are not looking at everything in the category, but actually check each one to make sure it has the category on it, and then removing its transclusion. 

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
