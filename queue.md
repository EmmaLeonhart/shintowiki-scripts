# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, shrine-disambig content strip) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.


## sync_duplicated_content + sync_need_translation: same "delete new-repo files" bug (2026-05-27)

- [ ] **Apply the sync_git_synced_pages fix to `sync_duplicated_content.py` and `sync_need_translation.py`.** Same shape as the bug just fixed in sync_git_synced_pages.py (DEVLOG 2026-05-27): the "DELETE local (cat removed on wiki)" branch fires regardless of whether the file has ever been on the wiki, so a freshly-committed new repo file gets deleted on the next sync. Patch: when `base_sha is None` (no prior sync baseline), PUSH-CREATE to the wiki instead of deleting. Note: these dirs use static wiki-wins policy and are usually wiki-driven (new files normally appear via wiki-side category-tagging, not via the repo), so the bug is less likely to fire in practice — but the code shape is identical and the fix should be too. `sync_fandom_unique_pages.py` and `sync_miraheze_unique_pages.py` use a different "no category in either side" gate that's already safe; no change needed there.

## Case-collision lowercase Template:Infobox pages (2026-05-27)

- [ ] **Run `delete_lowercase_template_collisions.py --apply` once the
  `canonicalize_template_case` sweep finishes.** Script lives at
  `shinto_miraheze/delete_lowercase_template_collisions.py`; per-page
  safeguard refuses to delete unless (a) lowercase variant exists,
  (b) canonical capitalised twin exists, (c) content is byte-identical
  OR lowercase is a `#REDIRECT` to canonical (relaxed 2026-05-27 — see
  DEVLOG), (d) `embeddedin` returns zero transclusions. Currently every
  page on both wikis still has live transclusions; re-run after another
  full orchestrator cycle or two.
## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
