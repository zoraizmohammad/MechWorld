# P01-10 integration verification

Integration revision before the evidence/state commit: `916c5a7` on `main`. The returned commit was reviewed for path ownership and retained sole authorship and committer identity by Mohammad Zoraiz <zoraizmohammad@gmail.com>.

| Check | Exact command | Exit | Measured result | Artifact / SHA-256 |
|---|---|---:|---|---|
| Focused acceptance | `.venv\Scripts\python.exe -m pytest tests\physics\test_structural_observables.py -q --junitxml=evidence\integration\P01-10\focused.xml` | 0 | 19 passed in 3.09s | `focused.xml`; `933ccdc685aee7b40c085897ab22b152524065860a3c8e92b34f2d4ec15dafdd` |
| Periodic/generator/orientation compatibility | `.venv\Scripts\python.exe -m pytest tests\unit\test_periodic_geometry.py tests\unit\test_generator_reproducibility.py test\test_glycan_orientation.py -q --junitxml=evidence\integration\P01-10\compatibility.xml` | 0 | 33 passed in 4.23s | `compatibility.xml`; `a459a50abc39e2cd4a7abaa4c16151bac30e63584c4f854376921f1a36e312a6` |
| Full merged suite | `.venv\Scripts\python.exe -m pytest -q --junitxml=evidence\integration\P01-10\full.xml` | 0 | 112 passed in 6.22s | `full.xml`; `426e49172adc75948a521b799cf98c2682fd3611c6946b897dcff3fc4f7d317a` |
| Compilation | `.venv\Scripts\python.exe -m py_compile src\process_pores.py src\process_orientation.py tests\physics\test_structural_observables.py evidence\subagents\P01-10\measure_sensitivity.py` | 0 | all targets compiled | console result |
| Whitespace/conflict check | `git diff --check` | 0 | no errors | console result |
| Declared raster sensitivity | `.venv\Scripts\python.exe evidence\subagents\P01-10\measure_sensitivity.py` | 0 | reproduced subagent values and crossing components | console result and `evidence/subagents/P01-10/sensitivity.json` |

For the same one-bond 10 x 10 fixture, occupied fractions were `0.010625` at 40 x 40/1 px, `0.00515625` at 80 x 80/1 px, and `0.065625` at 40 x 40/5 px; complement areas were `98.9375`, `99.484375`, and `93.4375`. At the visual crossing, the declared bond graph remained exactly `{1,2}` and `{3,4}`. This demonstrates raster-setting sensitivity and topology separation; it is not a convergence result.

The original exact red evidence is preserved in `evidence/subagents/P01-10/red-regression.txt` (grayscale failure) and `follow-up-red-pixel-scale.txt` (row/column scale defect). Accepted definitions are restricted to 2D orthogonal/restricted-triclinic cells, four-neighbor periodic image-complement components, a declared square pixel brush, and bond-table-only chemical connectivity.

These tests do not establish molecular pore ground truth, resolution convergence, rigidity, load-bearing connectivity, persistent per-edge images, native 3D mechanics, physical parameter validity, or experimental agreement. Legacy cache filenames still omit raster/provenance settings and must not be treated as fresh sensitivity evidence.
