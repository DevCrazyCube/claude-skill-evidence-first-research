"""python3 -m unittest discover -s tests"""
import datetime
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SCRIPT = os.path.join(ROOT, 'scripts', 'claims_lint.py')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import claims_lint as cl  # noqa: E402

TODAY = datetime.date(2026, 6, 1)


def problems(text, **options):
    return [message for _, message in cl.lint(text, TODAY, **options)['problems']]


class Parsing(unittest.TestCase):
    def test_top_level_items_are_claims_and_wrapped_lines_are_joined(self):
        text = ('# Log\n\nSome prose.\n\n'
                '- [OPEN] Does it scale\n  past ten users?\n'
                '* [OPEN] And why?\n'
                '1. [OPEN] Numbered too?\n\n'
                'Not a claim.\n')
        self.assertEqual(cl.claims(text), [(5, '[OPEN] Does it scale past ten users?'),
                                            (7, '[OPEN] And why?'),
                                            (8, '[OPEN] Numbered too?')])

    def test_nested_items_belong_to_their_parent(self):
        text = '- [OPEN] Which one is it?\n  - the first\n  - the second\n'
        self.assertEqual(cl.claims(text), [(1, '[OPEN] Which one is it? - the first - the second')])

    def test_fenced_code_checkboxes_and_switched_off_parts_are_skipped(self):
        text = ('```\n- not a claim\n```\n'
                '~~~\n- nor this\n~~~\n'
                '- [ ] a to-do\n- [x] a done to-do\n'
                '<!-- claims: off -->\n- a plain list\n<!-- claims: on -->\n'
                '- [OPEN] Only this one?\n')
        self.assertEqual(cl.claims(text), [(12, '[OPEN] Only this one?')])

    def test_a_tilde_fence_is_not_closed_by_backticks(self):
        text = '~~~\n```\n- still code\n~~~\n- [OPEN] After the fence?\n'
        self.assertEqual(cl.claims(text), [(5, '[OPEN] After the fence?')])

    def test_groups_keep_balanced_brackets(self):
        found = cl.groups('x (test: call f(1) and g(2) twice) y (because: it is so)')
        self.assertEqual([(k, v) for k, v, _, _ in found],
                         [('test', 'call f(1) and g(2) twice'), ('because', 'it is so')])
        self.assertIsNone(cl.groups('x (test: never closed')[0][1])


class Facts(unittest.TestCase):
    def test_a_sourced_and_a_measured_fact_pass(self):
        text = ('- [FACT] The limit is 100 requests a minute (source: https://example.com/limits, accessed 2026-05-30)\n'
                '- [FACT] The suite takes 12 s here (measured: `make test`, 2026-06-01)\n'
                '- [FACT] The effect was replicated (source: doi:10.1000/xyz123, accessed 2026-01-02)\n')
        self.assertEqual(problems(text), [])

    def test_a_fact_without_evidence_fails(self):
        self.assertEqual(problems('- [FACT] The limit is 100 requests a minute\n'),
                         ['a fact needs (source: URL, accessed YYYY-MM-DD) or (measured: command or file, YYYY-MM-DD)'])

    def test_evidence_needs_a_real_date_that_is_not_in_the_future(self):
        self.assertEqual(problems('- [FACT] It is so here (measured: `x`, last week)\n'),
                         ['(measured: …) must end with ", YYYY-MM-DD"'])
        self.assertEqual(problems('- [FACT] It is so here (measured: `x`, 2026-13-45)\n'), ['2026-13-45 is not a date'])
        self.assertEqual(problems('- [FACT] It is so here (measured: `x`, 2026-06-02)\n'), ['2026-06-02 is in the future'])

    def test_a_source_needs_accessed_and_a_link(self):
        self.assertEqual(problems('- [FACT] It is so there (source: https://example.com, 2026-05-01)\n'),
                         ['a source needs the word "accessed" before its date'])
        self.assertEqual(problems('- [FACT] It is so there (source: a colleague, accessed 2026-05-01)\n'),
                         ['a source is a URL or a DOI (or run with --offline-sources)'])
        self.assertEqual(problems('- [FACT] It is so there (source: Knuth vol. 3, p. 110, accessed 2026-05-01)\n',
                                  offline_sources=True), [])

    def test_a_url_with_brackets_and_commas_is_one_source(self):
        text = '- [FACT] The page says so (source: https://example.com/a_(b),c?d=1, accessed 2026-05-01)\n'
        self.assertEqual(problems(text), [])

    def test_a_hedge_makes_it_a_hypothesis(self):
        got = problems('- [FACT] The cache is probably cold on Mondays (measured: `x`, 2026-06-01)\n')
        self.assertEqual(got, ['"probably" in a fact: a fact with a hedge in it is a hypothesis'])
        # a hedge inside the evidence is not the claim's
        self.assertEqual(problems('- [FACT] The cache is cold on Mondays (measured: `maybe.sh`, 2026-06-01)\n'), [])
        # "likely" is caught as a word, not inside another word
        self.assertEqual(problems('- [FACT] The likelyhood column is empty (measured: `x`, 2026-06-01)\n'), [])

    def test_max_age(self):
        text = '- [FACT] The limit is 100 a minute (source: https://example.com, accessed 2026-01-01)\n'
        self.assertEqual(problems(text), [])
        self.assertEqual(problems(text, max_age=151), [])
        self.assertEqual(problems(text, max_age=90),
                         ['evidence is 151 days old (limit 90): check it again or make it a hypothesis'])

    def test_check_files(self):
        with tempfile.TemporaryDirectory() as base:
            open(os.path.join(base, 'run.json'), 'w').close()
            ok = '- [FACT] The run finished clean (measured: run.json, 2026-06-01)\n'
            gone = '- [FACT] The run finished clean (measured: other.json, 2026-06-01)\n'
            command = '- [FACT] The run finished clean (measured: `other.json`, 2026-06-01)\n'
            self.assertEqual(problems(ok, check_files=True, base=base), [])
            self.assertEqual(problems(gone, check_files=True, base=base), ['measured file not found: other.json'])
            self.assertEqual(problems(command, check_files=True, base=base), [])
            self.assertEqual(problems(gone, base=base), [])


class OtherLabels(unittest.TestCase):
    def test_hypothesis(self):
        self.assertEqual(problems('- [HYPOTHESIS] The cache is cold on Mondays (test: compare hit rates per weekday)\n'), [])
        self.assertEqual(problems('- [HYPOTHESIS] The cache is cold on Mondays\n'),
                         ['a hypothesis needs (test: how it would be checked)'])
        self.assertEqual(problems('- [HYPOTHESIS] The cache is cold on Mondays (test: check)\n'),
                         ['(test: …) must say how, in at least three words'])
        self.assertEqual(problems('- [HYPOTHESIS] It is probably the cache layer (test: turn the cache off)\n'), [])

    def test_a_result_is_one_of_three_words(self):
        good = '- [HYPOTHESIS] The cache is cold on Mondays (test: compare hit rates) (result: refuted, see the fact above)\n'
        bad = '- [HYPOTHESIS] The cache is cold on Mondays (test: compare hit rates) (result: looks fine)\n'
        self.assertEqual(problems(good), [])
        self.assertEqual(problems(bad), ['(result: …) starts with confirmed, refuted or inconclusive'])

    def test_decision(self):
        self.assertEqual(problems('- [DECISION] Use the file form (because: the folder form exits 1)\n'), [])
        self.assertEqual(problems('- [DECISION] Use the file form\n'), ['a decision needs (because: the reason)'])
        self.assertEqual(problems('- [DECISION] Use the file form (because: yes)\n'),
                         ['(because: …) must give the reason, in at least three words'])

    def test_open_is_a_question(self):
        self.assertEqual(problems('- [OPEN] Since which version?\n'), [])
        self.assertEqual(problems('- [OPEN] Find the version\n'), ['an open item is a question: it has a question mark'])

    def test_labels(self):
        self.assertEqual(problems('- The limit is 100\n'),
                         ['no label: start with [FACT], [HYPOTHESIS], [DECISION] or [OPEN]'])
        self.assertEqual(problems('- [fact] The limit is 100\n'), ['[fact] must be upper case: [FACT]'])
        self.assertEqual(problems('- [TODO] Look it up\n'),
                         ['[TODO] is not a label: use [FACT], [HYPOTHESIS], [DECISION] or [OPEN]'])

    def test_an_unclosed_group_and_an_empty_claim(self):
        self.assertEqual(problems('- [DECISION] Use the file form (because: the folder form exits 1\n'),
                         ['(because: … is never closed'])
        self.assertEqual(problems('- [FACT] (measured: `x`, 2026-06-01)\n'),
                         ['the claim itself is missing: say it in at least three words'])

    def test_a_log_without_claims_fails(self):
        self.assertEqual(problems('# Notes\n\nJust prose.\n'),
                         ['no claims found: a research log has at least one labelled list item'])


class Report(unittest.TestCase):
    TEXT = ('- [FACT] The limit is 100 a minute (source: https://example.com, accessed 2026-05-01)\n'
            '- [HYPOTHESIS] It resets on the minute (test: send 100, wait, send one)\n'
            '- [HYPOTHESIS] It counts per key (test: use two keys) (result: confirmed, see run 3)\n'
            '- [DECISION] Batch in tens (because: it stays under the limit)\n'
            '- [OPEN] Does a failed request count?\n')

    def test_counts_and_line_numbers(self):
        report = cl.lint(self.TEXT + '- [FACT] Nothing here to see\n', TODAY)
        self.assertEqual(report['counts'], {'FACT': 2, 'HYPOTHESIS': 2, 'DECISION': 1, 'OPEN': 1})
        self.assertEqual([line for line, _ in report['problems']], [6])

    def test_still_open_is_the_questions_and_the_untested(self):
        rows = cl.still_open(cl.lint(self.TEXT, TODAY))
        self.assertEqual([(r['line'], r['label']) for r in rows], [(2, 'HYPOTHESIS'), (5, 'OPEN')])


class CommandLine(unittest.TestCase):
    def run_cli(self, text, *args):
        with tempfile.TemporaryDirectory() as base:
            path = os.path.join(base, 'log.md')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            done = subprocess.run([sys.executable, SCRIPT, path, '--today', '2026-06-01', *args],
                                  capture_output=True, text=True)
            return done.returncode, done.stdout.replace(path, 'log.md'), done.stderr

    def test_clean_log_exits_0_with_a_summary(self):
        code, out, _ = self.run_cli(Report.TEXT)
        self.assertEqual(code, 0)
        self.assertEqual(out, 'log.md: 5 claims (1 FACT, 2 HYPOTHESIS, 1 DECISION, 1 OPEN), 0 problems\n')

    def test_problems_exit_1_and_name_the_line(self):
        code, out, _ = self.run_cli(Report.TEXT + '- [FACT] It is likely per key\n')
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines(), [
            'log.md:6: a fact needs (source: URL, accessed YYYY-MM-DD) or (measured: command or file, YYYY-MM-DD)',
            'log.md:6: "likely" in a fact: a fact with a hedge in it is a hypothesis',
            'log.md: 6 claims (2 FACT, 2 HYPOTHESIS, 1 DECISION, 1 OPEN), 2 problems'])

    def test_open_lists_and_exits_0(self):
        code, out, _ = self.run_cli(Report.TEXT, '--open')
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ['log.md: 2 still open',
                                            '  2: [HYPOTHESIS] It resets on the minute',
                                            '  5: [OPEN] Does a failed request count?'])

    def test_what_cannot_run_exits_2(self):
        gone = subprocess.run([sys.executable, SCRIPT, os.path.join(HERE, 'no-such-log.md')],
                              capture_output=True, text=True)
        self.assertEqual(gone.returncode, 2)
        self.assertIn('cannot read', gone.stderr)
        code, _, err = self.run_cli(Report.TEXT, '--max-age', '-1')
        self.assertEqual(code, 2)
        self.assertIn('--max-age', err)

    def test_several_logs_one_bad_one_fails_the_run(self):
        good, bad = os.path.join(ROOT, 'examples', 'node-test-folder.md'), os.path.join(ROOT, 'examples', 'unlabelled-notes.md')
        both = subprocess.run([sys.executable, SCRIPT, good, bad, '--today', '2026-11-11'], capture_output=True, text=True)
        self.assertEqual(both.returncode, 1)
        summaries = [line for line in both.stdout.splitlines() if ' claims (' in line]
        self.assertEqual(len(summaries), 2)
        self.assertTrue(summaries[0].endswith('0 problems'))
        twice = subprocess.run([sys.executable, SCRIPT, good, good, '--today', '2026-11-11'], capture_output=True, text=True)
        self.assertEqual(twice.returncode, 0)
        # an unreadable log stops the run before anything is printed
        gone = subprocess.run([sys.executable, SCRIPT, good, os.path.join(HERE, 'no-such-log.md')],
                              capture_output=True, text=True)
        self.assertEqual((gone.returncode, gone.stdout), (2, ''))

    def test_the_shipped_example_and_template(self):
        for name, code in (('examples/node-test-folder.md', 0), ('examples/unlabelled-notes.md', 1),
                           ('research-log-template.md', 0)):
            done = subprocess.run([sys.executable, SCRIPT, os.path.join(ROOT, name), '--today', '2026-11-11'],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, code, name + '\n' + done.stdout)


if __name__ == '__main__':
    unittest.main()
