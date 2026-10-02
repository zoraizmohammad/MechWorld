# P02-04 and P03-01 integrated-main verification

Date: 2026-10-02 (America/New_York)

Working directory: `C:\Users\mzora\MechWorld`

Integration base: `eef815913417431211029c06ac734d500b8d48bd`

Environment controls used for every pytest command:

- `.venv\Scripts\python.exe` (CPython 3.11 project environment)
- `PYTHONHASHSEED=0`
- `OMP_NUM_THREADS=2`
- `OPENBLAS_NUM_THREADS=2`
- `MKL_NUM_THREADS=2`
- `NUMEXPR_NUM_THREADS=2`
- `PYTHONPATH` prefixed with the checkout `src` directory
- one test process at a time

## Commands and results

1. Initial combined source check:
   `.venv\Scripts\python.exe -m pytest tests/physics/test_fracture_accounting.py tests/unit/test_schema.py -q --junitxml=evidence/integration/P02-04-P03-01-focused.xml`
   exited 0 with 156 passed and one JUnit-family warning in 7.08 s. This
   artifact is retained as the first integrated-main check; the later focused
   run uses the legacy JUnit family required by the real-LAMMPS evidence
   property.
2. Focused source plus package-contract check:
   `.venv\Scripts\python.exe -B -m pytest tests/physics/test_fracture_accounting.py tests/unit/test_schema.py tests/release/test_packaging_contract.py -q -o junit_family=legacy --junitxml=evidence/integration/P02-04-P03-01/focused-and-package.xml`
   exited 0 with 163 passed in 3.98 s. This includes 48 P02-04 fracture
   accounting tests (including the bounded real serial-LAMMPS fixture), 108
   P03-01 schema tests, and 7 packaging-contract tests.
3. Isolated installed-wheel check:
   `.venv\Scripts\python.exe -B -m pytest tests/release/test_wheel_install.py -q -o junit_family=legacy --junitxml=evidence/integration/P02-04-P03-01/wheel-install.xml`
   exited 0 with 1 passed in 115.98 s. The exact wheel allowlist includes only
   the new `pgworld.data` source modules; the fresh environment imported them
   outside the checkout, round-tripped a v1 `Cell2D`, passed `pip check`, and
   retained the existing private/generated-artifact exclusions. LAMMPS came
   from the authorized local 2 Sep 2026 installer path recorded by the test.
4. Full integrated suite:
   `.venv\Scripts\python.exe -B -m pytest -q -o junit_family=legacy --junitxml=evidence/integration/P02-04-P03-01/full-suite.xml`
   exited 0 with 487 passed and 14 warnings in 119.37 s. The warnings are the
   already documented legacy elastic-route deprecation plus inherited invalid
   escape-sequence warnings found by tracked-source compilation.
5. Planning-helper applicability check:
   `.venv\Scripts\python.exe -B PG_WORLD_MODEL_EXECUTION_PACKET\tools\check_packet.py --root .`
   exited 1 before task-DAG validation because the live repository intentionally
   does not contain seven packet-only root files (`START_HERE.md`,
   `CODEX_START_PROMPT.md`, packet review helpers/evidence). The packet remains
   preserved untracked instead of being blindly copied over the live checkout.
   `TASKS.json` was separately parsed successfully with PowerShell
   `ConvertFrom-Json`. This command is recorded as an inapplicable packet-layout
   check, not as a software-test failure, and should not be repeated against the
   live root without first writing a repository-specific validator.

## Artifact SHA-256 values

- `P02-04-P03-01-focused.xml`:
  `a666618268fe06724178a4c2a4e9f8a4e3ec34ad1c5e79b6f1747a8740bc5349`
- `focused-and-package.xml`:
  `3bdf70d7f24a09041783c93bf4a7c86e6a7069c0e7fb640919542d898b0a55ad`
- `wheel-install.xml`:
  `581391016da51be33c86d8bee8c75d544e553ad92797e7e287ce6e6eb90c1893`
- `full-suite.xml`:
  `4d35de12a824be6b121dee2a6c525cb88d9bfafe3b4bae495645b2dbf09613aa`

## Acceptance boundary

P02-04 accepts deterministic bounded localization and phase-specific accounting
only for its certified tiny harmonic fixture and supported diagonal
deformation/extension-ratio path. It does not establish nonlinear-peptide
localization, persistent campaign restart equivalence, sensitivity, physical
time, biological fracture parameters, or G2.

P03-01 accepts strict in-memory/JSON-compatible typed records and replay/access
validation. It does not provide solver export, HDF5 storage, datasets, grouped
splits, normalizers, a trained model, experimental data, or G3. P03-02 remains
responsible for agreement between real solver values and exported canonical
trajectory records.
