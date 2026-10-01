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

- Local smoke tests and bounded pilot-scale development are authorized by the execution request.
- Available local resources at preflight: 4 CPU cores / 8 logical processors, 15.71 GiB RAM, NVIDIA T500 4 GiB, and 48.67 GiB free disk.
- No paid cloud provisioning, large cluster campaign, public hosting, remote push, public data/model upload, paper submission, or production compute/storage budget is authorized.
- Production campaign size, concurrency, storage retention, and retry limits require a pilot-informed human decision under P04-03.
- Lab protocol, experimental data access, parameter review, failure endpoint, physical-time scope, release rights, and manuscript authorship remain human/data dependencies under P00-06 and WP8/WP10.

Unknown remote scheduler state, private lab artifacts, and unpublished datasets remain `[UNVERIFIED]`; absence from this checkout is not evidence that they do not exist.
