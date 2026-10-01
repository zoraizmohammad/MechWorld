# P01-10 structural observables handoff

## Outcome

The assigned implementation now separates chemical topology from image morphology and makes the inherited 2D pore/orientation conventions executable on known fixtures.

- `chemical_connected_components` reads only persistent atom IDs and explicit bond endpoints. A visual crossing remains two chemical components unless a bond is actually present.
- The pore path has a deterministic, bounded periodic flood fill. An all-empty periodic mask terminates as one pore instead of looping around a row indefinitely.
- Grayscale, grayscale-alpha, RGB, and RGBA input semantics are explicit: opaque non-white pixels are occupied; transparent/white pixels are background.
- Restricted-triclinic/orthogonal bond rendering uses the integrated exact 2D minimum-image routine on a fractional periodic raster. Raster dimensions and square-brush width are required metadata.
- Pixel pore areas carry cell/pixel area, resolution, width, occupied fraction, and component counts. They remain explicitly image-derived.
- The rectangular-image x-scale defect is fixed: image columns, not rows, define x resolution.
- Absolute orientation is explicitly signed deviation from hoop `+y` with `x` axial. Peptide attachment vectors now use the same supported periodic minimum image as glycan vectors. Zero/nonfinite vectors fail explicitly.

## Acceptance evidence

- Exact pre-production red: `evidence/subagents/P01-10/red-regression.txt`, **1 failed in 8.63s**.
- Follow-up rectangular-scale red: `evidence/subagents/P01-10/follow-up-red-pixel-scale.txt`, **1 failed in 1.68s**.
- Focused green: **19 passed in 1.47s**.
- Related compatibility: **33 passed in 1.76s**.
- Complete suite: **112 passed in 5.70s**.
- Compilation and `git diff --check`: exits 0.
- Full commands, hashes, measured values, invariant definitions, and limitations: `evidence/subagents/P01-10/verification.md`.

The sensitivity artifact measures occupied fraction 0.010625 at 40 x 40/1 px, 0.00515625 at 80 x 80/1 px, and 0.065625 at 40 x 40/5 px on the same one-bond fixture. This deliberately demonstrates that pixel morphology changes with raster settings. It is not a convergence claim.

## Scientific boundaries and remaining work

- The implementation does not infer bonds from coordinates, intersections, or pixels and makes no rigidity/load-bearing claim.
- Pore metrics are four-neighbor components of the periodic image complement, not molecular pore topology or experimentally calibrated areas.
- The supported geometry is the existing 2D orthogonal/restricted-triclinic contract. General triclinic/native 3D input is not accepted.
- Rendering uses a static minimum image, not a canonical persistent per-edge image offset; that remains P03-01 scope.
- Legacy file caches do not encode raster configuration/provenance. They are retained for compatibility but are not evidence of a fresh sensitivity sweep.
- The orientation convention is a tested code convention, not confirmation of lab-axis mapping or a native 3D result.
- No physical constants, private data, production compute, or experimental claims were introduced.

## Integration note

The integrator must independently inspect/rerun this branch and update `README.md`, `handoff.md`, `TASKS.json`, and `docs/ownership.md` together if accepting the handoff. This subagent did not edit those shared files or accept a gate/task.
