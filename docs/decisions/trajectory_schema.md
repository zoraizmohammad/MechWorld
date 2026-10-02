# P03-01 trajectory schema decision

Status: corrected computational contract at `pgworld.trajectory.v1` and
`pgworld.trajectory_access.v1`. The first return (`c489b8f`/`c38e4ab`) was
rejected in independent review; this document describes the corrected
contract. It does not implement persistence, export a dataset, accept G3, or
certify biological parameters.

## Record families and identity

The interface uses frozen typed records with exact field sets, finite values,
explicit schema versions, and SHA-256 content hashes. Replay never coerces an
integer into an opaque string ID, so `"001"` and `"1"` remain distinct. Static
node, physical-edge, angle, control, state, frame, event, lineage, and
material IDs remain stable across rupture. Component labels remain stable
while topology is unchanged and may be recomputed after a topology change.

The record separates immutable graph/reference data, controls, accepted
scientific state phases, accepted topology events, failure endpoints, and
privileged/rejected diagnostics. Rejected trials never enter the accepted
state sequence.

Parallel physical edges are allowed only when canonical endpoint pair plus
`solver_bond_type` is unique. A chemical label cannot disambiguate two solver
bonds that the deletion API cannot distinguish. The P02 topology adapter
preserves opaque bond/node IDs, solver bond type, chemical type, signed image,
and source displacement without lossy coercion.

Each three-node angle depends on exactly two unique physical edges. Those
edges must be the two adjacent node segments; a `glycan_bend` requires two
glycan edges. An angle cannot disappear independently of a linked dependent
edge-removal event and cannot heal.

## Reference, geometry, mechanics, and controls

`ReferenceStateRecord` is a separately hash-bound
`fixed_cell_equilibrated_not_zero_tension` record. It contains the fixed-box
cell, minimized node coordinates, measured total reference tension, solver
iteration limit, force tolerance, achieved iterations/residual, profile
identity, and exact static-graph hash. It is never called unstressed.
Provenance, graph, controls, states, and failure endpoints bind to that one
reference. Every state must satisfy

```text
incremental_tension = total_tension - fixed_reference_total_tension
```

Factory hashing uses the same normalized real-valued representation as replay,
so integer and floating spellings of the same accepted real value do not create
different hashes or a false hash mismatch.

`Cell2D` stores origin and restricted-triclinic column-vector matrix
`H = [[Lx, xy], [0, Ly]]`, with `x = axial`, `y = hoop`. A physical edge uses

```text
r_ij = x_j - x_i + H @ n_ij
```

Signed reference/current images must be zero on nonperiodic axes. An alive
edge's stored length is recomputed from positions, the full current `H`, and
signed `n_ij` to an absolute tolerance of `1e-12 nm`. A dead edge has no
current image, length, tension, or energy; the immutable reference image
retains provenance. Component labels may use arbitrary opaque names, but their
equivalence partition must exactly match connected components of alive
physical edges. Labels remain stable while the alive-edge topology is
unchanged. During an accepted deletion, surviving edges retain their periodic
image branch across the same-position pre/post-topology boundary.

Controls retain P02-01 kind/mode, orthonormal axial/hoop basis, fixed
reference, absolute and incremental deformation gradients or tension targets,
cumulative path progress and increment, per-node constrained DOFs, weakening,
and prescribed removal. One trajectory has one continuous family/unit;
interventions inherit that established path unit. Each progress increment is
the absolute change in load coordinate and cumulative progress is its sum from
zero. A prescribed intervention has no independent mechanical target, so it
cannot advance the load coordinate or path progress; it inherits the active
mechanical target. Replay verifies deformation composition, additive tension
targets, and `H_state = F_absolute @ H_reference`, including intervention
states carried at the active deformation target. Pressure controls preserve
`N_axial=pR/2`, `N_hoop=pR`, cylinder radius, and the closed-thin-cylinder
assumption. The principal tension tensor is rotated by the declared basis as
`B @ diag(pR/2,pR) @ B.T`; it is a membrane-tension target, not normal
inflation of a flat patch.

`BoundaryConditionRecord` hash-binds stable anchor IDs to positive solver atom
IDs, constrained x/y DOFs, affine-remap behavior, reaction-force availability,
node-force scope, and residual-force scope. Its identity must match provenance
and control constraints.

Effective coefficients are not arbitrary per-state features. Replay starts
from immutable reference names/values/units and applies the ordered declared
weakening factors. Any undeclared `K`, `r0`, or other coefficient change fails.
P02 energy names `pe`, `ebond`, and `eangle` are mandatory in `pN nm`;
additional energy names are allowed with the same unit.

## Quasi-static phases, convergence, damage, and endpoints

Canonical stored phases are `accepted_equilibrium`, `pre_intervention`,
`pre_rupture`, `post_topology_change`, and `post_event_equilibrium`. The only
P02 raw-phase adapter is:

| P02 phase | Stored phase |
|---|---|
| `pre_delete_relaxed` | `pre_rupture` |
| `post_delete_unrelaxed` | `post_topology_change` |
| `post_event_relaxed` | `post_event_equilibrium` |

The source spelling is optional provenance and must map exactly. Relaxed
accepted phases require `iterations < max_iterations`, residual at or below
`force_tolerance_pN`, and reason `converged`. The unrelaxed post-delete phase
preserves P02 raw diagnostics exactly: `converged=false`, `accepted=false`,
zero iterations, and reason `phase_not_relaxed`, even though the phase itself
is retained as an accepted scientific record.

Schema v1 is strictly quasi-static. Control/state/event/endpoint units are
`dimensionless` for the present deformation path or `pN/nm^2` for a pressure
coordinate. Physical time, seconds, or a physical-time capability are rejected.
The `local_stress` capability also remains false because v1 has no typed local
stress payload; total and incremental 2D membrane tension remain explicit.

Material thresholds are positive, stable-edge keyed, unit-consistent, and
sampled once outside this schema. Every physical edge has one immutable
threshold even when no rupture occurs in the tested range. Predictor
visibility is explicit. Hidden
thresholds and every seed/realization proxy remain privileged. A visible study
exposes only the declared criterion, unit, and values, never its seed or
future event information. Material event criteria are exactly one of
`bond_extension_ratio`, `bond_tension`, or `bond_energy` with units
`dimensionless`, `pN`, or `pN nm`. Replay derives the event value from the
linked pre-state edge observation, compares it at `1e-12` absolute tolerance,
and requires it to cross the immutable per-edge threshold.

Event sequence follows linked state chronology, in addition to progress,
control/load linkage, phases, alive-to-dead
transition, dependent-angle removal, and cascade ancestry are validated.
Prescribed events require a declared weakening/removal of that edge; a
material rupture cannot be declared prescribed. Cascades may continue after
damage initiation. Damage initiation is the first accepted material rupture,
not an ordinary trajectory termination reason.

Failure endpoints are isomorphic to accepted P02
`TrajectoryFailureEndpoints`: `damage_initiation`,
`load_bearing_connectivity_loss`, `load_or_stiffness_degradation`, and
`mechanical_instability`. Each preserves P02 status/evidence/coordinate
semantics and profile/reference identity, plus law fingerprint and threshold
realization. Damage evidence is a SHA-256 material-event ID. Right censoring
binds the terminal tested coordinate/progress; `not_evaluated` invents no
criterion or observation. Successful evaluation ends with
`completed_schedule`; budget/error terms require consistent non-accepted
quality status. An `invalid_reference` trajectory cannot retain an accepted
topology event, because the event's mechanical baseline would be undefined.

## Access projections

Observed, target-only, and privileged views are independently content-hashed,
strictly typed, and relationally replay-validated. Observed history requires
contiguous state/event sequences, valid controls, static universes, geometry,
reference tension, phases, event links, and irreversible topology. Target
replay validates its anchor, contiguous future sequence, controls, event
pre/post links, and endpoint/event/terminal relations. The target record keeps
a typed context record for the first material rupture, allowing a projection
anchored after that event to preserve and validate the historical
damage-initiation endpoint while `validate_against(parent)` proves its source.
Full, observed, and target replay use the same control-path validator for
ordering, increments, composition, intervention inheritance, referenced
nodes/edges, state load/progress fields, and active deformation-cell binding.
Recursive observed
validation rejects seed/RNG, realization, future/oracle, rejected-trial,
normalizer/scaler, and private access-policy aliases.

A projection hash proves only internal content integrity. It cannot prove
that a self-consistent projection came from a particular trajectory.
`AccessProjection.validate_against(parent)` performs the required exact
derivation check against a validated parent record. Callers must use it at
trust boundaries.

## Boundaries and limitations

- The schema binds supplied profile ID/hash strings consistently, but does not
  prove registry membership. A solver/profile adapter must perform that check.
- `from_p02`/topology/phase helpers preserve accepted P02 record shapes; P03-02
  still owns full solver-to-schema value agreement.
- This task implements no HDF5/NPZ writer, shard, atomic completion,
  split assignment, normalizer fitting, or migration tool. The draft shared
  data contract remains integrator-owned and must be superseded/reconciled
  after this correction is accepted.
- No real/private/experimental data, dataset, model, or biological
  certification was created. G3 remains unaccepted.
