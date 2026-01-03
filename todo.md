# 12/22/2025

Areas of focus, discussed last time:

* [x] Produce a figure showing the distribution of strain in peptide bonds (done, see process_deformed_state).

* [x] Revisit lammps modulus examples to understand math (done, see handwritten notes)

* [x] Adapt lammps modulus example to 2D Peptoglycan (done, see ELASTIC_2D_ZERO_TEMP/)

* [x] Compare lammps method to force-tally method, should it agree? (Not exactly. lammps gives volume-average, force-tally has one specific plane)\

- [ ] 

Other things:

* [x] New lammps script that applies isotropic strain and output data needed for figures 2.6B, 2.6D, and 2.6E,

* [ ] Produce figure to show relative energies of bonds/angles. This is blocked, lammps is not producing the outputs I'd expect. (analogous to 2.6B)

* [x] Produce a figure showing non-linear stress-vs-strain curves for different levels of isotropy. (analogous to 2.6D)

* [x] Produce a figure showing ratio of longitudinal (x) and circumferential (y) stresses for different levels of isotropy. (analogous to 2.6E)

- [ ] Notes on these figures: Randomness plays a significant role in these figures. Higher densities lead to more consistent behaviors (fewer large defects), but of course are less representative of PG. A more robust network-averaging sweep would be better.



Next directions:

* [x] Examine rho_gap vs. rho_mesh. Why are they different (arbitrary size, infinite size)? Correct if bug.

1/rho_gap is defined as the horizontal spacing between columns of glycan, and the vertical (ideal) spacing between strands.
rho_mesh is defined as (number_of_atoms * DSU**2) / (simbox_actual_width * simbox_actual_height);

If the vertical gap between glycans is zero, then rho_mesh ~= rho_gap. In this case, the space allocated to each Atom is a box with dimensions of 1 DSU (vertical) by 1/rho_gap DSU (horizontal). Therefore Area/Atom = 1/rho_gap, so Atom/Area = rho_gap. There is a commented section of code that shows this and it can be observed the two variables approach as the box grows.

* [x] Update network assembly script to increase crosslink diversity

Added a first-favored policy where the first peptide between each glycan pair is allowed to have greater energy than subsequent bonds. 
* These extra bonds account for ~11% of all bonds in a 0.5 rho_gap network, and ~19% of all bonds in a 1.0 rho_gap network.
* The 1st bond is allowed to be at 80% of the maximum extension (before minimization of course).

* [ ] Streamline isotropic prestrain to use python lammps library
  
  * [ ] CLI analysis options, no manual file moving/renaming.
  
  * [ ] Multiple-network averaging
  
  * [ ] Figures that agree with expected results?
  
  

Concerns/observations/question:

1. LAMMPS command of `compute bond` is not producing expected output. It seems to return all zeros.
2. Expected output for non-linear curves for 2.6D and 2.6E, might be a consequence of density.
3. Now using 1.03 nm from Xaoxuan 2024 as reference length everywhere.
4. What is the ideal starting density parameter for the network? Current = 0.7
   - To achieve a cross-linking percentage of 40% - 60%, the density parameter must be between 0.5 (~0.43 cross-linking) and 0.7 (~0.63 cross-linking). This is how Xaoxuan's paper did it.
   - Comparison against literature suggests that the density parameter should be... to be determined. Variability is very high based on life stage. No concrete numbers from the papers I have access to.
     - https://academic.oup.com/femsre/article/32/2/149/2683904
     - https://journals.asm.org/doi/epub/10.1128/mmbr.62.1.181-203.1998
5. Some random networks can be majorly defective. Regions without bonds may become obvious as deformation happens. This is more likely at lower densities.
   - Approach? Penalize crosslinks between two glycans with a bunch of crosslinks already. This inflates the percentage. Reward crosslinks between molecules that don't have them, allowing them to have higher initial energy.
   - Network rejection criteria? Number of bonds in each subarea?
   - Find regions with few crosslinks and add them in with higher initial energy.
6- How much prestrain should the network be placed under?
   1- Xaoxuan's thesis was vague about how this is calculated