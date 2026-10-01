# P01-01 parser-slice verification

- Base commit: `c0ec8aa7ed99ecf8cb21f0a9bf8223447743fc39`
- Branch: `research/p01-01-periodic-bounds`
- Worktree/cwd: `C:\Users\mzora\MechWorld-wt-p01-01`
- Interpreter: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`
- Runtime: Python 3.11.9; pytest 7.4.3; local CPU only; no network or solver campaign.
- Inputs: synthetic dump text generated under pytest's temporary directory; no lab or external data read.

## Red regression

Command:

`C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q tests/unit/test_periodic_geometry.py`

Exit 1 before the parser edit: 3 failed in 8.18s. The exact original full-terminal transcript was inspected live. A final exact, concise capture made with the baseline parser restored exited 1 with `3 failed in 9.27s`; it is retained in `red-regression-exact.txt`.

## Green verification

Focused command:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q tests/unit/test_periodic_geometry.py`

Exit 0:

```text
...                                                                      [100%]
3 passed in 7.59s
```

Inherited full-suite command:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q`

Exit 0:

```text
........                                                                 [100%]
8 passed in 7.97s
```

Diff-integrity command:

`git diff --check`

Exit 0. Git emitted only its configured LF-to-CRLF checkout warning for the modified legacy source file; no whitespace error was reported.

## Pre-commit file hashes

- `src/import_data_from_dumps.py`: SHA-256 `3E8AD3E2B6BDDEAE92FAC66FFCCD43C35BE1B44820F58EA98B995CD49DAB1735`
- `tests/unit/test_periodic_geometry.py`: SHA-256 `25104671781F48C316DE808311762638F1F86C2920F20A788C04E4F97AF41BF5`

There was no model, run configuration, or dataset for this bounded parser slice.
