# Local compute policy

`local_smoke.json` is a sanitized, bounded development policy for the new run
manager. It contains no user, account, email, project-allocation, cluster path,
or submission command. Scheduler submission, MPI, and GPU execution are
explicitly disabled.

`scheduler_disabled.json` records the portable fields a future approved
scheduler adapter will need, but deliberately has no account, queue, working
directory, or submission command and keeps `submission_enabled` false. It is not
accepted by the local-config loader and cannot submit a job.

The values are recorded with each expanded run configuration. The manager
enforces `max_concurrent_runs` with an in-process semaphore and exposes a
cooperative walltime check to the run callback. It does not claim to enforce an
operating-system memory limit. Production campaign sizing, scheduler templates,
and remote submission remain outside this local adapter and require the recorded
human/resource approval.

The inherited runners are not silently redirected by this change. A migrated
caller must construct the solver with `RunContext.solver_arguments` and write
dumps, images, restarts, and raw results to the corresponding absolute paths in
`RunContext.paths`.
