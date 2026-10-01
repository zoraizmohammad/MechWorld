# P01-09 verification evidence

## Context

- Worktree: `C:\Users\mzora\MechWorld-wt-p01-09`
- Branch: `research/p01-09-analysis`
- Base: `a79a7aaf337f32dd459a00444babe2851633046d`
- Interpreter: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe` (`Python 3.11.9`)
- Test runner: `pytest 7.4.3`
- Effective author and committer: `Mohammad Zoraiz <zoraizmohammad@gmail.com>` (`git var` checked after setting repository-local identity)
- No simulator, training, scheduler, network, or private-data operation was run.

## Red regression

The first source-unmodified run of the newly added regression file was:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests/unit/test_analysis_regression.py -q --junitxml=evidence/subagents/P01-09/red.xml
```

It exited `1`: **6 failed in 9.30s**. The failures directly exposed A16, A17, and A18. See `red.txt` and `red.xml`.

## Green verification

| Check | Exit | Fresh result | Evidence |
|---|---:|---|---|
| Targeted regression | 0 | 6 passed in 7.06s | `targeted.txt`, `targeted.xml` |
| Complete suite | 0 | 68 passed in 9.56s | `full_suite.txt`, `full_suite.xml` |
| Targeted `py_compile` | 0 | no output | `py_compile.txt` |
| `git diff --check` | 0 | no whitespace errors | `diff_check.txt` |

## Dimensional derivation exercised by the regression

LAMMPS `units nano` has energy base unit

```text
1 ag nm^2/ns^2 = 1e-21 J = 1 pN nm = 1e-3 aJ.
```

For area in `nm^2`, `pe/(lx*ly)` is numerically `pN/nm`. Therefore

```text
energy_density [aJ/nm^2] = pe/(lx*ly) * 1e-3.
```

The regression uses `pe=10`, `lx=2`, `ly=5`, proving that raw density `1 pN/nm` is exported as `0.001 aJ/nm^2`. It separately checks the audited two-dimensional virial conversion `1 raw pressure = 1e-3 N/m`. Material coefficients and total-versus-incremental tension semantics were not changed.

## Final content hashes before commit

```text
acc54baf540a166e1aeb48b1d54aa6eeeb3215aa92f5a949200bbcceb96ca532  src/process_network_ensembles.py
5d0a17c6c716d7f20e00bc2726d3ae0740dcab3df86003b27f6888b8394fe748  src/process_elastic_tensor.py
90b06ea0e565247ebc0231f04ec82e271d7ba5760f9a90c2c054fb9ffe64ca60  tests/unit/test_analysis_regression.py
```

## Scope and limitations

- Raw `*.elastic_constants` records are byte-preserved. The derived `*.moduli` summary is rebuilt completely and installed atomically, so repeated processing is byte-identical rather than append-only.
- Individual trajectories must have a strictly monotonic strain axis. Descending axes are reversed; duplicates, direction changes, non-finite values, extrapolation, zero denominators, mixed units, and replicate-count mismatches raise explicit errors.
- The inherited comparison CLI has no shared persistent replicate key. It now pairs deterministic filename-sorted cohorts positionally and records `replicate_index`; callers remain responsible for supplying semantically matched cohorts. It will no longer silently mix concatenated networks.
- Historical figures are not rewritten. Regenerating an energy-density figure with the repaired function changes the legacy mislabeled numeric curve by the audited factor `1e-3`; provenance must identify the coefficient profile used by any historical data.
- `MPa*nm` is retained for inherited two-dimensional stiffness records because it is dimensionally equivalent numerically to `pN/nm`. No three-dimensional `MPa` claim is made without a reviewed thickness.
- No parameter profile, material coefficient, reference-state definition, or solver output was changed.

## Path-boundary proof

Immediately before commit, `git status --short`, `git diff --name-only`, and
`git ls-files --others --exclude-standard` listed only:

```text
src/process_elastic_tensor.py
src/process_network_ensembles.py
tests/unit/test_analysis_regression.py
evidence/subagents/P01-09/
docs/subagents/P01-09-analysis.md
```

All are within the assignment's exclusive ownership. Root ledgers, README,
contracts, dependencies, and unrelated working files are untouched.
