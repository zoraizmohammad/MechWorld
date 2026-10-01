# Phenomenological quasi-static damage contract

Decision date: 2026-10-01

Status: computational reference contract for P02-02; not a biologically
certified molecular-cleavage model.

## Scope and claims

The first damage model is a solver-independent threshold law over accepted
quasi-static equilibria. It supplies deterministic event semantics for later
solver/cascade work. It does not run LAMMPS, remove dependent angles, localize
an event between load steps, implement a rupture cascade, or assign physical
time. Those operations remain P02-03 and later trajectory work.

Every law record says
`phenomenological_not_experimentally_constrained_molecular_cleavage`. A
numerical result under this law must not be called an experimentally verified
chemical cleavage mechanism, biological time-to-failure, fatigue lifetime, or
three-dimensional failure stress. Threshold values remain provisional.

## Versioned law

Schema `pgworld.quasistatic_damage.v1` supports three scalar criteria:

| Criterion | Definition expected from mechanics adapter | Unit |
|---|---|---|
| `bond_extension_ratio` | declared bond extension divided by its declared reference length | dimensionless |
| `bond_tension` | physical-bond tensile force under the recorded sign convention | pN |
| `bond_energy` | physical-bond potential energy under the recorded potential | pN nm |

The mechanics adapter must supply the criterion consistently; this module does
not infer it from an ambiguous field name. Non-finite values, wrong units, and
boolean-as-number values fail closed. A bond is a candidate when its accepted
criterion value is greater than or equal to its frozen threshold.

Each law binds the complete registered physics-profile ID/hash pair and one
fixed-cell-equilibrated reference-state ID. Records from another profile hash
or reference cannot be assessed or aggregated silently. The profile remains
provisional even when its ID/hash validates.

## Deterministic and quenched heterogeneous variants

`deterministic_threshold` assigns one positive threshold to every stable
physical-bond ID and consumes no disorder seed.

`quenched_heterogeneous_threshold` currently uses a uniform relative interval.
For base threshold `t`, half-width `w` with `0 < w < 1`, nonnegative material
disorder seed `s`, law fingerprint `L`, and UTF-8 stable physical-bond ID `b`,
the exact numerical policy is:

```text
digest = SHA256("pgworld.quasistatic_damage.v1\0" + L + "\0" + s + "\0" + b)
u64    = unsigned big-endian integer from digest bytes 0..7
u      = u64 / 2^64
t_b    = t * (1 + w * (2*u - 1))
```

This is a deterministic keyed U64 mapping for reproducibility, not evidence of
a biological probability distribution. It makes each draw stable under input
reordering, assessment retries, solver retries, and unrelated bond additions.
Thresholds are materialized once into an immutable, content-hashed threshold
field and are never redrawn during minimization, loading, or display.

The law explicitly records `visible_to_predictor` or
`hidden_from_predictor`. A threshold-field record with
`hidden_from_predictor` is privileged simulator/reference provenance. Neither
its thresholds, seed, realization ID as a proxy, nor future event information
may be placed in model inputs. P03 schema/export and model feature-selection
code must enforce that separation; storing reproducibility metadata does not
make it an admissible predictive feature.

## Reference preparation and event acceptance

Reference observations are checked against the already materialized field.
Any reference bond at or above threshold is flagged in the immutable
`initial_threshold_violation_mask`. The state remains intact for diagnosis,
but all material-rupture assessment is ineligible. Such a state is invalid
reference preparation and its condition cannot be relabeled as damage
initiation.

Only `accepted_equilibrium` states can yield material-rupture candidates.
Reference preparation, rejected numerical trials, and solver errors return an
explicit excluded assessment with no candidates. For an eligible state,
candidate order is deterministic:

1. decreasing criterion/threshold utilization;
2. stable physical-bond ID in ascending lexical order for an exact tie.

Only rank zero is accepted by one call. The event binds the pre-state hash,
assessment hash, candidate hash, law ID/fingerprint, threshold realization,
profile ID/hash, reference ID, control ID, load coordinate, criterion, and
threshold. It also records the accepted P02-01 monotone path progress with
`cumulative_absolute_lambda_increment` semantics. Retrying the same immutable
state and assessment produces the same event and post-state record. Cascade
execution must relax and reassess after each accepted event rather than
accepting a stale candidate list.

## Irreversibility and event origin

The stable bond universe has three separate masks:

- `alive_mask`: current physical participation;
- `rupture_mask`: accepted mechanically triggered material ruptures;
- `prescribed_removal_mask`: user-prescribed removals.

An alive bond can become mechanically ruptured or prescribed-removed, never
both. No transition may reactivate it, clear either terminal mask, alter an
initial-violation flag, rewrite accepted event history, or change stable IDs,
law, profile, threshold realization, or reference. This is logical damage
state only; the later cascade must make the matching LAMMPS/topology and angle
changes.

The following origins never count as damage initiation:

- prescribed weakening or removal;
- computational-neighbor changes;
- rendering changes; and
- solver errors.

A prescribed removal changes physical alive/removal masks but not the rupture
mask. A prescribed weakening leaves these masks unchanged. Computational,
rendering, and solver records cannot mutate a physical bond. All excluded
records are content-hashed and fail closed on source/kind/state tampering.

## Failure endpoints

Four endpoint records remain distinct:

1. `damage_initiation`: first accepted mechanically triggered irreversible
   physical-bond rupture after valid reference preparation;
2. `load_bearing_connectivity_loss`: a separately predeclared load-bearing
   connectivity analysis;
3. `load_or_stiffness_degradation`: a separately predeclared load/stiffness
   criterion; and
4. `mechanical_instability`: a separately predeclared mechanical-stability
   criterion.

When no material rupture occurs over the executed control schedule,
`damage_initiation` is explicitly right-censored at its terminal state. The
record keeps both the terminal instantaneous control coordinate and monotone
cumulative path progress. The terminal coordinate is not an exposure bound:
after cyclic loading/unloading it may return to zero while path progress stays
positive. No synthetic failure coordinate is inserted. Material-event path
progress must be nondecreasing, may stay equal through a same-control cascade,
and cannot exceed terminal path progress. The other endpoints are
`not_evaluated` until their own accepted analyses exist. Connectivity alone and
minimizer nonconvergence are inadmissible evidence of mechanical instability.
A solver error is diagnostic, not physical failure.

## Numerical and release boundaries

- Load coordinates are quasi-static and use either dimensionless deformation
  coordinates or the accepted pressure coordinate in pN/nm2. Physical time is
  always null and invalid. Cumulative absolute load-coordinate increment is a
  path coordinate, not elapsed time.
- Events in one endpoint summary must use the same load-coordinate unit,
  profile, and reference, with unique event and physical-bond IDs.
- Direct constructors and record replay validate schema, registered profile
  pair, reference, units, sources, masks, hashes, ordering, and immutable
  provenance. Duplicate JSON-object keys remain the responsibility of the
  eventual strict file loader; typed record APIs reject duplicate ID rows.
- No profile or threshold in this contract is approval for a production
  campaign, biological parameter certification, public release, or manuscript
  claim.

## Typed records and replay boundary

The public solver-independent surface is deliberately explicit:

| Type/function | Frozen record content and validation role |
|---|---|
| `DamageLaw` | schema; law ID/kind; criterion/unit/base threshold/distribution; predictor visibility; registered profile ID/hash; reference ID; quasi-static/time/source/mechanism/sampling invariants; content fingerprint |
| `ThresholdField` / `materialize_thresholds` | content-hashed realization ID; law fingerprint; profile/reference; criterion/unit/visibility; canonical stable-ID threshold rows; optional material-disorder seed; sample-once/no-time invariants |
| `CriterionObservation` | stable physical-bond ID, criterion, unit, finite value; exact-key record replay |
| `DamageState` / `initialize_damage_state` | law/fingerprint/realization; profile/reference; canonical bond universe; alive, rupture, prescribed-removal, and initial-violation masks; sha256 material-event history and first event; content-derived state ID |
| `RuptureCandidate` | content-hashed candidate ID; canonical rank; bond criterion/threshold/utilization; control, instantaneous coordinate, path progress, pre-state, law/realization, profile/reference; accepted-equilibrium/material-source/no-time invariants |
| `DamageAssessment` / `assess_material_rupture` | content-hashed assessment ID; exact phase and canonical exclusion reason; eligibility; canonical candidate sequence; state/law/realization/profile/reference/control/coordinate/progress binding |
| `MaterialRuptureEvent` / `accept_next_material_rupture` | content-hashed event ID and sequence; pre-state, assessment, candidate, law/fingerprint/realization; bond/control/criterion/threshold; instantaneous coordinate/path progress; registered profile/reference; accepted alive-to-dead and first-event semantics |
| `ExcludedEventRecord` / `apply_excluded_event` | content-hashed non-material event; exact source/kind; profile/reference; accepted flag and optional prescribed physical-bond alive transition; false mechanical trigger and no physical time |
| `EndpointObservation` | endpoint name/status; profile/reference; endpoint-specific evidence; instantaneous or terminal-control coordinate semantics; monotone path progress; explicit no-time fields |
| `TrajectoryFailureEndpoints` / `build_failure_endpoints` | law/fingerprint/threshold realization even for no-event censoring; the four separate endpoint records; exact profile/reference identity and chronological unique material events |

Every listed `as_record`/`from_record` pair requires exact fields and rejects
unknown keys. Nested records are reconstructed through their own validators.
`DamageTransition` is an in-memory checked wrapper rather than a persisted
record: it binds the event pre-state and provenance to the exact resulting
dead/ruptured/not-prescribed event bond and material-event history. P03 owns
the eventual trajectory container and cross-record existence/index checks.

`validate_irreversible_transition` checks state-to-state mask/history
monotonicity. It is not an energy-balance check and does not prove a solver
state converged. The damage module accepts criterion observations; the later
mechanics adapter remains responsible for computing those values under the
declared potential/sign/reference convention.

The next implementation step is P02-03: apply control, relax the current
topology, assess this law, record one event, perform verified physical-bond and
dependent-angle changes, relax again, and repeat under explicit cascade,
localization, convergence, and restart budgets.
