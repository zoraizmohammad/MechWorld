# P02-03 integration verification

Date: 2026-10-01

Accepted subagent range:
`0ee619434daa414e76d70aacb914e6393c6652e7..23d9ed5bc67d1f6e27113be3c8f4a0a882c0cb90`.

Integrated main commits: `1ea1d25`, `875f298`, and `056dd98`. All source
commits have Mohammad Zoraiz `<zoraizmohammad@gmail.com>` as sole author and
committer. The independent reviewer accepted the immutable range after
adversarial correction and a final report-selector correction.

## Main-tree commands and results

- The first focused command used the repository virtual environment without
  adding the checkout `src` directory to `PYTHONPATH`. Collection failed twice
  with `ModuleNotFoundError: pgworld`; exit 2. This environment error is
  preserved as `focused-main.xml` (SHA-256
  `f662cead2f4cbc4ccc2d0a10033be20128c101d536e236b3015e2bcf74eccd77`).
- Corrected focused command, with main `src` and the authorized LAMMPS Python
  path on `PYTHONPATH` and all numerical thread variables capped at two:
  `.venv\Scripts\python.exe -B -m pytest tests/unit/test_fracture_topology.py tests/integration/test_fracture_cascade.py -q --junitxml=evidence/integration/P02-03/focused-main-correction.xml`.
  Exit 0; **60 passed in 9.07 s**. Artifact SHA-256:
  `fd82b79d5a44b646d14c1d34c9bc103fb17b2df3dfcff18ce0cf38223f7e658a`.
- Full integrated command under the same environment:
  `.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence/integration/P02-03/main-full.xml`.
  Exit 0; **331 passed, 14 warnings in 552.04 s**. Artifact SHA-256:
  `22710e1d1f974140ce895d89f19be0b6ab7bd1136b91968b44c2e8e7b8621ca1`.

The integrated result accepts the bounded transactional cascade contract and
its constrained real serial harmonic fixture. It does not accept G2, a
production/general PG or nonlinear-peptide adapter, event localization,
derived energy/work accounting, restart/sensitivity, physical time,
biological parameters, or public release.
