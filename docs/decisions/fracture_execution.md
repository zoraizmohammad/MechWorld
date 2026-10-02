# P02-03 quasi-static fracture execution contract

Status: implemented and bounded to the phenomenological P02-02
`bond_extension_ratio` law. This decision does not certify biological rupture
parameters, physical time, loading-rate behavior, fatigue, three-dimensional
mechanics, or experimental validity.

## Topology identity and periodic geometry

`TopologyRegistry` is the immutable source-of-truth mapping between opaque
stable string IDs and solver atom/bond/angle types. Every physical edge must
provide a source-derived signed integer image offset `n_ij`; the production
constructor never guesses it from a shortest image. The recorded source edge
identity satisfies

`r_ij = x_j - x_i + H @ n_ij`.

Explicit non-nearest and half-cell branches are permitted when the source
provides their identity. The bounded fixture-only inference helper is limited
to orthogonal cells and rejects half-cell and long-edge ambiguity. Registry
construction rejects duplicate endpoint/type bond selectors, invalid angle
dependencies, non-glycan angle dependencies, and ambiguous angle triples.
The LAMMPS adapter additionally rejects two angles that share the same
atom-set/type deletion selector, because `delete_bonds group angle type` could
otherwise remove both.

All nodes remain in topology states after rupture. Components therefore retain
isolated and disconnected atoms. An alive angle is valid only while both of
its exact dependent bonds remain alive.

## Supported control and event loop

P02-03 accepts only identity-axis, diagonal deformation-gradient controls. A
complete validated P02-01 `QuasiStaticControlStep` record is stored in every
observation and result. Replay checks the control ID, step, mode, axes, load
coordinate, cumulative path progress, increment, absolute and incremental
deformation gradients, reference ID, and quasi-static/no-time semantics. The
accepted cell must satisfy `H = F_absolute @ H_reference`. Pressure-derived,
rotated, reflected, shear, and other general mappings fail before a backend
command.

For each accepted control step the transaction is:

1. audit live solver topology against the logical state;
2. apply the control, minimize, and require the convergence policy;
3. evaluate the frozen P02-02 threshold field on the accepted equilibrium;
4. stage only rank-zero material rupture and its exact topology plan;
5. checkpoint; delete dependent angles, then the exact physical bond;
6. audit topology and capture the same-position unrelaxed phase;
7. re-minimize at the unchanged control/cell and audit again;
8. commit the damage transition and immutable three-phase envelope;
9. reassess fresh mechanics until stable or a declared budget is exhausted.

LAMMPS deletion uses temporary endpoint groups and exact solver types. It never
uses `any` and rejects every command containing `bond/break`. Temporary groups
are deleted and tracked for cleanup retry. Atoms and unrelated topology are
never deleted.

The backend currently computes only dimensionless bond extension ratio.
P02-02 tension- and energy-based damage laws are valid contracts elsewhere,
but this executor rejects them before any solver command rather than inferring
those criteria from extension.

## Transaction, rollback, and convergence semantics

Only a converged post-event state is committed. Mutation, topology audit,
unrelaxed capture, or post-relaxation failure restores the last accepted
checkpoint and compares topology, positions, forces, complete cell/PBC,
total and incremental tension, raw energies, criteria, source/current offsets,
and boundary conditions. A failed or corrupted restore is
`rollback_failed`; it is never reported as a successful rollback.

The LAMMPS iteration count is the minimizer step delta, not cumulative thermo
step. A normal solver return that reaches the iteration ceiling or misses the
residual tolerance is `rejected_nonconvergence`. Solver nonconvergence and
connectivity loss do not, by themselves, establish mechanical instability or
physical failure. Event and relaxation budgets are independent.

## Snapshot, replay, and visibility boundary

Every observation is immutable and hash-bound. It records full cell/origin/PBC,
persistent atom tags and stable node IDs, copied tag-ordered positions and
forces, topology/damage masks, authoritative source and decoded current image
offsets, raw named `pe`/`ebond`/`eangle` phase energies, total and incremental
2D tension, the explicit fixed-reference total tension, convergence
diagnostics, complete control, boundary conditions, and
profile/reference/law identity. Replay requires
`incremental = total - reference_total` within `1e-12 pN/nm` and preserves
that reference tensor across phases, event chains, and final snapshots. It
also recomputes extension ratios from positions, cell, offsets, and registry
geometry.

Transition and result privileged metadata contain strict replayable copies of
the `DamageLaw`, frozen `ThresholdField`, and `TopologyRegistry`. The threshold
field includes its sample-once material-disorder seed and per-bond thresholds.
It is reference/simulator metadata and is recursively absent from predictor
records when visibility is hidden. Observable projections use explicit
allowlists and expose the current control/state only; accepted event IDs,
candidate/assessment IDs, thresholds, disorder seeds, realization IDs, and
future post-event states are excluded. Zero-event, invalid-reference, and
nonconverged results carry the same result-level replay provenance.

## Bounded real-LAMMPS fixture boundary condition

The real P02-03 fixture is explicitly constrained and is not evidence for an
unconstrained network. Its two degree-one endpoint atoms are affinely remapped
with the cell and then held by `fix setforce 0 0 0`; the interior atom is free.
Every phase records the paired anchored stable and solver IDs, constrained
`x/y` components, and phase-invariant boundary kind.

LAMMPS-reported endpoint forces and `fmax` are post-constraint: reaction forces
are unavailable. Consequently, recorded convergence means equilibrium of the
free degrees of freedom after the constraint, not global unconstrained force
balance. The fixture starts from a fixed-cell minimized and measured reference;
damage initialization uses its measured criteria and reference tension before
any loaded event step.

The accepted serial fixture uses a periodic crossing edge with explicit
`n_ij=(1,0)`. The fixed reference has two 1.03 nm bonds (criterion 1.0); a
1.2 axial box scale produces 1.236 nm bonds (criterion 1.2), above the bounded
deterministic threshold 1.1. Stable-ID tie order selects the first bond. Exact
angle/bond deletion leaves one stretched bond at identical coordinates; the
free middle atom then relaxes about 0.206 nm and the surviving bond returns to
about 1.03 nm. These values validate implementation consistency only.

## Deliberate boundaries

- The only real-LAMMPS P02-03 evidence is the serial orthogonal,
  sequential-tag `tiny_harmonic_fixture`. It is not a production/general PG
  adapter and does not execute the nonlinear peptide law.
- `run_step` owns and closes one backend while executing one controlled step.
  A persistent multi-step schedule runner and restart continuation across
  controlled steps are not implemented here.
- P02-04 owns event localization and derived deletion/work/relaxation energy
  accounting. P02-03 records raw phases only.
- P02-06 owns restart portability and sensitivity campaigns. P02-03 uses a
  transaction-local restart solely for rollback.
- P03 owns canonical trajectory storage, dataset schema, splitting, and model
  feature enforcement.
- Disconnected atoms are retained; connectivity is not treated as rigidity.
- No experimental data, cluster production, public release, or biological
  parameter certification is implied.
