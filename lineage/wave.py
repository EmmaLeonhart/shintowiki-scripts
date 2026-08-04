"""Lineage classification waves — bookkeeping for the full-read agent passes.

Two commands:

    python lineage/wave.py plan <set> [group_size]
        print the still-unclassified titles of <set> in groups, ready to paste
        into an agent prompt.  <set> is a directory name under _agent_input/.

    python lineage/wave.py record <set> < lines
        read agent output lines of the form
            <filename> | CLASS | <source> | <exact Japanese sentence>
        and append them to lineage/agent_results.tsv (title/class/source/quote),
        skipping titles already recorded.

The results file is the accumulator for the whole 444-article pass (345 Beppyo
別表神社 + 99 神宮125社); it survives restarts, the agents do not.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, 'lineage', 'agent_results.tsv')
CLASSES = {'TRANSFER', 'NETWORK', 'AUTOCHTHONOUS', 'UNKNOWN'}


def recorded():
    if not os.path.exists(RESULTS):
        return {}
    out = {}
    with open(RESULTS, encoding='utf-8') as fh:
        next(fh, None)
        for line in fh:
            parts = line.rstrip('\n').split('\t')
            if parts and parts[0]:
                out[parts[0]] = parts
    return out


def titles(setname):
    d = os.path.join(ROOT, '_agent_input', setname)
    return sorted(f[:-4] for f in os.listdir(d) if f.endswith('.txt'))


def plan(setname, size):
    done = recorded()
    todo = [t for t in titles(setname) if t not in done]
    print(f'{setname}: {len(todo)} left of {len(titles(setname))}')
    for i in range(0, len(todo), size):
        group = todo[i:i + size]
        print(f'--- G{i // size + 1} ({len(group)})')
        print(', '.join(t + '.txt' for t in group))


def record(setname):
    done = recorded()
    added = 0
    dupes = 0
    bad = []
    rows = []
    for line in sys.stdin.read().splitlines():
        line = line.strip()
        if not line or '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 2 or parts[1] not in CLASSES:
            bad.append(line[:80])
            continue
        title = parts[0][:-4] if parts[0].endswith('.txt') else parts[0]
        source = parts[2] if len(parts) > 2 else ''
        quote = parts[3] if len(parts) > 3 else ''
        if title in done:
            dupes += 1
            continue
        done[title] = True
        rows.append((title, parts[1], source, quote))
        added += 1
    new = not os.path.exists(RESULTS)
    with open(RESULTS, 'a', encoding='utf-8', newline='') as fh:
        if new:
            fh.write('title\tclass\tsource\tquote\n')
        for r in rows:
            fh.write('\t'.join(x.replace('\t', ' ') for x in r) + '\n')
    print(f'added {added}, already-recorded {dupes}, unparsed {len(bad)}')
    for b in bad:
        print('  ?', b)
    tally = {}
    for parts in recorded().values():
        tally[parts[1]] = tally.get(parts[1], 0) + 1
    print('total', sum(tally.values()), dict(sorted(tally.items())))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'plan':
        plan(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12)
    elif cmd == 'record':
        record(sys.argv[2])
    else:
        raise SystemExit(__doc__)
