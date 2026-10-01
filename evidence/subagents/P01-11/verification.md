# P01-11 verification record

## Scope and identity

- Worktree: `C:\Users\mzora\MechWorld-wt-p01-11`
- Branch: `research/p01-11-package-g1`
- Accepted base: `a0d625994d593c236195dda2734c62111d201ea1`
- Substantive implementation revision:
  `ea59aea89e9431689b63db1bc8288b30116a2534`
- Final evaluated source revision:
  `a9d6d690e89a761758acc1ac3e72f98087278543` (EOF-whitespace-only
  correction after the substantive commit)
- Implementation author and committer: Mohammad Zoraiz
  `<zoraizmohammad@gmail.com>`
- Development interpreter:
  `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B`
- Resource ceiling: one build/test/solver process at a time; every command was
  below the assigned ten-minute smoke limit.

## Red contract

Command:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest tests/release/test_packaging_contract.py tests/release/test_tracked_python_compiles.py -q --junitxml=evidence/subagents/P01-11/red.xml
```

Result: exit 1; 5 failed in 0.45 s (outer 1.135 s). The failures independently
captured the absent `pyproject.toml`, absent packaged profiles, absent package
CLI, unsafe/unmigrated task behavior, and the seven Python 3.11 parse failures.
SHA-256 of `red.xml`:
`8c8d8e375a57dc0e69f42c8d676638018b5195abbb868feb1a2b4ccff8ee4689`.

Recorded intermediate failures were retained rather than overwritten:

- `focused-initial.xml`: only the working-tree CRLF versus Git-blob byte check
  failed. The final test correctly compares package resources to accepted Git
  blobs, not autocrlf checkout bytes.
- The first wheel build attempt failed because the local environment lacked the
  `wheel` distribution. The authorized `wheel==0.45.1` prerequisite was
  installed and pinned.
- The first clean legacy import attempt exposed missing pandas when only system
  packages were inherited.
- `wheel-retry.xml`: a project-venv dependency overlay passed technically but
  was rejected during review as insufficiently isolated.
- `wheel-isolated.xml`: the corrected clean exact-lock environment passed.

## Final source verification

Final full command:

```text
$env:PGWORLD_WHEEL_EVIDENCE=(Resolve-Path .).Path + '\evidence\subagents\P01-11\wheel-install.json'
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence/subagents/P01-11/full.xml
```

Result at final revision `a9d6d69`: exit 0; **172 passed, 0 failed, 0 errors, 0
skipped**, 14 warnings in 183.73 s; outer PowerShell timer 185.5233859 s. The warnings are two expected
legacy-forensic deprecations and twelve pre-existing invalid-escape warnings
found while compiling otherwise valid tracked scripts. SHA-256 of `full.xml`:
`a37bbbef98013f32f9a3c5bf2c47dc37387f46222c7876336b97fac1976eee02`.

Focused final evidence:

- packaging/wrapper contract: 6 passed in 0.65 s; XML SHA-256
  `24bf60c94e859f59eee0f17eaca8a4e3294970b10fffd7c368d17fce2e6d0284`;
- package/profile/doctor/compile/wheel selection: 24 passed in 23.38 s; XML
  SHA-256
  `2b8ebc1b226db42545c3dccefb0f35710a5df265ba850a54ba4f640605675620`;
- standalone tracked compile after implementation commit: 80 files, 0
  failures, exit 0 in 0.2696212 s; see `tracked-compile.json`.

## Isolated artifact verification

The wheel test copied only packaging inputs into a temporary source tree and
ran the default isolated PEP 517 build (no `--no-isolation`). It created a
fresh venv without system site packages, installed all exact lock entries,
installed the wheel with `--no-deps`, cleared `PYTHONPATH`, wrote a `.pth` only
for the authorized external LAMMPS installer, and executed the actual
`pgworld.exe doctor` command from a temporary working directory.

Measured artifact:

- wheel: `mechworld_pg-0.1.0.dev0-py3-none-any.whl`;
- SHA-256:
  `3f2884d62609493801194148f5b8387178799a37548cb7ed52832e0546b2a4db`;
- strict payload allowlist: passed;
- default isolated build: exit 0 in 9.617 s;
- fresh venv creation: exit 0 in 16.454 s;
- exact locked dependency install: exit 0 in 119.182 s; the captured pip log
  shows every artifact came from the local HTTP cache during the final run;
- wheel install: exit 0 in 1.859 s;
- `pip check`: exit 0 in 0.836 s, `No broken requirements found.`;
- all 28 locked distribution versions matched exactly;
- installed smoke: exit 0 in 12.094 s;
- installed profile tamper rejection: exit 0 in 0.148 s.

The temporary fresh venv was
`C:\Users\mzora\AppData\Local\Temp\pytest-of-mzora\pytest-211\test_wheel_installs_profiles_l0\fresh-venv`.
All `pgworld` and twelve legacy module paths resolved below that venv's
`Lib\site-packages`. `lammps.__file__` resolved to
`C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python\lammps\__init__.py`.
No `sys.path` entry was below either checkout. The temporary artifact was not
retained in the source tree.

The wheel's exact member list, commands, exit codes, runtimes, pip output,
locked versions, module paths, full doctor report, profile hashes, and limits
are machine-readable in `wheel-install.json` (SHA-256
`edc2567c7eb65b8c1e0c171ee3c9a6515b6a4d979094bbab34f232220556c3fe`).

## Installed scientific fixtures

- `pgworld doctor` used profile `legacy_python_2026_03_12_v1` with canonical
  hash
  `sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b`,
  recorded `legacy_unreviewed_reproduction_only`, explicitly recorded
  `biological_parameter_certification=false`, reproduced all analytical energy
  checks, used LAMMPS `20260902`, and closed.
- Installed P01-06 harmonic analytical-versus-LAMMPS comparison had energy
  error `0.0 pN nm`, maximum force error `0.0 pN`, and maximum virial error
  `0.0 pN nm`; the solver closed.
- Installed P01-07 periodic harmonic-ring tangent started seven LAMMPS
  instances and closed seven; `all_instances_closed=true`, version `20260902`,
  `physical_time_claim=false`.
- All four immutable packaged hashes matched their accepted values. Mutating
  installed harmonic `K` to 1 caused `PhysicsProfileError` with a different
  computed canonical hash.

## Cleanup, provenance, and limits

- `git status` found no source-tree `build/`, `dist/`, or egg-info artifact.
- `git diff --check a0d625994d593c236195dda2734c62111d201ea1..a9d6d690e89a761758acc1ac3e72f98087278543`
  exited 0 after the explicit EOF-whitespace correction.
- The wheel payload contains only the declared package modules/resources,
  twelve named legacy modules, and five dist-info files. Tests, evidence,
  results, data, checkpoints, restarts, dumps, images, artifacts, and caches are
  absent.
- The repository has no tracked license/notice; none was invented. Package
  authorship metadata was omitted because commit identity does not establish
  inherited software or manuscript authorship.
- LAMMPS is external and has no distribution metadata. The lock is exact for
  this verified workstation, not universally binary-reproducible.
- These checks do not certify biological parameters, experiments, rupture,
  physical time, production campaigns, public release, or manuscript claims.
  `reports/gates/G1.candidate.json` is not gate acceptance.
