# AI AGENT HANDOFF LEDGER

## 🎯 Current Mission & Goals

- **Ultimate goal:** Complete the evidence-gated MechWorld-PG program: verified inherited mechanics, irreversible topology change, reproducible graph trajectories, trained/evaluated physics-structured world models, actual experimental integration, a scientist-facing explorer, and an evidence-linked release candidate.
- **Current session objective:** Reconcile the execution packet with the actual checkout, establish the measured workstation baseline and isolated subagent workflow, then integrate the first reproduced-defect regression repair and continue through eligible dependencies.
- **Project lead / new commit identity:** Mohammad Zoraiz <zoraizmohammad@gmail.com>. Repository-local author and committer identity is verified; inherited history remains attributed to its original authors.
- **Live branch/base:** `main`; inherited base `248644000c34dbb93c85976b3bf433bb2f7344c5` (`5245d459c426d3e0a1c78a0fd1eee985d13f741e` tree).
- **Gate state:** G0-G11 remain not accepted. P00-01, P00-02, and P00-04 have measured evidence ready for integration review. P00-03 and P00-05 are in progress. P00-06 is blocked on human/lab decisions without blocking independent engineering.

## 📊 Transient State & What Changed

- The supplied `PG_WORLD_MODEL_EXECUTION_PACKET/` was the only initial uncommitted path and remains preserved as untracked user-provided source material.
- No root `AGENTS.md`, `handoff.md`, `TASKS.json`, or `docs/` existed, so the durable packet instructions/specifications were copied into new root paths without overwriting a prior ledger.
- New live-checkout records were added in `docs/provenance.md`, `docs/environment.md`, `docs/access_and_resources.md`, `docs/ownership.md`, and `docs/sessions/2026-09-30-bootstrap.md`.
- Baseline and source-audit evidence is under `evidence/baseline/`, `evidence/source_audit_live/`, and `evidence/preflight/`. Historical packet review evidence is preserved separately in `evidence/packet_review/`.
- An ignored `.venv` was created with system site packages. Missing declared runtime dependencies `pandas` and `matplotlib`, plus planned HDF5 dependency `h5py`, were installed there. No tracked inherited source was changed by environment setup.
- Repository-local Git identity is set to Mohammad Zoraiz <zoraizmohammad@gmail.com>; effective author and committer values were checked with `git var`.
- Available local solver: LAMMPS 2 Sep 2026. A bounded library `run 0` completed and the instance closed. Repeatable project doctor/integration evidence is assigned under P00-03.
- No simulation, training, viewer, or experimental job is running. Historical Hoffman2 job IDs in `status.md` have not been verified remotely because scheduler clients/access are absent.

## ✅ Verification & Hard Evidence

- `git status --short --branch` at entry: `main...origin/main` plus only `?? PG_WORLD_MODEL_EXECUTION_PACKET/`.
- Packet SHA check: 21/21 listed files matched `PG_WORLD_MODEL_EXECUTION_PACKET/SHA256SUMS`.
- Packet planning validation: exit 0; 73 unique tasks, 72 mandatory, acyclic dependencies, gates G0-G11, links/source IDs/helper syntax passed. This validates planning only.
- Initial untouched baseline with system Python: `python -m pytest -q --junitxml=evidence/baseline/pytest.xml` exited 2; two collection errors due to missing `pandas`. Evidence: `evidence/baseline/pytest.txt`, `pytest.xml`, and `pytest_context.txt`.
- Dependency-complete local baseline: `.venv/Scripts/python.exe -m pytest -q --junitxml=evidence/baseline/pytest_after_dependencies.xml` exited 0; **5 passed in 12.32s**. Evidence: matching `.txt`, `.xml`, and context files.
- Live defect reproduction: `.venv/Scripts/python.exe PG_WORLD_MODEL_EXECUTION_PACKET/tools/review_upstream.py --repo . --out evidence/source_audit_live` exited 0. A01-A05 all reproduced; no LAMMPS solver was constructed. Evidence: `evidence/source_audit_live/`.
- Basic LAMMPS library probe: Python module loaded solver version 20260902, executed a bounded two-atom `run 0`, closed normally, and found required style names in `lmp -h`. This is environment evidence only, not PG/fracture validation.
- Packet archive limitation: no ZIP was present; the historical archive SHA-256 could not be recomputed. Live inventory matches the packet's counts, but byte identity is `[UNVERIFIED]`.

## 🚫 Constraints & "Do Not Touch" Zones

- Preserve uncommitted packet material, inherited `status.md`/`todo.md`, Git history, licenses/notices, tracked restart data, and private lab information. Do not reset, force-push, rewrite history, or attribute inherited code to the new commit author.
- Do not call minimized states physical time, a configured `fix bond/break` fracture during minimization, an illustrative cylinder native 3D mechanics, or a saved/untrained checkpoint a validated model.
- No production campaign, paid/cloud resource, public deployment, remote push, private-data upload, paper submission, or release approval is authorized.
- Only the integrator edits `handoff.md`, `TASKS.json`, shared contracts, root dependency files, and gate state. Subagents use dedicated branches/worktrees or read-only scope and may write only assigned paths plus their return report.
- P00-06/P01-05/WP8 human decisions and actual lab acquisition cannot be self-approved or replaced with synthetic data. Continue independent eligible implementation.

## ⏭️ Next Concrete Steps

1. [ ] Finish P00-03 with a committed doctor, actual required-style smoke test, and exact log.
2. [ ] Finish P00-05 by launching and recording isolated geometry/data and environment worktrees plus a read-only physics reviewer.
3. [ ] P01-01: integrate the first A01/A02 failing regression and minimal parser fix; do not mark broader periodic identity semantics complete without their tests.
4. [ ] Independently review the subagent diffs and rerun targeted plus inherited tests in the integration worktree before each commit.
5. [ ] Continue eligible A03/A04/A06 and distribution/RNG repairs while P00-06 and lab inputs remain blocked.
6. [ ] Do not begin a main dataset sweep before G1; do not begin model claims before real rupture, schema, split, and pilot gates.

**Active jobs:** none. **Persistent simulation/training jobs:** none. Inspect `reports/jobs.jsonl` before starting any future job.

**Resume command:** `cd C:/Users/mzora/MechWorld; git status --short --branch; .venv/Scripts/python.exe -m pytest -q`
