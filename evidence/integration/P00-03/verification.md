# P00-03 integration verification

- CWD: `C:/Users/mzora/MechWorld`
- Integrated source revision: `4faeab167192476eedb08f60140ec5b6ff13eec7`
- Interpreter: `C:/Users/mzora/MechWorld/.venv/Scripts/python.exe` (Python 3.11.9)
- `tools/doctor.py` blob: `163f85cc8492c0d2820abf72b681af3c3ccac502`
- `tests/integration/test_lammps_smoke.py` blob: `4b83b9e3b26cbf7f8d1b457ec5845eec4fae0dcc`

Commands and results:

1. `.venv/Scripts/python.exe tools/doctor.py --output evidence/integration/P00-03/doctor.json` → exit 0. The identical stdout is `doctor_stdout.json`; `ok=true`, LAMMPS 20260902, serial/no MPI, all four required styles present, 3 atoms/2 bonds/1 angle, analytical component-energy checks passed, solver closed, no errors.
2. `.venv/Scripts/python.exe -m pytest tests/integration/test_lammps_smoke.py -q --junitxml=evidence/integration/P00-03/targeted.xml` → exit 0; 2 passed in 1.60s, no skips.
3. `.venv/Scripts/python.exe -m pytest -q --junitxml=evidence/integration/P00-03/full_suite.xml` → exit 0; 14 passed in 8.41s.
4. `.venv/Scripts/python.exe -m py_compile tools/doctor.py tests/integration/test_lammps_smoke.py` → exit 0.

`fix bond/break` was configured and removed without a dynamics step. This is not fracture evidence. No PG minimization, MPI/GPU run, production job, model, or experiment was performed.
