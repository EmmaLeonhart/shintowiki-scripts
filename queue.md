# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

This is the home stretch for everything touching Wikidata (Emma, 2026-10-08). New jawiki translations
and retranslating finished-but-bad pages are out of the queue; they are in `todo.md`.

## stuff to do

⛔ **Strict order. Do not skip ahead to an easier item while the one above it waits** (Emma, 2026-10-09:
"you have the tendency to lose track of the difficult items"). If the first item is waiting on something, the work-loop reports that and does not start the next one.


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
