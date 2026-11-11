---
name: evidence-first-research
description: Keep a research log in which every claim is labelled FACT, HYPOTHESIS, DECISION or OPEN, every fact carries a dated source or a dated measurement, and nothing is stated that was not read or run. Use when investigating a question whose answer someone will act on (a bug's cause, a library's behaviour, a benchmark, a market or literature question), when asked to "research", "find out", "verify", "check whether" or "compare", and before reporting a number or a cause.
---

# Evidence-first research

A research answer is worth what its weakest claim is worth. This skill keeps the claims apart by what holds
them up, in a log a script can check.

## The log

One Markdown file per question (start from `research-log-template.md`). Every top-level list item is one claim
and starts with one of four labels:

| Label | What it is | What it must carry |
|---|---|---|
| `[FACT]` | Something read in a primary source, or seen in a run | `(source: URL or doi:…, accessed YYYY-MM-DD)` or `(measured: \`command\` or file, YYYY-MM-DD)` |
| `[HYPOTHESIS]` | Something that may be true | `(test: how it would be checked)`, and later `(result: confirmed \| refuted \| inconclusive, where that is shown)` |
| `[DECISION]` | Something chosen | `(because: the reason, pointing at facts in the log)` |
| `[OPEN]` | Something not known | A question mark |

Check the log before reporting from it:

```bash
python3 scripts/claims_lint.py LOG.md          # exit 0 clean, 1 problems, 2 cannot run
python3 scripts/claims_lint.py LOG.md --open   # what is still open
```

The linter checks the form: a label, the evidence, a real date that is not in the future, no hedge word in a
fact. It cannot check that a source says what the claim says. That part is yours, and it is the rules below.

## The rules

1. **A fact is something you read or ran in this piece of work.** What you remember is a hypothesis until you
   have looked. Training knowledge, a forum answer and another agent's report are all "remembered".
2. **Primary sources.** The documentation, the source code, the paper, the standard, the dataset. A blog post
   about the documentation is a pointer to it; follow the pointer and cite where it lands. Give the URL and the
   day you read it, and say which version the page is for when it has one.
3. **A third party's claim is a fact about the claim.** "The vendor's page says 99.9 %" is a fact. "It is
   99.9 %" is not, until something independent shows it.
4. **Never invent a result.** Every number in the log comes from a command run for this log or from a cited
   source. If neither exists, write "not measured" under the log's last heading. No estimate dressed as a
   measurement, no example output that was not produced.
5. **Record the command, not the impression.** `(measured: …)` holds the exact command or the file it wrote, so
   someone else can run it. Note versions and the machine in the Setup line.
6. **A hedge moves the claim.** If the sentence needs "probably", "should" or "seems", it is a hypothesis.
   Write it as one, with the test that would settle it.
7. **A hypothesis names its test before the test is run.** Then run it if it is cheap. The result is a new
   fact, and the hypothesis gets `(result: …)` pointing at it.
8. **Append, never rewrite.** A refuted hypothesis stays in the log with its result. A fact that turned out
   wrong stays too, followed by the fact that corrects it. The log is the record of how the answer was reached.
9. **Unknowns fail loudly.** An input the method does not understand, a row that does not parse, a case that
   was skipped: count it and report it. Never drop it silently, never fill it with a default.
10. **No information from later.** When judging an earlier decision or testing a rule on past data, use only
    what was known at that moment. Data used to choose a method is not used to score it. A held-out set is
    looked at once.
11. **Results net of costs, against doing nothing.** A gain is reported after every cost that applies (time,
    money, fees, failures), next to the result of the simplest alternative, including "change nothing".
12. **A confident sentence is not evidence.** This applies to your own earlier text as much as to anyone
    else's. Re-read a claim's source before building on it.
13. **Old evidence expires.** For anything that changes (APIs, prices, versions), run the linter with
    `--max-age DAYS` and check the stale facts again.
14. **Gates before anything costly or irreversible.** The log can end in a recommendation. Spending money,
    publishing, deleting or switching something on needs the owner's explicit yes, given after they have seen
    the log's open items.

## How to work

1. Write the question as a question, and the setup.
2. Write down what you believe as `[HYPOTHESIS]` lines, each with its test. Write what you do not know as
   `[OPEN]`.
3. Read and run. Each thing found becomes a `[FACT]` with its evidence, added the moment it is found.
4. Give hypotheses their results. Add the decisions, each pointing at the facts it rests on.
5. Run the linter. Fix the log, not the linter's complaint: a fact without evidence becomes a hypothesis or gets
   its evidence; it does not get a made-up source.
6. Run `--open` and read the list.

## The report

Four parts, in this order, each taken from the log:

1. **Answer** — one or two sentences, only as strong as the facts.
2. **What it rests on** — the facts, each with its source or command.
3. **What is not known** — the output of `--open`, and the "Not measured" section.
4. **What I would do** — the decisions, and what needs the owner's yes.

If the answer is "not known yet", say that first and say what test would settle it.

## Files

- `research-log-template.md` — the empty log
- `scripts/claims_lint.py` — the linter (standard library, Python 3.8+)
- `examples/node-test-folder.md` — a real log that passes; `examples/unlabelled-notes.md` — one that fails
