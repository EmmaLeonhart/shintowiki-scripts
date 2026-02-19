#!/usr/bin/env python3
"""
test_wikidata_ill.py
====================
Test the ill template parsing and wikidata addition on a single page
"""
import re, requests

# Test template from the error message
test_template = "{{ill|Diagonal star clocks|de|Diagonalsternuhr|qq=|qq=draft|qq=draft|qq=draft|qq=draft|12=simple|qq=|12=simple|13=User:Immanuelle/Diagonal star clocks|13=User:Immanuelle/simple|qq=|12=simple|13=User:Immanuelle/Diagonal star clocks|qq=|12=simple|13=User:Immanuelle/Diagonal star clocks|qq=}}"

print("Original template:")
print(test_template)
print()

# Extract languages
def extract_languages_from_ill(template_text: str):
    languages = []
    content = template_text[6:-2]
    parts = content.split('|')

    english_title = parts[0]
    print(f"English title: {english_title}")
    print(f"Total parts: {len(parts)}")
    print()

    i = 1
    while i < len(parts):
        part = parts[i]
        print(f"Part {i}: '{part}'", end="")

        if '=' not in part and len(part) <= 3 and part.isalpha():
            lang_code = part
            if i + 1 < len(parts) and '=' not in parts[i + 1]:
                title = parts[i + 1]
                languages.append((lang_code, title))
                print(f" -> LANGUAGE: {lang_code}|{title}")
                i += 2
            else:
                print(f" -> Language code but no title after")
                i += 1
        else:
            print(f" -> parameter")
            i += 1

    return languages

languages = extract_languages_from_ill(test_template)
print()
print(f"Extracted languages: {languages}")
print()

# Simulate adding WD parameter
new_param = "|WD=Q12345"
new_template = test_template[:-2] + new_param + "}}"

print("New template:")
print(new_template)
print()

# Check if content is preserved
if "Diagonalsternuhr" in new_template and "qq=draft" in new_template and "User:Immanuelle" in new_template:
    print("[SUCCESS] All original content preserved!")
else:
    print("[FAILED] Original content was lost!")
