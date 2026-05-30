# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

## 1. Review the deferred-verification log

Walk `docs/deferred_verification.md` and actually TEST each Open item — the batched verification we skip in the moment because wiki/CI changes are slow lagging indicators (8–24h to manifest). Highest priority right now: the **sync `.state`-file removal** (shipped 2026-05-30, all 5 sync scripts now stateless + timestamp-based) — watch the next sync cycles for spurious deletions / category-churn and fix the stateless orphan/winner logic if needed (do NOT bring the `.state` files back). For each item: run its check; if it works, move it to the doc's Verified section with the date + what you saw; if it's broken, fix it. (The `monthly-verification-sweep.yml` GH Action re-adds this task monthly.)
