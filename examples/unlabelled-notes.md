# Notes: node --test (the "before" example)

The same question as [`node-test-folder.md`](node-test-folder.md), written the way notes usually are. **Nothing
below is a finding.** Each line is here because the linter refuses it; several are untrue.

- `node --test tests/` runs every test in the folder.
- [FACT] The folder form works since Node 18.
- [FACT] It probably broke in Node 22 (source: https://nodejs.org/api/test.html, accessed 2026-11-11)
- [FACT] Glob patterns are supported (source: the Node docs, 2026-11-11)
- [FACT] All nine tests pass here (measured: `node --test`, yesterday)
- [HYPOTHESIS] The folder form still works on Node 20
- [DECISION] Use the folder form in CI
- [OPEN] Check the changelog
- [fact] Nine tests pass
