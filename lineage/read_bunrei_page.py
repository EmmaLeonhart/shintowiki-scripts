#!/usr/bin/env python3
"""
read_bunrei_page.py
===================
Extract the readable text of the shintowiki 分霊 (Bunrei) page from the saved
HTML Emma downloaded, so the 11 judgement calls can actually be read.

The blackout forbids any request to shinto.miraheze.org, including reads, until
2026-08-09 — so the page arrives as a file, not over the wire. This script makes
no network request of any kind.

Usage: python lineage/read_bunrei_page.py [--section <substring>]
"""
import argparse
import html
import io
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = os.path.join(SCRIPT_DIR, 'bunrei_page_saved_2026-08-04.html')


def to_text(fragment):
    """Wikitext-ish plain text from a MediaWiki-rendered HTML fragment."""
    t = fragment
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', '', t)
    t = re.sub(r'(?is)<sup\b[^>]*class="[^"]*reference[^"]*".*?</sup>', '', t)
    t = re.sub(r'(?is)<span\b[^>]*class="[^"]*mw-editsection.*?</span>', '', t)
    # Keep the block structure that carries meaning on a wiki page.
    t = re.sub(r'(?i)</(p|div|li|dd|dt|tr|h[1-6])>', '\n', t)
    t = re.sub(r'(?i)<li\b[^>]*>', '\n* ', t)
    t = re.sub(r'(?i)<(dd|dt)\b[^>]*>', '\n: ', t)
    t = re.sub(r'(?i)</t[dh]>', ' | ', t)
    t = re.sub(r'(?i)<h([1-6])\b[^>]*>', r'\n\n== ', t)
    t = re.sub(r'(?i)<br\s*/?>', '\n', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n\s*\n\s*\n+', '\n\n', t)
    return '\n'.join(line.strip() for line in t.split('\n')).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', help='only print blocks containing this string')
    args = ap.parse_args()

    raw = open(SRC, encoding='utf-8', errors='replace').read()
    m = re.search(r'(?is)<div[^>]*class="[^"]*mw-parser-output[^"]*"[^>]*>', raw)
    body = raw[m.end():] if m else raw
    end = re.search(r'(?is)<div[^>]*class="[^"]*(printfooter|catlinks)', body)
    if end:
        body = body[:end.start()]

    text = to_text(body)
    if args.section:
        blocks = [b for b in text.split('\n\n') if args.section in b]
        print('\n\n'.join(blocks))
    else:
        print(text)


if __name__ == '__main__':
    main()
