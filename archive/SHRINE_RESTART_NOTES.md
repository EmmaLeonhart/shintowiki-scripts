# Shrine List Generator - Restart Instructions

## Current Status
The shrine list generator script has been fixed and is ready to run.

## File Location
`C:\Users\Immanuelle\Documents\Github\q\wikibot\engishiki_list_generator\update_shikinaisha_lists_v3.py`

## What the Script Does
1. Queries all province lists from `Category:Lists_of_Shikinaisha_by_location` in alphabetical order
2. Finds "Izumi Province" in that list
3. **Starts processing from Izumi Province onward** through the rest of the alphabet
4. Saves progress to `shiki_list_progress.json` after each successful province list
5. Respects the progress file - won't reprocess provinces already done

## How to Start

### Option 1: Simple start (recommended)
```bash
cd "C:\Users\Immanuelle\Documents\Github\q\wikibot\engishiki_list_generator"
python update_shikinaisha_lists_v3.py
```

### Option 2: With logging to file
```bash
cd "C:\Users\Immanuelle\Documents\Github\q\wikibot\engishiki_list_generator"
python update_shikinaisha_lists_v3.py 2>&1 | tee -a "../engishiki_shrine_run.log"
```

## Before Starting
1. Delete progress file if starting fresh: `del C:\Users\Immanuelle\Documents\Github\q\wikibot\engishiki_list_generator\shiki_list_progress.json`
2. Verify all Python processes are dead (check Task Manager, or run: `taskkill /F /IM python.exe`)

## If Something Goes Wrong
Kill all Python processes:
```bash
taskkill /F /IM python.exe
```

Then delete the progress file and restart.

## Why This Approach Works
- **Gets ALL provinces first**, then slices from Izumi's index - no hardcoded names
- **No fragile conditional logic** - simple list slicing
- **Infinite retry on login failures** - won't die on 429 rate limit errors
- **Won't die on HTTP timeouts** - catches all exceptions and retries
- **Progress file prevents redundant work** - but can be cleared for fresh start

## Key Implementation Details
The script uses this logic:
```python
all_pages = list(cat_members("Category:Lists_of_Shikinaisha_by_location"))
# Find Izumi's index
izumi_index = [i for i, page in enumerate(all_pages) if "Izumi" in page][0]
# Process from Izumi onward
for page in all_pages[izumi_index:]:
    # process...
```

This is bulletproof because it doesn't rely on any hardcoded province names or fragile conditional checks.
