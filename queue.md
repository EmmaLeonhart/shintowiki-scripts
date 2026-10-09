# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

This is the home stretch for everything touching Wikidata (Emma, 2026-10-08). New jawiki translations
and retranslating finished-but-bad pages are out of the queue; they are in `todo.md`.

## stuff to do

⛔ **Strict order. Do not skip ahead to an easier item while the one above it waits** (Emma, 2026-10-09:
"you have the tendency to lose track of the difficult items"). If the first item is waiting on something, the work-loop reports that and does not start the next one.


- [ ] Finish translating the `need_translation/` pages: Miwa Shrine (Gifu); then put the links on the already-English 三野後国造, 伊佐我命, 沼田国造,
  知々夫国造, 穂国造, 角鹿国造, 遠淡海国造, 長狭国造 into `{{ill|EN|ja|JA|lt=|lt_ja=}}` form. Before every
  save: compare the live text (sha1), not just the revid, and check whether the page is in `git_synced/`
  (if so, build on that copy, keep `[[Category:Git synced pages]]`, and update the file too).

- [ ] **The core job: run the QuickStatements rounds until they are actually finished** (Emma 2026-10-09: "the
  important thing is just getting all the quick statements rounds actually finished"). The crons do NOT end
  after the translations; only once a regeneration produces 0 lines (everything clear) are the crons ended.

<!-- Spent injector markers below. NOT queue items, and not a done-list:
     scheduled/inject_due_items.py re-injects any item whose marker is missing from this
     file, whatever its json records, so the marker has to outlive the work. Each one's
     outcome is in DEVLOG.md under its date. -->
<!-- scheduled:p361-duplicate-part-of-removals -->
<!-- scheduled:p958-corrections-batch-paste -->
<!-- scheduled:label-generator-continue-on-error -->
<!-- scheduled:label-generator-continue-on-error-campaign -->
