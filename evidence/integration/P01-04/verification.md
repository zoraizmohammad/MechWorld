# P01-04 integration verification

Integration revision before the evidence/state commit: `1f90577` on `main`. The returned commit was path-reviewed before integration and retained sole authorship by Mohammad Zoraiz <zoraizmohammad@gmail.com>.

| Check | Exact command | Exit | Measured result | Artifact / SHA-256 |
|---|---|---:|---|---|
| Focused acceptance | `.venv\Scripts\python.exe -m pytest tests\unit\test_generator_reproducibility.py -q --junitxml=evidence\integration\P01-04\targeted.xml` | 0 | 14 passed in 8.45s | `targeted.xml`; `efe805aa6c067f804b156e2a78d41d6d9a85d85024fe2c8ffe48cec3b89bd827` |
| Distribution/orientation/periodic compatibility | `.venv\Scripts\python.exe -m pytest tests\unit\test_distributions.py test\test_glycan_orientation.py tests\unit\test_periodic_geometry.py -q --junitxml=evidence\integration\P01-04\compatibility.xml` | 0 | 45 passed in 8.83s | `compatibility.xml`; `3b201fc943bf888d586c1cce7f2dd3519b92f868aa1542b19f7813f7cad01071` |
| Full merged suite | `.venv\Scripts\python.exe -m pytest -q --junitxml=evidence\integration\P01-04\full.xml` | 0 | 93 passed in 12.27s | `full.xml`; `23b1d8376ce61b4025dc5c22019aac2765d8e972f01463c8ee1014bbbf2de682` |
| Compilation | `.venv\Scripts\python.exe -m py_compile src\assemble_pg_network.py src\lammps_PG_objects.py tests\unit\test_generator_reproducibility.py` | 0 | all targets compiled | console result |
| Whitespace/conflict check | `git diff --check` | 0 | no errors | console result |
| Real LAMMPS reader | `.venv\Scripts\python.exe evidence\subagents\P01-04\lammps_read_data_probe.py` | 0 | LAMMPS 20260902 loaded 108/108 atoms; 324 coordinate tokens; max/RMS error 0; solver closed | deterministic graph `c345367c3ceb3bf282679f55549c00d220780dd82dcb91ac1d2c148ba1c7814c` |

The original red evidence remains at `evidence/subagents/P01-04/red-pytest.xml`: nine tests failed before the implementation. The implementation provides independently derived integer seeds for geometry, material disorder, events, and model training; only the geometry stream and an injectable material Bernoulli source are consumed by this task. It reports achieved, not requested, network metrics and preserves tested binary64 coordinates with 17-significant-digit text output.

This accepts deterministic generator and serialization behavior only. It does not validate physical coefficients, material fields, rupture events, native 3D mechanics, solver relaxation, model training, experimental agreement, or production use. Historical two-decimal exports are not repaired. Exact streams can intentionally differ from inherited mixed global RNG behavior.
