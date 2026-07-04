# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Newly added stuff

If you are the session that is not central command, can you please add all the stuff that you're still working on into the queue so that it's clear what you're doing and it can be easily restarted? 

Remove some of the vestigial stuff from the Shinto label generator directory. It does not really need its own Claude.md and things like that, and these things should probably be either moved into this or moved into the larger repository or stuff like that. They're not really that significant. It's weird they're there like this. 

And yeah, our mass label import stuff is things we are doing for the purposes of trying to generalise a lot of the important texts and concepts and deities and things like that across many languages. This is something that I presume you have enough context for, but you might not, and this is worthy. 

Also, because there is a 6:00 UTC, when is that? When is that? Did it actually happen? I'm pretty sure that has happened already. If it hasn't happened already, if it has happened already, there should have been a cron job or something for it. Let's just probably set up all of those things to do a cron job at 6:00 PM. 

Although I'm also really weird because I'm also confused, because some of the queue data suggests you might have already done it. 

## Verify the category-prefix fix (gate: tonight's ~06:00 UTC cleanup-loop run — first to carry f88f3a9c)

After the run + daily-edits cycle: [[QuickStatements/Category label fixes]]
populates, the drip applies prefixed labels, no bare category labels re-emitted.
Ship details: DEVLOG 2026-07-04.

## Category-orchestrator wedge discriminator (gate: tonight's ~06:00 UTC run — first instrumented one in-pipeline)

Month-long daily 160-min zero-output wedge. Standalone dispatch with current
code SUCCEEDED in 6m24s (2026-07-04), so it does not reproduce outside the
pipeline. Tonight discriminates: wedges again → the faulthandler dump in the
job log names the line, fix it; succeeds → the mwclient retry-cap fix was the
cure, delete this item. Full forensic trail: DEVLOG 2026-07-04.

## 同上 pipeline residuals

1. **Generalize beyond 出雲国** (gate: doujou drip convergence): re-run the
   SPARQL in resolve_doujou_addresses.py; if other provinces carry 同上,
   extend the resolver's article list.
2. **Verify the FULL province-list sweep** (dispatched run 28712654559 in
   progress; daily cron 18:37 UTC thereafter): run green AND 2-3 non-Awa
   pages carry the Address column.

## Standardization — deferred tails only (rungs 1-3 shipped+verified, DEVLOG 2026-07-04; ALL_LANGS now 48)

- **th** (33/135 labels): needs a real Thai transliterator (pre-posed vowel
  signs); build only as its own deliberate task.
- **pa/km/lo/dz/new/mad/shn** (≤16 labels each): no script converter, 0-2
  observed labels — revisit only if a converter arrives or Sonnet does them.
- **cdo**: zero observed labels, mixed-script wiki — parked with evidence.

## Wikidata direct path at 300/day — verify + cleanup

Emma decisions 2026-07-04: QS permanently dead (no manual batch ever);
direct_daily_edits.py is the only editor, MAX_EDITS=300 at 30-90s.
1. VERIFY after 2-3 daily cycles: reports/ show ~300-line runs; sampled
   temple QIDs gain en labels.
2. Cleanup: retire submit_daily_batch's QS attempt (burns a failed API call
   per file per day).

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
