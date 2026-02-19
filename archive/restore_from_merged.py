#!/usr/bin/env python3
import sys
import io
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Read the original merged content
with open('Ōarahiko Shrine_merged.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the Japanese section and End Japanese heading to get back original content
lines = content.split('\n')
new_lines = []
in_japanese = False
for line in lines:
    if line.strip() == '== Japanese Wikipedia content ==':
        in_japanese = True
        continue
    if line.strip() == '==End Japanese==':
        in_japanese = False
        continue
    if not in_japanese:
        new_lines.append(line)

original_content = '\n'.join(new_lines)
# Remove the translated page template
original_content = original_content.split('{{translated page|')[0].strip()

site = mwclient.Site('shinto.miraheze.org', path='/w/')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

page = site.pages['Ōarahiko Shrine']
page.save(original_content, summary='Restoring page for retry')
print("Restored Ōarahiko Shrine")
