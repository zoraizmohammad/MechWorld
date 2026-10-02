# P03-01 schema specialist return

Task: freeze the versioned graph/control/reference/state/event/access contract.

Base: `0222b6d6fdee180e2e2daa86ccfebb276c91f1f6`

Branch/worktree: `research/p03-01-schema` at
`C:\Users\mzora\MechWorld-wt-p03-01`

The first-pass commits `c489b8f7b1560ad1e18157303cc00633dd9fdae6` and
`c38e4ab735b0c73ff229cc831d705b2433dfca49`, and the first correction through
`ebde2164211286dd5d2db09de733d26b9aeb5f74`, were rejected in independent
review and are superseded. Later exact
audit rounds are preserved as red commits
`be578d70cfbd28c4d4a21079fea466dbe6c0717d`,
`9e70bf6b4b64bea7badb1164b1383ac4403f9cd9`, and
`11359743bc1fba8a648b910d005dc27569fc3d31`. Final reviewed source is
`9f94f79f238aab251245c8381baf666cb55d9011`. New commits have Mohammad Zoraiz
`<zoraizmohammad@gmail.com>` as sole author and committer. Nothing was pushed.

## Corrected implementation

- Added relationally strict observed/target replay and an explicit
  `validate_against(TrajectoryRecord)` derivation check. A projection hash is
  documented only as content integrity, never parent provenance.
- Added hash-bound fixed-cell equilibrated reference records with coordinates,
  prestress, minimization limit/tolerance/result, profile identity, and graph
  identity. State incremental tension is bound to total minus the invariant
  reference total tension.
- Added typed boundary semantics for stable/solver anchors, constrained DOFs,
  affine remap, force/reaction availability, and residual-force scope.
- Preserved accepted P02 convergence semantics, failure endpoint records,
  threshold visibility, threshold realization/law/profile/reference identity,
  raw energy names, phase mapping, load/progress semantics, and strict absence
  of physical time.
- Added exact geometry replay: signed images respect periodic axes, alive-edge
  lengths derive from positions/full `H`/`n_ij`, dead edges carry no invented
  current image, and component partitions equal alive-edge connectivity.
- Reconciled P02 multigraph topology by requiring endpoint plus solver bond
  type uniqueness. Chemical labels cannot hide solver ambiguity. Angle
  dependencies are exactly the two adjacent segments with glycan semantics.
- Effective coefficients reconstruct from immutable references plus ordered
  declared weakening. Undeclared coefficient changes fail.
- Event replay binds material criteria to pre-event edge geometry/tension/
  energy and positive per-edge thresholds, distinguishes prescribed actions,
  validates exact dependent-angle removal and cascade ancestry, and continues
  evaluation after the damage-initiation endpoint.
- Control replay derives progress from absolute load-coordinate changes,
  prohibits mixed continuous families/units, lets interventions inherit the
  parent deformation or pressure unit, and rotates the pressure-derived
  principal tension tensor through the declared axis basis.
- Added direct P02 topology and failure-endpoint adapters without editing P02.
- Closed later immutable-audit gaps: unsupported local-stress claims and empty
  threshold fields fail; invalid references cannot retain events; component
  labels and periodic images cannot silently rebranch; intervention and event
  order are bound; integer/floating real spellings hash canonically; and target
  damage context preserves historical initiation without weakening future
  event validation.
- Observed/target event replay now checks graph/control/angle universes, exact
  topology deltas, survivor images, derived pre-state criteria, and available
  endpoint identities. Full/observed/target replay share control sequencing and
  state-binding validation, including load/progress and active-F cell binding.

## Verification returned

Detailed commands, environment, exits, timings, failure causes, exact hashes,
and limitations are in `evidence/subagents/P03-01/verification.md`.

- Five first-correction red artifacts preserve 21 exact failures before fixes:
  projection relations (5), typed contracts (4), geometry/connectivity (3),
  threshold/event/angle physics (5), and control/basis semantics (4).
- Three later audit rounds preserve **19 additional exact failures** before
  their fixes: 10 core replay/identity gaps, 7 event/context delta gaps, and 2
  shared state/control gaps.
- Final commit-sensitive focused schema suite: **108 passed**, no failures,
  errors, or skips.
- Final loading/damage/tracked-source compatibility: **99 passed**, with 12
  inherited invalid-escape warnings.
- Final broader no-wheel suite with authorized external LAMMPS 20260902:
  **378 passed**, with 14 inherited/expected warnings and no failures/errors/
  skips.
- Targeted compilation passed. Diff/path/identity checks are recorded before
  final return.

## Ownership proof

The correction changes only assigned path groups:

- `src/pgworld/data/__init__.py`
- `src/pgworld/data/schema.py`
- `tests/unit/test_schema.py`
- `docs/decisions/trajectory_schema.md`
- `docs/subagents/P03-01-schema.md`
- `evidence/subagents/P03-01/`

No root README/handoff/task/ownership ledger, shared data contract, package
manifest, release gate, dependency, P02 path, or private-data path was edited.

## Limitations and next ownership

- No persistence, dataset, split, normalizer, migration, model, simulation
  campaign, or experimental artifact was produced; G3 is not accepted.
- Profile identity is consistently hash-bound but registry membership must be
  checked by the consuming profile/solver adapter.
- P03-02 owns full accepted-P02-to-schema solver value comparison. P03-04 owns
  HDF5 shards/manifests/atomic completion. The integrator owns reconciliation
  of the now-superseded shared draft data contract and package/wheel allowlist.
