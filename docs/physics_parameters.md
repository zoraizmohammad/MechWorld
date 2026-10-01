# Computational physics profiles

Status: **P01-05A computational contract**. This document freezes route-specific
configuration identities for reproduction and bounded numerical development. It
does not complete P01-05 or certify a biological parameter model.

## Fail-closed boundary

The main study is quasi-static. A loading increment, minimization, or rupture
event is a load/event coordinate, not elapsed physical time. All four profiles:

- use LAMMPS `units nano` and native two-dimensional membrane quantities;
- use `pN/nm` internally and `N/m` in summaries for membrane tension and
  in-plane stiffness (`1 pN/nm = 1e-3 N/m`);
- use `pN nm` for energy (`1 pN nm = 1e-21 J`);
- prohibit physical-time claims because the inherited mass is a placeholder or
  is not recovered from the direct route;
- set `thickness_nm=null` and `stress_3d_allowed=false`;
- use the fixed-cell coordinate-minimized state as
  `fixed_cell_equilibrated`, explicitly not a zero-tension state;
- require total configurational-virial 2D tension as the primary observable and
  incremental-from-reference tension as the secondary observable, excluding
  kinetic pressure;
- use computational `x=axial` and `y=hoop`, while leaving every laboratory
  transform dataset-specific and unconfirmed;
- name first mechanically triggered irreversible physical-bond rupture
  `damage_initiation`, under a not-yet-configured phenomenological law; and
- disable a final science campaign and biological certification.

A cylinder is only **“2D mechanics displayed on a cylindrical surface.”** No
profile turns that display into native three-dimensional mechanics.

## Immutable registered identities

| Profile ID | Route and allowed use | Canonical SHA-256 |
|---|---|---|
| `legacy_python_2026_03_12_v1` | Exact inherited current-Python coefficients; reproduction and bounded numerical fixtures | `sha256:47a96afb4aca5abc413fd0d75ea68b8a45e470cb4bf2a0a398a32a45d9ed022b` |
| `legacy_direct_isotropic_pre_unit_fix_v1` | Exact retained `src/IsotropicPrestrain` 1/1000-scale route; forensic reproduction only | `sha256:9b4c3963f2123984a0822a67d3bbc3080f0edce943c3846e18bd83dbb7607ac5` |
| `legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1` | Exact retained `ELASTIC_2D_ZERO_TEMP` route, including its distinct nonlinear fit and invalid GPa interpretation; forensic reproduction only | `sha256:bc2f7532284d1ac35363aa8f01fcfadf6c0368b86abd986a7546d721499bb8c8` |
| `reviewed_physics_provisional_v0` | Current-Python values copied only for bounded numerical fixtures and development; pending and not biologically certified | `sha256:d9c1e83e911bb5623d65df6238cb6daa6b10fc4445059ee32397596972326d38` |

`legacy_python_2026_03_12_v1` uses the date **2026-03-12** because the two
inherited commits that established the present coefficient/unit family,
`8f4135739218e6a0d9d5568c07a748be776f2035` and
`41548169a2e5eaef9de5cfa64d4717efceb1c0db`, were authored that day; the latter
is the final inherited parameter-related change in
`src/simulation_constants_settings.py`. The suffix `v1` means the first
immutable capture in this profile schema. It does not rename those inherited
commits, claim that the values were scientifically approved on that date, or
rewrite their authorship.

The hash is calculated from canonical UTF-8 JSON with sorted keys and compact
separators after removing only the self-referential `canonical_hash` field. The
loader also pins each expected digest in code. Editing a JSON file and merely
recomputing its embedded digest therefore cannot mutate an existing ID.

## Exact route-specific values

LAMMPS evaluates the following equations:

\[
E_h=K(r-r_0)^2,
\qquad
E_{nl}=\frac{\epsilon(r-r_0)^2}{\lambda^2-(r-r_0)^2},
\qquad
E_\theta=K_\theta(\theta-\theta_0)^2.
\]

`epsilon` and the angle coefficient are energies (`pN nm`); the angle
displacement is in radians internally even though LAMMPS accepts
`theta0` in degrees.

| Route | Harmonic `(K pN/nm, r0 nm)` | Nonlinear `(epsilon pN nm, r0 nm, lambda nm)` | Angle `(K pN nm/rad², theta0 deg)` | Mass |
|---|---:|---:|---:|---:|
| Current Python | `(5570, 1.03)` | `(185.328520541486, 1.0, 4.034069292365436)` | `(41.8, 180)` | `0.0004271587301788674 ag`, placeholder |
| Direct `IsotropicPrestrain` pre-fix | `(5.570, 1.03)` | `(0.185567402281798, 1.0, 4.035190236993014)` | `(0.0418, 180)` | unrecovered data-file input |
| Direct `ELASTIC_2D_ZERO_TEMP` pre-fix | `(5.570, 1.03)` | `(0.1709, 0.9065, 4.0878)` | `(0.0418, 180)` | unrecovered data-file input |
| Provisional reviewed destination | same numbers as current Python | same numbers as current Python | same numbers as current Python | same placeholder |

The direct routes are kept separate. Their numbers must never be pooled under a
generic “legacy” label. The direct elastic input also retains
`cfac=1.01325e-8` and its declared `GPa` label as provenance. That label is
dimensionally invalid for a two-dimensional virial without a wall thickness;
it is not accepted for new results. The old direct isotropic kg/J nano-unit
comments are known to be wrong by a factor of 1000 and are likewise preserved
as provenance, not adopted as the actual unit convention.

## Numerical derivations, not molecular confirmation

For the current-Python/provisional numbers:

- one harmonic edge has tangent `2K = 11140 pN/nm`;
- two identical straight edges in series have tangent `K = 5570 pN/nm` and
  rest length `2 × 1.03 = 2.06 nm`;
- the nonlinear local tangent is
  `2 epsilon/lambda² = 22.776424425306164 pN/nm`;
- the nonlinear extension pole is
  `r0 + lambda = 5.034069292365436 nm`; and
- the angle-energy curvature is `2K = 83.6 pN nm/rad²`.

These are mechanical consequences of the encoded equations. They do not prove
that two 1.03 nm code edges represent one published two-disaccharide spring.
The bead/disaccharide mapping, peptide attachment placement, rupture energy,
and resolution-consistent angle scaling remain unresolved. In particular, no
candidate angle rescaling is frozen into `reviewed_physics_provisional_v0`.

## Provisional reviewed destination

`reviewed_physics_provisional_v0` deliberately has:

- `review_status=pending`;
- `biological_parameter_certified=false`;
- `coarse_graining_status=unresolved`;
- `nonlinear_fit_status=unreproduced`;
- `angle_resolution_status=unreviewed`;
- `mass.status=placeholder` and `physical_time_valid=false`;
- `thickness_nm=null` and `stress_3d_allowed=false`; and
- `final_science_campaign_allowed=false`.

Prof. Christoph Schmidt is recorded only as the **proposed, unconfirmed**
scientific reviewer. Octavio is recorded only as the **proposed, unconfirmed**
checker of inherited implementation and provenance. Neither assignment nor an
approval is asserted.

The profile copies current-Python numbers so P01-06 can run independent
energy/force/virial fixtures under an explicit contract. A numerical match to
LAMMPS will verify implementation consistency, not biological correctness.

## Run and aggregation contract

Load a registered profile and place its complete detached snapshot in each run,
dataset, checkpoint, evaluation, and visualization record:

```python
from pgworld.config.physics_profiles import load_physics_profile

profile = load_physics_profile("reviewed_physics_provisional_v0")
run_metadata["physics_profile"] = profile.expanded_snapshot()
```

At minimum, a compact row may store `profile.identity`, which contains both the
ID and hash, but the run manifest must also retain one expanded snapshot. The
loader rejects unknown fields, missing fields, malformed scalar types,
non-finite numbers, a changed ID, an embedded hash mismatch, a digest that does
not match the registry, or a change to exact route values.

Silent aggregation of unlike IDs/hashes is an error. A comparison may include
multiple profiles only when it explicitly requests
`comparison_mode="stratified_by_profile"`; the outputs then remain grouped by
profile identity. Stratification permits comparison, not concatenation as a
homogeneous cohort.

## Pending P01-05 review

P01-05 remains blocked on actual reviewer acceptance and source reconciliation:

- final bead/disaccharide and one-edge/two-edge mapping;
- resolution-consistent bending/angle mapping;
- original nonlinear fit samples, domain, weights, residuals, and acceptance;
- a physical mass/mobility/damping model if time claims are ever proposed; and
- an approved final `reviewed_physics` profile.

No file in `configs/physics/` constitutes that approval. The governing decision
record is `docs/decisions/scope.md`; the detailed inherited audit is
`docs/subagents/P01-05-physics-audit.md`.
