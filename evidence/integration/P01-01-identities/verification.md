# P01-01 periodic-identity integration verification

## Integrated change

- Reviewed source commit: `84dad0b460c97ebbb5dac07121ca161c830c145b`
- Integrated on `main` as: `71a5700`
- Runtime: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe` (Python 3.11.9)
- Scope: local CPU unit tests and deterministic oracle only; no solver campaign, model training, private data, or external publication

The integrated implementation explicitly rejects unsupported general-triclinic and nonzero out-of-plane restricted-triclinic dumps, wraps arbitrary signed lattice offsets with integer image accounting, computes the exact 2D restricted-triclinic minimum image, preserves persistent atom IDs across column/row reordering, and routes legacy glycan orientation through the corrected geometry helper.

## Main-tree verification

Focused regression command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv\Scripts\python.exe -m pytest -q tests/unit/test_periodic_geometry.py --junitxml=evidence/integration/P01-01-identities/targeted.xml
```

Result: exit 0, `15 passed in 6.18s`.

Complete merged suite command:

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/integration/P01-01-identities/full_suite.xml
```

Result: exit 0, `62 passed in 9.35s`.

Targeted compilation:

```powershell
.venv\Scripts\python.exe -m py_compile src/import_data_from_dumps.py src/lammps_PG_objects.py tests/unit/test_periodic_geometry.py
```

Result: exit 0 with no output.

Deterministic brute-force oracle:

```powershell
.venv\Scripts\python.exe evidence/subagents/P01-01-identities/minimum_image_oracle.py
```

Result: exit 0, `1000 randomized restricted-triclinic minimum-image cases matched brute force`.

`git diff --check` also exited 0.

## SHA-256 after integration

- `src/import_data_from_dumps.py`: `7CF204CCC0C77E83932AE67C84EE54B28F7982266FE99A7B1DBE1FA9F85560F5`
- `src/lammps_PG_objects.py`: `74EA10F70D545CE4745E3DA2F44E3E341BF136AE68D847969864470EA506DB0E`
- `tests/unit/test_periodic_geometry.py`: `C3424046F4125AC7A700979B6A84665D1E734B5382C4C34CD525227FA3F32D58`
- `targeted.xml`: `7914DC23AD1AF2ACFDFE14481D264AE8D172ED9939A98FB7FEFEBC49BB77C764`
- `full_suite.xml`: `BD7D3B9E7A49EB191EAD99B3DC99FBD86A603D9C87DC0D71B54CB5492DB4DD78`

## Explicit limitations and follow-up ownership

- Minimum-image offsets are inferred per call; canonical, persistent per-edge image offsets remain part of P03-01's trajectory schema.
- `import_bonds_from_dump` still uses its legacy local indexing and is not accepted as the canonical stable-edge path.
- Scaled/unwrapped coordinate columns and general 3D triclinic boxes are rejected or unsupported, not silently reinterpreted.
- Legacy visualization-only crossing helpers remain outside this repair.

