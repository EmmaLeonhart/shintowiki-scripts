#!/usr/bin/env python3
"""
IPA to Illish Phonology Converter
==================================
Converts English IPA pronunciation to Illish orthography following
phonology rules: tone assignment, coda reduction, vowel length, nasalization.

Usage:
    from ipa_to_illish_converter import english_ipa_to_illish
    illish_form = english_ipa_to_illish("kæt")  # Returns "ka" (with low tone mark)
"""

import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Tone diacritics (combining marks to add AFTER the vowel)
TONES = {
    'low': '',          # unmarked: a
    'high': '\u0304',   # combining macron
    'rising': '\u0301', # combining acute
    'sinking': '\u0300', # combining grave
    'peaking': '\u0302', # combining circumflex
    'dipping': '\u030c'  # combining caron
}

# Vowel inventory
VOWELS = set('ɪɛæɔʊɑɒəɜaeiouɨʉɯʌ')
VOICED_OBSTRUENTS = set('bvdðgzʒ')  # dʒ handled separately

def is_vowel(char):
    """Check if character is a vowel"""
    return char in VOWELS

def analyze_word(ipa_str):
    """
    Parse IPA string into syllables
    Returns: list of (onset, vowel, coda) tuples
    """
    ipa = ipa_str.strip().strip('/').replace('ˈ', '').replace('ˌ', '')

    if not ipa:
        return []

    syllables = []
    i = 0

    while i < len(ipa):
        onset = ''
        nucleus = ''
        coda = ''

        # Collect onset consonants
        while i < len(ipa) and not is_vowel(ipa[i]):
            onset += ipa[i]
            i += 1

        # Collect nucleus (vowel + optional length mark)
        if i < len(ipa) and is_vowel(ipa[i]):
            nucleus += ipa[i]
            i += 1
            if i < len(ipa) and ipa[i] == 'ː':
                nucleus += ipa[i]
                i += 1

        # Collect coda consonants (up to next vowel or end)
        while i < len(ipa) and not is_vowel(ipa[i]):
            coda += ipa[i]
            i += 1

        if nucleus:
            syllables.append((onset, nucleus, coda))

    return syllables

def collapse_s_supercluster(onset):
    """
    Handle S + plosive + liquid clusters -> tɬ
    Only collapse if S is actually at word boundary (full cluster), not just any s+liquid
    """
    # Only collapse complete supercluster patterns
    patterns = [
        ('str', 'tɬ'), ('spr', 'tɬ'), ('spl', 'tɬ'), ('skr', 'tɬ')
    ]
    for pattern, replacement in patterns:
        if onset.startswith(pattern):
            return replacement + onset[len(pattern):]
    return onset

def classify_coda(coda):
    """Classify coda type for tone assignment"""
    if not coda:
        return 'open'

    plosives = set('ptkbdg')
    fricatives = set('sfvθðzʃʒhʂʐɕʑ')
    nasals = set('mnŋ')
    liquids = set('lr')
    affricates = {'tʃ', 'dʒ'}

    if coda in affricates:
        return 'fricative'

    if len(coda) == 1:
        if coda in plosives:
            return 'plosive'
        elif coda in fricatives:
            return 'fricative'
        elif coda in nasals:
            return 'nasal'
        elif coda in liquids:
            return 'liquid'

    if len(coda) > 1:
        if any(c in liquids for c in coda):
            return 'liquid_cluster'
        if all(c in plosives for c in coda):
            return 'plosive_cluster'
        return 'other_cluster'

    return 'open'

def assign_lexical_tone(coda_type):
    """Assign lexical tone based on coda"""
    tone_map = {
        'open': 'high',
        'plosive': 'low',
        'fricative': 'high',
        'nasal': 'high',
        'liquid': 'high',
        'plosive_cluster': 'rising',
        'liquid_cluster': 'sinking',
        'other_cluster': 'high'
    }
    return tone_map.get(coda_type, 'low')

def should_vowel_be_long(nucleus, coda):
    """Determine if vowel should be long (from voiced obstruent in coda)"""
    has_length = 'ː' in nucleus

    if coda:
        # Check for voiced obstruents
        if len(coda) >= 2 and coda[-2:] == 'dʒ':
            return True
        if coda[-1] in VOICED_OBSTRUENTS:
            return True

    return has_length

def reduce_coda_to_illish(coda):
    """
    Reduce English coda to Illish inventory (s, f, m, n, l, Ø)
    Returns: (illish_coda, is_nasalized)
    """
    if not coda:
        return '', False

    # Handle affricates
    if coda in {'tʃ', 'dʒ'}:
        return 's', False

    # Single consonants
    if len(coda) == 1:
        c = coda[0]
        if c in {'s', 'z', 'ʃ', 'ʒ', 'θ', 'ð', 'ʂ', 'ʐ', 'h'}:
            return 's', False
        elif c in {'f', 'v'}:
            return 'f', False
        elif c == 'm':
            return 'm', True
        elif c in {'n', 'ŋ'}:
            return 'n', True
        elif c == 'l':
            return 'l', False
        elif c == 'r':
            return 'l', False  # r -> l in Illish
        elif c in 'ptkbdg':
            return '', False

    # Complex clusters: remove plosives and recurse
    non_plosives = [c for c in coda if c not in 'ptkbdg']
    if non_plosives:
        return reduce_coda_to_illish(''.join(non_plosives))

    return '', False

def normalize_vowel(vowel_char):
    """Normalize IPA vowels to base orthographic vowel (a, e, i, o, u)"""
    normalize_map = {
        'ɑ': 'a', 'æ': 'a', 'ə': 'a', 'ʌ': 'u',
        'ɛ': 'e', 'ɪ': 'i', 'ɔ': 'o', 'ʊ': 'u',
        'ɒ': 'o', 'ɜ': 'e',
    }
    return normalize_map.get(vowel_char, vowel_char)

def apply_tone(vowel_base, tone_name):
    """Apply tone diacritic to vowel"""
    tone_mark = TONES.get(tone_name, '')

    if not tone_mark:
        # Low tone: unmarked
        return vowel_base

    # Combining marks are added after the vowel
    return vowel_base + tone_mark

def apply_nasalization(vowel_with_tone):
    """Add nasalization combining tilde"""
    nasalization_mark = '\u0303'
    # Insert before length mark if present
    if 'ː' in vowel_with_tone:
        return vowel_with_tone.replace('ː', nasalization_mark + 'ː')
    return vowel_with_tone + nasalization_mark

def english_ipa_to_illish(ipa_string):
    """
    Convert English IPA to Illish orthography

    Pipeline:
    1. Parse into syllables
    2. Apply onset rules (S-cluster collapse)
    3. Classify codas and assign tones
    4. Reduce codas to Illish inventory
    5. Apply tone marks and nasalization
    """
    syllables = analyze_word(ipa_string)

    if not syllables:
        return ""

    result = []

    for onset, nucleus, coda in syllables:
        # Step 1: Onset rules
        onset = collapse_s_supercluster(onset)

        # Step 2: Coda classification and tone
        coda_type = classify_coda(coda)
        tone = assign_lexical_tone(coda_type)

        # Step 3: Vowel length
        is_long = should_vowel_be_long(nucleus, coda)

        # Step 4: Reduce coda
        illish_coda, nasalized = reduce_coda_to_illish(coda)

        # Step 5: Build output
        vowel_base = nucleus.replace('ː', '')
        vowel_norm = normalize_vowel(vowel_base)
        vowel_with_tone = apply_tone(vowel_norm, tone)

        if nasalized:
            vowel_with_tone = apply_nasalization(vowel_with_tone)

        if is_long and 'ː' not in vowel_with_tone:
            vowel_with_tone += 'ː'

        syllable = onset + vowel_with_tone + illish_coda
        result.append(syllable)

    return ''.join(result)


# Test cases
if __name__ == '__main__':
    test_cases = [
        ('kæt', 'ka'),                      # cat: plosive -> low tone, no coda output
        ('bæʃ', 'ba\u0304s'),              # bash: fricative -> high tone + s
        ('bæn', 'ba\u0304\u0303n'),        # ban: nasal -> high + nasalization + n coda
        ('/kæt/', 'ka'),                    # cat: slashes stripped
        ('sliːp', 'sliː'),                  # sleep: sl onset + i long + p plosive coda -> low tone (no mark)
        ('ɪŋ', 'i\u0304\u0303n'),          # -ing: nasal -> high + nasalization + n coda
        ('dʒʌs', 'dʒu\u0304s'),            # judge: fricative ending -> high + s
        ('kɛpt', 'ke\u0301'),               # kept: plosive cluster pt -> rising tone, pt deleted
    ]

    print("IPA to Illish Conversion Tests")
    print("=" * 70)

    for ipa_input, expected in test_cases:
        result = english_ipa_to_illish(ipa_input)
        status = "OK" if result == expected else "DIFF"
        print(f"{status:4} {ipa_input:15} -> {result:20} (expected: {expected})")
