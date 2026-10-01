# P01-04 verification evidence

Environment: `C:\Users\mzora\MechWorld-wt-p01-04`, branch `research/p01-04-reproducibility`, shared ignored environment `C:\Users\mzora\MechWorld\.venv`, Python 3.11.9.

| Check | Exact command | Exit | Measured result | Artifact |
|---|---|---:|---|---|
| Red regression | `python -m pytest tests/unit/test_generator_reproducibility.py -q --junitxml=evidence/subagents/P01-04/red-pytest.xml` | 1 | 9 failed in 7.22s before production edits | `red-pytest.xml`, `red-regression.md` |
| Focused acceptance | `python -m pytest tests/unit/test_generator_reproducibility.py -q --junitxml=evidence/subagents/P01-04/targeted-pytest.xml` | 0 | 14 passed in 3.38s | `targeted-pytest.xml` |
| Distribution/orientation compatibility | `python -m pytest tests/unit/test_distributions.py test/test_glycan_orientation.py -q --junitxml=evidence/subagents/P01-04/compatibility-pytest.xml` | 0 | 30 passed in 6.46s | `compatibility-pytest.xml` |
| Full inherited/current suite | `python -m pytest -q --junitxml=evidence/subagents/P01-04/full-pytest.xml` | 0 | 76 passed in 6.00s | `full-pytest.xml` |
| Compilation | `python -m py_compile src/assemble_pg_network.py src/lammps_PG_objects.py tests/unit/test_generator_reproducibility.py` | 0 | all three targets compiled | console result |
| Whitespace/conflict check | `git diff --check` | 0 | no errors; Git reported only the worktree's LF-to-CRLF warning | console result |
| LAMMPS data reader | `python evidence/subagents/P01-04/lammps_read_data_probe.py` | 0 | LAMMPS 20260902 loaded 108/108 atoms, closed, and the 324 coordinate tokens had measured max/RMS round-trip error 0 | `lammps-read-data.txt` |

Evidence-formatting note: an attempted `perl -pi -e "s/[ \t]+$//" evidence/subagents/P01-04/red-pytest.xml` exited 1 because Perl is not installed. The six pytest-traceback trailing-whitespace lines were then removed explicitly, and `git diff --cached --check` passed. No test was rerun or result changed by this XML-only formatting.

The deterministic fixture uses `Ny=12`, requested density `0.7`, anisotropy `0.6`, `UNI=2=5`, master seed `20261001`, and RNG backend `python`. Its realized graph SHA-256 is `c345367c3ceb3bf282679f55549c00d220780dd82dcb91ac1d2c148ba1c7814c`. It contains 108 atoms, 97 bonds, 44 angles, 32 glycans, 76 glycan bonds, 21 peptide bonds, 13 connected components, achieved density `0.6999999999999996`, and achieved crosslink fraction `0.3888888888888889`. The realized length tuple includes a 6-DSU filler strand even though requested support ends at 5, directly exercising achieved rather than requested reporting.

Source/test hashes at verification:

- `src/assemble_pg_network.py`: `4d5a0f15f8c9f06e5f46c8e9b487e2604e72bf6f0641913aa90a3542fc5b5da5`
- `src/lammps_PG_objects.py`: `190569fccae7b9c02c5d4e83fd01a4108ca4219b4c79c9a428d2ec86b0f2bd29`
- `tests/unit/test_generator_reproducibility.py`: `67f1a1319afdb4f298f06e6a3c6c4760e29801c202e32d23810545621337bf9b`

These are software/generator checks only. No production simulation, fracture, trained model, or experimental validation was run or claimed.
