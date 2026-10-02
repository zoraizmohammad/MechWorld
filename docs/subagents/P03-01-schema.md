# P03-01 schema specialist return

Task: P03-01, freeze versioned graph, control, state, event, provenance, and
access records.

Base: `0222b6d6fdee180e2e2daa86ccfebb276c91f1f6`

Branch/worktree: `research/p03-01-schema` at
`C:\Users\mzora\MechWorld-wt-p03-01`

Implementation commit:
`c489b8f7b1560ad1e18157303cc00633dd9fdae6` (`Define versioned trajectory
access schema`). Author and committer are solely Mohammad Zoraiz
`<zoraizmohammad@gmail.com>`.

## Returned implementation

- Added the installable `pgworld.data` package with the frozen
  `pgworld.trajectory.v1` and `pgworld.trajectory_access.v1` contracts.
- Reconciled the planning draft's `int64` IDs with accepted P02 opaque string
  identities without coercion; numeric-looking spellings remain exact.
- Added immutable, content-hashed static graph and trajectory replay with
  exact-version/exact-key validation, restricted-triclinic column-vector cell
  geometry, origin/periodic axes, and signed per-edge `n_ij`.
- Added immutable reference node/edge/angle records and reconstructible
  per-state effective edge parameters, damage, alive masks, dependent-angle
  masks, component labels, mechanics, convergence, and capability flags.
- Added full P02-01-compatible controls: kind/mode, orthonormal axial/hoop
  basis, absolute and incremental deformation/tension controls, cumulative
  progress and increments, per-node constrained DOFs, local weakening/removal,
  and explicit closed-cylinder pressure-to-tension provenance.
- Replay binds deformation-state `H` to `F_absolute @ H_reference`, validates
  deformation composition and additive tension targets, preserves same-load
  subevents, and rejects healing, repeats, unrelated mutation, missing
  dependent-angle deletion, source-phase forgery, or unlinked topology change.
- Added full root/branch lineage plus source/profile/reference/law/config,
  observation-model, and boundary-condition provenance. Split ID and
  assignment/manifest hashes are optional as one all-or-none group and remain
  predictor-hidden.
- Added separately hash-bound `observed`, `target_only`, and `privileged`
  projections. Observed payloads omit lineage/split/raw/private records and
  recursively reject threshold/seed/disorder/future/oracle/rejected/
  normalizer/privacy aliases before exact nested replay.
- Documented canonical semantic event phases and the exact fail-closed P02
  mapping: `pre_delete_relaxed -> pre_rupture`,
  `post_delete_unrelaxed -> post_topology_change`, and
  `post_event_relaxed -> post_event_equilibrium`.

## Verification

The detailed commands, environments, exits, timings, warnings, artifact hashes,
and failure explanation are in
`evidence/subagents/P03-01/verification.md`.

- Initial red: 1 collection error, missing `pgworld.data`.
- Expanded-contract red: 1 collection error, missing typed pressure derivation.
- Final focused: **46 passed**, no failures/errors/skips.
- Relevant loading/damage/compile compatibility: **99 passed**, 12 inherited
  deprecation warnings.
- Broader no-wheel suite: the first run preserved 3 environmental collection
  errors after omitting external LAMMPS from `PYTHONPATH`; the corrected run
  with the authorized LAMMPS 20260902 path passed **316 tests** with 14 inherited/
  expected deprecation warnings and no failures/errors/skips.
- Targeted `py_compile`: exit 0.
- Strict wheel install was not run because its allowlist is integrator-owned.

## Ownership proof

The implementation/evidence range changes only the assigned paths:

- `src/pgworld/data/__init__.py`
- `src/pgworld/data/schema.py`
- `tests/unit/test_schema.py`
- `docs/decisions/trajectory_schema.md`
- `docs/subagents/P03-01-schema.md`
- `evidence/subagents/P03-01/`

No root ledger, README, task file, ownership ledger, shared contract, package
manifest, release gate, dependency, P02 path, or private-data path was edited.

## Limitations and next ownership

- P03-01 implements no HDF5/NPZ writer, shard, atomic completion, dataset,
  split assignment, normalizer fitting, or migration tool.
- P03-02 must implement/verify the actual accepted-P02-to-schema adapter and
  solver-value agreement. P03-04 owns storage/manifests and can populate split
  and manifest fields only after those artifacts exist.
- The wheel payload allowlist/package installation proof belongs to the
  integrator because release-test and package-manifest paths were explicitly
  outside this assignment.
- No real/private/experimental data, model, simulation campaign, or biological
  certification was created. G3 is not accepted by this return.
