# P01-10 verification evidence

## Scope and environment

- Worktree: `C:\Users\mzora\MechWorld-wt-p01-10`
- Branch: `research/p01-10-observables`
- Assigned base: `9280b5d1486496b705e0c178c43da7a488568c67`
- Base tree: `6f9110dcf81a896873ea8a0e0695723fe6bc144d`
- Interpreter: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`, Python 3.11.9
- Packages observed during verification: NumPy 2.2.2, Matplotlib 3.11.2, pandas 3.0.6, pytest 7.4.3
- Inputs: source-controlled synthetic structures only. No private lab data, production simulation, external upload, or physical coefficient choice was used.

## Red-first evidence

Before either production module was edited, this command was run from the worktree:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests\physics\test_structural_observables.py -q
```

Exit 1: `1 failed in 8.63s`. A 4 x 6 all-white grayscale image raised `ValueError: not enough values to unpack (expected 3, got 2)` in inherited `bool_me`. Exact transcript: `red-regression.txt`.

A follow-up rectangular-image regression was then added and isolated:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests\physics\test_structural_observables.py::test_pixel_scale_uses_image_columns_for_x_resolution -q
```

Exit 1: `1 failed in 1.68s`. A 3-row x 7-column image over a 7-unit x cell returned `3/7` px/unit because rows were used as x pixels. Exact transcript: `follow-up-red-pixel-scale.txt`.

## Green verification

All commands below ran from the worktree.

1. Focused structural observables:

   ```text
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests\physics\test_structural_observables.py -q --junitxml=evidence\subagents\P01-10\focused.xml
   ```

   Exit 0: **19 passed in 1.47s**. Transcript: `focused.txt`; JUnit: `focused.xml`.

2. Periodic geometry, generator metrics, and inherited glycan-orientation compatibility:

   ```text
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests\unit\test_periodic_geometry.py tests\unit\test_generator_reproducibility.py test\test_glycan_orientation.py -q --junitxml=evidence\subagents\P01-10\compatibility.xml
   ```

   Exit 0: **33 passed in 1.76s**. Transcript: `compatibility.txt`; JUnit: `compatibility.xml`.

3. Complete branch suite:

   ```text
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence\subagents\P01-10\full-suite.xml
   ```

   Exit 0: **112 passed in 5.70s**. Transcript: `full-suite.txt`; JUnit: `full-suite.xml`.

4. Compilation and whitespace checks:

   ```text
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m py_compile src\process_pores.py src\process_orientation.py tests\physics\test_structural_observables.py evidence\subagents\P01-10\measure_sensitivity.py
   git diff --check
   ```

   Both exited 0. Git emitted only the worktree's LF-to-CRLF conversion warnings. Transcript: `static-checks.txt`.

5. Declared raster sensitivity measurement:

   ```text
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe evidence\subagents\P01-10\measure_sensitivity.py
   ```

   Exit 0. Reproducer: `measure_sensitivity.py`; result: `sensitivity.json`.

## Measured fixture results

For one open bond in a 10 x 10 orthogonal cell, the periodic image-complement metric changed as follows:

| Raster | Width | Pixel area | Occupied fraction | Complement area |
|---|---:|---:|---:|---:|
| 40 x 40 | 1 px | 0.0625 | 0.010625 | 98.9375 |
| 80 x 80 | 1 px | 0.015625 | 0.00515625 | 99.484375 |
| 40 x 40 | 5 px | 0.0625 | 0.065625 | 93.4375 |

This is direct evidence that the image observable depends on resolution and brush width. It is not presented as a converged physical pore measurement. In the crossing-lines fixture, the raster is occupied at the visual intersection while the explicit bond graph remains exactly two components, `[1, 2]` and `[3, 4]`.

## Definitions under test

- Chemical connected components use persistent integer atom IDs and only declared bond endpoints. Pixel contact and geometric line intersection are ignored. Missing endpoints are errors. The result says nothing about rigidity or load-bearing connectivity.
- An image pore is a four-neighbor connected component of unoccupied pixels on the periodic raster torus. Pixel area is `cell area / pixel count`; pore area is component pixel count times pixel area.
- A rendered bond follows the exact supported 2D minimum image in an orthogonal or restricted-triclinic five-value cell, then uses a declared square pixel brush. Rows follow the second lattice coordinate and columns the first.
- Absolute glycan orientation is a 2D nematic deviation from positive hoop `+y`, with axial `x`: `atan2(-vx, vy)` folded into the inherited `[-90, +90]` representation. Relative and attachment angles remain directed angles in `[0, 180]`. Glycan and peptide vectors use the supported periodic minimum image.

## Source hashes before commit

```text
b4241f967809026b1e87352d9d6a7c120fee6030c9d7bf26a95a33b56fc5bb1f  src/process_pores.py
e71ebdef9f86128bd0949cef0a95d0610fe4d174a0193f3d12d8fc4262e63809  src/process_orientation.py
b4077158a9be37c8e21feb9931b93c27b289b2e115d2699fc5ee02aede417389  tests/physics/test_structural_observables.py
3037952446e5ab8550de58c93b7162adf6054e2a6f148ab7cc8eefde1615d0c5  evidence/subagents/P01-10/measure_sensitivity.py
4b1d75cbcf4fb686d9a3b99ae83c2fce15d093da246cffe1efd427cb067d6fe9  evidence/subagents/P01-10/sensitivity.json
```

## Limitations

- The raster metric is an image-analysis observable, not a chemical-pore ground truth, experimental calibration, or resolution-converged quantity. Anti-aliasing/subpixel coverage is not modeled.
- Only the established 2D orthogonal/restricted-triclinic five-value cell is accepted. General triclinic and native 3D cells are unsupported.
- Static rendering infers a minimum image; it does not provide P03-01's future persistent per-edge image identity. Ambiguous half-cell images inherit the minimum-image tie behavior.
- Four-neighbor pixel connectivity and a square brush are explicit conventions. Other segmentation/connectivity conventions can change pore counts.
- Legacy `.png`, `.pores`, and `.pareas` cache filenames do not encode raster settings or code provenance. Existing cached results must not be treated as fresh sensitivity evidence; the new in-memory API is the validated route in this task.
- Orientation fixtures validate code conventions and PBC behavior only. They do not validate lab-axis mapping, native 3D mechanics, physical coefficients, structural rigidity, or experimental architecture.

## Failed command handling

An evidence-inventory command included an unquoted PowerShell argument `HEAD^{tree}`. PowerShell transformed the braced expression and `git rev-parse` failed for that subcommand. It was not retried identically: `git rev-parse "HEAD^{tree}"` was run and returned the base tree hash recorded above. No repository state changed.

A later hash-formatting command tried `[System.IO.Path]::GetRelativePath`, which is unavailable in this workstation's PowerShell/.NET surface. The SHA query was rerun without that formatting helper and produced the hashes above. No repository state changed.
