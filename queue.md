# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

This is the home stretch for everything touching Wikidata (Emma, 2026-10-08). New jawiki translations
and retranslating finished-but-bad pages are out of the queue; they are in `todo.md`.

## stuff to do

- [ ] Review every kami item we created (`deity_creates.txt`, `deity_role_creates.txt`, the Inochi deity,
  and any other create batch) and give each the English label form of batch #289889: the same romanised
  label in mul, en, en-us, fr and es, plus its ja label. Most have no English label; most look like close
  epithets of related kami. Done as a generator whose file is registered, so it goes out in the batch.
- [ ] Before any merging: set the obvious gender on those created kami. Many carry P21 = unknown
  (Q24238356) where the name says otherwise (…hime / 姫 / 媛 / 売 → female; …hiko / 彦 → male). Only the
  obvious cases; generator + registered file, as above.
- [ ] Then merge each created kami into the item that is pretty obviously its real identity, agentically
  in the browser (Emma 2026-10-08 orders this for these items, which overrides CLAUDE.md's "Emma merges
  duplicate items" rule for this set). One merge at a time; record each pair in `DEVLOG.md`.

- [ ] Finish translating the `need_translation/` pages: Ono Shrine (Atsugi), Kotokuji Temple (Koka
  City), Miwa Shrine (Gifu); then put the links on the already-English 三野後国造, 伊佐我命, 沼田国造,
  知々夫国造, 穂国造, 角鹿国造, 遠淡海国造, 長狭国造 into `{{ill|EN|ja|JA|lt=|lt_ja=}}` form. Before every
  save: compare the live text (sha1), not just the revid, and check whether the page is in `git_synced/`
  (if so, build on that copy, keep `[[Category:Git synced pages]]`, and update the file too).

- [ ] **LAST, after every item above:** end all the cron jobs (`CronDelete` each one in `CronList`).

<!-- Spent injector markers below. NOT queue items, and not a done-list:
     scheduled/inject_due_items.py re-injects any item whose marker is missing from this
     file, whatever its json records, so the marker has to outlive the work. Each one's
     outcome is in DEVLOG.md under its date. -->
<!-- scheduled:p361-duplicate-part-of-removals -->
<!-- scheduled:p958-corrections-batch-paste -->
<!-- scheduled:label-generator-continue-on-error -->
<!-- scheduled:label-generator-continue-on-error-campaign -->
