# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Action items

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

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
