"""run_wikidata_workflow.py
================================================
Master script to run the complete wikidata workflow:
1. resolve_wikidata_from_interwiki.py - resolve wikidata from interwiki links
2. categorize_wikidata_links.py - categorize pages based on P11250 property
3. generate_quickstatements_wikidata_links.py - generate quickstatements for uncategorized pages
================================================
"""

import subprocess
import sys
import time
import os

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIBOT_DIR = r'C:\Users\Immanuelle\Documents\Github\q\wikibot'

scripts = [
    ('resolve_wikidata_from_interwiki.py', 'Resolve Wikidata from interwiki links'),
    ('categorize_wikidata_links.py', 'Categorize Wikidata links based on P11250'),
    ('generate_quickstatements_wikidata_links.py', 'Generate QuickStatements for uncategorized pages'),
]

def run_script(script_name, description):
    """Run a Python script and return True if successful."""
    script_path = os.path.join(WIKIBOT_DIR, script_name)

    print(f"\n{'=' * 70}")
    print(f"Starting: {description}")
    print(f"Script: {script_name}")
    print(f"{'=' * 70}\n")

    try:
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=WIKIBOT_DIR,
            check=False,
            timeout=3600
        )
        elapsed_time = time.time() - start_time

        print(f"\n{'=' * 70}")
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            print(f"Elapsed time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
            print(f"{'=' * 70}\n")
            return True
        else:
            print(f"✗ {description} failed with exit code {result.returncode}")
            print(f"{'=' * 70}\n")
            return False
    except subprocess.TimeoutExpired:
        print(f"\n{'=' * 70}")
        print(f"✗ {description} timed out (> 1 hour)")
        print(f"{'=' * 70}\n")
        return False
    except Exception as e:
        print(f"\n{'=' * 70}")
        print(f"✗ {description} failed with error: {e}")
        print(f"{'=' * 70}\n")
        return False


def main():
    """Run the complete wikidata workflow."""
    print(f"\n{'=' * 70}")
    print(f"WIKIDATA INTEGRATION WORKFLOW")
    print(f"{'=' * 70}")
    print(f"Starting at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 70}\n")

    overall_start = time.time()
    results = []

    for script_name, description in scripts:
        success = run_script(script_name, description)
        results.append((description, success))

        if not success:
            print(f"ERROR: {description} failed. Stopping workflow.")
            break

    overall_time = time.time() - overall_start

    # Summary
    print(f"\n{'=' * 70}")
    print(f"WORKFLOW SUMMARY")
    print(f"{'=' * 70}")
    for description, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status}: {description}")

    print(f"\nTotal elapsed time: {overall_time:.1f} seconds ({overall_time/60:.1f} minutes)")
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 70}\n")

    # Return success only if all scripts passed
    all_passed = all(success for _, success in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
