# P01-11 — installable mechanics package and G1 candidate

## Return status

The implementation is complete on `research/p01-11-package-g1` from accepted
base `a0d625994d593c236195dda2734c62111d201ea1`. The substantive implementation
commit is `ea59aea89e9431689b63db1bc8288b30116a2534`; the final evaluated source
revision is `a9d6d690e89a761758acc1ac3e72f98087278543`, whose only change removes four
terminal blank lines flagged by `git diff --check`. Gate acceptance,
integration, and release remain integrator decisions; this report does not
accept G1.

## Implemented result

- A standards-based `pyproject.toml` builds `mechworld-pg` and exposes only the
  `pgworld doctor` console command.
- All four immutable profile JSON files are package resources copied exactly
  from their accepted Git blobs. Loading works outside the checkout, preserves
  all canonical IDs/hashes, and rejects a modified installed resource.
- `tools/doctor.py` is a compatibility wrapper around `pgworld.doctor`. The
  real LAMMPS fixture is profile-provenanced and closes the solver.
- The verified `pgworld` modules and twelve required top-level legacy core
  modules are installed deliberately. Figure/task/sandbox/cluster scripts and
  private/generated material are excluded by a strict member allowlist.
- The old elastic task is default-deny. Explicit forensic execution is labeled;
  deletion needs a second flag and cannot occur after false return, exception,
  or through a symbolic-link input.
- The exact seven Python 3.11 nested-f-string parse failures have quote-only
  repairs. All 80 Git-tracked Python files compile after the implementation
  commit.
- The workstation lock records exact Python distributions while explicitly
  separating external LAMMPS 20260902, which has no distribution metadata.

## Clean artifact evidence

The final full-suite wheel test used an isolated PEP 517 build and a fresh venv
without system site packages. It installed every exact lock entry, returned
`No broken requirements found.` from `pip check`, installed the wheel, cleared
`PYTHONPATH`, and added only the authorized external LAMMPS path through a
`.pth` file. Every `pgworld` and legacy module resolved under the fresh venv's
`Lib/site-packages`; `lammps` resolved under the exact installer path; neither
checkout appeared on `sys.path`.

The transient wheel was
`mechworld_pg-0.1.0.dev0-py3-none-any.whl`, SHA-256
`3f2884d62609493801194148f5b8387178799a37548cb7ed52832e0546b2a4db`.
Its exact member list and strict allowlist result are in
`evidence/subagents/P01-11/wheel-install.json`. No wheel, build directory, or
egg-info remains in the checkout.

Installed numerical evidence:

- `pgworld doctor`: exit 0; LAMMPS `20260902`; solver closed; immutable legacy
  profile identity recorded; analytical component energies passed.
- P01-06 harmonic fixture: energy error `0.0 pN nm`, maximum force error
  `0.0 pN`, maximum configurational-virial error `0.0 pN nm`; solver closed.
- P01-07 periodic tangent: seven instances started and seven closed under
  LAMMPS `20260902`; no physical-time claim.
- Installed profile tamper test: `PhysicsProfileError` with a changed computed
  hash, as required.

## Verification summary

- Exact initial red contract: 5 failed in 0.45 s. Missing metadata, resources,
  CLI, forensic task flags, and seven tracked syntax failures all reproduced.
- Final focused/compatibility selection: 24 passed in 23.38 s.
- Final wrapper/contract selection: 6 passed in 0.65 s.
- Final full suite at revision `a9d6d69`: 172 passed, 0 failed, 0 errors, 0
  skipped, 14 warnings in 183.73 s (outer 185.52 s).
- Standalone tracked-source compilation after the implementation commit:
  80 files, 0 failures, exit 0 in 0.270 s.
- `git diff --check a0d6259..a9d6d69` exited 0.

Commands, exact paths, exit codes, runtimes, wheel members/hash, module paths,
locked versions, solver/profile evidence, and limitations are recorded in
`evidence/subagents/P01-11/verification.md` and `wheel-install.json`.

## Boundaries

- Numerical agreement validates implementation consistency, not biological
  parameters or the unresolved molecular coarse-graining.
- The dependency lock is workstation-specific because LAMMPS is an external
  native installer dependency.
- The repository has no tracked license/notice file; no license was invented.
- No large sweep, restart migration claim, experiment, trained model, public
  release, deployment, or gate acceptance is claimed.
