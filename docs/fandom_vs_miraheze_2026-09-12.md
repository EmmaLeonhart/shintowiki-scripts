# Should operations move to shinto.fandom.com? — the evidence, 2026-09-12

Emma's `todo.md` item: *"a serious analysis of whether it will be a good idea to long term switch
our operations to the fandom wiki… the miraheze wiki would become a mirror that gets the fandom
edits propagated to it eventually. Do not do this without my permission — do the research and run an
AskUserQuestion about it after."*

This is the research. Nothing is changed by it. Every number below is measured from this repo's own
state or read live from the two wikis today; where something is not known, it says so.

⚠ Reports expire after a week (CLAUDE.md). Delete this by 2026-09-19.

> ## ⛔ Read §1 with this correction, written the same day
>
> §1 was measured before the cause was known, and it does **not** compare the two wikis' reliability.
> It compares **one host that Cloudflare challenges our GitHub runners on against one that does not.**
> Miraheze is not down, not refusing our bot, and not rejecting our User-Agent: the identical probe
> from Emma's own connection returns 200 throughout, and the same runner sending a deliberately
> generic UA still gets Miraheze's own policy refusal — so the UA layer is reachable and working.
> `EmmaBot/3.1` also passed from CI on 08-19, 08-23 and 08-30 and landed ~800 edits a day on
> 09-01..09-04. The block is **intermittent** and began between 09-04 and 09-06.
>
> Nothing in §1 is factually wrong. The framing is: "Fandom works and Miraheze does not" is a
> statement about our runners' route to each host, not about the wikis. Any decision to migrate on
> the strength of that table would be founded on a comparison that was never made.
> See `shinto_miraheze/probe_miraheze_403.py` and the DEVLOG entries of 2026-09-12.

## 1. Reliability — as measured, and what it does NOT show

Read from each wiki's `list=recentchanges` today.

| | shinto.fandom.com | shinto.miraheze.org |
|---|---|---|
| last 500 changes span | 2026-08-05 → **2026-09-11** | **2026-09-04 only** |
| distinct days with edits in that span | **38 of 38** — no gap | 1 |
| days since the most recent edit | **1** | **8** |
| who is editing | `Their Eminence`, 500/500 | `EmmaBot`, 500/500 |

Fandom's cadence over those 38 days is 1–124 edits a day and it never skips one. Miraheze's last 500
changes all fall on a single day and then stop.

**Miraheze's weekly edit-test record**, from the committed history of
`shinto_miraheze/wiki_editing_lockout.state`:

| result | dates |
|---|---|
| FAILED — HTTP 403 | 2026-07-19, 07-26, 08-09, 08-16, **09-06** |
| PASSED | 2026-08-19, 08-23, 08-30 |

**5 of 8 weekly tests failed**, each with a 403 on `api.php`, each locking editing for the following
week. Before the weekly test existed there were three more 403 events (07-12, 07-13, 07-15, the last
an explicit Cloudflare challenge). Separately, Emma called a full blackout 07-27 → 08-10.

The wiki was locked when this was written. It still is; the daily test re-decides it every
morning from 2026-09-13.

**This is the pressure behind her sentence** *"the fandom wiki editing actually appears to work"*.
It does — and the reason it does is that Fandom is not challenging our runners. That is the whole of
the difference the table above measures.

⚠ The "5 of 8 weekly tests failed" line also needs reading with care: a weekly cadence means one
challenged request condemned the following eight days, whether or not the wiki was reachable during
them. The failure count is therefore closer to a count of unlucky Sundays than of bad weeks. Made
daily on 2026-09-12 for exactly that reason.

## 2. What already exists on the Fandom side

Not a greenfield move. Already built and running:

* `fandom/fandom_subset_orchestrator.py` (+ its `.state`), `import_template_list_to_fandom.py`,
  `import_commons_wantedfiles_to_fandom.py`
* Workflows `fandom-sync.yml`, `fandom-cleanup.yml`, `import-templates-to-fandom.yml` —
  **fandom-sync is 20/20 successful over its last 20 runs**
* `shinto_miraheze/orchestrators/ops/fandom_mirror.py`, used by `history_offload`
* `shinto_miraheze/sync_fandom_unique_pages.py` and `fandom_unique/` — **651 pages**
* `generate_p6262_quickstatements.py` / `clean_p6262_quickstatements.py` — the Fandom sitelink
  property on Wikidata

## 3. The direction of travel is currently the OPPOSITE, and that is the real decision

`fandom_mirror.py` carries `FANDOM_SUNSET_DATE = datetime.date(2027, 1, 1)`:

> All writes to shinto.fandom.com stop on this date. […] Date chosen by the user: 2027-01-01.

Seven entry points import and honour it: `fandom_subset_orchestrator`,
`import_commons_wantedfiles_to_fandom`, `bootstrap_seed_fandom_unique_from_miraheze`,
`clean_p6262_quickstatements`, `generate_p6262_quickstatements`, `fandom_mirror`,
`sync_fandom_unique_pages`.

**It was set on 2026-05-13** — commit `c9b82787`, *"Fandom sunset on 2027-01-01: gate every entry
point that writes there"*. That is **two months before the first Miraheze 403** (2026-07-12). So the
decision to wind Fandom down was taken under conditions that no longer hold, and none of the
evidence in §1 existed yet.

Switching operations to Fandom is therefore not an incremental change of emphasis. It is reversing a
standing decision that seven scripts enforce.

## 4. The direction the mirror runs today

`fandom_mirror` pushes **miraheze → fandom**, full revision history, as a pre-stage of
`history_offload`. Emma's proposal inverts this: Fandom becomes primary and *"the miraheze wiki would
become a mirror that gets the fandom edits propagated to it eventually."*

Nothing in the repo does fandom → miraheze. That direction would have to be built, and it would
inherit the same 403 problem on the writing end — the propagation into Miraheze is a write to
Miraheze, so it stalls exactly when Miraheze is locked. That is survivable in a way the current
arrangement is not (a mirror falling behind is not the work stopping), but it is not free.

## 5. What is NOT established here

* **Fandom's bot policy.** Emma named it as the main disadvantage and I have not verified it. What
  is observable is that our account has edited there daily for 38 days without interruption; that is
  evidence about practice, not about policy or about what happens at a higher rate.
* ~~Whether Miraheze's 403s are rate-related or account-related.~~ **SETTLED the same day**: it is a
  Cloudflare managed challenge on the connection, not the account and not the User-Agent. The
  2026-07-14 UA change was not the fix and no further UA change will be. What remains unknown is
  *why* the challenge starts and stops — the leading untested fit is that four days of ~800 edits
  preceded it and the challenge page says "unusual activity", but Emma's 2026-07-27 quiet period is
  evidence against volume being the whole story.
* **Licence and content-ownership implications** of making Fandom primary. Not researched.
* **History preservation.** Emma's stated reason for favouring Fandom is that it *"clearly preserves
  all of the history."* `fandom_mirror`'s own docstring says the GitHub XML archive is
  "the authoritative backup", so history is already preserved independently of either wiki. Her
  point may be about something narrower that I have not identified.
