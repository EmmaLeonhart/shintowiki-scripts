import mwclient
import io
import sys
import re

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to shinto.miraheze.org
site = mwclient.Site('shinto.miraheze.org')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

page = site.pages['Folk Cultural Property']
text = page.text()

print("First 1000 characters of page:")
print(text[:1000])
print("\n\n" + "="*50)

# Check for template
has_translated_template = bool(re.search(r'\{\{translated page\|', text, re.IGNORECASE))
print(f"\nHas translated page template: {has_translated_template}")

# Show all templates
templates = re.findall(r'\{\{[^}]+\}\}', text[:2000])
print(f"\nTemplates found (first 2000 chars):")
for t in templates:
    print(f"  {t}")

# Search for "translated page" anywhere in text
matches = list(re.finditer(r'translated page', text, re.IGNORECASE))
print(f"\n\nFound {len(matches)} matches for 'translated page' in full text")
for i, m in enumerate(matches):
    print(f"\nMatch {i+1} (position {m.start()}-{m.end()}):")
    print(f"  Context: {text[max(0, m.start()-50):min(len(text), m.end()+150)]}")
