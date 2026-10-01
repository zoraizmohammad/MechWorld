# P01-09 return: grouped, non-destructive analysis repair

## Assignment and result

- Task: P01-09, **Repair non-destructive grouped analysis and dimensional labels**.
- Branch/worktree: `research/p01-09-analysis` at `C:\Users\mzora\MechWorld-wt-p01-09`.
- Base: `a79a7aaf337f32dd459a00444babe2851633046d`.
- Exclusive paths respected: the two inherited analysis modules, one new regression file, `evidence/subagents/P01-09/`, and this report.
- Root `README.md`, `handoff.md`, `TASKS.json`, ownership, contracts, dependencies, and all other paths were not edited.
- This return is branch evidence for integrator review; it does not self-accept P01-09 or G1.

## Production changes

1. `combine_elastic_constant_files_into_one_file_per_network` now groups raw records by exact network basename, parses and validates them, sorts by recorded strain, rejects duplicate strains/mixed units, builds the full derived summary in a temporary file, and atomically replaces the prior summary. It never edits or deletes a raw `*.elastic_constants` file. Repeating the call produces identical bytes and a deterministic returned output list.
2. Ensemble comparison now interpolates within each independent numerator/denominator replicate pair before concatenating ratios for statistics. Input order is deterministic. Strictly descending axes are reversed. Duplicate, non-monotonic, non-finite, out-of-range, count-mismatched, or zero-denominator inputs fail explicitly rather than entering `numpy.interp` silently.
3. Elastic tables now carry a `network_id`. Values printed at a requested strain are interpolated once within each network and only then averaged, replacing interpolation on a concatenated unsorted ensemble array.
4. The legacy `energy_density` plotting field now contains the value matching its declared `aJ/nm^2` label. Explicit `energy_density_aJ_per_nm2` and raw-equivalent `energy_density_pN_per_nm` columns make the conversion inspectable.
5. Existing tension values remain in `N/m`; the regression fixes their signs and `1e-3` two-dimensional virial conversion. No coefficient, stiffness profile, prestress convention, or physical reference state changed.

## First red and final green

The first run after adding tests and before source edits exited `1` with **6 failures in 9.30s**. After the repair:

- targeted regression: **6 passed in 7.06s**, exit 0;
- complete repository suite: **68 passed in 9.56s**, exit 0;
- targeted `py_compile`: exit 0;
- `git diff --check`: exit 0.

Commands, JUnit XML, hashes, unit derivation, and exact limitations are in `evidence/subagents/P01-09/verification.md`.

## Scientific boundary and follow-up

The A16 correction follows the already audited identity `1 nano energy = 1e-3 aJ`; it is not a new parameter choice. Historical energy-density figures are not retroactively changed and need coefficient-profile provenance when regenerated. The inherited comparison API lacks a persistent cross-cohort replicate key, so deterministic positional pairing is explicit but still requires the caller to provide semantically matched cohort lists. A future data-contract task should replace this with manifest IDs.

The integrator should independently inspect the diff, rerun the targeted and full suite on the integration branch, and update `TASKS.json`, `handoff.md`, and the root `README.md` together if accepting the task, per the user's README-at-every-handoff amendment.
