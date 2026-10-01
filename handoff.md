# AI AGENT HANDOFF LEDGER

## 🎯 Current Mission & Goals

- **Ultimate goal:** Complete the evidence-gated MechWorld-PG program: verified inherited mechanics, irreversible topology change, reproducible graph trajectories, trained/evaluated physics-structured world models, actual experimental integration, a scientist-facing explorer, and an evidence-linked release candidate.
- **Current session objective:** Reconcile the execution packet with the actual checkout, establish the measured workstation baseline and isolated subagent workflow, then integrate the first reproduced-defect regression repair and continue through eligible dependencies.
- **Project lead / new commit identity:** Mohammad Zoraiz <zoraizmohammad@gmail.com>. Repository-local author and committer identity is verified; inherited history remains attributed to its original authors.
- **Live branch/base:** `main`; inherited base `248644000c34dbb93c85976b3bf433bb2f7344c5` (`5245d459c426d3e0a1c78a0fd1eee985d13f741e` tree).
- **Gate state:** G0 is accepted from measured source-preservation, environment, access, and isolated-workflow evidence; G1-G11 remain not accepted. P00-01 through P00-05, P01-01 through P01-03, and P01-08 are done. P00-06 and P01-05 are blocked on human/lab decisions without blocking independent engineering.

## 📊 Transient State & What Changed

- The supplied `PG_WORLD_MODEL_EXECUTION_PACKET/` was the only initial uncommitted path and remains preserved as untracked user-provided source material.
- No root `AGENTS.md`, `handoff.md`, `TASKS.json`, or `docs/` existed, so the durable packet instructions/specifications were copied into new root paths without overwriting a prior ledger.
- New live-checkout records were added in `docs/provenance.md`, `docs/environment.md`, `docs/access_and_resources.md`, `docs/ownership.md`, and `docs/sessions/2026-09-30-bootstrap.md`.
- Baseline and source-audit evidence is under `evidence/baseline/`, `evidence/source_audit_live/`, and `evidence/preflight/`. Historical packet review evidence is preserved separately in `evidence/packet_review/`.
- An ignored `.venv` was created with system site packages. Missing declared runtime dependencies `pandas` and `matplotlib`, plus planned HDF5 dependency `h5py`, were installed there. No tracked inherited source was changed by environment setup.
- Repository-local Git identity is set to Mohammad Zoraiz <zoraizmohammad@gmail.com>; effective author and committer values were checked with `git var`.
- Available local solver: LAMMPS 2 Sep 2026. A bounded library `run 0` completed and the instance closed. Repeatable project doctor/integration evidence is assigned under P00-03.
- No simulation, training, viewer, or experimental job is running. Historical Hoffman2 job IDs in `status.md` have not been verified remotely because scheduler clients/access are absent.
- Three native subagents were launched from base `c0ec8aa`. The P01-01 parser and P00-03 environment commits were path-reviewed, independently rerun, and integrated as `912c9cc` and `4faeab1`. The report-only P01-05 physics audit was path-reviewed and integrated as `59ecfdc`. The P01-03 distribution, P01-08 run-isolation, and remaining P01-01 periodic-identity returns were reviewed and integrated as `eef253f`, `9429b4c`, and `71a5700`. P10-01 current related-work review uses a separate worktree from `a2805a6`; P01-04 reproducibility and P01-09 analysis repair now use isolated worktrees from accepted main revision `a79a7aa`. Exact ownership is in `docs/ownership.md`; none owns the root ledger, README, or shared contracts.
- P01-08 adds a typed local-only adapter with immutable per-run artifact trees, deterministic expanded config/provenance, failure/interruption/close status, and per-process concurrency control. Inherited runners remain unmigrated. Restart resume/equivalence, hard walltime/memory enforcement, cross-process scheduling policy, MPI/GPU, and production use remain unclaimed.
- P01-03 replaces expanded million/100-million-entry arrays with a normalized finite `DiscreteDistribution`. It preserves inherited FS number/molar and separate WFS weight laws, retains the inherited integer-grid lognormal definition, validates truncation/input, and documents the intentional seeded-stream change. P01-04 now owns namespaced RNG propagation and achieved-network metrics.
- The physics audit found that current 2D tension conversion is dimensionally correct, A16 is a definite factor-1000 energy-density label/conversion defect, and A12 cannot be resolved by blindly halving the harmonic coefficient because a two-edge series interpretation reproduces the cited coarse spring. Three legacy parameter routes must remain distinct. Physical time, any 3D thickness, coarse-grain mapping, angle mapping, nonlinear-fit provenance, and reference-state/observable choices remain human-review questions.
- P01-02 repaired the reproduced A03/A04/A06 control-flow defects: analysis filters now accumulate, one-shot output criteria mutate the caller-owned schedule, and the ensemble wrapper passes the current minimizer API by explicit keywords while preserving requested initial/final dumps and remap selection.

## ✅ Verification & Hard Evidence

- `git status --short --branch` at entry: `main...origin/main` plus only `?? PG_WORLD_MODEL_EXECUTION_PACKET/`.
- Packet SHA check: 21/21 listed files matched `PG_WORLD_MODEL_EXECUTION_PACKET/SHA256SUMS`.
- Packet planning validation: exit 0; 73 unique tasks, 72 mandatory, acyclic dependencies, gates G0-G11, links/source IDs/helper syntax passed. This validates planning only.
- Initial untouched baseline with system Python: `python -m pytest -q --junitxml=evidence/baseline/pytest.xml` exited 2; two collection errors due to missing `pandas`. Evidence: `evidence/baseline/pytest.txt`, `pytest.xml`, and `pytest_context.txt`.
- Dependency-complete local baseline: `.venv/Scripts/python.exe -m pytest -q --junitxml=evidence/baseline/pytest_after_dependencies.xml` exited 0; **5 passed in 12.32s**. Evidence: matching `.txt`, `.xml`, and context files.
- Live defect reproduction: `.venv/Scripts/python.exe PG_WORLD_MODEL_EXECUTION_PACKET/tools/review_upstream.py --repo . --out evidence/source_audit_live` exited 0. A01-A05 all reproduced; no LAMMPS solver was constructed. Evidence: `evidence/source_audit_live/`.
- P01-02 pre-fix regression: `.venv/Scripts/python.exe -m pytest tests/unit/test_legacy_control_flow.py -q` exited 1 with 4 expected failures covering A03/A04/A06. After the fix, the same target exited 0 with **4 passed in 7.67s**; the full suite exited 0 with **9 passed in 7.40s**. A fresh historical diagnostic now observes the expected multi-filter indices and a consumed `ONCE` criterion, while A01/A02/A05 still reproduce. Evidence: `evidence/regressions/P01-02/`.
- Targeted `py_compile` for the P01-02 files exited 0. A broader `compileall -q src` exited 1 on seven untouched figure/result scripts whose nested double-quoted f-string expressions require Python 3.12 syntax. This new inherited Python 3.11 compatibility gap is recorded under P01-11 and is not reported as a P01-02 regression.
- Basic LAMMPS library probe: Python module loaded solver version 20260902, executed a bounded two-atom `run 0`, closed normally, and found required style names in `lmp -h`. This is environment evidence only, not PG/fracture validation.
- Integrated P00-03 doctor: `tools/doctor.py --output evidence/integration/P00-03/doctor.json` exited 0; required harmonic/nonlinear bond, harmonic angle, and `fix bond/break` styles were present; the bonded fixture's analytical energies matched; solver closed. Targeted pytest: **2 passed in 1.60s**, no skips. Full suite: **14 passed in 8.41s**. `fix bond/break` was configuration-only and did not run or rupture.
- Integrated P01-01 periodic identities: the earlier parser slice passed 3 focused tests, then the remaining reviewed slice passed **15 focused tests in 6.18s** on main and the merged full suite passed **62 tests in 9.35s**. Compilation passed and a deterministic 1,000-case brute-force oracle matched every restricted-triclinic minimum image. General/3D unsupported forms are rejected; arbitrary signed wrapping, image shifts, skew-cell minimum image, glycan orientation, and persistent atom IDs are covered. Persistent per-edge image identity remains P03-01 scope. Evidence: `evidence/integration/P01-01-identities/`.
- P00-05 isolation verification: `git worktree list --porcelain` showed distinct main, parser, environment, physics-audit, and distribution worktrees on separate branches. Each returned commit stayed inside its written ownership boundary; only the integrator changed the ledger, README, contracts, and gate state.
- G0 accepted: all terminal tasks P00-01 through P00-05 are done, inherited/untracked source remains preserved, the target environment and access limitations are recorded, and the actual LAMMPS smoke passed. Evidence index: `reports/gates/G0.json`.
- Integrated P01-03 distribution repair: exact red A05 regression failed once before the fix; integration rerun passed **26 targeted tests in 7.68s** and **40 total tests in 7.89s**. `py_compile` and the current five-case source diagnostic exited 0; the diagnostic now accepts `UNI=2=4` as `DiscreteDistribution` and the generator returns without exception. Evidence: `evidence/integration/P01-03/`.
- Integrated P01-08 run isolation: targeted lifecycle suite passed **10 tests in 0.97s** and the merged full suite passed **50 tests in 7.73s**. Compile and compute-config sanitization checks passed. A separate real serial LAMMPS 2 Sep 2026 one-atom `run 0` executed through the manager, recorded `quality_status=accepted`, and recorded successful solver close. Evidence: `evidence/integration/P01-08/`.
- Packet archive limitation: no ZIP was present; the historical archive SHA-256 could not be recomputed. Live inventory matches the packet's counts, but byte identity is `[UNVERIFIED]`.

## 🚫 Constraints & "Do Not Touch" Zones

- Preserve uncommitted packet material, inherited `status.md`/`todo.md`, Git history, licenses/notices, tracked restart data, and private lab information. Do not reset, force-push, rewrite history, or attribute inherited code to the new commit author.
- Do not call minimized states physical time, a configured `fix bond/break` fracture during minimization, an illustrative cylinder native 3D mechanics, or a saved/untrained checkpoint a validated model.
- No production campaign, paid/cloud resource, public deployment, remote push, private-data upload, paper submission, or release approval is authorized.
- Only the integrator edits `handoff.md`, `TASKS.json`, shared contracts, root dependency files, and gate state. Subagents use dedicated branches/worktrees or read-only scope and may write only assigned paths plus their return report.
- P00-06/P01-05/WP8 human decisions and actual lab acquisition cannot be self-approved or replaced with synthetic data. Continue independent eligible implementation.

## ⏭️ Next Concrete Steps

1. [ ] Review P01-04 from `research/p01-04-reproducibility`; require exact red/green evidence for named RNG independence, achieved network metrics, and measured serialization error.
2. [ ] Review P01-09 from `research/p01-09-analysis`; require exact red/green evidence for idempotence, raw-evidence preservation, independent-network interpolation, and A16 dimensional correction without parameter-profile edits.
3. [ ] Independently review every subagent diff and rerun targeted plus inherited tests in the integration worktree before acceptance.
4. [ ] Migrate inherited simulation entry points to P01-08 paths in a later owned task and add true restart-resume/suffix-equivalence coverage before claiming restartability.
5. [ ] Continue eligible independent engineering while P00-06/P01-05 and lab inputs remain blocked.
6. [ ] Preserve P03-01 ownership of canonical persistent per-edge image offsets and stable edge identity; the P01-01 inferred minimum image is not a trajectory identity substitute.
7. [ ] Review P10-01 from `research/p10-01-related-work`: require a validated bibliography, explicit search boundary, and overlap matrix; broad fracture-GNN novelty is already contradicted by prior work.
8. [ ] Repair and test the seven inherited Python 3.11 figure-script syntax failures before P01-11 clean-install acceptance.
9. [ ] Do not begin a main dataset sweep before G1; do not begin model claims before real rupture, schema, split, and pilot gates.

**Active jobs:** none. **Persistent simulation/training jobs:** none. Inspect `reports/jobs.jsonl` before starting any future job.

**Resume command:** `cd C:/Users/mzora/MechWorld; git status --short --branch; .venv/Scripts/python.exe -m pytest -q`
