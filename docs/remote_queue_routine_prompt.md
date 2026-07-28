# The remote-queue routine — canonical prompt (paste-ready)

**Why this file exists.** On 2026-07-27 Emma switched Claude accounts and the claude.ai routine that
drains `remote_queue.json` did not come with her. Recreating it meant reconstructing its prompt from
`docs/remote_queue_pipeline.md` plus DEVLOG entries that happened to quote fragments of it — the prompt
itself was stored **only inside the claude.ai console**, which is exactly the thing an account switch
takes away. That is now fixed: the canonical text lives here, in the repo, and any future session can
rebuild the routine from it in one paste.

**Keep this file in sync.** If the routine's prompt is edited in the console, update this file in the
same sitting. A drifted copy is worse than none.

## How to (re)create the routine

Create it **in the claude.ai console**, not via the `RemoteTrigger` API. Two things were learned the
hard way on 2026-07-27:

- The API has **no field for attaching a repo.** `git_repo`, `repository`, and a nested
  `session_context.git_repo` were all accepted with HTTP 200 and then silently dropped from the stored
  config. Unknown fields vanish without an error, so an API-created routine has no repo bound to it.
- `action: "update"` **replaces `job_config` wholesale** rather than merging. Sending a partial
  `job_config` to tweak one field deletes the `events` block — i.e. the prompt. If you must update via
  the API, always resend the complete `job_config` including `events`.

Two API-created runs (2026-07-27 23:33 and 23:56 UTC) fired cleanly — `enabled: true`, empty
`suspension_reason` and `ended_reason` — and produced no commit either time. The console path is the
one known to work: it is how the original `trig_013F9aeKeL3hx8zo7weKj3Ed` was set up, and it ran daily
for months.

Settings to match the original:

| Setting | Value |
|---|---|
| Name | Drain remote_queue.json (5 random/day) |
| Repo | `EmmaLeonhart/shintowiki-scripts`, branch `main` (**pick it in the repo selector**) |
| Model | Sonnet |
| Schedule | daily, ~07:41 UTC (the old routine's commits landed ~07:46 UTC) |

## The prompt

```
Work in the repo EmmaLeonhart/shintowiki-scripts, branch main. This is an unattended
scheduled run — nobody is watching, so do not ask questions; make the edits and push.

If the clone or the push fails for ANY reason (auth, network, permissions), do NOT stop
silently. Report the exact failing command and its full error output as your final
message, so the failure is visible.

## Task: drain remote_queue.json — 5 random items

1. Read remote_queue.json at the repo root. Shape:
   {schema_version, generated_at, item_count, items[]}; each item is
   {id, file, category, instruction}. It is regenerated daily from the actual current
   wiki content mirrored into the repo, so it is always "what still needs work".

2. Pick 5 items at RANDOM from items. Random selection (NOT in-order) is the whole
   point. There is NO cursor and NO state file. DO NOT read or write
   consume_remote_queue.state — ignore it entirely.

3. For each of the 5, open item.file and do exactly what item.instruction says. The
   instruction is self-contained and authoritative — follow it LITERALLY. Do not
   substitute your own idea of the task, do not "improve" the approach, do not widen
   the scope. (Historic failure: the routine deduped infobox parameters when the
   instruction was about merging whole duplicated article bodies. Read the
   instruction, do that.)

4. When an item is genuinely finished, remove its gating category from the file (the
   instruction names the category). The repo<->wiki sync treats a file that has lost
   its gating category as done and deletes it, so removing the category is how work
   drains. If an item is NOT genuinely finished, leave the category in place and leave
   it for a later run — never strip a category to fake completion.

5. Touch NOTHING else in the repo. No refactors, no unrelated cleanup, no edits to
   scripts, workflows, docs, or queue files.

6. Files are UTF-8 Japanese/English wikitext. Preserve encoding exactly; do not
   normalize or transliterate characters, and do not reflow unrelated lines.

7. Commit and push to main with the message:

   chore(remote-queue): address N items via remote routine [skip ci]

   where N is how many items you actually completed. The [skip ci] suffix is REQUIRED.
   If the push is rejected, git pull --rebase and retry. Never force-push and never
   reset --hard.

If remote_queue.json is missing or has zero items, do nothing and make no commit — and
say so explicitly in your final message.
```

## Where the constraints come from

Each numbered rule encodes a failure the pipeline already had. Do not "simplify" them away:

- **5 random, no cursor** — the original walked a counter in `consume_remote_queue.state` and never
  revisited, so files that were fixed-but-not-yet-synced were skipped forever and ~105 pages were
  processed under the wrong instruction. Fixed 2026-05-23.
- **Follow `instruction` literally** — the routine once read "duplicated content" as duplicated
  *infobox parameters* and deduped those, when the real task is merging whole article bodies copied in
  two or three times. The per-item `instruction` is authoritative precisely because the category names
  are ambiguous.
- **Remove the gating category only when genuinely done** — category removal is what tells the sync a
  file is finished, and the sync then deletes the local file. Stripping it early destroys queued work.
- **Touch nothing else** — the routine runs unattended against a repo with live CI; scope creep here
  lands unreviewed.

See `docs/remote_queue_pipeline.md` for the end-to-end pipeline and how to debug each stage.
