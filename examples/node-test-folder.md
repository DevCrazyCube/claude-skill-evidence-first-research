# Does `node --test` take a folder?

A README said "run the tests with `node --test tests/`". Does that run the tests in `tests/`?

**Setup.** Node v26.2.0 on Linux. One project folder with one test file, `tests/progress.test.mjs`, holding
nine tests. Every command was run from the project folder.

## Measured

- [FACT] `node --test tests/` exits 1 on Node v26.2.0, and its output starts with "Cannot find module" and the
  folder's path (measured: `node --test tests/`, 2026-11-11)
- [FACT] `node --test` with no arguments exits 0 and reports 9 tests, 9 passed
  (measured: `node --test`, 2026-11-11)
- [FACT] `node --test "tests/*.test.mjs"` exits 0 and reports 9 tests, 9 passed
  (measured: `node --test "tests/*.test.mjs"`, 2026-11-11)
- [FACT] `node --test tests/progress.test.mjs` exits 0 and reports 9 tests, 9 passed
  (measured: `node --test tests/progress.test.mjs`, 2026-11-11)

## Read

- [FACT] The current documentation (the page is for v26.13.1) says that with no arguments Node runs the files
  that match a fixed list of patterns, among them `**/*.test.{cjs,mjs,js}` and `**/test/**/*.{cjs,mjs,js}`
  (source: https://nodejs.org/api/test.html, accessed 2026-11-11)
- [FACT] The same section says glob patterns can be given as the final arguments, and it names no folder
  argument (source: https://nodejs.org/api/test.html, accessed 2026-11-11)
- [FACT] The documentation for v20 (the page is for v20.20.2) gives `node --test test1.js test2.mjs
  custom_test_dir/` as an example and says a folder given this way is searched recursively
  (source: https://nodejs.org/docs/latest-v20.x/api/test.html, accessed 2026-11-11)

## Not yet known

- [HYPOTHESIS] The folder form runs the nine tests under Node 20 (test: run `node --test tests/` under Node 20
  in the same project folder)
- [HYPOTHESIS] With no arguments, a helper file `tests/helper.mjs` is not run as a test, because the folder
  pattern is `test` and not `tests` (test: add the file with one failing test and run `node --test`)
  (result: confirmed, by the fact under "Measured later")
- [OPEN] In which Node version did the folder form stop working?

## Measured later

- [FACT] In a scratch folder holding `tests/a.test.mjs` (one passing test) and `tests/helper.mjs` (one failing
  test), `node --test` exits 0 and reports 1 test, 1 passed (measured: `node --test`, 2026-11-11)

## Decided

- [DECISION] READMEs and CI name the test file, never the folder (because: the folder form exits 1 on Node 26,
  the file form exits 0, and both are measured above)

## Not measured

Nothing here was run on Node 20 or 22. The v20 behaviour is what its documentation says, not something seen.
The helper-file result is for a folder named `tests`; a folder named `test` was not tried.
The two version numbers differ on purpose: the commands ran on the installed v26.2.0, and the documentation
page that nodejs.org serves is for v26.13.1.
