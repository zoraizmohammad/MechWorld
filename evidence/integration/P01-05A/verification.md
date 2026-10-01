# P01-05A integration verification

Accepted implementation revision before the evidence/state commit: `c41c58a`
on `main`. The returned commits were reviewed for isolated path ownership and
retain Mohammad Zoraiz <zoraizmohammad@gmail.com> as sole author and committer.

The first implementation pass was not accepted immediately. Independent review
found that it conflated historical default-pressure behavior with the new
virial-only output policy and allowed an arbitrary expanded snapshot to be
paired with a registered ID/hash. The exact forged-snapshot red regression and
both correction cycles are preserved under `evidence/subagents/P01-05A/`.
Final independent review accepted the corrected contract.

| Check | Exact command | Exit | Measured result | Artifact / SHA-256 |
|---|---|---:|---|---|
| Focused acceptance | `.venv\Scripts\python.exe -B -m pytest tests/physics/test_physics_profiles.py -q --junitxml=evidence/integration/P01-05A/focused.xml` | 0 | 15 passed in 0.34s; wrapper 0.887s | `focused.xml`; `a15c0d77cd03917c0c696326e63de6388734838707c815b6a402174ccf7d4bb0` |
| Generator/observable compatibility | `.venv\Scripts\python.exe -B -m pytest tests/unit/test_generator_reproducibility.py tests/physics/test_structural_observables.py -q --junitxml=evidence/integration/P01-05A/compatibility.xml` | 0 | 33 passed in 1.77s; wrapper 2.509s | `compatibility.xml`; `4d14b462aa1b61a6a34d03432b10ebf4769bcbb66404dc41cb47d3d093fa9ea0` |
| Full merged suite | `.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence/integration/P01-05A/full.xml` | 0 | 127 passed in 3.42s; wrapper 4.292s | `full.xml`; `ac66f71817ce54baba1089c6b6f9ae32ea787dca63c1a079a3bad570799e0f03` |
| Strict load, canonical round trip, and persisted-snapshot read-back | `.venv\Scripts\python.exe -B -c "... load_physics_profile ... validate_expanded_profile_snapshot ..."` | 0 | all four registered profiles passed | console result |
| Forged expanded-snapshot probes | same bounded Python command; mutate current-profile harmonic `K` to `1.0`, then try direct construction and persisted-snapshot validation | 0 | `FORGED_SNAPSHOT_REJECTIONS=2` | console result; original failing regression in `evidence/subagents/P01-05A/forged-red.txt` |
| Source compilation without bytecode output | `.venv\Scripts\python.exe -B -c "... compile(...) ..."` | 0 | profile loader and tests compiled | console result |
| Whitespace/conflict check | `git diff --check facd80c..HEAD` | 0 | no errors | console result |
| Returned ownership | path filter over `git diff --name-only facd80c..HEAD` | 0 | `OUTSIDE_OWNERSHIP=NONE` | console result |
| Commit identity | `git log --format='%an <%ae>|%cn <%ce>' facd80c..HEAD` plus exact identity check | 0 | `COMMIT_IDENTITIES=MOHAMMAD_ONLY` | console result |
| Root task-DAG/state validation after acceptance | PowerShell JSON parse, unique/dependency/evidence/mandatory-state checks, Kahn acyclicity pass, and eligibility query | 0 | 74 tasks, 73 mandatory; only `P01-06` eligible | console result |

Final registered identities:

- `legacy_python_2026_03_12_v1`:
  `sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b`;
- `legacy_direct_isotropic_pre_unit_fix_v1`:
  `sha256:9307aa15c01a557f671fff08d50793dccbf4837f0cd3c78eb0d3d9d7ab3b1df0`;
- `legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1`:
  `sha256:b005c666d187538d60bbe6f924959473d6823e2287089e11621a1fc0dbc43771`;
- `reviewed_physics_provisional_v0`:
  `sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5`.

The profiles freeze route-specific numerical coefficient families and explicit
provenance. They distinguish historical default LAMMPS thermo pressure and
retained NVE/deform behavior from the required configurational-virial-only
policy for new outputs and reanalysis. The direct-isotropic route correctly
records no tangent output. Every legacy historical entry point must be present
in both repository-source records and provenance routes.

This accepts only the provisional computational contract. It does not validate
the biological coarse-graining, nonlinear fit, angle-resolution mapping,
physical time, a wall thickness, rupture thresholds, or a final reviewed
profile. P01-05 remains blocked on actual human scientific review. P01-06 owns
the independent analytical/finite-difference/LAMMPS energy, force, and virial
fixtures; existing runners have not yet been migrated to the declarative new
output policy.
