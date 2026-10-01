# Commit, Subagent, and Resumption Playbook

These are operating contracts, not evidence that agents were spawned or commits made during planning. Respect existing live project instructions when integrating this file.

## 1. Establish ownership before delegating

The integrator owns `handoff.md`, `TASKS.json`, shared schema/config contracts, lockfiles, main integration branch, merges and final acceptance. Assign two or three independent tasks at a time initially, not every role at once. The task list can propose overlapping paths across time; **do not schedule overlapping writers concurrently**.

For the first wave, a sensible split is:

| Role | Scope | Editing restriction |
|---|---|---|
| Geometry/data | P01-01 parser/periodic regression | Assigned parser/geometry files and tests only |
| Environment | P00-03 actual LAMMPS probe | Environment documentation and its isolated smoke test only |
| Physics reviewer | Read-only parameter/energy audit | Return findings; integrator assigns later implementation |

Follow with filter/scheduler and sampler repairs after ownership is reconciled. Worktrees isolate files; they do not allocate GPUs, protect a shared absolute output directory, or guarantee scientifically compatible interfaces.

## 2. Native delegation and branch isolation are separate

Inspect the actual installed Codex client and its supported subagent workflow [S02]. Do not invent CLI switches from memory. If native delegation is unavailable, record the limitation and execute role contracts sequentially; do not claim parallel execution occurred.

A normal Git worktree pattern, **only after verifying a real checkout, a safe base, and permissions**, is:

```sh
git status --short
git worktree list --porcelain
git worktree add -b research/p01-01-periodic-bounds ../pg-wt-p01-01 HEAD
```

The branch and directory are examples; check for existing names, preserve existing worktrees and avoid duplicate workers. Do not reset, delete, or force-recreate anything. Use unique project output directories within each assigned worktree or a manifest-controlled run store. Avoid global log/restart/image names.

## 3. Delegation contract

Every actual assignment includes:

```text
task_id:
scientific_or_engineering_objective:
base_commit_or_snapshot_hash:
branch_and_worktree:
owned_paths:
read_only_paths:
accepted_dependency_artifacts:
input_output_schema_versions:
regression_or_acceptance_tests:
resource_and_runtime_limit:
forbidden_actions:
return_report_path:
```

Specify expected evidence, not “make it work.” Examples: rectangular/sheared parser round trip; real post-rupture equilibrium; own-topology autoregressive rollout; a viewer-selected bond ID that matches the canonical dataset.

## 4. Subagent return report

Subagents write `docs/subagents/<task-id>.md`, not the root ledger:

```markdown
# Task Return: <task-id>
## Base and Scope
Base revision/hash, branch, worktree and owned files.
## Changes
What changed and why; no claims beyond the actual diff.
## Commands and Results
Exact command, cwd/environment, exit status, result, log/artifact path.
## Scientific Checks
Units, invariant checks, analytical fixtures, dataset/model assumptions.
## Known Limitations
Explicit [UNVERIFIED] items, failed approaches and remaining blockers.
## Integration Notes
Dependencies, schema changes requested, migration needs and conflict risks.
```

The integrator reviews the diff, verifies tests in the integrated environment, and records the accepted task/evidence. A subagent's assertion that a test passed is not a substitute for accessible logs and integrator verification of critical changes.

## 5. Commit identity

In the correct repository:

```sh
git config --local user.name "Mohammad Zoraiz"
git config --local user.email "zoraizmohammad@gmail.com"
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

Check environment overrides before committing. Use this identity for new authorized work; do not amend/rebase inherited history to change authors. Preserve imported code attribution, source hashes, notices, and disclosures. A new source-import commit must say it imports upstream work, not imply it was all freshly written by Mohammad.

Do not add agent/AI/bot coauthors. Preserve honest AI-use disclosure where appropriate; “no AI coauthor” does not mean falsely claiming no AI assistance. Manuscript authorship is a separate human contribution/permission decision.

## 6. Logical commit examples

Use plain messages for actual completed work, not a predetermined series of empty milestones:

```text
Document the imported PG simulator and baseline checks
Fix periodic bounds when reading LAMMPS dumps
Apply every requested analysis filter
Make one-shot trajectory output criteria persistent
Sample strand lengths without allocating giant lists
Make PG network generation reproducible from a seed
Check bond and angle forces against LAMMPS
Record rupture cascades with stable edge IDs
Export graph trajectories with explicit controls and units
Keep related networks out of different dataset splits
Train and evaluate the pilot graph baseline
Couple predicted bond loss to mechanical relaxation
Compare solver and model rollouts in the explorer
Validate the AFM observation model on held-out measurements
Package model weights and reproducible research figures
```

A training or validation commit requires real corresponding work; never use these messages for a stub or an unexecuted config. Avoid “everything complete,” “all fixed,” or “production ready” without the full required evidence.

Before committing: run relevant checks, inspect `git diff --stat` and `git diff`, review sensitive data, update task evidence and the ledger, then commit only the intended paths. Avoid blind `git add .` in a research repository containing raw/private data. Do not push, tag publicly, or submit anything without authorization.

## 7. Persistent jobs and resumption

For each real simulation/training job, record task ID, actual job ID/PID and host, code/config/input hashes, execution environment, output/checkpoint path, resource allocation, start/status, and exact inspect/resume/cancel command. Do not commit credentials.

On reconnect, read this record and inspect the actual scheduler/process and latest validated checkpoint. A stale status line is not proof that a job is running. Resume or report failure; do not silently restart and duplicate the campaign. Cancel only specifically identified jobs belonging to this project under the user's authority.

## 8. Session handoff and stopping

After every integrated milestone or important blocker, update the requested root handoff headings and update root `README.md` in the same logical change. The README must give a current scientist/developer-facing summary of completed evidence, active ownership/jobs, blockers, remaining gates/tasks, and exact next steps; reconcile it with `handoff.md` and `TASKS.json` before committing. A stale README blocks handoff completion. Archive long history under `docs/sessions/` and leave the root ledger compact enough to use.

Stop the affected task for missing data/access, human scientific review, resource limits, or a repeated reproducible failure. Continue independent tasks. When a session must end, do not imply background progress without an actual persistent job. A research hypothesis can fail while its evaluation is complete; a missing experiment cannot be relabeled complete because engineering finished.
