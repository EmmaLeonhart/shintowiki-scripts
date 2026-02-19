# Wikibot Repository Improvement Plan

## Current State
The repository contains 150+ standalone Python scripts for maintaining Shinto Wiki. While functional, the structure is dispersed and could benefit from organization and modernization.

## Quick Wins (Easy, High Impact)

### 1. Create a Shared Configuration Module
**Problem:** Credentials hardcoded in every script
**Solution:** Create `config.py`
```python
import os
from dotenv import load_dotenv

load_dotenv()

WIKI_URL = os.getenv('WIKI_URL', 'shinto.miraheze.org')
WIKI_PATH = os.getenv('WIKI_PATH', '/w/')
USERNAME = os.getenv('WIKI_USERNAME')
PASSWORD = os.getenv('WIKI_PASSWORD')
THROTTLE = float(os.getenv('THROTTLE', '0.3'))
```
Add `.env` to `.gitignore` and create `.env.example`

### 2. Create a Shared Helpers Module
**Problem:** `safe_save()` duplicated in 50+ scripts
**Solution:** Create `helpers.py`
```python
import mwclient

def get_site():
    """Get authenticated MediaWiki site connection"""
    from .config import WIKI_URL, WIKI_PATH, USERNAME, PASSWORD
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    return site

def safe_save(page, text, summary):
    """Standard safe save implementation"""
    if not page.exists:
        return False
    # ... rest of implementation

def has_category(text, category_name):
    """Check if page has a specific category"""
    # ... implementation
```

### 3. Create Regex Patterns Module
**Problem:** Similar regex patterns defined in every script
**Solution:** Create `patterns.py`
```python
import re

INTERWIKI = re.compile(r'\[\[([a-z]{2}):([^\]]+)\]\]')
CATEGORY = re.compile(r'\[\[Category:([^\]]+)\]\]')
TEMPLATE = re.compile(r'{{(.*?)}}')
WIKIDATA = re.compile(r'{{wikidata link\|([Qq](\d+))}}')
ILL_TEMPLATE = re.compile(r'{{\s*ill\s*\|')
```

## Medium-Term Changes (1-2 weeks of work)

### 4. Organize Scripts by Function
Create subdirectories:
```
bots/
  wikidata/
    ├── __init__.py
    ├── resolve_from_interwiki.py
    ├── sync_wikidata.py
    └── tag_missing_wikidata.py
  interwiki/
    ├── __init__.py
    ├── add_interwiki_links.py
    └── cleanup.py
  categories/
    ├── __init__.py
    ├── restore_from_jawiki.py
    └── create_wanted.py
  templates/
    ├── __init__.py
    └── sync_infobox.py
```

### 5. Create Entry Point Scripts
Instead of running `add_enwiki_interwiki.py` directly, create `scripts/` directory:
```
scripts/
  ├── add_enwiki_interwiki.py (thin wrapper with argparse)
  ├── sync_wikidata.py
  └── manage_categories.py
```

Each script handles argument parsing and logging.

### 6. Add Logging Infrastructure
Replace print statements with proper logging:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/{bot_name}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Processing {len(pages)} pages")
```

### 7. Add Unit Tests
Create `tests/` directory with pytest tests for:
- Pattern matching (regex)
- Safe save logic
- Category detection
- Interwiki parsing

## Major Refactoring (2-4 weeks)

### 8. Create a Base Bot Class
```python
class MediaWikiBot:
    def __init__(self, bot_name):
        self.site = get_site()
        self.bot_name = bot_name
        self.stats = {'processed': 0, 'modified': 0, 'skipped': 0, 'errors': 0}

    def log_edit(self, page_name, success, reason):
        """Track all edits"""

    def process_page(self, page):
        """Override in subclass"""
        raise NotImplementedError

    def run(self, pages):
        """Standard execution loop"""
        for page in pages:
            try:
                if self.process_page(page):
                    self.stats['modified'] += 1
                else:
                    self.stats['skipped'] += 1
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Error on {page.name}: {e}")

        self.print_summary()
```

### 9. Implement Dry-Run Mode
Add to all scripts:
```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')
parser.add_argument('--limit', type=int, help='Process only N pages')
parser.add_argument('--start', type=int, default=0, help='Start from page N')
args = parser.parse_args()

def safe_save(page, text, summary, dry_run=False):
    if dry_run:
        logger.info(f"[DRY RUN] Would save {page.name}")
        return True
    # ... normal save
```

### 10. Create Centralized Data Management
```
data/
  ├── pages.txt
  ├── categories.txt
  └── processed_pages.json  (tracks what was already done)
```

Add a simple SQLite database to track execution:
```python
import sqlite3

db = sqlite3.connect('bot_execution.db')
db.execute('''
    CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY,
        bot_name TEXT,
        page_name TEXT,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
```

## Migration Strategy

### Phase 1 (Week 1): Foundation
- [ ] Create `config.py` and migrate all scripts to use it
- [ ] Create `helpers.py` and `patterns.py`
- [ ] Create `.env.example` and update `.gitignore`
- [ ] Add README.md with usage instructions

### Phase 2 (Week 2-3): Organization
- [ ] Create subdirectories in `bots/`
- [ ] Move scripts to appropriate subdirectories
- [ ] Create `scripts/` entry points
- [ ] Add argparse to all entry points

### Phase 3 (Week 4+): Enhancement
- [ ] Add logging throughout
- [ ] Create base bot class
- [ ] Add dry-run functionality
- [ ] Add tests
- [ ] Add execution tracking

## File Structure After Improvements

```
wikibot/
├── .env.example              # Example environment variables
├── .gitignore               # Updated to exclude .env, logs/
├── README.md                # Comprehensive usage guide
├── REPOSITORY_STRUCTURE.md  # This document
├── IMPROVEMENT_PLAN.md
├── requirements.txt         # Python dependencies
├── setup.py                 # Package installation
│
├── wikibot/                 # Main package
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── helpers.py          # Shared utilities
│   ├── patterns.py         # Regex patterns
│   ├── wiki_client.py      # Wrapper around mwclient
│   │
│   └── bots/               # All bot implementations
│       ├── __init__.py
│       ├── base.py         # Base bot class
│       ├── wikidata/
│       │   ├── __init__.py
│       │   ├── resolve_from_interwiki.py
│       │   └── sync_wikidata.py
│       ├── interwiki/
│       │   ├── __init__.py
│       │   └── manage_links.py
│       ├── categories/
│       │   ├── __init__.py
│       │   └── manage_categories.py
│       ├── templates/
│       │   ├── __init__.py
│       │   └── sync_infobox.py
│       └── general/
│           ├── __init__.py
│           └── utilities.py
│
├── scripts/                 # Executable entry points
│   ├── add_wikidata_links
│   ├── manage_categories
│   ├── sync_interwiki
│   └── sync_templates
│
├── data/
│   ├── pages.txt
│   ├── categories.txt
│   ├── processed_pages.json
│   └── bot_execution.db
│
├── logs/
│   ├── wikibot.log
│   ├── bot_execution.log
│   └── [per-bot logs]
│
├── tests/
│   ├── __init__.py
│   ├── test_helpers.py
│   ├── test_patterns.py
│   └── test_bots.py
│
└── moved_from_downloads/   # Archive of old scripts
```

## Benefits of These Changes

1. **Maintainability**: One change to safe_save affects all bots
2. **Security**: Credentials in environment variables, not source code
3. **Discoverability**: Clear organization makes finding scripts easier
4. **Testing**: Shared code can be unit tested
5. **Reliability**: Dry-run mode reduces accidental changes
6. **Monitoring**: Logging and execution tracking improve oversight
7. **Collaboration**: Clear structure makes onboarding easier

## Estimated Effort

- Phase 1: 4-6 hours
- Phase 2: 8-10 hours
- Phase 3: 12-16 hours
- **Total: 24-32 hours of work**

## Priority

Given the size of the repository, recommend tackling Phase 1 first (credentials and shared code) as it provides immediate security and maintainability benefits while requiring minimal changes to existing scripts.

