#!/usr/bin/env python
"""Test bracket detection logic"""

def count_brackets(text, open_char, close_char):
    open_count = 0
    close_count = 0
    for i, char in enumerate(text):
        if char == open_char:
            if i == 0 or text[i-1] != '\\':
                open_count += 1
        elif char == close_char:
            if i == 0 or text[i-1] != '\\':
                close_count += 1
    return open_count, close_count

def has_unclosed_brackets(text):
    results = {
        'parentheses': False,
        'square': False,
        'curly': False,
    }
    open_p, close_p = count_brackets(text, '(', ')')
    if open_p != close_p:
        results['parentheses'] = True
    open_s, close_s = count_brackets(text, '[', ']')
    if open_s != close_s:
        results['square'] = True
    open_c, close_c = count_brackets(text, '{', '}')
    if open_c != close_c:
        results['curly'] = True
    return results

# Test cases
test_cases = [
    ('This is normal text', {'parentheses': False, 'square': False, 'curly': False}),
    ('This has (unclosed paren', {'parentheses': True, 'square': False, 'curly': False}),
    ('This has balanced (parens)', {'parentheses': False, 'square': False, 'curly': False}),
    ('This has [unclosed bracket', {'parentheses': False, 'square': True, 'curly': False}),
    ('This has [balanced] brackets', {'parentheses': False, 'square': False, 'curly': False}),
    ('This has {unclosed brace', {'parentheses': False, 'square': False, 'curly': True}),
    ('This has {balanced} braces', {'parentheses': False, 'square': False, 'curly': False}),
    ('Multiple (issues ( here', {'parentheses': True, 'square': False, 'curly': False}),
    ('(Balanced) and [balanced] and {balanced}', {'parentheses': False, 'square': False, 'curly': False}),
]

print('Testing bracket detection logic:')
print('=' * 60)
all_pass = True
for text, expected in test_cases:
    result = has_unclosed_brackets(text)
    status = 'PASS' if result == expected else 'FAIL'
    if result != expected:
        all_pass = False
    print(f'{status}: {text}')
    if result != expected:
        print(f'      Expected: {expected}')
        print(f'      Got: {result}')
print('=' * 60)
print(f'Overall: {"All tests passed!" if all_pass else "Some tests failed"}')
