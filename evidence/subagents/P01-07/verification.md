# P01-07 verification evidence

Status: **subagent implementation complete; accepted by the assigned read-only
physics reviewer; pending integrator rerun and integration.** This evidence does
not accept G1 or certify biological parameters.

## Exact revision and environment

- Assigned base: `0edcf671c51e828164506ed8590f1282a18f5ce2`.
- Exact final source revision verified below:
  `a8063f5e333459eb439fc49108a4f86e3a6f336b`.
- Worktree: `C:\Users\mzora\MechWorld-wt-p01-07`.
- Interpreter: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`, Python
  3.11.9, NumPy 2.2.2.
- Real serial solver: LAMMPS `20260902` (2 Sep 2026); the standalone version
  probe and all fixture instances closed normally.
- Compute stayed bounded: one serial solver instance at a time, no production
  run, no physical-time dynamics, and every smoke command completed well below
  ten minutes.
- New commits use Mohammad Zoraiz `<zoraizmohammad@gmail.com>` as sole author
  and committer. No inherited history was rewritten.

## Red regression

The first committed run preceded implementation:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest tests\physics\test_elastic_tangent.py -q --junitxml=evidence\subagents\P01-07\red.xml
```

It exited `2` in 4.4743388 s during collection because the new immutable raw
export API did not exist (`ImportError: cannot import name
read_raw_tangent_record`). The UTF-8-normalized stdout/context and JUnit record
are `red.txt`, `red_context.txt`, and `red.xml`; the JUnit SHA-256 is
`bb5aa9d5e205f090898acba58098ae3ee96622a76b896f70503f78d1d6f8a30c`.

## Final test evidence

All contexts below name the exact final source revision `a8063f5...` and record
cwd, command, exit status, and outer wall time.

| Scope | Exact command (shared interpreter; `-B`) | Result | JUnit SHA-256 |
|---|---|---|---|
| Focused | `-m pytest tests/physics/test_elastic_tangent.py -q --junitxml=evidence/subagents/P01-07/focused.xml` | exit 0; 11 passed, 0 failed/errors/skips; pytest 1.986 s; outer 2.6939265 s | `9be2131170a18acf698738c89be41273f29ed94d014851498ddde1f7d3799b3f` |
| Compatibility | `-m pytest tests/physics/test_elastic_tangent.py tests/physics/test_energy_force_virial.py tests/physics/test_physics_profiles.py tests/unit/test_analysis_regression.py -q --junitxml=evidence/subagents/P01-07/compatibility.xml` | exit 0; 58 passed, 0 failed/errors/skips; pytest 2.704 s; outer 3.5650342 s | `2b99d241233d6bfd48b876ac97bc8c6480ee0fb13d8bd4e1f91f54a57c0dd9d2` |
| Full | `-m pytest -q --junitxml=evidence/subagents/P01-07/full.xml` | exit 0; 164 passed, 0 failed/errors/skips; pytest 5.532 s; outer 6.6160578 s | `d9f50a44cc98a9b061b6b9c5db1320969b174ffe85e9a2eeecd84cf1fc9d427d` |

The two warnings in each pytest run are intentional `DeprecationWarning`s from
the tests that explicitly opt into the inherited positive-only, default-
pressure, symmetrized forensic adapter. Its ordinary public call now fails
closed.

Targeted in-memory `compile()` of the two owned source files, the focused test,
and the convergence reproducer exited 0 in 0.101776 s. Evidence:
`compile.txt` (SHA-256
`0bc3f8e9caf967e6b276a6cc60f3780eaf06a34eb78bbd4568ca9ef7acdfccb1`).

## Numerical convergence and solver comparison

`reproduce_convergence.py` independently differentiates one current-area
harmonic-bond tension formula, multiplies it by the eight bonds in the balanced
periodic `(1,1)` winding ring, and compares that closed form with real minimized
LAMMPS central differences at `h = 1e-3, 5e-4, 2.5e-4`.

The run exited 0 in 0.4309659 s. Its machine-readable output is
`convergence.json`, SHA-256
`93fbb8b29e09db811e29dff1046cd32a6da1be906e2983ca5ed93dd4c8c26212`;
its canonical payload hash excluding the self-reporting field is
`sha256:1434d2131531253e775be37d3f250aea06bf7c891ae009011ec147174dd2c10d`.

- Frobenius errors: `5.904046840491583e-4`, `1.4760120851179542e-4`,
  `3.69002652444176e-5 pN/nm`.
- Successive ratios: `0.25000006351491927` and `0.24999975011362255`,
  consistent with second-order central convergence.
- Solver closure: 21/21 serial LAMMPS instances; version `20260902` throughout.
- All 21 fixed-cell minimizations met the convergence guard; maximum recorded
  force was `2.45563569478691e-11 pN`.
- Finest-step geometric-identity residuals were
  `-1.6336503620095755e-5`, `9.227857731275435e-6`, and
  `4.209596227155998e-6 pN/nm` for
  `C12-C21-(Nyy-Nxx)`, `C13-C31-2Nxy`, and `C23-C32`, respectively.
- Every sample records its actual `H(q)=F_inc(q)@H_base`, current area,
  `N-/N0/N+`, step/component, topology/branch, minimization state/max force,
  solver version/closure, and complete validated physics profile.

## Contract checks and corrections

- Rows are `[Nxx,Nyy,Nxy]`; columns are `[epsilon_xx,epsilon_yy,gamma_xy]`.
  `gamma_xy` is engineering simple shear in
  `F_inc=[[1+epsilon_xx,gamma_xy],[0,1+epsilon_yy]]`.
- A general sample uses an affine trial remap followed by fixed-cell,
  same-topology/same-branch nonaffine relaxation. The exactly affine balanced
  ring is a special analytical fixture, not the general state-update claim.
- `N=-W/A_current` is configurational-virial-only, native 2D `pN/nm`, and is
  explicitly labeled a current-area Cauchy-like membrane tension. The output is
  a local spatial/algorithmic tangent, not a general finite-strain material
  tensor.
- The immutable initial fixed reference and later local tangent base are stored
  separately. The record retains `H_ref/N_ref` and `H_base/N_base`, their load
  coordinates/IDs, `N_base-N_ref`, and a checked `base_is_fixed_reference`
  flag; it never silently resets the study reference at a prestrain.
- All nine raw values survive export. `C12/C21` and both directions of every
  normal-shear coupling remain independent. Asymmetry is diagnostic only and
  never replaces raw values.
- Central samples must retain profile, topology, and branch. A branch-changing
  one-sided quotient is serialized as a directional secant, never an elastic
  tangent or equilibrium modulus.
- Readback reconstructs all nine entries from persisted stencil observations,
  rejects altered cells/areas/steps/IDs/profile/minimization/closure, and rejects
  a forged raw matrix even when its asymmetry diagnostics are recomputed.
- Raw JSON uses exclusive creation and will not overwrite earlier evidence.
- Both the new solver fixture and explicit legacy-forensic adapter close on
  injected failure. The old adapter is disabled unless the caller explicitly
  sets `allow_legacy_forensic_output=True`.

## Independent review and limitations

The assigned read-only physics reviewer rejected intermediate versions for a
false minimization claim, insufficient stencil replay, unsafe legacy labeling,
fixed-reference reset ambiguity, and affine-only coordinate wording. Each was
corrected. The reviewer then returned **ACCEPT** on the final physics/schema
behavior, with the factual periodic-ring docstring correction included in the
exact verified revision above.

Limitations:

- This validates a bounded harmonic periodic ring, not a full heterogeneous PG
  network tangent and not the complete finite-strain simulation campaign.
- It does not certify the provisional profile or any biological parameter.
- A raw nonsymmetric 3x3 local derivative is not a stability proof; no
  `eigvalsh` or positive-definiteness claim is made for it.
- `task_compute_elastic_tensor.py` still calls the inherited adapter without
  forensic opt-in and therefore now fails closed until a later explicit
  migration to the validated raw engine.
- No rupture, irreversible-event physics, physical time, 3D modulus/thickness,
  production compute, experiment, public release, or G1 acceptance is claimed.

