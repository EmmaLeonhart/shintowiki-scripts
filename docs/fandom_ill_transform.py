#!/usr/bin/env python3
"""
Transform fandom_unique wiki files:
- Convert {{ill|TITLE|...|1=DISPLAY}} and {{ill|TITLE|...|lt=DISPLAY}} to [[TITLE|DISPLAY]] or [[TITLE]]
- Drop {{wikidata link|...}} and {{translated page|...}} entirely
- Drop {{draft categories|...}} blocks  
- Drop miraheze-only maintenance categories
"""
import re
import sys

def parse_ill_template(template_text):
    """Parse {{ill|...}} and return (title, display)."""
    # Remove outer {{ }}
    inner = template_text[2:-2]
    # Remove leading 'ill|'
    if inner.startswith('ill|'):
        inner = inner[4:]
    
    # Split by | but respect nested templates
    params = []
    depth = 0
    current = []
    for ch in inner:
        if ch == '{':
            depth += 1
            current.append(ch)
        elif ch == '}':
            depth -= 1
            current.append(ch)
        elif ch == '|' and depth == 0:
            params.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        params.append(''.join(current))
    
    if not params:
        return None, None
    
    title = params[0].strip()
    display = None
    
    for p in params[1:]:
        p = p.strip()
        if p.startswith('1='):
            display = p[2:].strip()
        elif p.startswith('lt='):
            display = p[3:].strip()
    
    return title, display

def convert_ill_to_wikilink(template_text):
    """Convert an {{ill|...}} template to a wikilink."""
    title, display = parse_ill_template(template_text)
    if title is None:
        return template_text  # fallback
    if display:
        return f'[[{title}|{display}]]'
    else:
        return f'[[{title}]]'

def transform_file(text):
    """Apply all transformations to a wiki file."""
    
    # 1. Convert {{ill|...}} templates to wikilinks
    # Find all {{ill|...}} templates (possibly nested, but ill templates don't nest)
    result = []
    i = 0
    while i < len(text):
        # Look for {{ill|
        if text[i:i+6] == '{{ill|':
            # Find the end of this template
            depth = 2  # started with {{
            j = i + 2
            while j < len(text) and depth > 0:
                if text[j:j+2] == '{{':
                    depth += 2
                    j += 2
                elif text[j:j+2] == '}}':
                    depth -= 2
                    j += 2
                else:
                    j += 1
            template_text = text[i:j]
            result.append(convert_ill_to_wikilink(template_text))
            i = j
        else:
            result.append(text[i])
            i += 1
    text = ''.join(result)
    
    # 2. Drop {{wikidata link|...}} (possibly multiline)
    text = re.sub(r'\{\{wikidata link\|[^}]*\}\}', '', text, flags=re.DOTALL)
    
    # 3. Drop {{translated page|...}}
    text = re.sub(r'\{\{translated page\|[^}]*\}\}', '', text, flags=re.DOTALL)
    
    # 4. Drop {{jalink|...}}
    text = re.sub(r'\{\{jalink\|[^}]*\}\}', '', text, flags=re.DOTALL)
    
    # 5. Drop {{draft categories|...}} block (from {{draft categories| to matching }})
    # This is complex - find the block and remove it
    start = text.find('{{draft categories|')
    if start != -1:
        # Find matching closing }}
        depth = 2
        j = start + 2
        while j < len(text) and depth > 0:
            if text[j:j+2] == '{{':
                depth += 2
                j += 2
            elif text[j:j+2] == '}}':
                depth -= 2
                j += 2
            else:
                j += 1
        text = text[:start] + text[j:]
    
    # 6. Drop {{everybodywiki link|...}}
    text = re.sub(r'\{\{everybodywiki link\|[^}]*\}\}', '', text, flags=re.DOTALL)
    
    # 7. Drop miraheze-only maintenance categories
    miraheze_cats = [
        r'\[\[Category:Pages with interwikis with duplicate languages\]\]',
        r'\[\[Category:Independently git synced pages\]\]',
        r'\[\[Category:translated pages with valid en interwikis\]\]',
        r'\[\[Category:Wikidata has short description\]\]',
        r'\[\[Category:Git synced pages\]\]',
    ]
    for cat_pattern in miraheze_cats:
        text = re.sub(cat_pattern + r'\n?', '', text)
    
    # 8. Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip() + '\n'


if __name__ == '__main__':
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        text = f.read()
    result = transform_file(text)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"Transformed {filename}")
