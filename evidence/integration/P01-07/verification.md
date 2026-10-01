# P01-07 integration verification

Date: 2026-10-01

Scope: independent main-worktree verification of the local native-2D elastic
tangent contract returned from `research/p01-07-elastic-tangent`. This accepts
P01-07 numerical behavior only. It does not certify biological parameters,
constitute a heterogeneous-network campaign, prove stability, or accept G1.

## Integrated commits and review

- `5990e09` — `Define elastic tangent regression contract`
- `8adf0de` — `Validate raw elastic tangent conventions`
- `b1c8fff` — `Correct periodic ring fixture documentation`
- `60cfa09` — `Record elastic tangent verification evidence`
- `b265c9e` — `Clean elastic verification report formatting`

`git diff --name-only 0ce42ad..b265c9e` contained only the assigned source,
test, report, and evidence paths. `git diff --check 0ce42ad..b265c9e` exited 0.
Every returned commit has author and committer exactly
`Mohammad Zoraiz <zoraizmohammad@gmail.com>`.

The independent read-only reviewer rejected intermediate versions that
misstated minimization, did not replay persisted stencils, left the legacy
route apparently scientific, conflated the immutable fixed reference with a
later tangent base, and implied all final coordinates were affine. All were
corrected before the reviewer returned `ACCEPT` with no remaining blocker.

## Main-worktree test evidence

All commands ran from `C:\Users\mzora\MechWorld` using the ignored local
`.venv`, one serial solver instance at a time.

1. Focused:

   `.venv\Scripts\python.exe -B -m pytest tests\physics\test_elastic_tangent.py -q --junitxml=evidence\integration\P01-07\focused.xml`

   Result: exit 0; 11 passed, 0 failed, 0 errors, 0 skipped; outer runtime
   4.6556155 s. SHA-256:
   `C6DB71D214938BCF760AEEAEE4D5FD6FA3ED07D7C117E25419C6CF2A58985378`.

2. Compatibility:

   `.venv\Scripts\python.exe -B -m pytest tests\physics\test_elastic_tangent.py tests\physics\test_energy_force_virial.py tests\physics\test_physics_profiles.py tests\unit\test_analysis_regression.py -q --junitxml=evidence\integration\P01-07\compatibility.xml`

   Result: exit 0; 58 passed, 0 failed, 0 errors, 0 skipped; outer runtime
   4.0039976 s. SHA-256:
   `563D974FF5492064B00044C8E34C186CC546078FD16D93492103AC30C2DFD3B8`.

3. Full:

   `.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence\integration\P01-07\full.xml`

   Result: exit 0; 164 passed, 0 failed, 0 errors, 0 skipped; outer runtime
   6.4091978 s. SHA-256:
   `980174EB602A20B60F447A077EA33905FBB1C5E0F58C74F44A1F27244F21B668`.

4. In-memory compilation with bytecode disabled covered the two owned source
   files, focused test, and convergence reproducer. Result: 4 files, exit 0,
   outer runtime 0.1683536 s.

5. The convergence reproducer was executed independently and parsed in memory.
   Result: exit 0 in 0.5985012 s; 21/21 real LAMMPS 20260902 instances closed;
   every minimization passed; maximum final force
   `2.45563569478691e-11 pN`; successive error ratios
   `0.25000006351491927` and `0.24999975011362255`; canonical payload hash
   `sha256:1434d2131531253e775be37d3f250aea06bf7c891ae009011ec147174dd2c10d`.

## Accepted contract

- The immutable fixed-cell reference and later local tangent base are distinct;
  `H_ref/N_ref` are retained while perturbations use
  `H(q)=F_inc(q)@H_base`.
- `q=[epsilon_xx,epsilon_yy,gamma_xy]`, with engineering simple shear; rows are
  `[Nxx,Nyy,Nxy]`, columns are the three q components.
- `N=-W/A_current` uses configurational virial only and remains in native
  `pN/nm`. The result is a local current-area Cauchy-like spatial/algorithmic
  tangent, not a general finite-strain material tensor or 3D modulus.
- A general sample receives an affine trial remap and then fixed-cell
  nonaffine relaxation on the same topology/branch.
- All nine raw entries are retained. Asymmetry and normal-shear coupling are
  diagnostics and are never averaged away.
- Persisted records replay every derivative entry from their saved stencil and
  fail closed on cell, area, step, branch, topology, profile, minimization, or
  solver-provenance changes.
- A branch-changing one-sided quotient is a directional secant with no elastic
  tangent/equilibrium modulus claim.
- The inherited positive-only, default-pressure, symmetrized route fails closed
  unless explicitly requested for labeled forensic reproduction. Both new and
  forensic solver paths close on injected failure.

## Limitations and follow-up

The real solver fixture is an eight-bond oblique prestressed minimized periodic
harmonic ring, not a heterogeneous PG-network campaign. A nonsymmetric 3x3
homogeneous tangent is not a stability proof. The inherited
`task_compute_elastic_tensor.py` wrapper now fails closed until P01-11 migrates
it to the validated raw route or explicitly confines it to forensic
reproduction. Final biological parameter review remains P01-05
`BLOCKED_HUMAN`.
