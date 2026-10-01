# P01-09 grouped-analysis integration verification

## Integrated change

- Reviewed branch commits: `7a9aca46a82c7d4352b8da504dfcb504816ee7ad` and `be71501aca3be541520ea485d1177fc1db15cf73`
- Integrated on `main` as: `6df2a91` and `717f678`
- Runtime: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe` (Python 3.11.9)
- Scope: local CPU analysis tests only; no solver run, private data, model training, or external action

The reviewed repair rebuilds derived moduli atomically and deterministically while preserving raw elastic-constant records byte-for-byte. It validates strains and units, interpolates within each independent network/replicate rather than across concatenated ensembles, reverses strictly descending axes, rejects ambiguous axes/extrapolation/zero denominators, and corrects the audited energy-density conversion without changing material coefficients.

## Main-tree verification

Focused command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv\Scripts\python.exe -m pytest -q tests/unit/test_analysis_regression.py --junitxml=evidence/integration/P01-09/targeted.xml
```

Result: exit 0, `6 passed in 5.76s`.

Complete merged suite:

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/integration/P01-09/full_suite.xml
```

Result: exit 0, `68 passed in 9.80s`.

Targeted compilation:

```powershell
.venv\Scripts\python.exe -m py_compile src/process_network_ensembles.py src/process_elastic_tensor.py tests/unit/test_analysis_regression.py
```

Result: exit 0 with no output. `git diff --check` also exited 0.

## Dimensional check

For LAMMPS `units nano`, `1 ag nm^2/ns^2 = 1e-21 J = 1 pN nm = 1e-3 aJ`. Therefore a raw `pe/(lx*ly)` value has units `pN/nm` and its numeric value must be multiplied by `1e-3` for the declared `aJ/nm^2` output. The regression separately preserves the audited `1e-3 N/m` conversion for a raw two-dimensional virial-pressure unit.

## SHA-256 after integration

- `src/process_network_ensembles.py`: `9E16F398A300C0C10418EDA6E5B2F15EE701334A2F51C5601DBB8E148178DF86`
- `src/process_elastic_tensor.py`: `3805A08E5F4735A7F79E233FE73D7041C56B26A211FB5E0641D26C586B1B8622`
- `tests/unit/test_analysis_regression.py`: `DA36835A649C97620A3B427C7BD030F547AE53297EF4ECF5C6DED30163441D79`
- `targeted.xml`: `B31DFC7D0EEC53FCEE087A8D3CB6D92F7C5B1FFF69542CFC19F22A2ABD66DE89`
- `full_suite.xml`: `D05189270AE3497AAC5A1B4083CBEFD1018200076C7FCBF77C311DEBC549404B`

## Limitation carried forward

The inherited comparison API has no persistent cross-cohort replicate identifier. Deterministically sorted cohorts are therefore paired positionally and count mismatches are rejected. Callers must supply semantically matched cohorts until a later manifest/data-contract task provides stable replicate IDs.
