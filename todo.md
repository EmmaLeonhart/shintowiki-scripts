# Todo

Long-horizon backlog: genuine, not-yet-done tasks only. Active work is in [queue.md](queue.md);
finished work and history are in [DEVLOG.md](DEVLOG.md); how things work is in [CLAUDE.md](CLAUDE.md)
and `docs/`.

Rewritten 2026-10-08 (Emma: the todo "should be completely rehashed at this point, since we edit in a
pretty different way now").

## How editing works now

- **Wikidata** goes through QuickStatements from Emma's logged-in browser: the generators fill the
  registered `.txt` files, `site/build_qs_home.py` collects them, and the hourly browser-batch cron
  submits each round in parts of up to 5,000 lines, then triggers a regeneration. The QS API route
  (`qs-daily-submit.yml`) still fails on `QS_TOKEN`; only Emma can fix that secret.
- **The shinto wiki** is edited from Emma's browser as Immanuelle (summaries end "(Claude-assisted)",
  every edit logged in `shinto_miraheze/browser_wiki/edit_log.tsv`). CI still cannot reach it.
- Emma is closing out the Wikidata work; `queue.md` holds the last of it.

## Translation (moved out of the queue 2026-10-08)

- Translate untranslated jawiki shrine articles that have no page on the wiki, highest-value first.
- Retranslate finished-but-bad pages (the "stinkers"); where an enwiki article exists, compare it with
  jawiki and synthesise. Himetataraisuzu-hime, Tamakushi-hime, Tamayori-hime and Kegare are done.

## Labels (long horizon)

- Every Shinto shrine, temple, deity and related entity on Wikidata labelled in all supported
  languages (reference: Q687168). Roadmap: [`docs/mass-label-expansion-plan.md`](docs/mass-label-expansion-plan.md).
  This is drip-owned and runs unattended; it has no deadline and none should be computed for it.

## Settled, so not to be re-opened

- 2026-09-17: the uncovered 59 languages were given up (the 54 covered are final); the low-confidence
  ILL residue, the double-category-QID dab pages, the multiple-`{{wikidata link}}` residual, the 26
  interlanguage pages with no item and the 9 large kokuzō articles are won't-do, with their detection
  ops still running. The temple labels were NOT dropped.
- `docs/program_audit_2026-06.md` is reference, not a task.
