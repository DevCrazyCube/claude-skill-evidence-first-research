#!/usr/bin/env python3
"""Lint a research log: every claim has a label, and every label carries what it needs.

    python3 claims_lint.py LOG.md                 check the log; exit 0 clean, 1 problems, 2 cannot run
    python3 claims_lint.py docs/research/*.md     several logs at once; exit 1 if any has a problem
    python3 claims_lint.py LOG.md --open          list the open questions and the hypotheses without a result
    python3 claims_lint.py LOG.md --max-age 90    also fail a fact whose evidence is older than 90 days
    python3 claims_lint.py LOG.md --check-files   also fail a (measured: FILE, DATE) whose file is not there
    python3 claims_lint.py LOG.md --offline-sources   accept a source that is not a URL or a DOI (a book, a talk)

A claim is a top-level list item. Its wrapped lines are indented. The four labels:

    - [FACT] what is true (source: https://…, accessed 2026-01-31)
    - [FACT] what was seen (measured: `the command` or the/file, 2026-01-31)
    - [HYPOTHESIS] what might be true (test: how it would be checked)
    - [HYPOTHESIS] … (test: …) (result: confirmed | refuted | inconclusive, and where that is shown)
    - [DECISION] what was chosen (because: the reason)
    - [OPEN] a question?

Fenced code is skipped, and so is a checkbox item ("- [ ] …"). Everything between
<!-- claims: off --> and <!-- claims: on --> is skipped too.

Standard library only. Python 3.8 or newer.
"""
import argparse
import datetime
import os
import re
import sys

LABELS = ('FACT', 'HYPOTHESIS', 'DECISION', 'OPEN')
RESULTS = ('confirmed', 'refuted', 'inconclusive')
HEDGES = ('probably', 'likely', 'unlikely', 'presumably', 'seems', 'seemingly', 'appears to', 'apparently',
          'i think', 'i believe', 'i assume', 'should be', 'might', 'may be', 'maybe', 'perhaps', 'possibly')

ITEM = re.compile(r'^(?:[-*+]|\d+[.)])\s+(.*)$')
FENCE = re.compile(r'^\s*(```|~~~)')
TOGGLE = re.compile(r'<!--\s*claims:\s*(on|off)\s*-->')
CHECKBOX = re.compile(r'^\[[ xX]\](\s|$)')
LABEL = re.compile(r'^\[([^\]]*)\]\s*(.*)$', re.S)
KEY = re.compile(r'\((source|measured|test|because|result):\s*')
DATED = re.compile(r'^(.*),\s*(accessed\s+)?(\d{4}-\d{2}-\d{2})$', re.S)
LINK = re.compile(r'(https?://\S+|\bdoi:\s*\S+)', re.I)
HEDGE = re.compile(r'\b(' + '|'.join(re.escape(h) for h in HEDGES) + r')\b', re.I)


def claims(text):
    """(line number, text) for each top-level list item that is read as a claim. Wrapped lines are joined."""
    out, fence, on, current = [], None, True, None
    for n, line in enumerate(text.splitlines(), 1):
        mark = FENCE.match(line)
        if fence:
            if mark and mark.group(1) == fence:
                fence = None
            continue
        if mark:
            fence, current = mark.group(1), None
            continue
        toggle = TOGGLE.search(line)
        if toggle:
            on, current = toggle.group(1) == 'on', None
            continue
        item = ITEM.match(line)
        if item:
            current = None
            if on and not CHECKBOX.match(item.group(1)):
                current = [n, item.group(1).strip()]
                out.append(current)
        elif current is not None and line.strip() and line[0] in ' \t':
            current[1] += ' ' + line.strip()
        else:
            current = None
    return [(n, t) for n, t in out]


def groups(text):
    """Every "(key: …)" in the text, with balanced brackets: (key, inner or None when never closed, start, end)."""
    found, pos = [], 0
    while True:
        m = KEY.search(text, pos)
        if not m:
            return found
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {'(': 1, ')': -1}.get(text[i], 0)
            i += 1
        if depth:
            found.append((m.group(1), None, m.start(), len(text)))
            return found
        found.append((m.group(1), text[m.end():i - 1].strip(), m.start(), i))
        pos = i


def words(text):
    return len(text.split())


def check_evidence(key, inner, today, max_age=None, offline_sources=False, check_files=False, base='.'):
    """Problems with one (source: …) or (measured: …)."""
    m = DATED.match(inner)
    if not m:
        shape = 'accessed YYYY-MM-DD' if key == 'source' else 'YYYY-MM-DD'
        return [f'({key}: …) must end with ", {shape}"']
    what, accessed, stamp = m.group(1).strip(), m.group(2), m.group(3)
    out = []
    if not what:
        out.append(f'({key}: …) names nothing before the date')
    try:
        day = datetime.date.fromisoformat(stamp)
    except ValueError:
        return out + [f'{stamp} is not a date']
    if day > today:
        out.append(f'{stamp} is in the future')
    elif max_age is not None and (today - day).days > max_age:
        out.append(f'evidence is {(today - day).days} days old (limit {max_age}): check it again or make it a hypothesis')
    if key == 'source':
        if not accessed:
            out.append('a source needs the word "accessed" before its date')
        if what and not offline_sources and not LINK.search(what):
            out.append('a source is a URL or a DOI (or run with --offline-sources)')
    elif check_files and what and not what.startswith('`'):
        if not os.path.exists(os.path.join(base, what)):
            out.append(f'measured file not found: {what}')
    return out


def check_claim(text, today, **options):
    """(label or None, statement, groups by key, problems) for one claim's text."""
    m = LABEL.match(text)
    if not m:
        return None, text, {}, ['no label: start with [FACT], [HYPOTHESIS], [DECISION] or [OPEN]']
    label, rest = m.group(1).strip(), m.group(2)
    if label not in LABELS:
        if label.upper() in LABELS:
            return None, rest, {}, [f'[{label}] must be upper case: [{label.upper()}]']
        return None, rest, {}, [f'[{label}] is not a label: use [FACT], [HYPOTHESIS], [DECISION] or [OPEN]']
    found = groups(rest)
    statement = rest
    for _, _, start, end in reversed(found):
        statement = statement[:start] + statement[end:]
    statement = ' '.join(statement.split())
    by_key, out = {}, []
    for key, inner, _, _ in found:
        if inner is None:
            out.append(f'({key}: … is never closed')
        else:
            by_key.setdefault(key, []).append(inner)
    if words(statement) < 3:
        out.append('the claim itself is missing: say it in at least three words')
    if label == 'FACT':
        evidence = [(k, v) for k in ('source', 'measured') for v in by_key.get(k, [])]
        if not evidence and not out:
            out.append('a fact needs (source: URL, accessed YYYY-MM-DD) or (measured: command or file, YYYY-MM-DD)')
        for key, inner in evidence:
            out += check_evidence(key, inner, today, **options)
        hedge = HEDGE.search(statement)
        if hedge:
            out.append(f'"{hedge.group(1)}" in a fact: a fact with a hedge in it is a hypothesis')
    elif label == 'HYPOTHESIS':
        tests = by_key.get('test', [])
        if not tests:
            if not out:
                out.append('a hypothesis needs (test: how it would be checked)')
        elif words(tests[0]) < 3:
            out.append('(test: …) must say how, in at least three words')
        for result in by_key.get('result', []):
            first = re.split(r'[\s,.;:]', result, maxsplit=1)[0].lower()
            if first not in RESULTS:
                out.append('(result: …) starts with confirmed, refuted or inconclusive')
    elif label == 'DECISION':
        reasons = by_key.get('because', [])
        if not reasons:
            if not out:
                out.append('a decision needs (because: the reason)')
        elif words(reasons[0]) < 3:
            out.append('(because: …) must give the reason, in at least three words')
    elif '?' not in statement:
        out.append('an open item is a question: it has a question mark')
    return label, statement, by_key, out


def lint(text, today, **options):
    """{'claims': [...], 'counts': {label: n}, 'problems': [(line, message)]}"""
    rows, problems, counts = [], [], {label: 0 for label in LABELS}
    for line, body in claims(text):
        label, statement, by_key, bad = check_claim(body, today, **options)
        if label:
            counts[label] += 1
        rows.append({'line': line, 'label': label, 'statement': statement, 'groups': by_key})
        problems += [(line, message) for message in bad]
    if not rows:
        problems.append((1, 'no claims found: a research log has at least one labelled list item'))
    return {'claims': rows, 'counts': counts, 'problems': problems}


def still_open(report):
    """The open questions, and the hypotheses that have no result yet."""
    return [c for c in report['claims']
            if c['label'] == 'OPEN' or (c['label'] == 'HYPOTHESIS' and not c['groups'].get('result'))]


def main(argv):
    ap = argparse.ArgumentParser(description='Lint a research log of labelled claims.')
    ap.add_argument('logs', nargs='+', metavar='LOG', help='one or more research logs')
    ap.add_argument('--open', action='store_true', help='list open questions and hypotheses without a result')
    ap.add_argument('--max-age', type=int, metavar='DAYS', help="fail a fact whose evidence is older than this")
    ap.add_argument('--check-files', action='store_true', help='a (measured: FILE, DATE) file must exist')
    ap.add_argument('--offline-sources', action='store_true', help='accept a source that is not a URL or DOI')
    ap.add_argument('--today', help='YYYY-MM-DD, instead of the real date (for tests)')
    args = ap.parse_args(argv)
    try:
        today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    except ValueError:
        print(f'claims_lint: --today {args.today} is not a date', file=sys.stderr)
        return 2
    if args.max_age is not None and args.max_age < 0:
        print('claims_lint: --max-age cannot be negative', file=sys.stderr)
        return 2
    texts = []
    for log in args.logs:  # read them all first: one unreadable log stops the run before anything is printed
        try:
            with open(log, encoding='utf-8') as f:
                texts.append(f.read())
        except (OSError, UnicodeDecodeError) as err:
            print(f'claims_lint: cannot read {log}: {err}', file=sys.stderr)
            return 2
    bad = 0
    for log, text in zip(args.logs, texts):
        report = lint(text, today, max_age=args.max_age, offline_sources=args.offline_sources,
                      check_files=args.check_files, base=os.path.dirname(os.path.abspath(log)))
        if args.open:
            rows = still_open(report)
            print(f'{log}: {len(rows)} still open')
            for c in rows:
                print(f"  {c['line']}: [{c['label']}] {c['statement']}")
            continue
        for line, message in report['problems']:
            print(f'{log}:{line}: {message}')
        counts = ', '.join(f'{n} {label}' for label, n in report['counts'].items())
        n = len(report['problems'])
        bad += n
        print(f"{log}: {len(report['claims'])} claims ({counts}), {n} problem{'' if n == 1 else 's'}")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
