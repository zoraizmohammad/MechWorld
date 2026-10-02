# P03-01 trajectory schema decision

Status: implemented computational contract at `pgworld.trajectory.v1` and
`pgworld.trajectory_access.v1`. This decision does not implement storage,
export a dataset, accept G3, or certify biological parameters.

## Decision

The first trajectory interface is a strict family of frozen typed records,
not a permissive nested dictionary. `TrajectoryRecord.from_record` accepts
only the exact current version, exact field sets, finite typed values, and a
matching SHA-256 content hash. An older or mixed version fails with an
explicit-migration error. P03-04 owns any eventual migration and HDF5 storage;
P03-01 deliberately supplies no automatic or lossy migration.

Opaque node, edge, angle, event, control, frame, run, lineage, and component
IDs are trimmed strings. Integer IDs are rejected rather than converted, so
`"001"` remains distinct from `"1"`. Static graph rows and per-state rows use
stable ID universes; surviving interactions are never renumbered.

The top-level record separates:

- immutable static graph/reference material records;
- ordered quasi-static control records;
- accepted dynamic state/subevent records;
- accepted physical topology-event records;
- rejected numerical trials and other privileged reproducibility metadata.

Rejected trials never enter the accepted scientific state sequence. Static
edge parameters remain immutable. Every accepted state explicitly carries the
current effective parameter name/value/unit set, signed `n_ij`, alive flag,
valid physical measurements, and declared damage value or its absence. Thus a
reader reconstructs the exact coefficients and topology at any frame without
mutating the reference record or interpreting inactive-edge zeros as data.

## Geometry and mechanics conventions

`Cell2D` stores an origin and restricted-triclinic matrix
`H = [[Lx, xy], [0, Ly]]`. Vectors are columns and each signed edge image is
defined by:

```text
r_ij = x_j - x_i + H @ n_ij
```

The computational meanings are exactly `x = axial`, `y = hoop`. Periodic axes
are explicit. General triclinic cells, silently transposed matrices, inferred
nearest images, integer ID coercion, and ambiguous duplicate physical edge
endpoints fail closed in v1.

Controls retain the P02-01 distinctions between control kind and loading mode,
an explicit orthonormal axial/hoop basis, the fixed reference, absolute and
incremental deformation gradients or tension targets, cumulative path
progress and its increment, per-node constrained x/y DOFs, local weakening,
and prescribed removal. For ordered deformation controls, replay verifies
`F_absolute[k] = F_increment[k] @ F_absolute[k-1]` (identity/reference at the
first step) and verifies `H_state = F_absolute @ H_reference`. Ordered tension
targets use additive increments. Progress increments must equal changes in
cumulative path progress, including the first-step-from-zero policy.

Pressure-derived tension controls retain pressure, cylinder radius, the
closed-thin-cylinder/away-from-end-effects assumption, the relations
`N_axial = pR/2` and `N_hoop = pR`, and the declaration that this is a membrane
tension target rather than normal inflation of a flat patch. The schema does
not claim that a pressure target was solved successfully; that remains a
solver/export result.

## Event phases and replay

Storage has one canonical semantic vocabulary:

- `accepted_equilibrium`
- `pre_intervention`
- `pre_rupture`
- `post_topology_change`
- `post_event_equilibrium`

There are no interchangeable aliases in stored records. The explicit P02
adapter mapping is:

| P02 execution phase | Canonical stored phase |
|---|---|
| `pre_delete_relaxed` | `pre_rupture` |
| `post_delete_unrelaxed` | `post_topology_change` |
| `post_event_relaxed` | `post_event_equilibrium` |

The original P02 phase may be retained in `source_phase`, but only when this
exact mapping agrees with the canonical phase. Unknown/case-folded spellings
fail closed.

`sequence_index` and `subevent_index` preserve multiple states at one load
coordinate. Replay verifies monotone path progress, same-step subevent order,
material-rupture versus prescribed-intervention pre-phases, exact event links,
alive-to-dead edge transitions, every-and-only dependent angle removal,
unchanged positions in the immediate post-topology/pre-relaxation state, no
unlinked topology mutation, no repeated event, no edge or angle healing, and
retention of all nodes/components after disconnection.

## Provenance, status, and capabilities

Full provenance records root or branch lineage, source commit/tree/dirty
state, registered physics profile identity/hash, fixed reference identity/hash,
rupture-law identity/hash, configuration and raw-artifact hashes, simulator
version/features, observation-model identity/hash, and boundary-condition
identity/hash. Optional split ID, split-assignment hash, and manifest hash are
all absent before a later manifest exists or all present together. The schema
does not invent an experimental observation model: simulation fixtures use an
explicit native-solver observation identity.

Trajectory quality status, termination reason, observed versus right-censored
failure endpoint, load coordinate/path progress, and evidence event are
separate. Capability flags state whether optional velocity, virial, damage,
physical-time, local-stress, event-history, angle, or rejected-trial fields
exist; replay checks relevant flags against payload presence. A false physical
time capability cannot carry a time value.

## Access projections

The schema exposes three separately hash-bound records:

| Projection | Intended use | Contents |
|---|---|---|
| `observed` | predictor inputs/history through one anchor frame | physical static graph, reached controls, accepted states through the anchor, completed event history, non-private scientific context |
| `target_only` | supervised labels after the anchor | future accepted states/events plus outcome/censoring labels |
| `privileged` | replay/audit only | complete content-hashed trajectory, seeds, quenched thresholds/proxies, rejected trials, normalizers, raw/lineage/split metadata, and private access policy |

The observed payload omits run/parent/branch/split identity, source/config/raw
artifact hashes, graph/reference content hashes, rejected-trial capability,
threshold values, seeds, quenched-realization proxies, future states/events,
test-derived normalizers, and private policy/custodian metadata. Stable node,
edge, angle, frame, and event IDs remain correspondence keys, not numeric
features. The observed replay validator recursively rejects threshold/cutoff,
RNG/seed, disorder/realization, future/oracle, rejected, scaler/normalizer, and
privacy/access-policy aliases, then validates an exact nested projection shape.
Recomputing the projection hash cannot make an unknown nested field valid.

## Boundaries and limitations

- This is an in-memory/JSON-compatible contract only. P03-04 owns canonical
  HDF5 shards, atomic completion, checksums, and migration tooling.
- No real or private trajectory is exported. The tests use a small numerical
  fixture only.
- P03-02 must write the adapter from accepted P02 records; P03-01 does not
  change P02 execution records.
- Local-stress/coarse-grained virial fields are capability-gated but not yet
  implemented or validated.
- Optional physical time remains invalid for the quasi-static study.
- A schema round trip is necessary but insufficient for G3. Solver/exporter
  agreement, storage integrity, and real fixture statistics remain pending.
