# P01-01 periodic-identities return report

## Result

This continuation completes the requested bounded legacy geometry and atom-identity work on base `833273ea7560f4caa1d5e3d715b7c4e460c5a284`.

The change:

- explicitly rejects LAMMPS general-triclinic `abc origin` headers rather than silently treating them as orthogonal;
- explicitly rejects nonzero `xz/yz` in the 2D restricted-triclinic reader;
- wraps orthogonal and restricted-triclinic coordinates across arbitrary signed and repeated lattice offsets;
- loads optional atom `ix/iy` flags and accumulates later wrapping shifts;
- computes an exact two-dimensional nearest lattice image for non-square and skew cells;
- routes the existing glycan-orientation vector through the corrected minimum-image implementation;
- resolves atom dump columns by name, uses integer atom IDs as dictionary keys, remains invariant to row ordering, and rejects duplicate persistent atom IDs.

## Coordinate and image convention

For `H = [[Lx, xy], [0, Ly]]`, wrapping uses a lower-inclusive, upper-exclusive fractional cell. `Atom.image_shift` is an integer vector `n` satisfying:

```text
unwrapped_position = wrapped_position + H @ n
```

Each call to `correct_triclinic_PCB` or `correct_orthogonal_PCB` returns the shift applied on that call and adds it to `Atom.image_shift`. This changes the exact upper-face behavior from the legacy closed interval: a coordinate on the upper lattice face is represented on the equivalent lower face with the corresponding positive image shift.

For endpoints `i -> j`, `minimum_image_displacement_2d` returns the shortest vector and integer offset using:

```text
r_ij = x_j - x_i + H @ n_ij
```

The search does not assume componentwise fractional rounding is nearest in a skew cell. For each possible y image inside the current best-distance bound, it solves the best x image and compares Euclidean distance.

## Evidence

- Initial exact red transcript: `evidence/subagents/P01-01-identities/red-regression-exact.txt` (`9 failed, 3 passed in 4.07s`).
- Orientation-caller red transcript: `evidence/subagents/P01-01-identities/red-orientation-integration-exact.txt` (`1 failed in 7.55s`).
- Independent-review regression: `evidence/subagents/P01-01-identities/red-out-of-plane-rejection-exact.txt` (`1 failed in 7.30s`).
- Final focused suite: `15 passed in 6.00s`.
- Final inherited full suite: `26 passed in 7.96s`.
- Targeted `py_compile`: exit 0.
- Reproducible 1,000-case brute-force oracle: exit 0; every case matched.
- Independent read-only review: no remaining in-scope blocking finding after the nonzero-`xz/yz` fix; reviewer reruns were focused `15 passed`, full `26 passed`, diff check exit 0, and 20,000 randomized skew cases passed.

Exact commands, outputs, environment, and hashes are recorded in `evidence/subagents/P01-01-identities/verification.md`.

## Deferred risks and limitations

- The new minimum-image offset is inferred per call. It is not the persistent per-edge `n_ij` required by the eventual trajectory schema, and ties can change branch at an exact half-cell boundary. P03-01 must store solver/source edge image offsets rather than treating this inference as persistent identity.
- `import_bonds_from_dump` still hardcodes dump columns and treats dump-local `index` as `Bond.id`. It must not be used as the canonical persistent-edge path; stable edge identity belongs to P03-01 or a separately ledgered repair.
- Supported coordinates are legacy `x/y` with optional paired `ix/iy`. Scaled (`xs/ys`), unwrapped (`xu/yu`), and general three-dimensional triclinic coordinates remain unsupported and are not silently reinterpreted.
- Legacy visualization helpers in `process_pores.py` and the independent x/y crossing predicates remain orthogonal approximations. They were not redesigned in this task.
- No solver, simulation trajectory, private lab data, trained model, or experimental result was used or claimed.

The integrator alone owns `TASKS.json`, `handoff.md`, `README.md`, shared contracts, and release/gate state, including the synchronized README handoff update.
