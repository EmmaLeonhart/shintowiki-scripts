import mwclient, re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

site = mwclient.Site('shinto.miraheze.org', path='/w/',
    clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

TMPL_FROM = re.compile(r'\{\{\s*moved from\s*\|([^|]+?)\s*[|}]', re.IGNORECASE)
TMPL_TO   = re.compile(r'\{\{\s*moved to\s*\|([^|]+?)\s*[|}]',   re.IGNORECASE)

starting = set(p.name for p in site.categories['Move starting points'])
targets  = set(p.name for p in site.categories['Move targets'])

print(f'starting: {len(starting)}, targets: {len(targets)}')
print()

# Sample 5 from starting points
print('=== 5 pages from Move starting points ===')
for title in sorted(starting)[:5]:
    text = site.pages[title].text() or ''
    tos   = [m.group(1).strip() for m in TMPL_TO.finditer(text)]
    froms = [m.group(1).strip() for m in TMPL_FROM.finditer(text)]
    print(f'  PAGE: {repr(title)}')
    print(f'    moved to  : {tos}')
    print(f'    moved from: {froms}')
    if tos:
        b = tos[0]
        in_t = b in targets
        print(f'    b_title={repr(b)}  in targets={in_t}')
        if in_t:
            b_text = site.pages[b].text() or ''
            b_froms = [m.group(1).strip() for m in TMPL_FROM.finditer(b_text)]
            print(f'    B moved_from args: {b_froms}')
            print(f'    match? {b_froms[0] == title if b_froms else False}  ({repr(b_froms[0]) if b_froms else ""} vs {repr(title)})')

print()
print('=== 5 pages from Move targets ===')
for title in sorted(targets)[:5]:
    text = site.pages[title].text() or ''
    froms = [m.group(1).strip() for m in TMPL_FROM.finditer(text)]
    print(f'  PAGE: {repr(title)}')
    print(f'    moved from: {froms}')
    if froms:
        a = froms[0]
        print(f'    a_title={repr(a)}  in starting={a in starting}')
