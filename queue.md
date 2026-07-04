# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Verify the category-prefix fix after the next cleanup-loop run

The fix shipped 2026-07-04 (three legs, per Emma's spec): (1) both Len-emitting
generators (`generate_en_labels_quickstatements.py`, `generate_p11250_quickstatements.py`)
now keep the `Category:` prefix — the year-old strip was the bug; (2) new
`generate_category_label_prefix_fixes.py` renders corrective Len lines for
already-damaged items to [[QuickStatements/Category label fixes]], consumed by
`fetch_category_label_fixes_from_wiki.py` → `category_label_fixes.txt` →
`direct_daily_edits.py` (wbsetlabel overwrites; deliberately slow drip, multi-year
is fine); (3) queued Category: lines on [[QuickStatements/En labels]] are
auto-repaired to full titles by the generator's new repair pass each run.
After the next cleanup-loop + daily-edits cycle: confirm the fixes page populates,
the drip applies prefixed labels, and no bare category labels are re-emitted.

## Read the category-orchestrator stack dump after tonight's run (pipeline break, diagnosed to instrumentation stage)

Emma's "no run today" hunch verified 2026-07-04 and it's WORSE: cleanup-loop has
failed EVERY scheduled run since at least 2026-06-08 — always the
category-orchestrator job, timing out at 160 min with ZERO stdout/stderr and
ZERO state growth (never marks even one page done). Poison-page theory tested
and eliminated: every light + network op runs instantly on the first non-done
page (Category:Articles to be merged); no import-time side effects; login
retries are bounded and noisy. mwclient's silent-retry budget (25 retries ≈ 150
min of sleep) matched the timeout exactly and is now capped at 5, but the log
shows no retry warnings either, so the true wedge point is still unproven.
Instrumentation shipped: `python3 -u` + `faulthandler.dump_traceback_later(900,
repeat=True)` in `common.run_orchestrator` — the next wedge prints its own
thread stacks into the CI log every 15 min. NEXT ACTION: after the next
scheduled cleanup-loop run (02:23 UTC daily), read the category-orchestrator
job log, find the dumped stack, fix the named line.

## 同上 error


In the initial import of the Shikinaisha from jawiki there were numerous shrines that got the property

adress = 同上

for example on https://www.wikidata.org/wiki/Q135040965

I am extremely surprised that nobody has pointed this out for a full year. What it is, is that on Japanese Wikipedia, this was present in shrines on the lists. What this literally translates to is the same as above. I thought it was something like unknown, but it's the same as above. We have an odd characteristic of this, though, where these addresses are very clearly cited to the Wikipedia pages of the list of shiki naisha in the area. 

However, I believe none of them actually have the citation on them, so this adds an immediate complication to them. 

What I want you to do is:
1. Set something up that will, for the so what I want you to do right now, take a really long time and feel overly complicated.
2. Investigate the wiki data items to figure out how to get the actual Wikipedia link and give that as the source, and have it so that there is a thing that edits all of these things to make it so the source changes to that Wikipedia article.
3. Do something that, on our wiki, on the Shinto wiki, includes the Japanese language addresses on the periodic regeneration of the list of shiki naisha pages, which presumably are ones that regenerate constantly. If they are not ones that do so, they should be regenerating. I wouldn't say necessarily once a day, but I would probably say once every day.
Once we have those, we actually have the ability to use the addresses in it. If we have a sighted one, because the order is the same on both of them, if we have a sighted one that is the excited one with a citation that is the same as the one above it in the list on arWiki, which is a regular address, then we will essentially just have a thing that propagates that as far as adding it to the queued up edits. As these things go through the queued up edits, they will gradually be added and gradually propagating down until eventually we have the full citations and stuff all implemented and we have the other stuff.
I hope that makes sense. Just to clarify again, emphatically, all of this stuff is extremely slow, relying on just one single pipeline that is quite rate limited. It'll probably take multiple years for this pipeline to complete, and that's okay. What matters is that the pipeline is consistently correcting these things. It's going to gradually propagate down these so that in a few years the wiki data is going to be pretty good.

## Temple & Shrine Standardization

So I don't really know if this is the case or not. My expectation here is that likely a massive amount more languages have the infrastructure to have shrine names than temple names or shrine names. I want to standardise it a bit so that the languages with no shrine infrastructure, but just temple infrastructure, basically you just kind of guess at them or use the temple name or whatever, so that we are properly propagating all the names in that way. 


## Monthly verification sweep (<!-- monthly-verify-sweep --> 2026-07-01)

Walk `docs/deferred_verification.md` and actually TEST each Open item (the batched verification we skip in the moment because wiki/CI changes are slow lagging indicators). For each: run its check; if it works, move it to the doc's Verified section with the date + what you observed; if it's broken, fix it and note the fix. Then delete THIS block.

## Verify temple drip landed (residual of the shipped temple pipeline)

After the first drip cycles: confirm temple en-labels are landing on Wikidata and
downstream multilingual labels appear. Cloud-prompt note: the Sonnet routine gets
`"kind":"temple"` items and can enforce the `<Stem>-<suffix> Temple` form.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
## Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-06-22)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.
