# P02-01 subagent return: explicit quasi-static loading controls

## Result

Implemented a strict, versioned, solver-independent control contract at
`pgworld.simulation.controls` for isotropic, axial (`x`), hoop (`y`), unequal
biaxial, engineering simple shear, cyclic/loading-unloading, pressure-derived
tension, and prescribed local weakening/removal.

The contract stores both absolute targets and validated increments. It keeps a
single fixed-cell equilibrated reference ID, uses `lambda_load` as a
quasi-static coordinate, and defines cyclic progress as cumulative
`abs(delta lambda_load)`. Direct constructors fail closed: targets are replayed
from normalized mode metadata, increments are replayed from the preceding
target, pressure targets are recomputed from their exact assumptions, and
physical-time/reset/schema relabeling is rejected.

Tensor controls transform in a declared orthonormal coordinate frame while
preserving semantic `x=axial`, `y=hoop` axes. Pressure mode records only
`N_hoop=pR`, `N_axial=pR/2` for a closed thin cylinder away from end effects,
with exact native units. It does not convert strain to pressure or call the
target turgor inflation.

Prescribed interventions select stable physical-interaction IDs. Weakening
creates per-interaction effective parameters; removal creates an alive mask.
Chemical type is preserved, nonselected same-type interactions remain
unchanged, and event records state `source=prescribed_intervention`,
`counts_as_damage_initiation=false`, and
`shared_lammps_type_coefficient_mutated=false`.

Nine deterministic JSON templates cover every required mode. Their hashes are
recorded in `evidence/subagents/P02-01/verification.md`. The placeholder fixed
reference IDs are templates that must be replaced by an actual recorded
reference before solver execution. Run-level config hashing remains the
downstream manifest's responsibility. The cyclic template and typed
`mode_parameters` both retain `base_mode`.

## Verification

Implementation commit: `9291f0b686e079c7b38045d61f08b7c166665b3b`.

- Initial red: missing controls module, exit 1 (`red.xml`).
- Adversarial correction reds: 9, 4, and 2 exact failures in
  `review-red.xml`, `control-integrity-red.xml`, and
  `semantic-replay-red.xml`.
- Final focused: 40 passed (`semantic-replay-green.xml`).
- Final fresh wheel: 1 passed in 128.58 s; strict allowlist and installed
  controls import/smoke passed (`wheel-final.xml`,
  `wheel-verification-final.json`).
- Final full suite: 213 passed, no failures/errors/skips in 155.742 s
  (`full-final.xml`).
- Final compileall and `git diff --check`: exit 0.

An independent reviewer reproduced and closed constructor bypasses, mutable
nested metadata, coordinate covariance, inverted/inconsistent deformation,
pressure relabeling, cyclic metadata loss, arbitrary progress, and duplicate
or non-string interaction selectors. The final source-contract audit reported
no blocker.

## Limitations and next dependencies

This task defines controls only. It does not run a quasi-static solver, add a
rupture law, mutate topology, localize events, handle cascades, prove restart
equivalence, or generate a dataset. Those remain later WP2/WP3 work. The
parameter profile remains provisional and no biological, physical-time,
experimental, or public-release claim is made.

Complete commands, hashes, evidence paths, path boundary, and limitations are
in `evidence/subagents/P02-01/verification.md`.
