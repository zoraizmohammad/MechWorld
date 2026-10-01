# P01-06 verification record

Date: 2026-10-01 (America/New_York)

## Context

- CWD: `C:\Users\mzora\MechWorld-wt-p01-06`
- Branch: `research/p01-06-energy-force-virial`
- Base revision: `5243771fa97927beafe49dd66cea4c2bec07bb5c`
- Python: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`
- LAMMPS module:
  `C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python\lammps\__init__.py`
- LAMMPS version integer: `20260902`
- NumPy: `2.2.2`
- Execution: serial, one process, bounded `run 0` fixtures only
- Profile ID: `reviewed_physics_provisional_v0`
- Profile canonical hash:
  `sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5`
- Implementation commit: `e6bf57722a5394d33ffd41bcf89fd8adcdc66998`

## Red-first acceptance regression

```powershell
& 'C:\Users\mzora\MechWorld\.venv\Scripts\python.exe' -m pytest tests/physics/test_energy_force_virial.py -q
```

Exit `1`: collection failed with
`ModuleNotFoundError: No module named 'pgworld.physics'`; `1 error in 0.53s`.
The exact output is preserved at `red.txt`. An earlier test-path bootstrap issue
was corrected before this record, so the preserved red result isolates the
missing production implementation.

## Focused acceptance suite

```powershell
& 'C:\Users\mzora\MechWorld\.venv\Scripts\python.exe' -m pytest tests/physics/test_energy_force_virial.py -q --junitxml=evidence/subagents/P01-06/focused.xml
```

Exit `0`: **26 passed in 1.87s**; measured outer wall time `2.569s`.
The suite directly instantiated LAMMPS 20260902; no solver-dependent test was
skipped.

## Compatibility suite

```powershell
& 'C:\Users\mzora\MechWorld\.venv\Scripts\python.exe' -m pytest tests/physics/test_energy_force_virial.py tests/physics/test_physics_profiles.py tests/unit/test_periodic_geometry.py -q --junitxml=evidence/subagents/P01-06/compatibility.xml
```

Exit `0`: **56 passed in 2.07s**; measured outer wall time `2.812s`.
This checks the new oracle together with immutable profile validation and the
accepted periodic-geometry contract without adding a competing image convention.

## Full repository suite

```powershell
& 'C:\Users\mzora\MechWorld\.venv\Scripts\python.exe' -m pytest -q --junitxml=evidence/subagents/P01-06/full.xml
```

Exit `0`: **153 passed in 3.96s**; measured outer wall time `4.885s`.

## Compilation

```powershell
& 'C:\Users\mzora\MechWorld\.venv\Scripts\python.exe' -m py_compile src/pgworld/physics/__init__.py src/pgworld/physics/energy_force_virial.py src/pgworld/physics/lammps_oracle.py tests/physics/test_energy_force_virial.py
```

Exit `0`; measured wall time `0.127s`.

## Real-LAMMPS comparison reproducer

The focused test command is the executable reproducer. It covers harmonic
compression/rest/extension, nonlinear compression/rest/extension/near-pole,
the free-middle two-edge series, a noncollinear angle, horizontal/vertical/
oblique virials, z-width normalization, and kinetic/default-pressure separation.
A separate bounded inline driver serialized the same analytical-versus-solver
case values to `lammps_comparison.json`. A second bounded driver added the
orthogonal periodic-crossing result and one route-specific nonlinear case for
each registered profile.

Driver exit `0`; measured wall time `0.383s`. Observed maxima:

- energy absolute error: `0 pN nm`;
- force absolute error: `4.547473508864641e-13 pN`;
- virial absolute error: `1.8189894035458565e-12 pN nm`;
- z-width configurational-pressure difference: `0 pN/nm`; and
- all solver instances closed: `true`.

Registered-profile/periodic extension driver: exit `0`; measured wall time
`2.007s`. It recorded four exact profile IDs/hashes and the periodic offset
`(1, 0)`; all five solver instances closed. After provenance review, a bounded
metadata driver exited `0` in `0.370s`: the moving fixture used the profile's
`0.0004271587301788674 ag` placeholder mass and observed a kinetic `P_xx`
increment of `7.119312169123759e-06 pN/nm`, versus the reconstructable
`2*m/A = 7.119312169647791e-06 pN/nm`. It explicitly records no physical-time
claim.

A final periodic-nonlinear driver exited `0` in `1.697s`. The raw wrapped
separation exceeded the nonlinear pole, while the accepted minimum-image vector
was `(0.9000000000000004, 0.3) nm` with offset `(1, 0)`. LAMMPS matched the
local analytical oracle with zero energy difference, force difference
`2.220446049250313e-16 pN`, and virial difference
`1.1102230246251565e-16 pN nm`.

## Tolerances

- Native unit arithmetic: approximately `1e-12` absolute or tighter.
- Analytical versus LAMMPS: test-specific `1e-12` to `2e-10` relative, with
  `1e-10 pN nm`, `2e-7 pN`, and `2e-7 pN nm` absolute floors near zero/pole.
- Centered Cartesian finite differences: relative error below `2e-9` for the
  well-conditioned harmonic cases, `2e-6` for nonlinear including the 90%-pole
  point, and `3e-8` for the angle; step sizes are declared in the test.
- Internal force/torque balance: `2e-12` native absolute tolerance.
- z-width invariance: `1e-13 pN/nm` absolute tolerance.

No tolerance was changed to mask a persistent implementation mismatch. One
intermediate angle comparison exposed LAMMPS local atom reordering; the adapter
was fixed to map copied forces by atom ID. One rest-state finite-difference
comparison exposed an inappropriate purely relative near-zero denominator; the
test now uses a declared scale-aware `1e-8 pN` floor.

Independent review rejected an initial hidden `1.0 ag` fixture mass because it
made default pressure unreconstructable from the embedded provisional profile.
The final adapter uses the profile mass for kinetic fixtures, requires an
explicit positive synthetic override for a profile with unrecovered mass, and
records positions, box, velocities, mass, and mass source. Direct-route
overrides are zero-velocity only in this evidence, and no record claims physical
time.

## Independent review

The assigned read-only physics reviewer first rejected the hidden fixture-mass
override described above. After the fail-closed mass/provenance and full input
metadata repair, the reviewer returned **ACCEPT** with no remaining
mathematical/sign/domain/unit/provenance blocker. Their fresh read-only check
observed **23 focused tests passed in 2.39s**, `py_compile` passed, and
`git diff --check` passed.

## Final fail-closed follow-up

Integrator review found that the public harmonic LAMMPS fixture did not reject
zero length before solver construction and that nonlinear validation used raw
wrapped separation. The new regression returned **3 failed, 23 passed in
2.24s** before the fix; exact summary is in `followup_red.txt`. The final helper
computes an orthogonal minimum-image vector before solver construction, rejects
zero length for harmonic and nonlinear fixtures, and uses the same distance for
the nonlinear open-domain guard.

The independent reviewer returned **ACCEPT** on the follow-up: **26 focused
tests passed in 1.94s**, diff-check had only line-ending warnings, and an
independent 10,000-case orthogonal-box comparison against the accepted periodic
helper found maximum length mismatch `0`. The reviewer noted that half-box tie
sign is immaterial because this private validation helper consumes only length.

## Source/config hashes

Hashes are SHA-256 after the final verification rerun:

```text
3bf12a2070d80262f3c050a5bc3eac8f9809412bd1050a73a03631a7ec9074c8  src/pgworld/physics/__init__.py
cf4633882d7b208fe718c0560158992500a5fdf57477b2523e974631eabb2ce4  src/pgworld/physics/energy_force_virial.py
1eae46778a32128259a2534e34fda17ee6a9f79a18622df97bc38a73774f7426  src/pgworld/physics/lammps_oracle.py
4e8bbe2b309656c534132c0fc9207da7f6d72015ff0faf326613441648cdd755  tests/physics/test_energy_force_virial.py
bd366c6157cbcd273ff08afe6ae30d6756417a8ad340ffb22a6f452747256d54  configs/physics/reviewed_physics_provisional_v0.json
```

Final `git diff --check`, ownership-range inspection, author/committer checks,
and staged-cache checks are recorded after commits. Two explicit,
worktree-bounded PowerShell `Remove-Item` cleanup attempts were rejected by the
execution policy before any removal occurred. The ignored test-created caches
are not tracked, staged, or returned as evidence. No profile/config file,
inherited constant/runner, root ledger, README, handoff, task state, or release
gate was edited by this subagent.
