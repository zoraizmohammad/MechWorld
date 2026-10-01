# Primary References and Execution Documentation

Consulted September 30, 2026. Pin the actual installed software versions and verify that the applicable documentation matches them. This is a foundational reading list, **not** a completed novelty survey. The agent must update the search for dynamic-topology/fracture learning, hybrid stochastic simulators, and PG mechanics before making priority claims. Exact biological coefficients remain subject to recovery of their original sources and lab review.

## Agent workflow

**S01 — OpenAI: Custom instructions with AGENTS.md.** Project guidance discovery; keep root instructions compact and reference the larger plan explicitly.
`https://developers.openai.com/codex/guides/agents-md`

**S02 — OpenAI: Subagents.** Supported delegation and local-client behavior. Inspect the installed client's capabilities rather than inventing flags or assuming automatic worktree isolation.
`https://developers.openai.com/codex/multi-agent`

**S03 — Git: git-worktree.** Explicit isolated working trees for concurrent branches; merges still require review.
`https://git-scm.com/docs/git-worktree`

## LAMMPS mechanics and data

**S04 — units.** Nano-style base units; check derived energy/force units.
`https://docs.lammps.org/units.html`

**S05 — compute pressure.** Area normalization in 2D and global virial contributions.
`https://docs.lammps.org/compute_pressure.html`

**S06 — bond_style harmonic.** Energy convention and factor-of-two relationship to a conventional spring coefficient.
`https://docs.lammps.org/bond_harmonic.html`

**S07 — bond_style nonlinear.** Energy-valued epsilon coefficient, finite-extension potential, and package requirements.
`https://docs.lammps.org/bond_nonlinear.html`

**S08 — fix bond/break.** Event behavior, dependent topology removal, restart limitations, and absence of invocation during minimization.
`https://docs.lammps.org/fix_bond_break.html`

**S09 — dump.** Native formats, row identity/order, orthogonal versus triclinic bounds, and output conventions.
`https://docs.lammps.org/dump.html`

**S10 — compute bond/local.** Endpoint ordering and force/displacement sign semantics; a documented displacement-sign change occurred in the June 12, 2025 version.
`https://docs.lammps.org/compute_bond_local.html`

**S11 — compute stress/atom.** Per-atom virial/stress definitions, angular contributions, and normalization considerations.
`https://docs.lammps.org/compute_stress_atom.html`

**S18 — minimize.** Energy minimization and its convergence/termination semantics.
`https://docs.lammps.org/minimize.html`

**S20 — delete_bonds.** Deletion options and implications for dependent/special interactions. Verify behavior with actual fixtures before building a custom rupture loop.
`https://docs.lammps.org/delete_bonds.html`

## Foundational learned simulators

**S12 — Sanchez-Gonzalez et al., Learning to Simulate Complex Physics with Graph Networks, ICML 2020.** Reference for message-passing learned physical simulation and baseline design; not a novelty claim for this project.
`https://proceedings.mlr.press/v119/sanchez-gonzalez20a.html`

**S13 — Pfaff et al., Learning Mesh-Based Simulation with Graph Networks.** MeshGraphNets; distinguish adaptive computational meshes from material-bond rupture.
`https://arxiv.org/abs/2010.03409`

**S14 — Rubanova et al., Constraint-based graph network simulator.** Prior work on learned constraints/optimization in physical simulation; relevant to a learned relaxation/correction design.
`https://arxiv.org/abs/2112.09161`

## Experimental structure and visualization

**S15 — Turner et al., Molecular imaging of glycan chains couples cell-wall polysaccharide architecture to bacterial cell morphology, Nature Communications (2018).** Structural imaging reference. Review full methods/measurement conditions before quantitative reuse; it is not a substitute for the proposed new measurements.
`https://www.nature.com/articles/s41467-018-03551-y`

**S16 — Three.js: InstancedMesh.** Efficient rendering of many instances and instance-specific transforms/colors; benchmark the actual viewer.
`https://threejs.org/docs/pages/InstancedMesh.html`

**S17 — OVITO: LAMMPS dump reader.** Independent trajectory visualization and import/export checks.
`https://www.ovito.org/docs/current/reference/file_formats/input/lammps_dump.html`

**S19 — Git: git-config.** Repository-local identity configuration. Do not rewrite history or globally change identity.
`https://git-scm.com/docs/git-config`

## Required literature deliverable

Produce a verified related-work matrix with full title, authors/year, source, peer-review status, geometry, physics, state/control model, stochasticity, type of topology change, training/evaluation data, baselines, code/data availability, and what distinguishes this project. Include contrary/overlapping work. If the proposed architecture is not novel, refine the contribution toward a demonstrated capability, benchmark, or biophysical finding; do not suppress prior art.
