# P02-04 first-event localization and phase accounting contract

Status: implemented for a deliberately bounded, monotone harmonic fixture.
This contract does not certify a production peptidoglycan fracture model,
nonlinear peptide trials, physical time, rate dependence, fracture toughness,
mechanical instability, or biological parameters.

## Accepted bracket and load-path semantics

Localization begins with one fixed, converged, live-verified lower state that
has no eligible P02-02 rupture candidate. The upper state must be a converged
crossing under the same immutable topology, DamageLaw, frozen ThresholdField,
physics profile, reference state, axes, loading mode, and one P02-01 control
segment. A trial may update the lower or upper bound only after it has passed
the convergence policy and been reassessed as an accepted equilibrium.

For a one-segment cyclic/unloading move, the instantaneous load coordinate can
decrease while exposure remains monotone:

`path_progress_trial = path_progress_lower + abs(lambda_trial - lambda_lower)`.

The full diagonal deformation gradient is interpolated on that segment. Every
trial incremental gradient is recomputed as
`F_trial @ inverse(F_original_lower)`, because every trial starts from the
same accepted lower checkpoint. Pressure/tension control, shear, rotated axes,
general-cell mappings, mixed units, and nonpositive-determinant controls fail
before a trial command.

The published event coordinate is the crossing upper bound after both the
load-coordinate and path-progress bracket widths satisfy their recorded
tolerances. Rank and simultaneous-tie choice are delegated unchanged to the
P02-02 canonical utilization/stable-ID ordering. A simultaneous crossing is
one first event, not multiple independent labels.

## Trial transaction and budgets

The engine first compares a live backend observation with the supplied lower
snapshot, then checkpoints that exact state. Each trial applies one target,
captures the raw after-control state, relaxes, validates the complete
observation, and assesses only an accepted equilibrium. It then restores and
verifies the original lower checkpoint, including topology, cell/PBC,
positions, forces, tension tensors, raw energies, criteria, periodic offsets,
boundary conditions, runtime constraints, DamageState, event history, and the
frozen threshold realization. Trial observations and assessments are private;
they are not trajectory states or training labels.

Refinement, solver-trial, and retry budgets are independent and hash-bound.
Only the explicit convergence reason
`diagnosed_transient_solver_interruption` can use a retry, and it can do so at
most once. A deterministic residual/iteration failure such as
`max_iterations_or_residual_above_tolerance` is terminal and is never retried
blindly. Apply, observation, validation, relaxation, assessment, checkpoint,
or restore exceptions produce typed nonlabel diagnostics. A failed restore is
distinct from a successfully rolled-back rejected trial.

After localization, the engine restores the accepted crossing checkpoint and
runs the P02-03 exact deletion/re-relaxation transaction. If that transaction
or restoration of the original lower state fails, no localized event or
energy-accounting record is published. The owned backend is closed on every
return or exception path.

## Executable domain certificate

The executable certificate is restricted to the exact three-node, two-glycan-
bond, one-angle collinear harmonic fixture with a backend-bound monotone
extension-ratio response on one path segment. The certificate binds the
registry hash, profile hash, reference ID, bond universe, potential family,
monotonicity scope, and deterministic backend response-contract hash.
Collinearity and positive axial direction are checked on the two unwrapped
source legs in the angle's ordered node path. Arbitrary endpoint storage
orientation of either bond is reversed as needed, so a folded chain cannot
masquerade as a positive ordered chain.

A peptide-labeled bond cannot enter through the harmonic certificate. A
nonlinear endpoint-only pole margin is retained as an explicit non-executable
record: endpoint safety does not show that minimizer iterates stay outside the
singular domain. A backend that does not carry the exact monotone response
contract is rejected before control application. This is fixture evidence,
not a general proof for arbitrary harmonic networks.

## Five raw phases and energy identities

For the first localized event, the accounting record embeds and hash-binds:

1. `U_previous_accepted`;
2. `U_after_control_before_relax`;
3. `U_pre_event_relaxed`;
4. `U_post_delete_unrelaxed`;
5. `U_post_event_relaxed`.

All values are raw total potential energies in `pN nm`. Under the validated
instantaneous prescribed diagonal deformation, the narrowly defined
fixed-topology conservative loading input is

`W_control = U_after_control_before_relax - U_previous_accepted`.

It is split without conflation into

`Delta_U_equilibrium = U_pre_event_relaxed - U_previous_accepted`

and

`L_pre = U_after_control_before_relax - U_pre_event_relaxed`,

with `W_control = Delta_U_equilibrium + L_pre` within the recorded tolerance.
The signed, same-coordinate deletion change is

`Delta_U_delete = U_post_delete_unrelaxed - U_pre_event_relaxed`.

It is not fracture toughness or dissipation. Held-control boundary work during
the delete/re-relax phase is exactly zero only because the validated cell and
deformation target do not change. Post-delete relaxation loss is

`L_post = U_post_delete_unrelaxed - U_post_event_relaxed`.

The two relaxation losses may not be negative beyond numerical tolerance.
There is intentionally no assertion that potential energy decreases across
external loading or across deletion. Pressure, tension-target, and general-
cell work calculations fail closed rather than using a virial shortcut.

## Replay and visibility boundary

Localization, certificate, budget, controls, counters, terminal status, and
accounting records are immutable, strict-key, and hash-bound. Result replay
binds the complete original lower control and state IDs, localized event
coordinate, a complete `STABLE` cascade with no execution diagnostic, exact
raw phase records, law, ThresholdField,
registry, profile, and reference. Observable output explicitly marks
`accepted_label` and `label_eligible`. Every nonlocalized result is
`false` and contains no cascade label, bracket, trial coordinate, criterion,
threshold, material seed, or threshold-realization field.

The serialized localization record stores the final bracket controls but not
the private lower/upper trial observations or assessment digests. Therefore a
serialized record alone cannot independently re-prove that the lower bound
was noncrossing and the upper bound crossing. That claim remains bounded
execution evidence verified during the live transaction; canonical replay of
private localization trials is not implemented in P02-04.

## Deliberate boundaries

- The real solver check is the serial orthogonal, sequential-tag
  `tiny_harmonic_fixture` with fixed degree-one endpoints, free-DOF residuals,
  and unavailable endpoint reactions.
- The fixture is not a production/general PG adapter and does not validate the
  nonlinear peptide potential or its pole margins.
- Localization operates on one control segment and owns/closes one backend.
  Persistent schedules and restart continuation remain P02-06 work.
- Raw deletion and relaxation terms are not experimental fracture energy,
  fatigue lifetime, rigidity loss, or catastrophic cell failure.
- No canonical P03 trajectory schema, dataset gate, sensitivity campaign,
  experiment, cluster run, public release, or G2 acceptance is claimed.
