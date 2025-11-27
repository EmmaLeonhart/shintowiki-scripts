import mwclient
import time
import sys
import io
import csv
import urllib.parse
from multiprocessing import Process
from datetime import datetime

# Handle Windows Unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CATEGORY_TEXT = "[[Category:LINKED FROM WIKIDATA DO NOT OVERWRITE]]"
API_URL = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"

def process_pages(pages_list, process_id, total_processes):
    """Process a subset of pages"""
    try:
        # Create site connection for this process
        p = urllib.parse.urlparse(API_URL)
        site = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
        site.login(USERNAME, PASSWORD)

        processed = 0
        skipped = 0
        errors = 0

        for page_name in pages_list:
            try:
                page = site.pages[page_name]
                text = page.text()

                # Check if category already exists
                if CATEGORY_TEXT in text:
                    skipped += 1
                    print(f"[Process {process_id}] SKIP: {page_name}")
                    continue

                # Add category at the end
                new_text = text.rstrip() + "\n" + CATEGORY_TEXT

                # Save the page
                page.save(new_text, summary="Bot: Add wikidata category", bot=True)
                processed += 1
                print(f"[Process {process_id}] EDIT: {page_name}")

                # Rate limiting
                time.sleep(1.5)

            except Exception as e:
                errors += 1
                print(f"[Process {process_id}] ERROR: {page_name} - {str(e)}")
                time.sleep(1.0)

        print(f"[Process {process_id}] SUMMARY - Processed: {processed}, Skipped: {skipped}, Errors: {errors}")

    except Exception as e:
        print(f"[Process {process_id}] FATAL ERROR: {str(e)}")

def main():
    # Read CSV file
    print(f"Reading CSV file...")
    pages = []

    with open(r"C:\Users\Immanuelle\Downloads\ids and stuff 2.csv", 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                # Extract page name (remove index if present)
                page_name = row[0].split('→')[-1].strip()
                if page_name:
                    pages.append(page_name)

    print(f"Loaded {len(pages)} pages")

    # Split into 6 parts
    num_processes = 6
    chunk_size = len(pages) // num_processes
    chunks = [pages[i*chunk_size:(i+1)*chunk_size] for i in range(num_processes-1)]
    chunks.append(pages[(num_processes-1)*chunk_size:])  # Last chunk gets remainder

    print(f"Starting {num_processes} parallel processes...")
    print(f"Start time: {datetime.now()}")

    # Start processes with good spacing between login attempts
    processes = []
    for i, chunk in enumerate(chunks):
        p = Process(target=process_pages, args=(chunk, i+1, num_processes))
        p.start()
        processes.append(p)
        time.sleep(2.0)  # 2 second gap between login attempts to avoid rate limit

    # Wait for all to complete
    for p in processes:
        p.join()

    print(f"End time: {datetime.now()}")
    print("All processes completed!")

if __name__ == '__main__':
    main()
