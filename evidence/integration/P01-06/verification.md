# P01-06 integration verification

Date: 2026-10-01

Scope: independent integration review of the analytical, finite-difference, and
real serial LAMMPS energy/force/virial oracle returned from
`research/p01-06-energy-force-virial`. This verifies numerical implementation
consistency under immutable legacy/provisional profiles. It does not certify
biological parameters, physical-time behavior, rupture behavior, or gate G1.

## Integrated commits and ownership

- `05ef3fc` — `Add independent energy force and virial oracle`
- `56eec8b` — `Record P01-06 verification evidence`
- `709933f` — `Reject invalid periodic bond fixtures`
- `git diff --name-only 47834ce..709933f` contained only the assigned
  `src/pgworld/physics/`, `tests/physics/test_energy_force_virial.py`,
  `evidence/subagents/P01-06/`, and
  `docs/subagents/P01-06-energy-force-virial.md` paths.
- `git diff --check 47834ce..709933f` exited 0.
- Author and committer on all three commits were exactly
  `Mohammad Zoraiz <zoraizmohammad@gmail.com>`.

## Main-worktree verification

All commands ran from `C:\Users\mzora\MechWorld` with the ignored local
`.venv` and no persistent simulation or training process.

1. Focused suite:

   `.venv\Scripts\python.exe -B -m pytest tests\physics\test_energy_force_virial.py -q --junitxml=evidence\integration\P01-06\focused.xml`

   Result: exit 0; 26 passed, 0 failed, 0 errors, 0 skipped; outer PowerShell
   runtime 3.7111698 s. SHA-256:
   `67D17AC5426849C8DF5F20792998ADF85CBEA671CF5A09D7B682AACE65C953EE`.

2. Compatibility suite:

   `.venv\Scripts\python.exe -B -m pytest tests\physics\test_energy_force_virial.py tests\physics\test_physics_profiles.py tests\unit\test_periodic_geometry.py -q --junitxml=evidence\integration\P01-06\compatibility.xml`

   Result: exit 0; 56 passed, 0 failed, 0 errors, 0 skipped; outer runtime
   3.263041 s. SHA-256:
   `2D5EEF4DD7F11D8389F32E2ED8983FF0438F80514978A0EA953029F082812468`.

3. Full suite:

   `.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence\integration\P01-06\full.xml`

   Result: exit 0; 153 passed, 0 failed, 0 errors, 0 skipped; outer runtime
   5.234336 s. SHA-256:
   `76EDC7D0AAE18003C6CF607C8F48B005ED5EE1EB18B256FB495C276862B78571`.

4. Targeted source compilation used Python's `compile()` with bytecode disabled
   for `src/pgworld/physics/__init__.py`,
   `src/pgworld/physics/energy_force_virial.py`,
   `src/pgworld/physics/lammps_oracle.py`, and
   `tests/physics/test_energy_force_virial.py`. Result: exit 0; 4 files.

5. An independent report assertion checked LAMMPS version 20260902, solver
   closure, all four registered profile cases, both periodic-crossing cases,
   explicit non-physical-time metadata, and error ceilings of `1e-12 pN nm`
   for energy and `1e-10` for force/virial. It also compared 10,000 seeded
   random orthogonal cases against the accepted periodic helper. Result: exit
   0; maximum minimum-image length mismatch 0.0 nm.

## Numerical evidence

The real-LAMMPS comparison report records:

- maximum energy absolute error: `0.0 pN nm`;
- maximum force absolute error: `4.547473508864641e-13 pN`;
- maximum virial absolute error: `1.8189894035458565e-12 pN nm`;
- periodic nonlinear energy, force, and virial absolute errors of `0.0 pN nm`,
  `2.220446049250313e-16 pN`, and
  `1.1102230246251565e-16 pN nm`, respectively;
- kinetic-pressure increment `7.119312169123759e-06 pN/nm` versus the recorded
  analytical `2m/A` value `7.119312169647791e-06 pN/nm`;
- all solver instances closed.

The implementation rejects zero minimum-image bond lengths, nonlinear fixtures
outside the open periodic radial domain, and angles in the LAMMPS
`sin(theta) <= 0.001` clamp regime. New reported membrane tension is
configurational and native 2D, with `N = -W/A`; total tension is primary and
incremental tension is measured from the fixed-cell equilibrated reference.

## Review outcome and limits

Accepted for P01-06. The first returned implementation required two substantive
corrections before acceptance: complete mass/kinetic-pressure provenance and
minimum-image validation before nonlinear solver construction. A separate
read-only reviewer accepted the final correction. Persistent per-edge image
identity remains P03-01 scope. Final biological parameter certification remains
P01-05 `BLOCKED_HUMAN`; this result does not authorize a production sweep or
accept G1.
