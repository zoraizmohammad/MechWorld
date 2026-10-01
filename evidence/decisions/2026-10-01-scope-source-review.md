# 2026-10-01 scope/source review

Two independent read-only subagents reviewed the human decisions against the live task graph and physics audit. Neither edited the repository.

- Decision reconciliation: P00-06 can close because scope, primary endpoint, resource policy, release authority, and explicit unknowns now have owners; P01-05 must remain blocked for biological certification. A separate mandatory P01-05A computational-contract task is required to unblock bounded numerical work honestly.
- Physics review: the decisions and derivations are internally consistent for a provisional computational contract. They do not certify coarse-graining, the nonlinear fit, angle refinement, mass/time, experiments, or rights.

Primary-source findings checked on 2026-10-01:

- [Nguyen et al.](https://www.pnas.org/doi/10.1073/pnas.1504281112) state that each bead represents two disaccharides and report `kg=5570 pN/nm`, `lg=2.0 nm`, and `kb=8.36e-20 J`; this does not identify the repository's 1.03 nm edge mapping.
- [LAMMPS harmonic bonds](https://docs.lammps.org/bond_harmonic.html) use `E=K(r-r0)^2` with the conventional one-half included in `K`.
- [LAMMPS nonlinear bonds](https://docs.lammps.org/bond_nonlinear.html) define epsilon as energy.
- [LAMMPS pressure](https://docs.lammps.org/compute_pressure.html) uses area in 2D and includes a kinetic term unless a virial-only compute is selected.
- [LAMMPS box relaxation](https://docs.lammps.org/fix_box_relax.html) changes box size/shape during minimization toward a target pressure/stress; it is a distinct preparation protocol.
- [Rojas et al.](https://pubmed.ncbi.nlm.nih.gov/30022160/) show that whole-cell *E. coli* mechanics include a substantial outer-membrane contribution, so whole-cell AFM stiffness cannot be assigned to PG alone.

This is a source/decision audit, not physics-profile implementation, LAMMPS oracle evidence, experimental access, or biological validation.
