# wikibot

A bot framework for editing MediaWiki wikis, primarily [shinto.miraheze.org](https://shinto.miraheze.org), with integration against Wikidata and the [pramana.dev](https://pramana.dev) server.

---

## Current state

The root directory and `shinto_miraheze/` contain hundreds of accumulated one-off scripts, log files, and data CSVs from several years of iterative work. Most of these are legacy ChatGPT-era scripts that are no longer needed. A cleanup pass is planned (see [VISION.md](VISION.md)).

The active, maintained scripts are documented in [SCRIPTS.md](SCRIPTS.md).

All standard bot operations now run through GitHub Actions via `shinto_miraheze/cleanup_loop.sh`. The remaining open wiki tasks require manual intervention — there are no safe script additions left to make to the loop.

## Operations policy

I, Emma Leonhart, am no longer doing normal mass-edit runs from my local computer. Standard bot operations must run through GitHub Actions so they are auditable and lower-anxiety to operate. Major changes should be made by editing the GitHub repository/workflows and letting the pipeline execute them. Local manual script runs are reserved for emergency intervention only.

---

## Active scripts (shinto.miraheze.org pipeline)

These run in order via `shinto_miraheze/cleanup_loop.sh` (GitHub Actions, daily + on push):

| Script | Purpose |
|--------|---------|
| `shinto_miraheze/update_bot_userpage_status.py` | Updates `User:EmmaBot` with current run metadata |
| `shinto_miraheze/delete_unused_categories.py` | Deletes Special:UnusedCategories pages, skipping those with `{{Possibly empty category}}` |
| `shinto_miraheze/normalize_category_pages.py` | Enforces canonical layout (templates / interwikis / categories) on category pages |
| `shinto_miraheze/migrate_talk_pages.py` | Rebuilds talk pages and seeds them with discussion content from Wikipedia |
| `shinto_miraheze/tag_shikinaisha_talk_pages.py` | Adds a "generated from Wikidata" notice to shikinaisha talk pages |
| `shinto_miraheze/remove_crud_categories.py` | Strips `[[Category:X]]` tags from members of all Crud_categories subcategories |
| `shinto_miraheze/fix_erroneous_qid_category_links.py` | Fixes category/QID mismatches in Category:Erroneous_qid_category_links |
| `shinto_miraheze/remove_legacy_cat_templates.py` | Removes `{{デフォルトソート}}` and `{{citation needed}}` artifacts from category pages |

Everything else in the repo either completed its run, requires manual intervention, or is legacy/archived. See [TODO.md](TODO.md) for the full picture.

---

## Credentials / secrets

Active `shinto_miraheze/*.py` scripts now support environment-variable overrides:
- `WIKI_USERNAME`
- `WIKI_PASSWORD`

Until then, do not share this repo publicly.

Required credentials (to be moved to environment variables or a `.env` file):
- `WIKI_USERNAME` / `WIKI_PASSWORD` â€” MediaWiki bot password login (example username format: `EmmaBot@EmmaBot`)
- Pramana server credentials (future)

For local development, copy `.env.example` to `.env` and set real values in your shell or environment manager.

---

## Setup

```bash
pip install mwclient requests
```

Run any script directly:
```bash
python create_category_qid_redirects.py
python shinto_miraheze/resolve_category_wikidata_from_interwiki.py
```

Run the Ubuntu cleanup loop locally:
```bash
bash shinto_miraheze/cleanup_loop.sh
```

---

## GitHub Actions (Ubuntu)

A workflow is available at `.github/workflows/cleanup-loop.yml`.

Set these repository or environment secrets before running:
- `WIKI_USERNAME` (variable, bot username like `EmmaBot@EmmaBot`)
- `WIKI_PASSWORD`

The workflow runs on:
- manual dispatch (`workflow_dispatch`)
- every push (`push`)
- every 24 hours (`schedule`, at `00:00` UTC)

Pipeline behavior:
- Uses bot-password login (`WIKI_USERNAME` format `MainUser@BotName`)
- Writes a run-start status update to `[[User:EmmaBot]]` from `EmmaBot.wiki` + trigger metadata
- Runs unused-category deletion first (with `{{Possibly empty category}}` safeguard)
- Runs cleanup scripts sequentially with a per-script edit cap (`WIKI_EDIT_LIMIT=1000`)
- Commits updated `*.state` files back to the current branch after successful runs

---

## See also

- [VISION.md](VISION.md) â€” full architecture plan and future direction
- [SCRIPTS.md](SCRIPTS.md) â€” catalog of all scripts with status
- [API.md](API.md) â€” how every external service is accessed (mwclient, Wikidata, Wikipedia APIs)
- [SHINTOWIKI_STRUCTURE.md](SHINTOWIKI_STRUCTURE.md) â€” page structure on shintowiki: `{{ill}}`, `{{wikidata link}}`, QID redirects, category/template/talk page conventions, known issues
- [HISTORY.md](HISTORY.md) â€” wiki development timeline and context: origins, suspension/restoration, shikinaisha project, category system, WikiProject Shinto situation
- [TODO.md](TODO.md) â€” prioritized list of all known tasks

