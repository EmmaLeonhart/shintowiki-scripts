# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

_The English-label-first translation agenda (metabolized 2026-06-21) is complete: the 4-stage English-label pipeline (Stage 3 dropped per Emma), both downstream generators repointed to English, zh script variants, the per-language coverage registry (`shinto-label-generator/language_registry.py`, 44/116 covered), Vietnamese/Bengali/Greek/Hebrew + European/Latin affix batches, and the CJK→ja backfill all shipped. See `docs/english_label_pipeline.md` and `docs/language_coverage.md`. The remaining long-tail languages (Thai/Burmese/Georgian script maps, single-digit-label langs) were deliberately not hand-built — they failed the verification gate or are too low-value — and are left for the LLM/manual per Emma's scope decision._

_Japanese Buddhist temples now run the FULL automatic pipeline, same as shrines (shipped 2026-06-23, see DEVLOG): **Stage 1** deterministic kana→`<Stem>-<suffix> Temple` (`temple_english.py` + `generate_temple_en_labels.py`, 359/378 kana temples) AND **Stage 4** the cloud Sonnet routine — `select_shrines_to_translate.py` now returns a shrine batch + a temple batch (kind-tagged) from `temples_missing_en_label.json`, so the kana-less majority (~14.5k) flows through the LLM automatically with no cloud-side change and no shrine starvation. The daily worklist workflow refreshes both lists (new temples added to Wikidata flow through), the drip applies, and the multilingual generators propagate from English downstream._
---

## Stuff to do now

First thing is first, there's a fuck tonne of crud in here. 

Like a lot of it, so we should remove the crud. After we've removed the crud from the queue, then we can work on the one error that I am seeing, which is that the labels of categories, the English, when they're being applied as English labels, we do not have the category prefix on them. That makes it pretty bad. That makes it pretty bad. That makes it so that the categories really deviate from what they're supposed to be like. 


So my thought here is pretty simple. We are going to have to fix up so that:
1. This error doesn't happen again, so the pipeline for categories needs to be changed.
2. We need to have something set up, a separate task that makes Wikidata Quick Statements that go into the thing. For all of the categories that have had the error put onto them through this, it is going to create saved edit things that change the title to have the category prefix.

And finally, because I think that we'd like to locally store things or something like that, I don't really remember the full details of how this thing works. We're going to change all of the queued up edits of the category relay ones to have the category prefix for the English language label. 

I think the monthly verification sweep is something that is still scheduled. Now I don't know why it's a monthly verification sweep, but I'm going to say we do this stuff once and see if it has been properly fixed. And once you've cleared out the entire queue, we'll leave this thing in again if it turns out that the remaining (I think it was seven issues or something like that) that we had are not resolved. I'm pretty sure we had seven issues with the wiki that we set up stuff for and we thought were resolved but weren't sure about it. 

It also appears that we may have had our pipeline break again, but I'm not really sure, just cause there was no run today. I'd like you to do a bit of a verification on that. 

I also came across a relatively major error on wikidata that I introduced almost a full year ago at this point. I want to explain it, and I want you to do your best to set up a pipeline to stop it. I am going to make the pipeline into the next thing. 

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


## Monthly verification sweep (<!-- monthly-verify-sweep --> 2026-07-01)

Walk `docs/deferred_verification.md` and actually TEST each Open item (the batched verification we skip in the moment because wiki/CI changes are slow lagging indicators). For each: run its check; if it works, move it to the doc's Verified section with the date + what you observed; if it's broken, fix it and note the fix. Then delete THIS block.

## Temple close-out — full pipeline shipped; verify-only residual

The temple en-label pipeline now runs every stage shrines have:
- **Stage 1** deterministic kana → `<Stem>-<suffix> Temple` (`temple_english.py`).
- **Stage 2** identical-name reuse from same-ja-name Japanese temples (`generate_temple_identical_name_en_labels.py`, sharing the parametrized `generate_identical_name_en_labels.run`).
- **Stage 4** LLM via the cloud Sonnet routine (`select_shrines_to_translate.py` returns a temple batch; `"kind":"temple"` tag).
All wired into `ATOMIC_FILES`, `EXCLUDE_FILES`, and the daily worklist workflow; new temples flow through on refresh.

Multilingual propagation also covers temples now: `extract_name_from_en` recognises `<Stem>-<suffix> Temple` and returns `p_type="temple"`, and `format_label` already had temple words for every supported language — so once a temple en-label lands, it propagates to all the downstream languages exactly like a shrine.

Remaining (verify / cloud-side only, not coverage gaps):
- **Cloud-prompt note:** the Sonnet routine receives `"kind":"temple"` items; it can use the tag to enforce the exact `<Stem>-<suffix> Temple` form. Translation works regardless.
- **Verify after the first drip cycles:** confirm temple en-labels land on Wikidata and the downstream multilingual labels appear.

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
## Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-06-22)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.
