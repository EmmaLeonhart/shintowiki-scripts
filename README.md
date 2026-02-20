# wikibot

A bot framework for editing MediaWiki wikis, primarily [shinto.miraheze.org](https://shinto.miraheze.org), with integration against Wikidata and the [pramana.dev](https://pramana.dev) server.

---

## Current state

The root directory and `shinto_miraheze/` contain hundreds of accumulated one-off scripts, log files, and data CSVs from several years of iterative work. Most of these are legacy ChatGPT-era scripts that are no longer needed. A cleanup pass is planned (see [VISION.md](VISION.md)).

The active, maintained scripts are documented in [SCRIPTS.md](SCRIPTS.md).

---

## Active scripts (shinto.miraheze.org pipeline)

| Script | Purpose |
|--------|---------|
| `shinto_miraheze/resolve_category_wikidata_from_interwiki.py` | Resolves Wikidata QIDs for category pages by querying their interwiki links |
| `shinto_miraheze/create_category_qid_redirects.py` | Creates `Q{QID}` redirect pages in mainspace pointing to their category |
| `shinto_miraheze/fix_ill_destinations.py` | Fixes broken ILL template destinations |
| `shinto_miraheze/add_moved_templates.py` | Adds `{{moved to}}` / `{{moved from}}` templates after page moves |
| `shinto_miraheze/resolve_duplicated_qid_categories.py` | Merges CJK/Latin duplicate QID category pairs; tags Latin/Latin pairs as erroneous |
| `shinto_miraheze/create_wanted_categories.py` | Creates wanted category pages (categories with members but no page) |
| `shinto_miraheze/remove_crud_categories.py` | Strips all subcategories of Category:Crud_categories from member pages |

---

## Credentials / secrets

**All scripts currently have hardcoded credentials.** This must be fixed before the repo can be made public. See [VISION.md § Secrets](VISION.md#secrets) for the plan.

Until then, do not share this repo publicly.

Required credentials (to be moved to environment variables or a `.env` file):
- `USERNAME` / `PASSWORD` — MediaWiki bot account (`Immanuelle` on shinto.miraheze.org)
- Pramana server credentials (future)

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

---

## See also

- [VISION.md](VISION.md) — full architecture plan and future direction
- [SCRIPTS.md](SCRIPTS.md) — catalog of all scripts with status
- [API.md](API.md) — how every external service is accessed (mwclient, Wikidata, Wikipedia APIs)
- [SHINTOWIKI_STRUCTURE.md](SHINTOWIKI_STRUCTURE.md) — page structure on shintowiki: `{{ill}}`, `{{wikidata link}}`, QID redirects, category/template/talk page conventions, known issues
- [HISTORY.md](HISTORY.md) — wiki development timeline and context: origins, suspension/restoration, shikinaisha project, category system, WikiProject Shinto situation
- [TODO.md](TODO.md) — prioritized list of all known tasks
