# 12/22/2025

Areas of focus, discussed last time:
1. [x] Produce a figure showing the distribution of strain in peptide bonds (done, see process_deformed_state).
1. [x] Revisit lammps modulus examples to understand math (done, see handwritten notes)
1. [x] Adapt lammps modulus example to 2D Peptoglycan (done, see ELASTIC_2D_ZERO_TEMP/)
1. [x] Compare lammps method to force-tally method, should it agree? (Not exactly. lammps gives volume-average, force-tally has one specific plane)

Other things:
1. [ ] Produce figure to show relative energies of bonds/angles. This is blocked, lammps is not producing the outputs I'd expect. (analogous to 2.6B)
1. [?] Produce a figure showing non-linear stress-vs-strain curves for different levels of isotropy. (analogous to 2.6D)
1. [?] Produce a figure showing ratio of longitudinal (x) and circumferential (y) stresses for different levels of isotropy. (analogous to 2.6E)

Concerns/observations/question:
1. LAMMPS command of `compute bond` is not producing expected output. It seems to return all zeros.
1. Expected output for non-linear curves for 2.6D and 2.6E, might be a consequence of density.
1. Now using 1.03 nm from Xaoxuan 2024 as reference length everywhere.
1. What is the ideal starting density parameter for the network? Current = 0.7
    - To achieve a cross-linking percentage of 40% - 60%, the density parameter must be between 0.5 (~0.43 cross-linking) and 0.7 (~0.63 cross-linking).
    - Comparison against literature suggests that the density parameter should be... to be determined. Variability is very high based on life stage. No concrete numbers from the papers I have access to.
        - https://academic.oup.com/femsre/article/32/2/149/2683904
        - https://journals.asm.org/doi/epub/10.1128/mmbr.62.1.181-203.1998
1. Some random networks can be majorly defective. Regions without bonds may become obvious as deformation happens. This is more likely at lower densities.
    - Network rejection criteria? Number of bonds in each subarea?