# Task and edit ownership

The integrator owns `README.md`, `AGENTS.md`, `handoff.md`, `TASKS.json`, shared contracts, root dependency files, integration commits, and gate decisions. Every handoff update includes a matching README status/task refresh. Editing subagents receive dedicated Git branches/worktrees and non-overlapping paths. A worktree separates Git files; it does not authorize shared output directories, production compute, remote publication, or private-data access.

## Initial wave

All initial assignments use base `c0ec8aa7ed99ecf8cb21f0a9bf8223447743fc39`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Geometry/data | `research/p01-01-periodic-bounds`; `C:/Users/mzora/MechWorld-wt-p01-01` | P01-01: reproduce A01/A02 with regression tests and make the smallest legacy-compatible dump parser repair | `src/import_data_from_dumps.py`, `tests/unit/test_periodic_geometry.py`, `evidence/subagents/P01-01/`, `docs/subagents/P01-01-parser.md` | No ledger/shared-contract edits; parser slice does not claim all periodic-identity work complete |
| Environment/simulation | `research/p00-03-environment`; `C:/Users/mzora/MechWorld-wt-p00-03` | P00-03: create a repeatable doctor and actual LAMMPS smoke integration test | `tools/doctor.py`, `tests/integration/test_lammps_smoke.py`, `evidence/subagents/P00-03/`, `docs/subagents/P00-03-environment.md` | No dependency, ledger, environment-summary, or physics-source edits |
| Physics reviewer | `research/p01-05-physics-audit`; `C:/Users/mzora/MechWorld-wt-p01-05-audit` | P01-05 supporting read-only audit of coefficients, units, and LAMMPS conventions | `docs/subagents/P01-05-physics-audit.md` only; inherited source/specifications are read-only | No source edits and no self-approval of lab-dependent parameter values |

Editing worktrees were verified with `git worktree list --porcelain` before delegation. Native subagents were launched for all three assignments; their branch commits require integrator diff review and rerun before integration.

Integration state: the parser commit was reviewed and integrated as `912c9cc`; its integration rerun passed 3 targeted and 12 total tests. The environment commit was reviewed and integrated as `4faeab1`; its doctor exited 0 and integration rerun passed 2 targeted and 14 total tests. The physics audit was path-reviewed and integrated as `59ecfdc`; it remains evidence supporting a human-reviewed task, not a self-approved parameter decision. Generated untracked bytecode in isolated worktrees was neither committed nor treated as user source.

Exact branch, worktree, base revision, commands, runtime limit, and return-report path are recorded when each assignment is launched. The main checkout is the integration worktree. Subagent reports are evidence inputs, not automatic task acceptance.

## Second wave

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Distribution/data | `research/p01-03-distributions`; `C:/Users/mzora/MechWorld-wt-p01-03` | P01-03: first capture A05 in an exact red regression, then replace expanded legacy arrays with a bounded discrete sampler while preserving and documenting number- versus weight-fraction semantics | `src/assemble_pg_network.py`, `tests/unit/test_distributions.py`, `evidence/subagents/P01-03/`, `docs/subagents/P01-03-distributions.md` | No ledger, README, shared-contract, or unrelated source edits; no task-completion or scientific-validation claim |
| Periodic identities/data | `research/p01-01-periodic-identities`; `C:/Users/mzora/MechWorld-wt-p01-01-identities` | P01-01 remaining slice: reject unsupported general-triclinic dumps explicitly and verify repeated/large-offset wrapping, image shifts, minimum image, and persistent atom identity | `src/import_data_from_dumps.py`, `src/lammps_PG_objects.py`, `tests/unit/test_periodic_geometry.py`, `evidence/subagents/P01-01-identities/`, `docs/subagents/P01-01-identities.md` | Build on the integrated parser slice; no ledger/README/shared-contract edits and no unrelated geometry redesign |
| Run isolation/simulation | `research/p01-08-run-isolation`; `C:/Users/mzora/MechWorld-wt-p01-08` | P01-08: implement typed local run configuration/manager, unique directories, failure-safe solver lifecycle, and bounded concurrency/isolation tests | `src/pgworld/simulation/run_manager.py`, `configs/compute/`, `tests/integration/test_run_isolation.py`, `evidence/subagents/P01-08/`, `docs/subagents/P01-08-run-isolation.md` | No production jobs, scheduler submission, inherited account paths, ledger/README/shared-contract/dependency edits, or unrelated runner refactor |
| Related work/research | `research/p10-01-related-work`; `C:/Users/mzora/MechWorld-wt-p10-01` | P10-01: current primary-source search and matrix across learned simulators, fracture/damage/topology, stochastic hybrid models, and PG mechanics; constrain contribution claims to evidence | `docs/related_work.md`, `paper/references.bib`, `tools/check_references.py`, `tests/unit/test_references.py`, `evidence/subagents/P10-01/`, `docs/subagents/P10-01-related-work.md` | No manuscript claims beyond evidence, no fabricated exhaustive/priority claim, no ledger/README/shared-source/dependency edits, and no paywalled/private data access |

The distribution assignment uses base `d4274c14ed0da667a9e67e50138e20363a03457a`; the periodic-identity and run-isolation assignments use base `833273ea7560f4caa1d5e3d715b7c4e460c5a284`; the related-work assignment uses base `a2805a61305aae0e3fc1b8ab0fb737759ca36cd1`. They may run only bounded unit/integration/research work and must return exact commands, limitations, and sole-author commits for integrator review.

Integration state: the P01-03 distribution return was path-reviewed and integrated as `eef253f`. Independent integration verification passed 26 focused tests and 40 total tests, plus `py_compile` and the historical five-case diagnostic. P01-04 is now dependency-eligible but shares `src/lammps_PG_objects.py` with the active P01-01 identity worktree, so no overlapping edit assignment is launched until that ownership clears.

The P01-08 run-isolation return was path-reviewed and integrated as `9429b4c`. Independent integration verification passed 10 focused lifecycle tests and 50 total tests. A real serial LAMMPS one-atom `run 0` then completed through the manager with an accepted lifecycle record and successful close; this is adapter compatibility evidence, not restart, fracture, MPI, scheduler, or production validation.

The remaining P01-01 periodic-identity return was path-reviewed and integrated as `71a5700`. Independent main-tree verification passed 15 focused tests and 62 total tests, targeted compilation, and a 1,000-case exact minimum-image oracle. Its ownership is cleared. Canonical persistent edge/image identity remains deferred to the P03-01 schema rather than inferred from per-frame geometry.

## Third wave

Both assignments use accepted main revision `a79a7aaf337f32dd459a00444babe2851633046d` and have disjoint source/test/evidence paths.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Generator reproducibility/data | `research/p01-04-reproducibility`; `C:/Users/mzora/MechWorld-wt-p01-04` | P01-04: exact red-first named RNG independence, same-seed graph reproducibility, achieved-network metrics, and measured precise-export round trip | `src/assemble_pg_network.py`, `src/lammps_PG_objects.py`, `tests/unit/test_generator_reproducibility.py`, `evidence/subagents/P01-04/`, `docs/subagents/P01-04-reproducibility.md` | No ledger/README/shared-contract/dependency edits, no unapproved parameter selection, no production simulation, and no changes outside owned paths |
| Analysis regression/evaluation | `research/p01-09-analysis`; `C:/Users/mzora/MechWorld-wt-p01-09` | P01-09: exact red-first non-destructive/idempotent grouping, per-network monotonic interpolation, and A16 dimensional conversion/label repair | `src/process_network_ensembles.py`, `src/process_elastic_tensor.py`, `tests/unit/test_analysis_regression.py`, `evidence/subagents/P01-09/`, `docs/subagents/P01-09-analysis.md` | No ledger/README/shared-contract/dependency edits, no material-parameter changes, no deletion/overwrite of raw evidence, and no unrelated plotting redesign |

Each return requires a sole-author Mohammad Zoraiz commit, exact commands and results, limitations, path-boundary proof, and integrator review plus rerun before acceptance.

Integration state: the P01-09 analysis return was path-reviewed and integrated as `6df2a91` and `717f678`. Independent main-tree verification passed 6 focused tests and 68 total tests plus targeted compilation and diff checking. Its ownership is cleared. The lack of persistent cross-cohort replicate IDs remains an explicit later manifest/data-contract limitation rather than being hidden by positional pairing.

Integration state: the P10-01 audit and review expansion were path-reviewed and integrated as `8dfdfef` and `08cf163`. Independent main-tree verification accepted 29 bibliography/citation pairs, passed 11 focused tests and 79 total tests, and spot-checked eight decisive/current DOI records plus the key changing-graph full-text claim. Its ownership is cleared; the search-refresh and independent manuscript-claim review remain later release obligations.

Integration state: the P01-04 reproducibility return was path-reviewed and integrated as `1f90577`. Independent main-tree verification passed 14 focused tests, 45 compatibility tests, and 93 total tests plus targeted compilation and diff checking. Real LAMMPS 20260902 loaded 108/108 atoms from the deterministic fixture, preserved all 324 emitted coordinate tokens with zero measured max/RMS error, and closed. Its ownership is cleared. This is generator/serialization evidence, not approval of physics parameters, rupture behavior, training, or production use.

## Fourth wave

The assignment uses accepted main revision `9280b5d1486496b705e0c178c43da7a488568c67`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Structural observables/physics | `research/p01-10-observables`; `C:/Users/mzora/MechWorld-wt-p01-10` | P01-10: exact red-first validation of pore, 2D orientation, and chemical-connectivity observables on known structures, including PBC, rendering resolution/line width, periodic seams, and visually crossing unbonded lines | `src/process_pores.py`, `src/process_orientation.py`, `tests/physics/test_structural_observables.py`, `evidence/subagents/P01-10/`, `docs/subagents/P01-10-observables.md` | No ledger/README/shared-contract/dependency edits, no physics-parameter approval, no production solver work, no invention of chemical crosslinks from rendered crossings, and no edits outside owned paths |

The return requires a sole-author Mohammad Zoraiz commit, exact commands/results/limitations, path-boundary proof, and integrator review plus rerun before acceptance.

Integration state: the P01-10 return was path-reviewed and integrated as `916c5a7`. Independent main-tree verification passed 19 focused tests, 33 compatibility tests, and 112 total tests plus targeted compilation, diff checking, and the declared sensitivity reproducer. Chemical connectivity is derived only from explicit bonds; raster pores remain setting-dependent image observables. Its ownership is cleared. No further agent task is dependency-eligible until the recorded P00-06/P01-05 human decisions unblock P01-06.

Decision reconciliation state: two read-only subagents independently reviewed the 2026-10-01 human decisions. They made no file changes. Both supported closing P00-06 as governance, adding a mandatory provisional computational-contract slice P01-05A, retaining P01-05 as blocked final biological certification, and allowing bounded numerical validation to continue under explicit profile hashes and fail-closed status flags.

## Fifth wave

The assignment uses accepted main revision `78da30ffd8b374125a34edaacc71ae7650b8f722`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Provisional physics contract/physics | `research/p01-05a-computational-contract`; `C:/Users/mzora/MechWorld-wt-p01-05a` | P01-05A: exact red-first immutable route-specific legacy profiles and a fail-closed provisional reviewed profile with expanded identity/hash and mixed-profile rejection | `docs/physics_parameters.md`, `configs/physics/`, `src/pgworld/config/physics_profiles.py`, `tests/physics/test_physics_profiles.py`, `evidence/subagents/P01-05A/`, `docs/subagents/P01-05A-computational-contract.md` | No ledger/README/shared-contract/dependency edits; no final biological certification, parameter retuning, source-constant migration, solver run, production compute, or changes outside owned paths |

The return requires a sole-author Mohammad Zoraiz commit, exact red/green commands/results/limitations, path-boundary proof, and integrator review plus rerun before acceptance.

Integration state: the initial P01-05A return was integrated for review as
`3e734f3` and `7bc36e6` but was not accepted until adversarial review found and
closed two contract defects: historical default-pressure/NVE behavior had been
conflated with the required new virial-only output policy, and a forged expanded
snapshot could retain a registered compact ID/hash. Corrections `08b8a11` and
`c41c58a` add strict persisted-snapshot validation, separate historical/new
policy fields, explicit unknown range/fit provenance, installed-release-pinned
LAMMPS sources, and bidirectional source coverage for every legacy entry point.
Final independent review accepted the return. Main verification passed 15
focused, 33 compatibility, and 127 total tests plus strict load/read-back,
forgery rejection, compilation, diff, ownership, and identity checks. Ownership
is cleared; P01-05 remains human-review blocked and P01-06 is eligible.

## Sixth wave

The assignment uses accepted main revision
`5243771fa97927beafe49dd66cea4c2bec07bb5c`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Energy/force/virial oracle/physics | `research/p01-06-energy-force-virial`; `C:/Users/mzora/MechWorld-wt-p01-06` | P01-06: exact red-first independent analytical, finite-difference, and real serial LAMMPS checks for bond/angle energy, force, configurational virial, 2D tension normalization/sign, and fixed-reference total/incremental reporting | `src/pgworld/physics/`, `tests/physics/test_energy_force_virial.py`, `evidence/subagents/P01-06/`, `docs/subagents/P01-06-energy-force-virial.md` | No profile/config/ledger/README edits; no parameter retuning, rupture implementation, runner migration, production simulation, biological certification, or changes outside owned paths |

The return requires the exact red regression before implementation, sole-author
Mohammad commits, real LAMMPS version/close evidence, explicit tolerances and
units, singular/degenerate-input rejection, path-boundary proof, and limitations.
The integrator must independently review and rerun the branch before acceptance.

Integration state: the three P01-06 return commits were path- and
identity-reviewed and integrated as `05ef3fc`, `56eec8b`, and `709933f`.
The first pass was not accepted until mass/kinetic-pressure provenance and
minimum-image nonlinear-domain validation were corrected. Independent
main-tree verification passed 26 focused, 56 compatibility, and 153 total
tests, targeted compilation, a 10,000-case minimum-image comparison, and the
real-LAMMPS report assertions. All LAMMPS 20260902 instances closed. Ownership
is cleared; P01-07 is eligible.

## Seventh wave

The assignment uses accepted main revision
`0edcf671c51e828164506ed8590f1282a18f5ce2`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Elastic tangent/physics | `research/p01-07-elastic-tangent`; `C:/Users/mzora/MechWorld-wt-p01-07` | P01-07: exact red-first validation of smooth fixed-topology tangents, perturbation-size convergence, explicit strain/stress/shear conventions, unsymmetrized normal-shear coupling, and distinctly labeled one-sided irreversible diagnostics | `src/run_lammps_elastic_tensor.py`, `src/process_elastic_tensor.py`, `tests/physics/test_elastic_tangent.py`, `evidence/subagents/P01-07/`, `docs/subagents/P01-07-elastic-tangent.md` | No ledger/README/profile/P01-06-oracle edits; no parameter retuning, rupture implementation, production simulation, biological certification, or changes outside owned paths |

The return requires exact red and green commands, perturbation-convergence and
raw-export evidence, sole-author Mohammad commits, explicit units/conventions,
path-boundary proof, and limitations. The integrator must independently review
and rerun the branch before acceptance.

Integration state: the five P01-07 return commits were path- and
identity-reviewed and integrated as `5990e09`, `8adf0de`, `b1c8fff`, `60cfa09`,
and `b265c9e`. Intermediate designs were rejected until minimization truth,
strict persisted-stencil replay, legacy fail-closed behavior, immutable fixed
reference versus local base separation, and nonaffine-relaxation wording were
correct. Independent main verification passed 11 focused, 58 compatibility,
and 164 total tests, four-file compilation, and the convergence reproducer;
21/21 real LAMMPS instances closed. Ownership is cleared; P01-11 is eligible.

## Eighth wave

The assignment uses accepted main revision
`a0d625994d593c236195dda2734c62111d201ea1`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Package and G1 candidate/integration | `research/p01-11-package-g1`; `C:/Users/mzora/MechWorld-wt-p01-11` | P01-11: build and verify the installable package, bundled immutable profiles, `pgworld doctor`, Python 3.11 compatibility, explicit legacy-wrapper migration, clean isolated real-LAMMPS smoke, and candidate G1 evidence | Exact expanded list in `TASKS.json`: packaging/lock files; package CLI/doctor/profile resources; doctor wrapper; seven syntax-repair files; elastic task wrapper; tests; migration/candidate/evidence/report paths | No root ledger/README edit, no final `reports/gates/G1.json`, no parameter changes, no production sweep, no public release, no private data, and no edits outside assigned paths |

The return requires red-first packaging/compatibility tests, a clean source build
with no retained build products, an isolated installed-environment doctor and
analytical/real-LAMMPS fixtures outside the checkout, exact wheel/config hashes,
dependency and external-LAMMPS limitations, sole-author Mohammad commits, and
path/identity proof. The implementation agent may prepare only
`G1.candidate.json`; the integrator independently reruns, reviews, and owns the
final gate decision.

Integration state: the P01-11 return and its cross-platform correction were
path- and identity-reviewed and integrated as `2143d6c`, `f819c25`, `7e6295a`,
`f3746f4`, and `adf9d7d`. Independent main verification first reproduced and
then closed one Windows CRLF-versus-LF test-assertion defect. Final main runs
passed 7 focused, 173 total, and one separate isolated-wheel test; all 80
tracked Python files compiled, the fresh exact-lock venv passed `pip check`,
and installed P01-06/P01-07 real-LAMMPS checks passed with complete solver
closure. The integrator accepted G1 in `reports/gates/G1.json`. P01-11 edit
ownership is cleared; no agent owns root ledgers or gate state.

## Ninth wave

The assignment uses accepted and pushed main revision
`94c175a3c455e1cccecb82ba7bc219494950f7cb`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Loading/control protocols/simulation | `research/p02-01-loading-controls`; `C:/Users/mzora/MechWorld-wt-p02-01` | P02-01: exact red-first quasi-static isotropic, axial, hoop, unequal-biaxial, shear, cyclic/unloading, pressure-derived, and stable-ID local-intervention controls with coordinate-covariance and locality checks | `src/pgworld/simulation/controls.py`, `src/pgworld/simulation/__init__.py`, `configs/loads/`, `tests/physics/test_loading.py`, `tests/release/test_wheel_install.py`, `evidence/subagents/P02-01/`, `docs/subagents/P02-01-loading-controls.md` | No root ledger/README/shared-schema/profile/solver-oracle edits; release-test edit is limited to the exact new module member/import while all exclusions remain strict; no rupture-law implementation, shared bond-type weakening, physical-time claim, production simulation, gate decision, public release, private data, or changes outside owned paths |

The return requires exact red/green commands, stable units/axes/loading
coordinates, tensor transformation fixtures, pressure-shell assumption labels,
prescribed-intervention semantics distinct from material rupture, per-physical-
interaction locality proof, sole-author Mohammad commits, path/identity proof,
and explicit limitations. The integrator independently reviews and reruns the
return before acceptance.

Scope expansion record: the focused control contract passed 27/27. Its first
full suite passed 199 tests and failed only at the exact G1 wheel-member
allowlist, which correctly rejected the new `pgworld/simulation/controls.py`
until named. Ownership was expanded to `tests/release/test_wheel_install.py`
only for that expected-member/import assertion; private/generated payload
exclusions and all other P01-11 release checks remain unchanged.

Integration state: the immutable return tip `2b77d598` was independently
accepted and integrated as `c4e71c0`, `5c4907c`, `1999149`, and `736fe51`.
The final focused suite passed 40 tests, the separate fresh-wheel test passed,
and integrated `main` passed 213 tests. P02-01 edit ownership is cleared; no
agent owns root ledgers, shared contracts, or gate state.

## Tenth wave

The assignment uses accepted and pushed main revision
`7b2a025bdc7b74c7956cebf9787df59256403fce`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Damage law/physics | `research/p02-02-damage-law`; `C:/Users/mzora/MechWorld-wt-p02-02` | P02-02: exact red-first phenomenological deterministic and sample-once heterogeneous thresholds, irreversible masks, damage-initiation/censoring records, and distinct connectivity/degradation/instability endpoints | `docs/decisions/fracture_model.md`, `src/pgworld/physics/damage.py`, `tests/physics/test_damage_law.py`, `tests/release/test_wheel_install.py`, `evidence/subagents/P02-02/`, `docs/subagents/P02-02-damage-law.md` | No root ledger/README/shared-schema/profile/loading-control/solver-cascade edits; release-test edit is limited to the exact new module member/import smoke while all exclusions remain strict; no LAMMPS mutation, molecular-cleavage certification, physical-time/3D claim, production simulation, gate decision, public release, private data, or changes outside owned paths |

The return requires the first exact failing regression, stable-ID and
retry/order-invariant threshold fixtures, fail-closed units/profile/reference
checks, explicit predictor-visibility metadata, prescribed-intervention
exclusion, right-censored no-event outcomes, distinct endpoint semantics,
sole-author Mohammad commits, path/identity proof, and limitations. A separate
read-only reviewer audits the immutable return before integration.

Scope expansion record: the public damage module must be present in the
installable wheel, whose exact allowlist intentionally rejects every unnamed
member. Ownership therefore includes `tests/release/test_wheel_install.py`
only to add that module and an installed import/contract smoke; no exclusion
or other P01-11/P02-01 release assertion may be weakened.

Integration state: the immutable return tip `f47dc312` was independently
accepted and integrated as `15df7b8`, `06889af`, and `343296e`. Final focused
verification passed 58 tests, the separate fresh-wheel test passed, and
integrated `main` passed 271 tests. P02-02 edit ownership is cleared; no agent
owns root ledgers, shared schemas, solver/cascade code, or gate state.
