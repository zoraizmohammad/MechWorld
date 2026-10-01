# P01-07 — elastic tangent and coupling validation

## Return status

Implementation is complete on `research/p01-07-elastic-tangent` and has passed
the assigned independent physics/schema review. Integration and gate decisions
remain with the root integrator; this report does not accept G1.

Implementation commits verified by the final evidence are:

- `21f9334f7abf85005397457eec91344aed17b53c` — define the first failing
  regression contract;
- `d0957c51ca98b7f5346853a3b0da814aaab7a338` — implement and validate the
  raw tangent contract;
- `a8063f5e333459eb439fc49108a4f86e3a6f336b` — correct the periodic-ring
  fixture documentation before the exact final reruns.

Every commit has sole author and committer Mohammad Zoraiz
`<zoraizmohammad@gmail.com>`.

## Implemented result

`src/run_lammps_elastic_tensor.py` now defines a strict local 2D tangent API.
The serialized convention is:

- `q=[epsilon_xx,epsilon_yy,gamma_xy]`, with engineering shear;
- `F_inc=[[1+epsilon_xx,gamma_xy],[0,1+epsilon_yy]]` and
  `H(q)=F_inc@H_base`;
- affine coordinate trial followed by fixed-cell nonaffine minimization on the
  same topology/branch;
- rows `[Nxx,Nyy,Nxy]`, columns `[epsilon_xx,epsilon_yy,gamma_xy]`;
- `N=-W/A_current`, configurational virial only, in native `pN/nm`;
- x is axial and y is hoop; the loading coordinate is quasi-static, not time.

The quantity is explicitly a current-area Cauchy-like local
spatial/algorithmic tangent. It is not silently promoted to a general
finite-strain material tensor or a 3D modulus.

The immutable initial fixed-cell reference and local tangent base are separate
objects in every artifact. `H_ref/N_ref` do not reset at later prestrains;
`H_base/N_base`, both global load coordinates, `N_base-N_ref`, and
`base_is_fixed_reference` are retained.

Smooth fixed-topology central differences keep all nine raw entries. Separate
asymmetry diagnostics report, but never replace, `C12/C21` and the two
directions of all normal-shear couplings. Branch-changing one-sided quotients
are labeled directional secants and carry no elastic-tangent/equilibrium-
modulus claim.

`src/process_elastic_tensor.py` adds immutable raw JSON creation and fail-closed
readback. Existing legacy aggregation remains available. The inherited direct
elastic solver route is now explicitly forensic: it is positive-only, uses the
historical default pressure, symmetrizes output, warns when opted into, and
fails closed by default. Both success and injected-failure paths close the
solver.

## Real solver fixture

The solver comparison uses an oblique, prestressed eight-bond periodic harmonic
ring winding once through each cell vector. Equal and opposite neighboring
forces make every atom a true fixed-cell equilibrium under the supported
incremental deformation. Each of seven states per step (base and +/- for three
columns) runs a real serial LAMMPS 20260902 minimization, records its current
cell/area/tension/max force, and closes.

An independent closed-form derivative includes the current-area geometric term.
For steps `1e-3`, `5e-4`, and `2.5e-4`, the Frobenius errors are
`5.904046840491583e-4`, `1.4760120851179542e-4`, and
`3.69002652444176e-5 pN/nm`; successive ratios are essentially 0.25. All 21
instances closed, and the maximum final force was
`2.45563569478691e-11 pN`.

## Verification summary

- First red run: exit 2 at collection because raw tangent export/readback did
  not exist.
- Exact final focused run: 11 passed, no failures/errors/skips.
- Exact final compatibility run: 58 passed, no failures/errors/skips.
- Exact final full run: 164 passed, no failures/errors/skips.
- Four-file in-memory compilation: exit 0.
- Read-only physics/schema review: ACCEPT after all requested corrections.

Exact commands, runtimes, JUnit/output hashes, convergence matrices, profile
identity, cells/areas, forces, and closure records are in
`evidence/subagents/P01-07/verification.md` and `convergence.json`.

## Boundaries and follow-up

- The fixture is a bounded harmonic ring, not a full heterogeneous PG network
  tangent or biological-parameter validation.
- The raw nonsymmetric 3x3 derivative is not a stability certificate; do not
  apply symmetric-matrix eigenvalue tests to it as though it were one.
- `task_compute_elastic_tensor.py` now fails closed at its old call until a
  later task migrates it to the validated raw engine or explicitly requests
  labeled forensic reproduction.
- No rupture, physical time, effective thickness/3D modulus, production run,
  experimental validation, public release, or gate acceptance is claimed.
