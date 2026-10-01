# Access, artifacts, jobs, and resource limits

## Authorized local scope inspected

The repository, its configured Git remotes, installed local runtimes, and files under the supplied checkout were inspected read-only during preflight. Credentials and unrelated personal locations were not searched.

## Artifact inventory

- No `.out`, `.atoms`, `.bonds`, `.moduli`, HDF5, NPZ, PyTorch checkpoint, or generic checkpoint artifacts were found in the checkout outside the supplied planning material.
- One inherited tracked LAMMPS restart fixture exists at `ELASTIC_2D_ZERO_TEMP/restart.equil`; its provenance is the inherited repository and its scientific validity has not yet been re-established.
- No `data/`, `artifacts/`, trained-model, AFM raw-data, microscopy raw-data, or viewer directory existed at preflight.
- Historical `status.md` records cluster job IDs from June 2026 and an SFTP retrieval recipe. Those entries are historical notes only; they were not treated as live job evidence.

## Jobs and scheduler access

The local process scan found no running project Python, LAMMPS, MPI, `qsub`, or `qstat` process. Scheduler clients `qsub` and `qstat` were not installed on this host, and no authenticated cluster session was available to inspect historical Hoffman2 job IDs. `reports/jobs.jsonl` records the local negative observation without claiming remote jobs have ended.

## Current limits and authorization

- Local smoke tests and bounded pilot-scale development are authorized by the execution request and the 2026-10-01 decision in `docs/decisions/scope.md`.
- Available local resources at preflight: 4 CPU cores / 8 logical processors, 15.71 GiB RAM, NVIDIA T500 4 GiB, and 48.67 GiB free disk.
- No paid cloud provisioning, large cluster campaign, public hosting, public data/model upload, paper submission, or production compute/storage budget is authorized. Ordinary pushes of reviewed repository commits to the configured project fork are separately authorized by the project owner; that does not authorize public data/model release.
- Production campaign size, concurrency, storage retention, and retry limits require a pilot-informed human decision under P04-03.
- Lab protocol, experimental data access, parameter review, failure endpoint, physical-time scope, release rights, and manuscript authorship remain human/data dependencies under P00-06 and WP8/WP10.

Unknown remote scheduler state, private lab artifacts, and unpublished datasets remain `[UNVERIFIED]`; absence from this checkout is not evidence that they do not exist.

## 2026-10-01 bounded-compute decision

Until a measured pilot supports a new approval, use at most one heavy simulation/training process, two compute threads, `min(4 GiB, 25% installed RAM)`, 10 minutes per smoke command, 30 minutes per explicitly identified pilot, two cumulative heavy-compute hours before presenting a new estimate, and 5 GiB of newly generated results while preserving at least 20% free disk. Retry a diagnosed transient failure once; do not blindly retry reproducible failures. These are ceilings, not targets.

The main scope is quasi-static, so no physical-time production work is authorized. Production concurrency, walltime, CPU/GPU allocation, budget, retention, and retry policy remain a later P04-03 decision based on measured pilot evidence.

## Experimental and review access still pending

The proposed target is lab-approved quasi-static AFM force-indentation on an untreated laboratory *E. coli* baseline with matched morphology. Exact specimen conditions, protocol, custodian, data location, permitted uses, acquisition owner, training, and release restrictions remain unconfirmed. Prof. Christoph Schmidt and Octavio are proposed reviewers/coordinators only; participation and approval have not been confirmed. P08-01 is therefore blocked on access rather than treated as complete.
