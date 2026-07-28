# The remote-queue / cloud-Claude cleanup pipeline (reference + debugging)

(Moved out of `todo.md` 2026-05-30 — this is reference, not a task.)

**The whole idea.** A Python script reads the *actual current content* of the wiki (mirrored into the repo) and emits a worklist; a cloud-Claude routine fixes a few items each day; the sync pushes the fixes back to the wiki. As the wiki changes, the worklist regenerates itself. **There is no cursor and no hand-maintained state — "needs work" is defined purely by what's in the files.**

**The pieces, end to end:**
1. **Repo⟷wiki sync** (`shinto_miraheze/sync_*.py`, run by `wiki-cleanup.yml`): keeps `duplicated_content/`, `need_translation/`, `fandom_unique/`, `miraheze_unique/` mirrored with the matching wiki categories. Conflict policy as of 2026-05-30 is **most-recent-edit-wins** (timestamp); the old static per-dir policy (wiki-wins for the cloud-queue dirs, repo-wins for the template syncs) is only the tie-break. When a file loses its gating category the sync pushes it and **deletes the local file** (that's "done"). The scripts are stateless (no `.state` files) as of 2026-05-30.
2. **Queue generator** (`remote_queue.py`, daily via `build-remote-queue.yml`): scans those dirs → `remote_queue.json` = a shuffled list of `{file, category, instruction}`; for `duplicated_content` only files still carrying `[[Category:Pages with duplicated content]]`. Always "what still needs work, in random order."
3. **The cloud worker** = claude.ai routine **"Drain remote_queue.json (5 random/day)"** (`trig_015viL16x9ReKsQRmsJEscH7`, Sonnet, daily `41 7 * * *` UTC): picks 5 random items, applies each `instruction` (merge duplicated paragraphs / translate Japanese / strip fandom templates), removes the gating category when genuinely done, commits `[skip ci]`. No cursor.

**Account switch, 2026-07-27 — worker currently DOWN.** Emma moved to a new Claude account;
the routine did NOT migrate. The old worker was `trig_013F9aeKeL3hx8zo7weKj3Ed` (last fired
2026-07-27 07:46 UTC, commit `eb9dcccf`) and now 404s from this account. If the daily
`chore(remote-queue)` commits stop again, check the trigger list on the *current* account
first — a silent account switch looks exactly like a broken pipeline.

Recreating it via the `RemoteTrigger` API **did not work**: `trig_015viL16x9ReKsQRmsJEscH7`
fires cleanly (`enabled: true`, empty `suspension_reason`/`ended_reason`) but produced no
commit on either of two runs, and the API exposes no way to bind a repo to a trigger — the
fields tried were accepted with HTTP 200 and silently dropped. The console is the known-good
path. **The canonical prompt and step-by-step re-creation instructions now live in
[`remote_queue_routine_prompt.md`](remote_queue_routine_prompt.md)** so this is a one-paste
rebuild rather than an archaeology exercise.

**Failure-mode catalogue (all fixed 2026-05-23):**
- **Wrong concept of "duplicated content."** The instruction said "drop boilerplate / dedupe prose," so it stripped duplicate *infobox parameters* instead of MERGING macro-scale whole-body paragraph duplication (same article copied 2–3×, often under `==Accidentally Overwritten Content==` / `==merged content==`). Fixed: rewrote `DUPLICATED_CONTENT_INSTRUCTION`.
- **The cursor.** The old routine walked a counter (`consume_remote_queue.state`) and never revisited → files fixed-but-not-yet-synced were skipped forever; ~105 done with the wrong instruction. Fixed: 5-random, no cursor.
- **Sync jam.** Every dup page looked like a conflict → conservative "skip on conflict" left 134 unsynced. Fixed: conflict policy (then wiki-wins pull; now most-recent-edit-wins).

**How to debug it:**
- *Worker:* `RemoteTrigger {action:"get", trigger_id:"trig_015viL16x9ReKsQRmsJEscH7"}` — prompt, cron, model, `last_fired_at`. Its commits: `git log --grep="remote-queue"`. A `404 Trigger not found` means you are on a different Claude account than the one that owns it — recreate rather than assume it died.
- *Queue:* `remote_queue.json` (`item_count`, per-category counts); regenerate logic `remote_queue.py`; workflow `build-remote-queue.yml`.
- *Sync:* on a `cleanup-loop` run, grep the `sync_duplicated_content` / `sync_need_translation` step for `PULL` / `PUSH` / `DELETE` counts.
- *Did a fix reach the wiki?* If `duplicated_content/<title>.wiki` is **gone** → synced + drained; still there **with** category → still queued; still there **without** category → fixed locally, not yet pushed (check why the sync hasn't pushed it).
