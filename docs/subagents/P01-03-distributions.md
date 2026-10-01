# P01-03 isolated distribution repair

## Assignment and scope

- Worktree: `C:\Users\mzora\MechWorld-wt-p01-03`
- Branch: `research/p01-03-distributions`
- Base: `d4274c14ed0da667a9e67e50138e20363a03457a`
- Owned paths only: `src/assemble_pg_network.py`, `tests/unit/test_distributions.py`, `evidence/subagents/P01-03/`, and this report.
- Environment: Python 3.11.9, NumPy 2.2.2, SciPy 1.16.1, pytest 7.4.3, using `C:\Users\mzora\MechWorld\.venv`.

## Inherited contract recovered

Commit `0f2d7ad` and `todo.md` dated 2026-03-23 explicitly corrected the default Flory-Schulz implementation from a weight PDF to a number/molar PDF. The retained `FS` law is therefore proportional to `(1-p) p^(x-1)`. The later explicit `WFS` path remains proportional to `x (1-p)^2 p^(x-1)`. Both laws are now separately named and normalized after restriction to the requested integer interval. They were not silently interchanged.

The inherited lognormal path evaluated SciPy's lognormal PDF at each integer DSU value. This repair keeps that convention, names it `integer_grid_lognormal_pdf`, truncates it to the declared support, and normalizes the retained masses. It does not reinterpret those samples as integrated integer-bin probabilities.

## Red regression

The first test contained only the historical A05 path: parse `UNI=2=4`, then pass the result to `generate_pg_network(Ny=10, ...)`.

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests/unit/test_distributions.py -q --junitxml=evidence/subagents/P01-03/red-a05.xml
exit 1: 1 failed in 5.79s
distribution = range(2, 5)
src/assemble_pg_network.py:599: AssertionError at type(distribution) == list
```

Evidence: `evidence/subagents/P01-03/red-a05.txt` and `red-a05.xml`.

## Implementation

- Added a finite `DiscreteDistribution` carrying distinct integer support, normalized probabilities, a named law, cumulative probabilities, weighted mean/variance/raw moments, and inverse-CDF sampling.
- The retired `entries` argument remains accepted for source compatibility but is validated and never allocated. The former default request for 100,000,000 entries now stores 99 support values for DSU 2 through 100.
- Preserved the number-fraction `FS` law and separate weight-fraction `WFS` law. Uniform and inherited integer-grid lognormal paths use the same explicit abstraction.
- Added actionable validation for malformed specifications, bounds, network-size incompatibility, FS parameters, lognormal parameters, empty/invalid mass, and invalid support.
- Updated the generator's distribution mean and draws to use the weighted abstraction. Existing explicit list/tuple/range-style finite sequences remain accepted through the legacy sampling path.
- Updated `normalized_length_distribution` so compact distributions report their declared probabilities rather than treating the support as equiprobable.

## Verification

All commands ran from the assigned worktree.

| Check | Exact result | Evidence |
|---|---|---|
| `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests/unit/test_distributions.py -q --junitxml=evidence/subagents/P01-03/targeted.xml` | exit 0; 26 passed in 5.94s | `targeted.txt`, `targeted.xml` |
| `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/subagents/P01-03/full-suite.xml` | exit 0; 40 passed in 6.00s | `full-suite.txt`, `full-suite.xml` |
| `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m py_compile src/assemble_pg_network.py tests/unit/test_distributions.py` | exit 0 | `py-compile.txt` |
| Bounded representation probe | exit 0; all four laws normalized; 100,000,000 legacy entries stored as 99 support points | `distribution-contract.txt` |

The targeted suite covers the exact A05 generator path, uniform/FS/WFS/lognormal definitions, finite truncation and normalization, invalid input, legacy-list compatibility, bounded representation, normalized reporting, deterministic seeded sampling, zero-mass support handling, and first/second sample moments. Moment checks use 50,000 deterministic draws per law and a predeclared six-standard-error threshold derived separately for `X` and `X^2`.

Source and evidence hashes are recorded in `evidence/subagents/P01-03/verification-context.txt`.

## Random-stream implication

This intentionally changes exact generated networks for a fixed legacy global seed. The old code used `randrange` into a floor-rounded expanded list; the new sampler consumes one `random.random()` variate and uses the exact normalized discrete CDF. It removes expansion-size rounding bias but cannot preserve the old bit-for-bit draw stream. Explicit `random.Random` objects produce repeatable sampler sequences. Project-wide namespaced RNG injection remains P01-04 work.

## Limitations and follow-on work

- This is a bounded unit/integration repair, not scientific validation, a production simulation, a dataset, or a model result.
- Memory is proportional to the number of retained integer support points, not `entries`; there is no separate hard support-width cap. The parser requires the maximum to remain below the supplied network size.
- Generator filler/remainder glycans can make a finite network's realized strand histogram differ from the requested draw law. Achieved-network distribution reporting belongs to the later generator-metrics task; the statistical tests here validate sampler draws themselves.
- Global generator RNGs remain mixed and un-namespaced. P01-04 must define and propagate independent streams.
- Historical hyphen-delimited strings such as `FS-2-30-0.9` remain invalid; the supported syntax continues to use `=`. Auditing old submission scripts remains separate A20 work.
- Direct consumers must use `distribution.mean` for a probability-weighted mean; converting the compact object to a plain list exposes distinct support points, not an expanded weighted sample.
- The integrator must review the diff and rerun evidence after integration before deciding P01-03 task status.
