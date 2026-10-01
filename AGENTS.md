# Project Instructions: MechWorld-PG

## Mission

Extend the existing PG-Network-of-Springs work into the complete physics-structured, topology-changing bacterial-mechanics research project described in `docs/RESEARCH_PLAN.md`. Required outputs include actual trained model(s), reproducible evaluation, new experimental validation, and the scientist-facing 3D viewer/model-access workflow. A scaffold, mock dataset, or attractive animation does not complete the mission.

Read `handoff.md`, then the relevant tasks in `TASKS.json`, before each work session. Read the full research plan before selecting architecture or changing physics. Read task-specific contracts before editing. If this packet is not yet integrated at the repository root, reconcile it with existing instructions and ledgers first; never overwrite existing project state blindly.

## Source of truth

Actual files, executable tests, run artifacts, and measured results take precedence over prior agent summaries. The initial archive review is a historical baseline, not a current workstation verification. Every completed task needs evidence or an actual human approval/acquisition record. Unknown results are `[UNVERIFIED]`.

Keep the old simulator and its provenance. Make minimal tested repairs, then build compatible adapters. Do not replace inherited mechanics with a toy model or silently change constants, units, state meaning, or experimental assumptions.

## Delegation and integration

Use supported Codex subagents for independent work. Inspect the installed client's actual capabilities; do not invent flags, simulate subagents in prose, or assume they have separate working trees. If native subagents are unavailable, record that fact and execute the same role/task contracts sequentially or with authorized separate sessions.

The main agent is the integrator. It owns root `handoff.md`, `TASKS.json`, shared contracts, lockfiles, merges, and release gates. Assign each editing subagent a dedicated branch/worktree and bounded path ownership. Read-only audit agents may share an immutable source snapshot. Do not allow simultaneous writes to shared source/output directories.

Default to two or three active implementation agents, adjusted to verified resources. Do not run parallel expensive simulations/training just because more coding agents are available. Every delegation includes task IDs, base commit, owned paths, dependencies, expected artifacts, tests, resource limit, and a return-report path. One independent reviewer checks important physics, data, and model changes before integration.

## Scientific invariants

- Minimized loading states are not physical-time samples. Use load coordinates unless time/damping/mass are validated.
- `fix bond/break` is not invoked during minimization; implement and test the actual quasi-static event loop.
- Persistent IDs and correct periodic-cell geometry are mandatory. A rendered crossing does not create a chemical edge.
- Preserve angular mechanics, topology-dependent angle removal, and irreversible rupture masks.
- Confirm harmonic/nonlinear coefficient conventions and 2D tension units; do not blindly “correct” numeric constants from comments.
- Energy need not decrease across external loading or arbitrary topology changes. Validate the correct phase-specific balance.
- A cylinder embedding is labeled as a display of 2D mechanics. Only native computed 3D coordinates may be called a 3D mechanical result.
- Model inference cannot read future reference states, hidden rupture seeds, or test-derived normalizers.
- Related trajectories from the same base network remain in one split. Experimental repeats remain grouped by cell/batch.
- Simulated fixtures cannot satisfy experimental validation. Negative/null findings are retained.

## Git identity and commits

Use repository-local identity for new authorized work:

```sh
git config --local user.name "Mohammad Zoraiz"
git config --local user.email "zoraizmohammad@gmail.com"
```

Inspect `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT`; environment overrides can change the effective identity. Apply the requested identity to new work without rewriting historical commits or falsely reattributing inherited code. Preserve existing copyrights, license notices, and AI-use disclosures. Do not invent human coauthors or add agent coauthor footers. Manuscript authorship and public release require actual owner/lab confirmation.

Commit one coherent tested change at a time with plain-language messages, for example `Fix tilted simulation-box parsing` or `Record bond deletion events in trajectories`. Include relevant tests, migration/decision notes, and the updated ledger/task state in logical commits. Do not commit private data, secrets, huge generated artifacts, or unrelated user changes. Never reset, force-push, rewrite history, delete untracked files, or change remotes without explicit permission. Do not push or publish solely because local commits are authorized.

## Work cycle

1. Inspect actual state and recover any existing jobs/artifacts before starting duplicates.
2. Select an eligible task with accepted dependencies; mark it in progress.
3. Define a failing regression or acceptance test.
4. Implement the smallest coherent change.
5. Run targeted checks and relevant integration tests in an isolated run directory.
6. Obtain review for scientific/shared-contract changes; reconcile feedback.
7. Update evidence, task state, and the handoff ledger; commit.
8. Continue to the next eligible task. Do not stop after writing a plan or scaffolding while authorized independent implementation remains.

For a failed approach, record command, error, cause, and lesson. Do not repeat identical failed commands indefinitely. Escalate after two materially similar unsuccessful attempts, or sooner for credentials/safety. Continue independent tasks when a task is blocked.

## Evidence and handoff

Update root `handoff.md` after an integrated task, important failure, job submission/completion, scientific decision, and before ending/compacting context. In the same change, update root `README.md` so its current status, completed evidence, active work, blockers, remaining gates/tasks, and exact next steps agree with `handoff.md` and `TASKS.json`. A handoff is incomplete when the README is stale. Keep the handoff concise; archive detailed sessions in `docs/sessions/`. Subagents write their own `docs/subagents/<task-id>.md`, not the root ledger or README.

Record command, cwd/environment, exit status, result, log/artifact path, source/config/data hashes, and explicit limitations. Never copy old “passed” counts as a fresh test result. Keep actual job ID/owner/output/resume command in `reports/jobs.jsonl`; never store credentials. Background work is claimed only after a real authorized persistent job has been submitted and its identity verified.

## Resource and external-action boundaries

No paid cloud provisioning, large cluster campaign, public hosting, paper submission, or external data upload without the corresponding authorization. Never bypass login, sandbox, or institutional restrictions. Check available resources and set budgets before expensive work. Bound simulation retries, events, horizons, memory, and training runs. Avoid wildcard process termination; touch only this project's identified jobs.

When all currently eligible work is done, report exactly what remains blocked and how to resume. Full completion requires all mandatory gates in `docs/VERIFICATION_AND_RELEASE.md`, not merely passing software tests. Do not fabricate experiments, benchmarks, citations, approvals, or positive research findings.
