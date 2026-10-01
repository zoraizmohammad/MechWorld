# Packaging and legacy migration status

P01-11 introduces an installable `mechworld-pg` distribution without replacing
the inherited simulator. The supported console surface is exactly:

```text
pgworld doctor
```

`tools/doctor.py` remains as a source-checkout compatibility wrapper. Both
routes execute the same package implementation and emit the same structured
JSON schema. The bonded fixture now obtains its coefficients through the
bundled immutable `legacy_python_2026_03_12_v1` profile and records that
profile's ID, canonical hash, units, review status, and lack of biological
parameter certification.

## Installed contents

The wheel contains the `pgworld` package, including the physics oracles, local
run manager, CLI/doctor, and all four immutable physics profiles. The profile
JSON resource content matches the accepted Git blobs exactly after normalizing
only Git's platform CRLF checkout materialization to canonical LF in
`configs/physics/`; the originals remain unchanged. The registered IDs and
canonical hashes remain:

- `legacy_python_2026_03_12_v1` —
  `sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b`;
- `legacy_direct_isotropic_pre_unit_fix_v1` —
  `sha256:9307aa15c01a557f671fff08d50793dccbf4837f0cd3c78eb0d3d9d7ab3b1df0`;
- `legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1` —
  `sha256:b005c666d187538d60bbe6f924959473d6823e2287089e11621a1fc0dbc43771`;
- `reviewed_physics_provisional_v0` —
  `sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5`.

The wheel intentionally installs these inherited core modules because the
verified mechanics and analysis adapters still import them by their historical
top-level names:

```text
assemble_pg_network
import_data_from_dumps
lammps_PG_objects
process_elastic_tensor
process_network_ensembles
process_orientation
process_pores
run_lammps_elastic_tensor
run_lammps_isotropic_strain
simulation_constants_settings
units
utils_helpers
```

Figure drivers, result scripts, sandbox scripts, cluster submission scripts,
task drivers, private data, results, evidence, checkpoints, restart files,
dumps, and images are not installed. A strict wheel-member allowlist tests this
boundary. This is a compatibility package, not a public release bundle.

## Legacy elastic task

`src/task_compute_elastic_tensor.py` no longer runs or deletes a restart during
ordinary use. It fails closed with guidance because a raw restart does not
contain the reference/base-state metadata required for a validated P01-07 raw
tangent migration. Forensic use requires the explicit
`--allow-legacy-forensic-output` flag and is labeled as the inherited
positive-only, default-pressure, symmetrized route. The exact lexical restart
is retained by default. Deletion requires a separate `--delete-restart` flag,
occurs only after a true success result, and symbolic-link inputs are rejected.
False returns and exceptions preserve the input.

No claim is made that the inherited restart route now produces a validated raw
tangent artifact. New scientific work should use the P01-07 raw tangent API.

## Python and dependency contract

`pyproject.toml` uses the setuptools PEP 517 backend, requires Python 3.11 or
newer, and pins the verified build inputs (`setuptools==65.5.0` and
`wheel==0.45.1`). `requirements.lock` records the exact active Python closure
used for the clean-install test on this CPython 3.11 Windows workstation,
including build/test roots. `requirements.txt` delegates to that lock.

LAMMPS 20260902 is different: this workstation supplies its Python package and
native libraries from the external installer at:

```text
C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python
```

That module has no Python distribution metadata, so it cannot truthfully be
represented as a normal pip-locked wheel. The clean test creates a fresh venv,
installs every locked Python distribution, runs `pip check`, then adds only the
authorized LAMMPS installer path through a `.pth` file. Consequently, the lock
is exact for the verified workstation but is not a universal binary lock.

The seven inherited nested-f-string failures were repaired only by changing
the inner quote delimiter. A tracked-source regression compiles every Git
tracked `.py` file under Python 3.11.

## Provenance and release boundary

The distribution metadata deliberately does not declare Mohammad Zoraiz—or
anyone else—as the author. The requested Git identity applies to new commits;
it does not settle inherited software authorship or manuscript authorship. The
repository has no tracked `LICENSE`, `COPYING`, or `NOTICE`, which remains a
release blocker requiring owner review rather than an invented license.

This migration does not approve biological parameters, experimental data,
production compute, public distribution, or manuscript submission. The
provisional profile remains pending review, and G1 acceptance belongs to the
integrator after independent audit.
