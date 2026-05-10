# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

## Action items

Go through the notes of the [[Category:git synced pages]] — each
git_synced/ page has a leading `<!--...-->` instruction comment, and
those instructions must actually be executed, not just present. The
60 Sexagenary cycle pages have been fully standardized (commit 208006f
on 2026-05-10). The ~165 Shrine disambiguation pages got their first
SPARQL pass on 2026-05-10 (commit 0a67a90): `generate_shrine_disambig_lists.py`
extracts kanji from each page and writes an auto-managed
`== Shrines on Wikidata with this name ==` section, idempotent on
re-run. 146/165 pages now carry generated bullet lists. Follow-ups
on the remaining 19:
  * 4 pages skipped — no kanji extracted (Kobe (disambiguation),
    Kōtai Shrine (disambiguation), Meiji, Nitta Shrine). These have
    unusual lede formats; extract by hand or extend the script.
  * 15 pages skipped — kanji extracted but Wikidata returned 0
    exact-label matches. The script's SPARQL uses exact `rdfs:label`
    match — adding `skos:altLabel` and disambiguator-suffixed prefix
    matching would catch more (was tried, timed out at >60s for the
    full subclass tree; needs query optimization).
  * The script could also be wired into a cron so new Wikidata
    additions automatically appear on the disambig pages over time —
    currently it's a one-shot.

Translate all of the [[Category:Need translation]] —
`sync_need_translation.py` is a bidirectional file ↔ wiki mirror only;
it does not translate. 215 of 216 files under `need_translation/`
still contain CJK awaiting English translation. Per-page LLM work,
batchable but judgement-heavy.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
