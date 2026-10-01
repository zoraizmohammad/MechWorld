# P02-01 verification record

Date: 2026-10-01 (America/New_York)

Branch: `research/p02-01-loading-controls`

Base commit: `94c175a3c455e1cccecb82ba7bc219494950f7cb`

Base tree: `d4d1ecd7aeb78560883489769a15d0d9f7b34f84`

Implementation commit: `9291f0b686e079c7b38045d61f08b7c166665b3b`

Working directory: `C:\Users\mzora\MechWorld-wt-p02-01`

Interpreter: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe` (`Python 3.11.9`)

Resource boundary: local-only, one test/build process at a time, with
`OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`, and `MKL_NUM_THREADS=2` for the
final wheel/full runs. No production simulation, cluster, cloud, private data,
or public action was used.

## Exact defect-first evidence

- `python -m pytest tests/physics/test_loading.py -q --junitxml=evidence/subagents/P02-01/red.xml`
  exited 1 before implementation because `pgworld.simulation.controls` did not
  exist. This is the first reproduced-defect regression.
- The first implementation run is retained as `focused-initial.xml`: 26 passed,
  1 failed. The failure exposed the ambiguous `prescribed_remove` event name;
  the contract now records `prescribed_removal`.
- `review-red.xml` records 9 failures for direct-constructor bypasses, irrelevant
  cyclic fields, and non-string weakening parameter names. The matching
  corrected run `review-green.xml` records 36 passed.
- `control-integrity-red.xml` records 4 failures for inverted deformation,
  inconsistent increments, and missing cyclic/mode metadata. The matching
  corrected run `control-integrity-green.xml` records 39 passed.
- `semantic-replay-red.xml` records 2 failures for mode/pressure relabeling. The
  matching corrected run `semantic-replay-green.xml` records 40 passed.
- The pre-ownership-expansion full run `full.xml` records 199 passed and 1
  failed: the P01-11 exact wheel allowlist correctly rejected the new
  `pgworld/simulation/controls.py`. The integrator explicitly expanded P02-01
  ownership to that one release test; no exclusion check was removed.

## Final verification

1. Focused control contract:

   ```powershell
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests/physics/test_loading.py -q --junitxml=evidence/subagents/P02-01/semantic-replay-green.xml
   ```

   Exit 0: 40 passed, 0 failed/errors/skipped in 0.237 s.

2. Fresh installed-wheel verification:

   ```powershell
   $env:OMP_NUM_THREADS='2'
   $env:OPENBLAS_NUM_THREADS='2'
   $env:MKL_NUM_THREADS='2'
   $env:PGWORLD_WHEEL_EVIDENCE=(Resolve-Path evidence/subagents/P02-01).Path + '\wheel-verification-final.json'
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests/release/test_wheel_install.py -q --junitxml=evidence/subagents/P02-01/wheel-final.xml
   ```

   Exit 0: 1 passed in 128.58 s. The strict wheel allowlist passed; installed
   `pgworld.simulation.controls` resolved from the fresh site-packages; its
   schema/mode/time-claim smoke passed. The wheel SHA-256 was
   `b103aa8cbd32cd701cefffd622057e24efca632fb64927a1232c509a9fda143e`.
   The same clean-install test also retained the accepted bounded P01-06/P01-07
   checks. Exact environment and module paths are in
   `wheel-verification-final.json`.

3. Full repository suite:

   ```powershell
   $env:OMP_NUM_THREADS='2'
   $env:OPENBLAS_NUM_THREADS='2'
   $env:MKL_NUM_THREADS='2'
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/subagents/P02-01/full-final.xml
   ```

   Exit 0: 213 passed, 0 failed/errors/skipped in 155.742 s. Fourteen warnings
   are retained inherited deprecation/escape-sequence warnings, not P02-01 test
   failures.

4. Compilation and whitespace:

   ```powershell
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m compileall -q src tests/physics/test_loading.py tests/release/test_wheel_install.py
   git diff --check
   ```

   Both exited 0. Git emitted only Windows LF-to-CRLF checkout notices.

## Raw config SHA-256

| Config | SHA-256 |
|---|---|
| `axial_v1.json` | `fabd8fa22d5a4ae53019e88573e03fa36b41b1d5eb6245074d98ad03e304e967` |
| `cyclic_loading_unloading_v1.json` | `3953674eec3fffeaf6c405b3550af1bdafa45d5b6d077bea970197cc88255a8d` |
| `engineering_simple_shear_v1.json` | `586b4438d3c5c9a57789905b2870572418c93548b085ee84da62078d26f2bc61` |
| `hoop_v1.json` | `917e5fd5c9f1cb68c33d418151d11ee1ab7ec58d5db68cd1197f9252e4f2e8dc` |
| `isotropic_v1.json` | `4b85d2ac42b76e2f02c48eac310ce5754eb94f824203ee4e7942ba97c302a0f7` |
| `prescribed_local_removal_v1.json` | `99b89ba2da2ef3684857d2da5e61a320d92abbbc017db3c8067a1855e89ba318` |
| `prescribed_local_weakening_v1.json` | `5b4fa3e2efd57254bcaa0f7f22b30f3ac30c66390dfea49e52fdf218b4b3fbfb` |
| `pressure_closed_cylinder_v1.json` | `9dfa8ecd2d700aec8cc76cd6588afe0e6939d3e72b25e36df0f9e8fdfb4f78a8` |
| `unequal_biaxial_v1.json` | `f97fb669e01feaf38eba711fdac596a3b74d46dfb9b3092900a022456c0f1fc0` |

Source working-file SHA-256 values at verification were
`0211a46b1e22bafea80cfa9341e82b1c0c7e2206f11f5684c4a90dd8e36f5c15`
for `controls.py`,
`85d5ca94ef2a560d33688d920bc7bfce00f3db950c7b6e26d2f12b95eac1ff41`
for `test_loading.py`, and
`518be7704dfe26dac2de4085d2cb93c534ad8dad8aaa1ef2196d64fad509dbcc`
for the wheel-install test.

These raw hashes are evidence for the checked templates. A downstream run
manifest still must hash the exact bound run config and store its expanded
typed control records.

## Scope and limitations

- The implementation is a typed, solver-independent control contract. It does
  not implement relaxation, rupture criteria, topology mutation, cascades,
  restart equivalence, trajectory export, training, or a production sweep.
- `lambda_load` and cumulative absolute-lambda path progress are quasi-static
  loading coordinates, not time. Physical time is invalid in every record.
- The config files' `fixed-cell-equilibrated-input-required` IDs are explicit
  templates. A solver run must bind them to an actual recorded fixed-cell
  equilibrated reference; these placeholders are not reference evidence.
- The cyclic raw config retains `base_mode`; normalized immutable
  `mode_parameters` retains it in typed serialization, together with an
  unequal-biaxial direction or shear selector where applicable.
- Pressure targets implement only the declared closed thin-cylinder,
  away-from-end-effects balance. They do not relabel isotropic strain as
  turgor and do not model normal inflation.
- Prescribed weakening/removal remains distinct from material rupture and
  damage initiation. This task produces per-interaction effective parameters
  and alive masks; it does not mutate a shared LAMMPS type coefficient.
- The numerical profiles remain provisional and biologically uncertified.

## Ownership and identity

Changed paths are limited to the assigned P02-01 controls, package export,
load configs, focused tests/evidence/report, plus the integrator-authorized
single release allowlist/import-smoke file. Root README, handoff, TASKS, gates,
profiles, solvers, schemas, and private data were not edited.

Repository-local and effective author/committer identity both resolved to
`Mohammad Zoraiz <zoraizmohammad@gmail.com>` before commit.

Evidence-commit preparation had one non-scientific shell failure: a PowerShell
command containing the POSIX `|| exit 0` separator exited 1 at parse time, so
none of its operations ran. The cause was shell-syntax mismatch; it was rerun
with a native `$LASTEXITCODE` conditional. No source, test, or evidence file
was changed by the failed command.
