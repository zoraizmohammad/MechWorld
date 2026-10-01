# Task Return: P01-04 generator reproducibility and precision

## Base and Scope

- Base: `a79a7aaf337f32dd459a00444babe2851633046d`
- Branch/worktree: `research/p01-04-reproducibility`; `C:\Users\mzora\MechWorld-wt-p01-04`
- Owned production/test paths: `src/assemble_pg_network.py`, `src/lammps_PG_objects.py`, `tests/unit/test_generator_reproducibility.py`
- Owned evidence/report paths: `evidence/subagents/P01-04/`, this report
- No root ledger, README, task state, shared contract, dependency, private-data, or unrelated path was edited.

## Changes

1. Added a stable SHA-256-derived `RNGSeeds` namespace with explicit `geometry`, `material_disorder`, `events`, and `model_training` integer seeds. The current generator consumes only a local Python `Random` geometry stream. Atom material-disorder Bernoulli draws can consume the separately injected material stream. Event and model-training seeds are exposed for their future owners but are not falsely consumed here.
2. Propagated the geometry RNG through discrete length sampling, shuffling, initial vertical placement, DSU orientation, strand displacement/rotation, and peptide-candidate ordering. `seed=` is a convenience for namespace derivation; `rng_seeds=` accepts explicit independent seeds; supplying both or an unsupported backend fails explicitly. Seeded generation does not consume global Python or NumPy RNG state.
3. Added opt-in realized `NetworkGenerationMetrics`: cell size, exact counts, glycan/peptide bond counts, achieved density and crosslink fraction, atom-graph connected components and largest-component fraction, realized strand lengths, realized 2D strand orientations, a canonical graph SHA-256, and RNG provenance. Metrics are computed from the final generated objects. The fixed test fixture contains a realized 6-DSU filler strand outside its requested `UNI=2=5` support, proving this is not a target echo.
4. Replaced two-decimal atom output with validated 17-significant-digit formatting. The writer returns `DatafileExportMetrics` computed from the exact emitted coordinate tokens. A real LAMMPS 2 Sep 2026 `read_data` probe loaded all 108 fixture atoms; all 324 coordinate tokens round-tripped with measured max and RMS error 0.
5. Preserved default return shapes and legacy unseeded call signatures. `return_metrics=True` is opt-in: in-memory generation adds a seventh metrics value; file generation returns `(path, generation_metrics, export_metrics)`.

No physical coefficient, unit convention, periodic-image convention, distribution probability, or parameter profile was changed.

## Commands and Results

Exact commands, exit codes, timings, hashes, and artifacts are indexed in `evidence/subagents/P01-04/verification.md`.

- Red, before source edits: 9 failed in 7.22s, exit 1.
- Focused final: 14 passed in 3.38s, exit 0.
- P01-03 distribution plus orientation compatibility: 30 passed in 6.46s, exit 0.
- Full suite: 76 passed in 6.00s, exit 0.
- Targeted `py_compile`: exit 0.
- `git diff --check`: exit 0.
- LAMMPS high-precision `read_data`: exit 0; 108/108 atoms loaded; solver closed.

## Scientific Checks

- Achieved density and crosslink fraction are recomputed from realized atom/bond counts and realized box area.
- Length observations come from realized molecule membership, including generator-created filler lengths.
- Orientation observations use the already integrated restricted-triclinic minimum-image helper and the final centered orthogonal cell; singleton/zero-length orientations are excluded and counted explicitly.
- Connectivity is the physical atom/bond graph. It is not called rigidity, load-bearing connectivity, or biological failure.
- The graph fingerprint includes cell dimensions, persistent atom/molecule/type IDs, coordinates, image shifts, eligibility/link status, physical bonds, and angles in canonical ID order.
- The data export probe verifies parser acceptance and text precision only; it is not a mechanics validation or production simulation.

## Known Limitations

- The exact seeded graph intentionally differs from inherited mixed global Python/NumPy streams and from pre-P01-03 expanded-list draws. Legacy calls without a seed still work, but now draw generation randomness from Python's single global module rather than the old accidental mixed sources.
- `python` is the only declared RNG backend. The canonical graph hash freezes this implementation's exact output but is not a promise of bit identity across arbitrary future numerical-library changes.
- The generator does not yet implement a material-disorder field, intervention engine, stochastic rupture events, or model trainer. This slice supplies independent seeds and the material-draw injection point; downstream tasks must save/restore the relevant stream state.
- Realized orientation values describe the generated 2D geometry before solver relaxation. They do not validate native 3D mechanics or experimental structure.
- Seventeen-digit text preserves the tested binary64 coordinates, but does not repair already-written historical two-decimal files or bound downstream solver/analysis error.
- `return_metrics` is opt-in to preserve inherited tuple/string callers. Integrators creating canonical datasets should require and persist the metrics/provenance result.

## Integration Notes

- Cherry-pick the single returned commit, inspect that every changed path is in the ownership list, and rerun the focused/full suites in the integration worktree.
- P01-03 distribution semantics are preserved; compact distributions now consume the injected geometry stream.
- P01-01 image-shift and minimum-image conventions are reused unchanged.
- Future event/model tasks should use the integer seeds in `RNGSeeds` to initialize their own appropriate backend RNGs and record backend/version/state; they must not feed hidden event RNG state to a predictor.
