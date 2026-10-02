# P02-05 conditional stochasticity decision

Status: implemented computational contract for bounded quasi-static studies.
This decision does not validate a biological rupture distribution, stochastic
event kinetics, physical time, or a production simulation campaign.

## Chosen reference

P02-05 uses the accepted P02-02 `quenched_heterogeneous_threshold` law. Each
physical bond receives one threshold from P02-02's stable-ID-keyed SHA-256/U64
mapping. The threshold field is then frozen for the realization. P02-05 calls
`materialize_thresholds` and recomputes its complete canonical output during
constructor and serialized replay validation; it contains no second sampler.

Consequently, evolution is deterministic when the complete frozen threshold
field, accepted mechanical state, and controls are known. Apparent conditional
uncertainty for an observer arises because hidden material fields differ across
replicates conditioned on the same predictor-visible state. It is not a fresh
rupture lottery at each minimizer call or numerical retry.

## RNG namespaces and units

`RNGNamespaceRecord` preserves the exact P01-04 roles:

- `geometry`;
- `material_disorder`;
- `events`; and
- `model_training`.

Each value is a nonnegative integer seed under namespace version
`pgworld-pg-rng-v1`. Numeric seed values may coincide; their roles remain
distinct. P02-05 consumes only `material_disorder`, and only by passing it to
P02-02 threshold materialization. Material sampling is recorded as
`p02_02_keyed_sha256_u64`, not as a Python RNG stream.

The `events` seed is reserved and unconsumed. No mutable event-RNG state or
draw count is serialized. Event-process mode is exactly
`disabled_no_validated_hazard`, with null exposure unit. Hazard, rate,
per-minimizer Bernoulli, physical-time, and probability aliases fail closed.
A later event-process model requires a separately reviewed version and, for a
load-progress hazard, a subdivision-consistent nonnegative exposure contract.

## Conditional replicates and cohorts

Each immutable `ConditionalReplicate` binds:

- parent-network, graph, geometry-realization, and conditioned-state identity;
- the canonical stable physical-bond universe;
- the complete P01-04 seed namespace;
- complete P02-02 law, profile, fixed reference, criterion/unit, visibility,
  and canonical threshold field; and
- explicit quasi-static/no-time and disabled-event-process semantics.

The record is hash-bound and strict-keyed. Replay reconstructs the P02-02 law
and field, independently rematerializes the field from the law, bond IDs, and
material seed, and requires byte-equivalent record content. A merely
self-consistent forged threshold-field hash is insufficient.

`parent_network_id`, the prefixed graph hash, geometry-realization ID, and
conditioned-state ID are caller-supplied bindings. P02-05 validates their
syntax, binds them into the replicate hash, and requires equality across a
conditional cohort. It does not independently derive a graph hash from a
P01-04 graph or a conditioned-state ID from a P03-01 state record; those
producer-to-binding checks remain integration/export responsibilities.

A `ConditionalReplicateCohort` contains at least two canonical, contiguous
replicate indices and declares `hidden_quenched_material_disorder` as its sole
variation axis. Parent network, graph/geometry realization, conditioned state,
bond universe, law/profile/reference/units, geometry seed, event seed, and
model-training seed remain fixed. Material seeds, threshold realizations, and
replicate identities must be unique. Visible-threshold records cannot be
placed in a cohort labeled hidden material variation.

Changing geometry creates a different graph cohort. Changing an event seed
does not constitute executed stochastic-event replication while the event
process is disabled. All descendants of a parent network must remain grouped
in later dataset splits.

## Predictor boundary

Full replicate and cohort records are privileged reproducibility provenance,
not model inputs. `PredictorReplicateView` is a separate exact allowlist with a
`validate_against(parent)` derivation check.

For hidden fields, two material replicates conditioned on the same scientific
features produce byte-identical predictor views. The view omits all RNG seeds
and namespaces, material/geometry/cohort/replicate identities and hashes,
conditioned-state IDs, threshold values, threshold-realization IDs, future
events/outcomes, private metadata, and RNG state. It retains only declared
scientific semantics: criterion/unit, visibility, persistent material-state
meaning, deterministic-given-field meaning, disabled event-process status,
and quasi-static/no-time status.

For an explicitly `visible_to_predictor` threshold study, the view additionally
contains canonical stable-bond/threshold/unit rows. It still omits every seed
and realization proxy. Hidden-material cohorts remain hidden-only.

## Retry and restart meaning

Rejected numerical states, solver errors, and localization retries reuse the
same immutable field and cannot consume a rupture opportunity. P02-02 remains
responsible for excluding those phases from accepted events, and P02-04
restores the accepted lower checkpoint between trials.

P02-06 may serialize the complete privileged replicate record to preserve the
frozen field and all four seed roles across restart. Under this version,
"event RNG preserved" means the reserved event seed remains identical and
unconsumed. It does not establish stochastic event-process suffix equivalence.

## Deliberate boundaries

- The uniform-relative threshold distribution is a reproducible numerical
  policy, not an experimentally calibrated biological distribution.
- No event hazard, event probability calibration, physical time, fatigue,
  rate dependence, molecular cleavage validation, or 3D mechanics is added.
- No simulator topology mutation, localization, restart runner, dataset,
  trained model, experimental result, production compute, or G2/G3 acceptance
  is claimed by P02-05.
