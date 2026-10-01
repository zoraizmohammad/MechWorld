# AI AGENT HANDOFF LEDGER

## 🎯 Current Mission & Goals

- **Ultimate goal:** Complete the evidence-gated MechWorld-PG program: verified inherited mechanics, irreversible topology change, reproducible graph trajectories, trained/evaluated physics-structured world models, actual experimental integration, a scientist-facing explorer, and an evidence-linked release candidate.
- **Current session objective:** Reconcile the execution packet with the actual checkout, establish the measured workstation baseline and isolated subagent workflow, then integrate the first reproduced-defect regression repair and continue through eligible dependencies.
- **Project lead / new commit identity:** Mohammad Zoraiz <zoraizmohammad@gmail.com>. Repository-local author and committer identity is verified; inherited history remains attributed to its original authors.
- **Live branch/base:** `main`; inherited base `248644000c34dbb93c85976b3bf433bb2f7344c5` (`5245d459c426d3e0a1c78a0fd1eee985d13f741e` tree).
- **Gate state:** G0 is accepted from measured source-preservation, environment, access, and isolated-workflow evidence; G1-G11 remain not accepted. P00-01 through P00-05 and P01-02 are done. The A01/A02 parser slice of P01-01 is integrated, but P01-01 remains in progress for periodic identity/wrapping semantics. P00-06 and P01-05 are blocked on human/lab decisions without blocking independent engineering.

## 📊 Transient State & What Changed

- The supplied `PG_WORLD_MODEL_EXECUTION_PACKET/` was the only initial uncommitted path and remains preserved as untracked user-provided source material.
- No root `AGENTS.md`, `handoff.md`, `TASKS.json`, or `docs/` existed, so the durable packet instructions/specifications were copied into new root paths without overwriting a prior ledger.
- New live-checkout records were added in `docs/provenance.md`, `docs/environment.md`, `docs/access_and_resources.md`, `docs/ownership.md`, and `docs/sessions/2026-09-30-bootstrap.md`.
- Baseline and source-audit evidence is under `evidence/baseline/`, `evidence/source_audit_live/`, and `evidence/preflight/`. Historical packet review evidence is preserved separately in `evidence/packet_review/`.
- An ignored `.venv` was created with system site packages. Missing declared runtime dependencies `pandas` and `matplotlib`, plus planned HDF5 dependency `h5py`, were installed there. No tracked inherited source was changed by environment setup.
- Repository-local Git identity is set to Mohammad Zoraiz <zoraizmohammad@gmail.com>; effective author and committer values were checked with `git var`.
- Available local solver: LAMMPS 2 Sep 2026. A bounded library `run 0` completed and the instance closed. Repeatable project doctor/integration evidence is assigned under P00-03.
- No simulation, training, viewer, or experimental job is running. Historical Hoffman2 job IDs in `status.md` have not been verified remotely because scheduler clients/access are absent.
- Three native subagents were launched from base `c0ec8aa`. The P01-01 parser and P00-03 environment commits were path-reviewed, independently rerun, and integrated as `912c9cc` and `4faeab1`. The report-only P01-05 physics audit was path-reviewed and integrated as `59ecfdc`. A second-wave P01-03 distribution assignment was launched from `d4274c1` in its own worktree. Exact ownership is in `docs/ownership.md`; none owns the root ledger, README, or shared contracts.
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
- Integrated P01-01 parser slice: targeted pytest **3 passed in 7.82s**; full suite **12 passed in 7.90s**. The historical diagnostic now observes correct rectangular/orthogonal bounds and keeps A03/A04 fixed; only A05 remains among the five historical cases. General-triclinic rejection and periodic image/identity semantics remain unverified.
- P00-05 isolation verification: `git worktree list --porcelain` showed distinct main, parser, environment, physics-audit, and distribution worktrees on separate branches. Each returned commit stayed inside its written ownership boundary; only the integrator changed the ledger, README, contracts, and gate state.
- G0 accepted: all terminal tasks P00-01 through P00-05 are done, inherited/untracked source remains preserved, the target environment and access limitations are recorded, and the actual LAMMPS smoke passed. Evidence index: `reports/gates/G0.json`.
- Packet archive limitation: no ZIP was present; the historical archive SHA-256 could not be recomputed. Live inventory matches the packet's counts, but byte identity is `[UNVERIFIED]`.

## 🚫 Constraints & "Do Not Touch" Zones

- Preserve uncommitted packet material, inherited `status.md`/`todo.md`, Git history, licenses/notices, tracked restart data, and private lab information. Do not reset, force-push, rewrite history, or attribute inherited code to the new commit author.
- Do not call minimized states physical time, a configured `fix bond/break` fracture during minimization, an illustrative cylinder native 3D mechanics, or a saved/untrained checkpoint a validated model.
- No production campaign, paid/cloud resource, public deployment, remote push, private-data upload, paper submission, or release approval is authorized.
- Only the integrator edits `handoff.md`, `TASKS.json`, shared contracts, root dependency files, and gate state. Subagents use dedicated branches/worktrees or read-only scope and may write only assigned paths plus their return report.
- P00-06/P01-05/WP8 human decisions and actual lab acquisition cannot be self-approved or replaced with synthetic data. Continue independent eligible implementation.

## ⏭️ Next Concrete Steps

1. [ ] Continue P01-01 with general-triclinic rejection and repeated/large-offset periodic image/identity tests; do not mark the task complete before those pass.
2. [ ] Review P01-03 from `research/p01-03-distributions`: capture the A05 uniform-distribution failure, replace expanded distributions with a bounded sampler, and document number-versus-weight fractions.
3. [ ] Independently review the subagent diffs and rerun targeted plus inherited tests in the integration worktree before each commit.
4. [ ] Continue the eligible distribution/RNG repairs after recording their own failing regressions while P00-06/P01-05 and lab inputs remain blocked.
5. [ ] Implement the definite A16 conversion regression separately; do not mix it with an unapproved parameter-profile change.
6. [ ] Repair and test the seven inherited Python 3.11 figure-script syntax failures before P01-11 clean-install acceptance.
7. [ ] Do not begin a main dataset sweep before G1; do not begin model claims before real rupture, schema, split, and pilot gates.

**Active jobs:** none. **Persistent simulation/training jobs:** none. Inspect `reports/jobs.jsonl` before starting any future job.

**Resume command:** `cd C:/Users/mzora/MechWorld; git status --short --branch; .venv/Scripts/python.exe -m pytest -q`
