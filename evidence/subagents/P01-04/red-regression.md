# P01-04 red regression

- Working directory: `C:\Users\mzora\MechWorld-wt-p01-04`
- Interpreter: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe` (Python 3.11.9)
- Pre-source-edit command: `python -m pytest tests/unit/test_generator_reproducibility.py -q --junitxml=evidence/subagents/P01-04/red-pytest.xml`
- Exit status: 1
- Result: 9 failed in 7.22 seconds.
- Reproduced behavior: no named seed contract existed; `generate_pg_network` rejected `seed`; the data writer returned no export measurement and retained two-decimal atom coordinates.
- Machine-readable evidence: `red-pytest.xml` (SHA-256 `808cfead94c4e16afc737c50f4b80a2c8aec66e82c64e3356667335674396659`).

The first attempted red collection also exited 1 because importing the intentionally absent `RNGSeeds` symbol stopped collection. The test import was then changed, still before any production-source edit, so all nine intended acceptance tests executed and failed for the inherited behaviors above.
