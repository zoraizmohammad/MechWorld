# P01-06 independent energy, force, and virial oracle

## Assignment boundary

- Branch: `research/p01-06-energy-force-virial`
- Base: `5243771fa97927beafe49dd66cea4c2bec07bb5c`
- Worktree: `C:/Users/mzora/MechWorld-wt-p01-06`
- Profile used for numerical fixtures:
  `reviewed_physics_provisional_v0`, canonical hash
  `sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5`
- Solver: local serial LAMMPS `20260902` (2 Sep 2026)
- Compute: one bounded process, no dynamics, minimization, production job,
  network, private data, or external write.

Only the assigned physics package, one physics test, and P01-06 evidence/report
paths were edited. The root ledger, README, handoff, shared profile/config files,
inherited runners/constants, and release gates were not changed.

## Delivered implementation

`src/pgworld/physics/energy_force_virial.py` provides a profile-bound,
float64 analytical oracle and an independent centered finite-difference force
oracle. It covers:

- native-unit conversions (`pN/nm` to `N/m`, `pN nm` to `J`);
- LAMMPS harmonic and nonlinear bond energy, radial derivative, Cartesian
  force, and local configurational virial;
- a noncollinear harmonic-angle force/virial oracle with force and torque
  balance;
- explicit invalid-input rejection for nonfinite values, zero-length bonds or
  angle legs, collinear angle derivatives, and nonlinear singular/outside-domain
  states;
- native 2D tension `N=-W/A`, excluding kinetic pressure;
- a fixed reference-state observer that stores total tension as primary and
  subtracts that original reference for every later incremental result; and
- complete detached, validated profile snapshots in records, with silent
  mixed-profile aggregation rejected by the existing profile contract; and
- detached local input coordinates in every analytical record, so its energy,
  force, and virial can be replayed. For a periodic bond these are the accepted
  minimum-image coordinates, not the separately recorded wrapped solver inputs.

`src/pgworld/physics/lammps_oracle.py` builds tiny serial, in-memory LAMMPS
fixtures for one harmonic bond, one nonlinear bond, a two-harmonic-bond series
with a free middle atom and no angle, and one harmonic angle. It requests the
custom pressure computes in thermo before `run 0`, copies solver-owned arrays
immediately, remaps spatially reordered local forces to persistent atom-ID
order, checks the exact solver version, and closes every solver instance.
Each solver record also contains ID-order wrapped input positions, box
dimensions/area/z width, explicit velocities (zeros when omitted), and fixture
mass with its provenance.

Kinetic fixtures use the profile mass. A route whose mass is unrecovered fails
closed unless the caller supplies an explicit positive `fixture_mass_ag`; the
record then labels it `explicit_synthetic_override`. The two direct-route
profiles use `1.0 ag` only as such a disclosed, zero-velocity static solver
requirement. Neither an override nor a profile placeholder supports a
physical-time claim, and every serialized fixture states
`physical_time_claim=false`.

## Sign and normalization convention

For `d=x_j-x_i`, `r=|d|`, and `T=dU/dr`, the implementation uses

```text
F_i = T d/r
F_j = -F_i
W = sum_i x_i outer F_i = -(T/r) d outer d
P_config = W/A
N_total = -P_config = -W/A
```

Thus an extended horizontal bond has negative `W_xx` and `P_xx`, and positive
membrane tension `N_xx`. The solver comparison uses the installed-version
LAMMPS harmonic/nonlinear/angle equations and `compute pressure NULL virial`
semantics referenced by the immutable physics profile. In LAMMPS dimension 2,
tensor pressure is divided by xy area and is independent of the numerical z
width. Default pressure remains a separate observation because it adds kinetic
pressure when velocities are nonzero.

For affine virtual work with `x'=(I+L)x`, the checked convention is
`delta U=-W:L^T=A N:L^T`. An oblique fixture verifies the `xy` component and
simple shear `x'=x+gamma*y`; a large rigid translation verifies origin
independence within floating-point cancellation.

## Acceptance matrix and observed result

- Harmonic bond: compression `0.83 nm`, rest `1.03 nm`, extension `1.23 nm`;
  analytical derivative, Cartesian finite difference, force, energy, local
  virial, and real-LAMMPS global virial agree.
- Two identical harmonic edges: no angle term, combined rest length `2.06 nm`,
  zero middle force, and series tangent `5570 pN/nm`. This is labeled a
  mechanical derivation, not a confirmed molecular mapping.
- Nonlinear bond: compression, rest, extension, and a valid point at 90% of the
  extension-pole displacement; analytical derivative, finite difference, and
  LAMMPS agree. The independent API rejects `r<=0` and
  `|r-r0|>=lambda`; this numerical domain guard is not a rupture law or damage
  endpoint. `epsilon` is treated as energy (`pN nm`).
- Harmonic angle: noncollinear Cartesian forces agree with finite differences
  and LAMMPS; net force and net torque close; analytical and LAMMPS angle
  virials agree. Zero-leg and collinear cases are rejected because the exact
  derivative is undefined (and LAMMPS clamps very small sine internally).
- Angle resolution: equal sharing of one fixed turn between two angles produces
  half the one-angle energy under unchanged `K`. This demonstrates dependence;
  it does not select or approve a coefficient rescaling.
- Registered profiles: a safe, non-rest nonlinear fixture runs through both the
  analytical and real-LAMMPS paths for all four immutable profiles. Every result
  returns the exact expanded snapshot, ID, and canonical hash; the distinct
  direct-elastic coefficient family is therefore exercised rather than merely
  loadable.
- Horizontal, vertical, and oblique bonds: virial signs/components agree with
  virtual cell work and LAMMPS.
- Periodic geometry: wrapped atoms at `(4.6, 0.0)` and `(-4.5, 0.3)` in a
  `10 x 8 nm` box reconstruct the accepted local displacement `(0.9, 0.3)` and
  image offset `(1, 0)`; analytical energy/ID-ordered forces/virial agree with
  LAMMPS for both harmonic and nonlinear bonds. Solver fixtures reject a zero
  minimum-image length before constructing LAMMPS, and nonlinear domain checks
  use this local periodic length rather than raw wrapped separation. Persistent
  edge-image identity remains P03-01 scope.
- 2D normalization: changing z width from `1` to `7 nm` changes no
  configurational pressure component. Adding nonzero velocity leaves the
  virial-only pressure unchanged while increasing default `P_xx` by
  `7.119312169123759e-06 pN/nm` in the recorded fixture. The expected
  `2*m/A` value from the recorded placeholder profile mass, velocities, and
  area is `7.119312169647791e-06 pN/nm`; this is a pressure-term diagnostic,
  not a validated physical-time state.
- Fixed reference: later totals may be normalized using their own current area;
  every increment still subtracts stored `N(0)`. The API intentionally exposes
  no reference reset.

Across the recorded real-solver matrix, maximum absolute discrepancies were:

| Quantity | Maximum absolute difference |
|---|---:|
| Energy | `0 pN nm` |
| Cartesian force | `4.547473508864641e-13 pN` |
| Configurational virial | `1.8189894035458565e-12 pN nm` |

The detailed case table is
`evidence/subagents/P01-06/lammps_comparison.json`. All recorded solver
instances report `solver_closed=true`.

## Verification

The exact commands, exit statuses, wall times, file hashes, JUnit artifacts,
and red-first record are in `evidence/subagents/P01-06/verification.md`.
The final bounded results are:

- focused: **26 passed**;
- physics-profile and periodic-geometry compatibility: **56 passed**;
- full repository suite: **153 passed**;
- targeted source/test compilation: passed; and
- diff/path/identity checks passed, with no cache artifact tracked or staged.

## Explicit limitations

- Numerical agreement verifies the encoded equations and sign/unit conventions;
  it does not certify biological parameters, bead/disaccharide mapping,
  angle-resolution mapping, or nonlinear-fit provenance. P01-05 remains a
  human-review dependency.
- The two-edge result is only an axial series-mechanics consequence. It does not
  establish equivalent bending, attachment placement, molecular count, or
  rupture energy.
- No physical time, damping, rate, 3D stress/modulus, rupture, topology change,
  tangent tensor, large-network stability, or experimental agreement is tested.
- The fixtures require local LAMMPS version 20260902 and were run serially on
  this Windows/Python 3.11 environment. They do not claim portability to other
  solver versions until rerun.
- Exact and near-collinear angle comparison is intentionally excluded at
  `sin(theta)<=0.001`, matching the installed solver's force-clamp boundary.
  The periodic fixture consumes P01-01's accepted reconstruction helper;
  P01-06 does not create a second edge-image identity implementation.
- Test-created ignored Python/pytest caches remain local because two explicit,
  worktree-bounded PowerShell cleanup attempts were rejected by the execution
  policy. They are not tracked, staged, or returned as evidence artifacts.
