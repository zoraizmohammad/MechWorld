# 12/22/2025

Areas of focus, discussed last time:

* [x] Produce a figure showing the distribution of strain in peptide bonds (done, see process_deformed_state).

* [x] Revisit lammps modulus examples to understand math (done, see handwritten notes)

* [x] Adapt lammps modulus example to 2D Peptoglycan (done, see ELASTIC_2D_ZERO_TEMP/)

* [x] Compare lammps method to force-tally method, should it agree? (Not exactly. lammps gives volume-average, force-tally has one specific plane)\

Other things:

* [x] New lammps script that applies isotropic strain and output data needed for figures 2.6B, 2.6D, and 2.6E,

* [x] Produce figure to show relative energies of bonds/angles. (analogous to Xaoxuan 2.6B)

* [x] Produce a figure showing non-linear stress-vs-strain curves for different levels of isotropy. (analogous to 2.6D)

* [x] Produce a figure showing ratio of longitudinal (x) and circumferential (y) stresses for different levels of isotropy. (analogous to 2.6E)

- Notes on these figures: Randomness plays a significant role in these figures. Higher densities lead to more consistent behaviors (fewer large defects), but of course are less representative of PG. A more robust network-averaging sweep would be better.

Next directions:

* [x] Examine rho_gap vs. rho_mesh. Why are they different (arbitrary size, infinite size)? Correct if bug.

1/rho_gap is defined as the horizontal spacing between columns of glycan, and the vertical (ideal) spacing between strands.
rho_mesh is defined as (number_of_atoms * DSU**2) / (simbox_actual_width * simbox_actual_height);

If the vertical gap between glycans is zero, then rho_mesh ~= rho_gap. In this case, the space allocated to each Atom is a box with dimensions of 1 DSU (vertical) by 1/rho_gap DSU (horizontal). Therefore Area/Atom = 1/rho_gap, so Atom/Area = rho_gap. There is a commented section of code that shows this and it can be observed the two variables approach as the box grows.

* [x] Update network assembly script to increase crosslink diversity

Added a first-favored policy where the first peptide between each glycan pair is allowed to have greater energy than subsequent bonds. 
* These extra bonds account for ~11% of all bonds in a 0.5 rho_gap network, and ~19% of all bonds in a 1.0 rho_gap network.
* The 1st bond is allowed to be at 80% of the maximum extension (before minimization of course).
* Running this on a 500x500 network w/ rho_gap = 0.5, this policy increased the number of unique glycan pairs from 14611 to 21471. Almost +50% variety.

* [x] Revert to baseline rules for network generation
      * [x] Compare larger patches (500) additional rule -> density vs crosslinking
      * [x] Add function to delete free-floating glycans

* [x] Add 95% confidence intervals to the density vs. crosslinking plot

* [x] Should peptides be slack when length < "slack length"? Look for other models? We were using nonlinear bonds in LAMMPS for the peptides, but it has higher energy for negative strains, which the WLC doesn't. (Though the positive strains made a good curve fit.) Instead, investigate using lepton-style bonds to directly implement the WLC into lammps.
   -> Model in Nguyen 2015 DOES have E increase for r < r0 == 1 nm. I was adjusting the wrong parameter in Mondays working meeting. My fit was updated to consider negative strains, but the non-linear model still looks very close to WLC. New coefficents are the same to within 0.1%.

* [...] Streamline isotropic prestrain to use python lammps library

   Work is in progress

  * [x] Implement IsotropicPrestrain lammps script into python

  * [x] Automate creation and running of multiple networks, no manual file moving/renaming

  * [x] Takes about 2 hours to run 9 networks (200x200 DSU, rho_gap = 0.5)

  * [x] Add a bernoulli test to crosslinking rules (expect this to decrease crosslinking ratio, density of CR=0.6 will be higher, hopefully the percolation will be higher for same CR)

  * [x] Add screenshots of networks before & after deformations
  
  * [x] Network averaging with confidence intervals: Energy fractions

  * [x] Network averaging with confidence intervals: Stress magnitude and axial/hoop ratio

Jan 19th 2026:

[x] Write version of lammps function that uses a sequence of minimizations
    - It takes 1 hour to run a 200x200 DSU network, using 30 steps, using remapping for initial position guesses
    - It takes X hours to run a 200x200 DSU network, using X steps, using no remapping
    - Comparing this on a sample network between the two change_box and one nve method 

[x] Rerun 1.00 ensembles with more minimization iterations (1E4), see if this smoothes the start of stress ratio curves. Another option is to run the deformation for more iterations from strain of 0 to 0.1. (Try: 1E5 for 0 -> 0.1, 1E5 for 0.1 -> 0.3)
   - This helped reduce the craziness at the start, but didn't eliminate it all-together. I think the method going forward should be the "sequence of minimizations"

[x] Plot total system energy vs. strain for ensemble networks.
   [ ] Energy Density metric = E / (lx*ly)
   [ ] See early equations in Triangular network paper. You can get second derivative of energy with respect to strain -> This will give you...

[x] Run initial simulations to examine how patch size influences results
 - Test a smaller set (3 each) of smaller and larger networks, compare to current 200 DSU standard
 - After running, a larger sample size might be necessary...

[x] Add a functions to show ensemble histograms of strain for peptides: 1) initial state, 2) final state

Jan 26th 2026:

[x] Eliminate vertical gap between glycans in the same column. Why? rho_gap = rho_mesh in the limit, reduces impact of network size?

[x] New task! Move things onto Hoffman2 so I can run a crap ton of networks w/o my laptop!
   - Reorganize filesystem a bit
   - Python workflow with CLI
   - Test script with qrsh
      - Single-core works correctly, 100 DSU network gave: 133.9% CPU use with 1 MPI tasks x 1 OpenMP threads, Total wall time: 0:07:33. Requires more than 2G per core.
      - Multi-core (-pe shared 4) worked too, 551.4% CPU use with 1 MPI tasks x 4 OpenMP threads, Total wall time: 0:04:28.
   - Job submission script for SGE, use job array
      - I need load TWO modulefiles: python, intel
      - $ qsub hoffman2-submission-scripts/pg-network-dsu100-sweep-isotropy.sh
      - $ grep --binary-files=text "wall time" joblogs/joblog.12236817
   - Monitor jobs:
      - $ qstat -u jrrm
   - Behold! It works!!!

[x] Examine DSU of size 100,200,300,400 (3 samples, at least, more if time)

[x] Plot ratio of stress for 400 DSU vs 100 DSU, 400 vs 200 DSU, ... 
   - Is the difference due to force chains? Percolation?

[ ] Glycan angle and orientation plots? This would be a big task...

[ ] Start a note to approach interpretation of prestrain, relaxed conditions, etc
    - Reread triangular network paper; it talks about one approach on how to interpret strain on the network
    - Compute expected stress band for turgor pressure / cell size range, does it match?

[ ] See triangular network interpretation of continuum description and how to extract stress
   - 22/23 gives a way to find M from making incremental changes, note that current stress has an impact through R
   - How does young's modulus, poison ratio, etc, change based on the prestrain?

Notes on Octavio's Network Code (2/2/2026):
1. he starts with square grid separated by 1 DSU ("initial unitary grid")
2. Ny is given, so is "density". Nx (length is X direction) is determined based by rho and Ny
3. He enforces that wy = wx
4. Transformation occurs later, as does the number of nodes

Two inputs: Ny [DSU] & density [ATOMS / DSU_LEN**2]
A) as an input to his assembly function, he gives density = 1/((1+esp_x)(1+esp_y))
B) esp_y = esp_x / (1 + avg_rod_length)
C) Nx = np.floor( ((1+esp_y)/(1+esp_x))*Ny )

* The main difference is spacing in the y-direction
* His max displacement is 1/2 of a DSU
* He directly measures the angle between the axes of the glycan
* [!!!] He compares stem vectors against the peptide bond. You can perform a optimization with this knowledge too.
   * Atoms should contain molecule angle and stem vector

It is a square patch in the physical dimension sense (X nm by X nm)

Good idea for me: add length_distribution function with more obvious inputs

Note: He doesn't delete any glycans that have no peptides, he just allows them to float.

# 2/23/2026
Completed:
* Extraction of pores from network atoms & bond dumps
* Histogram of pore areas
* Distribution of glycan orientation by length
* Distribution of peptide attachment angle by strain

Goals:
* Compute extensional elastic coefficents as a function of strain
* Compute elastic moduli from elastic coefficents
* Shear strain & shear modulus
   * Lammps script to apply shear strain
   * Python script to calculate shear coefficents as a function of strain
* Compute all elastic coefficents for the results from a network
* Compute all modulus for a single network given isotropic and shear results

Approach #1: Massively Parallel
* At each step of deformation, the main isotropic script writes a restart file to a special folder.
* Another LAMMPS script takes a restart file and calculates the elastic coefficients by applying a small deformation in each direction.
* A python script deploys one job for each of the restarts, these tiny jobs can slip into the queue without much fuss.
* The elastic coefficients for each restart are written to a different files, then a script aggregates them into a single file per network.
* Something like: strain c11 c12 c13 c21 c22 c23 c31 c32 c33
Downsides: lots of files? maybe scripts delete the intermediate steps as we go?

* Double-check cross-linking percentage:
   * How many bonds? How many of each type?
   * How many atoms have the eligible flag?
      * Testing shows expected behavior, after looking at it from multiple angles, and running simple test cases.

* Mess with the distribution, produce results then compare them:
   * Tophat distribution -> min, max
      * Using 20-30 increased energy in an example network by 1.5x - 3x (the multiplier increases with strain)

Solving the force or energy problem:
* Current values are too low, both on energy and force front. Force is off by 3-5x, energy is off by ~5x. I'm going to list the dials we have and how much I trust their current settings.

Crosslinking Percentage:
* Current: 40% - 60%
* Sources: 
* Trust?

Sacculus Pre-strain:
* Current:
* Sources:
* Trust?

Network Density:
* Current:
* Sources:
* Trust?

Peptide & Glycan Bond Energies:
* Current:
* Justification:
* Trust?

Glycan Length Distribution:
* Current: Flory-Schulz with a = 0.9
* Justification:
* Trust? Not so much. Contradicting observations come from _. 

So...
* 

Concerns/observations/question:

1. Determining prestrain that corresponds to a biological scenerio...
   - Equating sigma_xx (axial) and sigma_yy (hoop) to turgur pressure?

2. What is a truely "relaxed" state of the network. As strain occurs, I can observe a point where relative energy fraction starts to shifts from peptides to glycans.