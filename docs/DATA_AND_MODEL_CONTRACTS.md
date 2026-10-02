# Data, Mechanics, and Model Contracts

**Status:** the immutable in-memory/replay contracts `pgworld.trajectory.v1`
and `pgworld.trajectory_access.v1` are implemented and independently reviewed
under P03-01. HDF5 persistence, solver export, dataset loading, split manifests,
normalizers, model APIs, and the proposed `pgworld` data/model commands remain
interfaces to implement. Schema changes require an integrator-reviewed decision
record and a migration test. See `docs/decisions/trajectory_schema.md` for the
exact accepted v1 contract and its limitations.

## 1. Physical coordinate contract

Use column vectors and a cell matrix `H` whose columns are lattice vectors. Store the origin separately. For a supported two-dimensional restricted triclinic cell:

```text
H = [[Lx, xy],
     [ 0, Ly]]
x = origin + H @ fractional_position
```

Record `dimension`, periodic flags, axis meanings, and coordinate representation. Initially use `x = axial`, `y = hoop` to match the existing tension-analysis convention; confirm this against the actual lab dataset and record any remapping.

For a bond from persistent node i to j, define a stored image offset `n_ij` so that:

```text
r_ij = x_j - x_i + H @ n_ij
```

Use this same convention in mechanics, model features, data validation, and visualization. Align force-vector signs explicitly with the chosen endpoint order. Test restricted skew cells and negative tilt. Do not trust local dump row indices as permanent bond IDs. LAMMPS dump ordering and bond-vector conventions require version-aware treatment [S09–S10].

For a legacy 2D triclinic dump with zero xz/yz:

```text
xlo = xlo_bound - min(0, xy)
xhi = xhi_bound - max(0, xy)
ylo = ylo_bound
yhi = yhi_bound
```

This two-dimensional formula is not a general three-dimensional parser. Orthogonal headers need no tilt columns. Support general triclinic input only after implementing and testing its actual format, or reject it with a clear error. Do not reinterpret it as restricted triclinic.

## 2. Storage decision

Use a small JSON manifest plus compressed HDF5 trajectory shards for the first research implementation. HDF5 is the canonical numeric store; browser-specific binary/JSON scene packages are derived artifacts. Keep a light NPZ+JSON fixture format if needed for tests. Avoid arbitrary pickled objects and prohibit loading untrusted Python checkpoints.

A shard is written to a temporary path, validated, checksummed, then atomically marked complete. A crash leaves an incomplete artifact that the loader refuses for training. One writer owns each shard; aggregate manifests after writers finish. Never share a writable HDF5 file across independent jobs without an explicitly tested parallel-I/O design.

## 3. Identity and provenance

Each run manifest contains:

| Field | Meaning |
|---|---|
| `schema_version` | Storage/schema compatibility |
| `run_id`, `parent_network_id`, `branch_id` | Stable run, base geometry, and counterfactual lineage |
| `parent_run_id`, `branch_frame_id` | Counterfactual provenance; null for root runs |
| `source_kind` | `lammps_reference`, `model_prediction`, `experimental`, or `test_fixture` |
| `source_commit`, `source_tree_hash` | Code used; record dirty-state information |
| `physics_profile`, `physics_profile_hash` | Exact potential/parameter definitions; export must resolve the hash against an immutable profile snapshot |
| `physics_profile_review_status`, `coarse_graining_convention` | Explicit provisional/review state and bead/edge mapping; never infer approval from a profile name |
| `reference_state_id`, `reference_state_hash` | Fixed-cell equilibrated reference, including prestress and minimization evidence |
| `simulator_version`, `build_features` | Actual LAMMPS version, styles/packages, precision/MPI details |
| `config_hash`, `raw_artifact_hashes` | Configuration and original outputs |
| `seeds` | Separate geometry, disorder, events, interventions, training streams |
| `units` | Explicit unit of every stored quantity |
| `geometry_axes`, `boundary_conditions` | Physical frame and constraints |
| `loading_mode`, `rupture_law_id`, `rupture_law_hash` | Semantic control and rupture-law versions; deterministic versus sample-once heterogeneous sampling is resolved by a typed or immutable law artifact |
| `observation_model_id`, `observation_model_hash` | Observation mapping identity; no implicit experimental mapping |
| `quality_status`, `termination_reason` | Accepted, rejected, incomplete, or censored |
| `split_id`, `access_policy` | Membership and publication/privacy rules |

Store seeds for reproducibility, but do not expose hidden rupture thresholds,
future events, test labels, rejected trials, private access metadata, or event
RNG state as predictor inputs. A model input can contain only information
declared available at inference. Keep provenance storage and predictive feature
selection separate. `AccessProjection.validate_against(parent)` is required at
trust boundaries: a projection hash proves internal integrity, not that the
projection came from a particular trajectory.

## 4. Numeric schema: one trajectory

For the primary rupture-only model let N be the fixed node count, E0 the initial
physical edge count, A0 the initial angle count, and T the number of recorded
states. The graph evolves by masking edges/angles, not by renumbering surviving
nodes. The accepted v1 interface is a strict typed record model. P03-04 may map
it to columnar HDF5 arrays only if round trips preserve every opaque identity,
nullable field, unit, hash, and relation below.

### Static arrays

```text
nodes/id                       opaque_string[N]
nodes/molecule_id              opaque_string[N]  # original identity, not current component
nodes/type                     opaque_string[N]
nodes/material_features        named_float64_with_units[N]
edges/id                       opaque_string[E0]
edges/endpoints                opaque_string[E0,2]  # persistent node IDs
edges/solver_bond_type         int32[E0]
edges/chemical_type            opaque_string[E0]
edges/reference_rest_length_nm float64[E0]
edges/reference_parameters     named_float64_with_units[E0]
edges/reference_image_n_ij     int32[E0,2]
angles/id                      opaque_string[A0]
angles/nodes                   opaque_string[A0,3]
angles/dependent_edges         opaque_string[A0,2]
angles/chemical_type           opaque_string[A0]
angles/reference_parameters    named_float64_with_units[A0]
```

Opaque IDs are never coerced to integers: `"001"` and `"1"` are distinct.
Parallel physical edges are permitted only when canonical endpoints plus
`solver_bond_type` are unique, because chemical type alone cannot identify a
solver bond for deletion. Each angle references exactly its two adjacent
physical edges.

Store the constitutive parameter names separately; a generic “stiffness” column is insufficient when one potential uses an energy parameter and another uses force/length.

### Per-state arrays

```text
states/frame_id                 opaque_string[T]
states/load_step_id             opaque_string[T]
states/control_id               opaque_string[T]
states/subevent_index           int64[T]
states/phase                    enum[T]
states/load_coordinate          float64[T]
states/load_coordinate_unit     enum[T]
states/path_progress            float64[T]
states/progress_unit            enum[T]
states/physical_time_ns         null[T]  # v1 is quasi-static
states/origin                   float64[T,d]
states/cell_matrix              float64[T,d,d]
states/positions                float64[T,N,d]
states/velocities               optional_float64[T,N,d]  # capability-gated
states/node_forces              float64[T,N,d]
states/node_virial              optional_float64[T,N,d,d] + convention_metadata
states/edge_alive               bool[T,E0]
states/edge_parameters          named_float64_with_units[T,E0]
states/edge_damage              optional_float64[T,E0]  # only under a declared damage law
states/edge_image_offsets       int32[T,E0,d] + valid_mask[T,E0]
states/edge_lengths             float64[T,E0] + valid_mask[T,E0]
states/edge_tension             float64[T,E0] + valid_mask[T,E0]
states/edge_energy              float64[T,E0] + valid_mask[T,E0]
states/angle_alive              bool[T,A0]
states/component_id             opaque_string[T,N]
states/total_tension            float64[T,d,d]  # pN/nm
states/incremental_tension      float64[T,d,d]  # total minus fixed reference
states/energy_terms             named_float64_with_units[T]
states/convergence_diagnostics  typed numeric fields
```

Schema v1 rejects physical-time and local-stress capability claims. Velocities,
raw node virials, and a continuous edge-damage value are present only when the
corresponding typed capability and semantics exist; missing quantities are not
fabricated. Threshold-only runs omit `damage_value` rather than inventing a
continuous damage coordinate. Raw energies `pe`, `ebond`, and `eangle` are
required in `pN nm`.

Keep reference parameters immutable and record the **effective current parameters** after local weakening. Repeated unchanged parameter arrays may use a validated change-log/deduplicated representation, but the loader must reconstruct the exact coefficients at every state. A damage variable is valid only under a declared law; a threshold-only experiment need not invent a continuous damage process.

Avoid assigning zero length/force to an inactive edge and treating it as a
physical observation. A dead edge has null current image, length, tension, and
energy while its immutable reference image remains available. Keep a stable
edge universe in each rupture-only run; optional future bond formation requires
schema migration, creation IDs, and a physically defined process.
Formation/healing is not required by this proposal. Component labels must
represent the exact connected-component partition and remain stable while the
alive topology is unchanged.

Suggested phases include `accepted_equilibrium`, `pre_intervention`, `pre_rupture`, `post_topology_change`, and `post_event_equilibrium`. A pair of frames at the same load may still represent a real event and must not be dropped as a duplicate. Record rejected numerical trials separately from accepted scientific trajectories.

### Controls and events

Each transition references a control object with absolute and incremental
deformation gradient or tension target, an orthonormal axial/hoop basis,
boundary displacement and force information where applicable, constrained-node
masks, external-pressure derivation, local weakening/removal, load coordinate,
and cumulative progress. One trajectory uses one continuous load family/unit.
For the present deformation paths the progress increment equals the absolute
load-coordinate change. A pure intervention inherits the active mechanical
target and cannot advance load or progress. Pressure targets use the declared
basis transformation of `diag(pR/2, pR)` and are not normal inflation of a
flat patch.

An event record contains stable SHA-256 event identity for material rupture,
edge/control/state links, source (`prescribed_intervention` versus
`material_rupture`), irreversible old/new state, quasi-static load/progress,
criterion name/value/unit, removed dependent angles, law/profile/reference
identity, threshold realization, and cascade parent. Event chronology follows
linked state chronology and the named edge/angles match the exact topology
delta. Event energy is not duplicated: the linked pre-rupture,
post-topology-change, and post-event-equilibrium states retain the raw energy
terms. Physical time is null and invalid in schema v1. Represent right
censoring explicitly when no failure occurs before the
loading endpoint. Damage initiation is the first accepted material rupture and
does not terminate cascade/degradation evaluation.

### Fixed reference and access views

Every trajectory binds one hash-verified
`fixed_cell_equilibrated_not_zero_tension` reference containing node
coordinates, full cell matrix, measured total 2D tension, minimization limit,
tolerance, achieved residual/iterations, profile identity, and static-graph
identity. The reference is not reset after loading or rupture. Every state
records total tension and incremental tension relative to that fixed reference.

The exact P02 phase adapter is `pre_delete_relaxed -> pre_rupture`,
`post_delete_unrelaxed -> post_topology_change`, and
`post_event_relaxed -> post_event_equilibrium`. Damage initiation,
load-bearing connectivity loss, load/stiffness degradation, and mechanical
instability remain four distinct endpoint records.

Observed, target-only, and privileged views have independent strict hashes and
relational replay validation. Observed inputs exclude hidden thresholds/seeds,
future states/events/topology, rejected trials, test-derived normalizers, and
private access metadata. A predictor-known requested control is supplied as an
authorized input rather than smuggled through a target. Target views preserve
historical damage-initiation context without relabeling later cascade events.
Privileged threshold records cover every physical edge and declare criterion,
unit, realization, and predictor visibility; seeds and realization proxies
remain hidden even when threshold values are deliberately visible.

## 5. Required physical consistency tests

1. Node IDs unique; edge endpoints valid; no duplicate physical bonds under the declared multigraph policy.
2. Angles reference existing nodes and remain active only while required physical bonds remain active.
3. The irreversible model satisfies `alive[k+1] <= alive[k]`; predictor and solver cannot resurrect edges.
4. A relaxed state with zero control change, zero time/load exposure, and no intervention remains unchanged within specified tolerances. A genuine stochastic time evolution at fixed load is not covered by this invariant.
5. Reconstructed periodic bond lengths agree with LAMMPS distances, including boundary-crossing fixtures.
6. Summed/normalized local virial matches global tension using the same kinetic and angular contributions. Record the coarse-graining definition, not just a color map [S05, S11].
7. Analytical force equals negative energy gradient in the independent oracle; compare signs and units against LAMMPS.
8. Work/energy checks are conditioned on the correct boundary-control and topology phase. A fixed-topology relaxation at fixed boundaries should not increase energy beyond numerical tolerance; external loading and deletion require a different energy balance.
9. Restarting from a saved accepted state reproduces the suffix within declared deterministic/stochastic tolerance. Include RNG and event-law state; a LAMMPS binary restart alone is not a complete stochastic experiment record.
10. Imported legacy states missing needed fields carry capability flags. Do not invent velocities or historical edge events.

## 6. Split and normalization contract

Allocate complete parent networks to train, validation, and test. All daughter trajectories, interventions, stochastic replicas, and windows derived from a parent stay in its assigned group. Deduplicate geometric hashes where feasible. Keep experimental culture/day groups separate as specified in the experimental plan.

Keep distinct tests for: unseen independent graphs within training parameter ranges; unseen architecture ranges; unseen load families; larger graphs at fixed morphology; new defects; and compound OOD. Do not report a size result that also changed strand truncation without naming both changes.

Normalizer statistics come from the training partition only and are saved with the checkpoint. Avoid graph IDs, filenames, future controls not known at decision time, event seeds, and test-derived features. Known future loading schedules may be supplied only when that same schedule is genuinely given to all competing methods.

## 7. Transition-model contract

Conceptual Python interface to implement:

```python
class WorldModel:
    def step(self, state, control, memory=None, rng=None):
        """Return next predicted state, events, memory, uncertainty, diagnostics."""

    def rollout(self, initial_state, controls, *, seed, max_events):
        """Autoregressive evolution without future reference states/topology."""
```

Outputs include accepted/rejected status and reason. A caller must not silently substitute reference states into failed predicted rollouts. Teacher-forced or oracle-topology runs are diagnostic modes and must be labeled separately from closed-loop inference.

A recommended computational sequence is:

```text
known affine/boundary update
→ graph-based nonaffine proposal
→ bounded physical correction on current topology
→ rupture probability / event proposal
→ irreversible topology and angle update
→ bounded redistribution update
→ repeat bounded cascade handling if required
→ accept with diagnostics or return explicit invalid state
```

Memory may encode persistent hidden disorder or history. Static material variability, epistemic uncertainty about model weights, and stochastic event noise are different sources and need separate tests. Do not add a variational latent variable merely to make a deterministic dataset look stochastic.

### Stochastic event choices

**Quenched-threshold reference:** sample bond thresholds once per realization; rupture depends on crossing the stored threshold. The observer may not see thresholds. Survival history then contains information; model memory must represent that if the state would otherwise not be Markovian.

**Time-based hazard reference:** for a physically calibrated event rate h, interval probability is `1 - exp(-h * delta_t)`. A rate per second is not a probability per minimizer call.

**Load-progress hazard:** permissible as an explicitly phenomenological law per nonnegative loading-path increment, not biological time. Define progress for unloading/cyclic paths and verify subdivision behavior.

Do not resample independent event opportunities every time an optimizer iterates, retries a step, or redraws the screen. Numerical retries restore RNG state or use a consistent integrated-hazard scheme. If events are correlated, a conditionally independent Bernoulli head is a baseline rather than an established full joint model.

### Mechanics structure

Use invariant scalar features and covariant vectors/tensors. Include angles through explicit triplet terms or validated features plus known-force evaluation. Known forces include angular contributions. Net-force/torque tests must account for boundary and external forces.

A learned proposal followed by a corrector is a numerical acceleration hypothesis. It must be compared against ordinary warm starts, fixed-budget optimization, and full convergence. Record corrector steps and fallback frequency in both accuracy and timing reports. A future residual energy requires evidence of missing/coarse-grained physics and cannot be justified solely by fitting labels generated from the same known energy.

## 8. Train/evaluate/infer lifecycle

First test one forward pass, gradients, masked event loss, serialization, and exact input/output shape contracts. Then overfit a tiny training set as an implementation test. Next run an unseen-network closed-loop trajectory. Only after these checks begin larger sweeps.

The curriculum may proceed from intact mechanics to teacher-topology rupture sequences to full joint rollout. Evaluate with predicted current positions, topology, and memory at every step; initialize only from allowed observations. Record when training uses reference topology and when it does not.

Class-imbalance handling must not corrupt event probabilities. If event oversampling or weighted losses are used, report sampling weights and recalibrate on representative validation data. Censoring and exposure length belong in survival losses. State whether uncertainty intervals reflect observation noise, event noise, material variation, model uncertainty, or a combination.

Every checkpoint bundle includes model/config versions, allowed inputs, feature schema, normalizers, physics profile, train/validation/test manifest hashes, intended-use card, seed, training history, and resume files. Release inference weights separately from internal optimizer and private metadata.

## 9. CLI acceptance contract

`pgworld doctor` is implemented as the bounded environment/mechanics diagnostic.
The remaining commands below are target interfaces and must not be assumed to
exist before their owning tasks are accepted:

```text
pgworld doctor
pgworld simulate --config configs/smoke/rupture.yaml
pgworld validate-data --manifest artifacts/smoke/manifest.json
pgworld train --config configs/models/baseline_smoke.yaml
pgworld train --config configs/models/hybrid_pilot.yaml
pgworld evaluate --config configs/study/frozen_evaluation.yaml
pgworld rollout --checkpoint PATH --initial-state PATH --controls PATH
pgworld export-scene --run PATH --output PATH
pgworld serve --host 127.0.0.1 --port PORT
pgworld reproduce --manifest PATH
```

All commands should validate inputs, provide actionable errors, avoid current-directory assumptions, return nonzero exit status on failure, and log artifact locations. Help output is not evidence that the command's research workflow works.
