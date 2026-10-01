# P02-02 subagent return: phenomenological damage/event contract

## Result

Implemented a solver-independent, versioned quasi-static damage contract in
`pgworld.physics.damage` and documented its scientific boundary in
`docs/decisions/fracture_model.md`.

The law supports deterministic bond extension-ratio, bond-tension, and
bond-energy thresholds plus a separate quenched heterogeneous variant. The
heterogeneous draw is keyed independently by stable physical-bond ID using the
documented SHA-256/U64 mapping, sampled once into an immutable content-hashed
field, and invariant to input order and retry. Every law explicitly states
whether threshold values are visible or hidden from predictors.

Only accepted quasi-static equilibria can create material-rupture candidates.
Initial threshold violations invalidate the reference without becoming damage
initiation. Candidate ordering is decreasing utilization followed by lexical
stable ID, and one accepted event irreversibly updates the physical alive and
rupture masks. Prescribed removal has a separate irreversible mask and never
counts as material rupture; prescribed weakening, computational-neighbor
changes, rendering changes, and solver errors are excluded sources.

Failure records keep damage initiation, load-bearing connectivity loss,
load/stiffness degradation, and mechanical instability distinct. No event over
an executed schedule is right-censored, not assigned a fabricated failure
coordinate. Instantaneous lambda is stored separately from monotone cumulative
path progress, so cyclic unloading can return lambda to zero without erasing
exposure. Endpoint summaries bind the registered physics profile/reference and
damage law/fingerprint/threshold realization even when no rupture occurred.

Implementation commit:
`24eb10712552171b93bc595fadd414b00a8ad3f7`.

## Verification

- Exact initial red: missing `pgworld.physics.damage`, pytest exit 2.
- Independent adversarial review reproduced and closed constructor/replay,
  transition binding, mixed-law endpoint, cyclic-progress, hidden-metadata,
  and canonical solver-error-reason gaps.
- Final focused: **58 passed in 0.43 s**.
- Fresh installed wheel: **1 passed in 122.26 s**; strict 33-member allowlist,
  exact-lock `pip check`, external LAMMPS fixtures, installed damage smoke, and
  checkout/private-path exclusions passed.
- Full suite: **271 passed in 114.80 s**, no failures/errors/skips; 14 inherited
  warnings.
- `compileall -q src` and `git diff --check`: exit 0.

Exact commands, hashes, all red/green records, and wheel metadata are in
`evidence/subagents/P02-02/verification.md`.

## Changed paths

- `docs/decisions/fracture_model.md`
- `src/pgworld/physics/damage.py`
- `tests/physics/test_damage_law.py`
- `tests/release/test_wheel_install.py`
- `docs/subagents/P02-02-damage-law.md`
- `evidence/subagents/P02-02/`

No root ledger, README, task state, ownership file, package initializer,
profile, solver/cascade code, trajectory schema, private data, or release gate
was changed.

## Limitations and next dependency

This task defines and validates logical damage/event state only. P02-03 must
implement the actual apply-control/relax/assess/change-topology/relax cascade,
dependent-angle removal, localization, bounded retries/events, energy
accounting, restart equivalence, and load-step sensitivity before G2 can be
considered. Biological parameter review remains pending; no physical-time,
three-dimensional, experimental, production, or public-release claim is made.

