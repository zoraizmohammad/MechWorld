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
* Current: 0.13+/-0.8
* Sources:
   * 
* Trust? Need access to paper

Network Density:
* Current: 0.53361 - 0.7086244
* Sources:
   * Wientjes FB, Woldringh CL, Nanninga N. Amount of peptidoglycan in cell walls of gram-negative bacteria. J Bacteriol. 1991 Dec;173(23):7684-91. doi: 10.1128/jb.173.23.7684-7691.1991. PMID: 1938964; PMCID: PMC212537.
   * see Sacculus Pre-Strain
* Trust? 

Peptide & Glycan Bond Energies:
* Current: See Nguyen et al 2015, Glycan Mechanical Properties & Peptide CrossLink Mechanical Properties
* Justification: Simulations of molecules in Nguyen et al 2015.
* Trust? Sure

Glycan Length Distribution:
* Current: Flory-Schulz w/ Min 2, Max 30, Alpha 0.9.
* Justification: 
   * Koch 2000
* Trust? At the least, we should not ignore the tail of strands longer than 30. There is evidence for very long strands of over 200 nm in other, more recent AFM measurements from Turner 2018.

# 3/2/2026
Work this week:
* Caching results of pores to reduce reanalysis
* Distribution now specified on a per-network basis instead of as global
* Scripts to properly calculate elastic moduli at each step of strain, "pleasantly" parallel way. Then results are combined into single file per network.
* Double-checked crosslink calcs, test cases -> no errors found.

Results to discuss:
* Comparison of FS distributions
* Energy approximation -> significantly off

Before friday's meeting:
* [x] Check whether this longer distribution changes the minimum network patch size we must analyze (300 DSU -> ?).
* [x] Calculate young's modulus in the new distribution 2-100, a=0.925
* [ ] Calculate pore distribution and compare to Turner 2018
* [ ] I'm going to make functions to analyze the metrics from Turner 2018 -> It has AFM measurements of orientation and pore size that we can directly compare against. It also makes an argument for much longer glycan molecules, measuring some at ~200 nm (195 DSU).

# 3/9/2026
Work this week:
* Added ability to cleanly specify when to output certain results (based on strain) and also insert specific strains into the autogenerated steps.
* Ran longer networks of length 200 and 400 DSU. It appears that dependence on network size has changed, 300 DSU might not be large enough.
* Calculated elastic moduli for 300 DSU, a=0.925. Created plot vs strain. Hand-checked a sample step at 0.13->0.131 strain.

Todo:
* [x] Reduce tolerance for elastic coefficent calculations (ftol = 1E-10, etol = 0)
* [x] Only consider patch extension to determine coefficients, not compression (relaxation).
* [x] Autogenerated filenames with moduli, rename extension to .moduli
* [ ] Compare sizes of 300, 350, 400, 450, 500 to see what we can use and record runtimes. 10 samples of each.
* [x] Understand how the Young's Modulus ratio of ~4:1 can result in a ~2:1 stress ratio during isotropic strain -> see handwritten note, basically poisson ratio plays a large enough role.
* [x] Add Vyx to modulus structure
* [x] Calculate inverse of stiffness matrix, get Young's modulus like this: M-1(1,1) = 1/Yx, etc
   * Inputs: network filepath, outputs: print errors as table in cli
* [ ] Compare pore sizes for 0.13
* [ ] Compare Turner 2018 metric of orientation against our parameter of 0.72

# 3/13/2026
* Justifying ratio of elastic coefficents. 
   * The elastic coefficents, at least for the alpha=0.72 case, are consistent with the 2:1 stress ratio during isotropic deformation.
   * The poisson ratio Vxy is 0.3->0.2 during the sweep of isotropic pre-strain. (x is transverse/induced, y is axial/applied)
   * The poisson ratio Vyx is ~0.8-0.9. (y is transverse/induced, x is axial/applied). This means that if you were to take the PG and stretch it along the longitudinal direction, the hoop direction would significantly contract. In fact, the area of the 2D surface would almost be unchanged.
   * These poisson ratios are physically possible for a non-isotropic material as their product is smaller than 1/2.
* The "great re-uniting". Realized that virial pressure in 2D is force/length, not force/area. Redid and double-checked all the units. Moduli are looking a LOT BETTER! But I need to rerun my networks, old results have wrong units for spring constants (nN/nm, should be pN/nm).

Concerns/observations/question:

1. Determining prestrain that corresponds to a biological scenario...
   - Equating sigma_xx (axial) and sigma_yy (hoop) to turgor pressure?

2. What is a truly "relaxed" state of the network. As strain occurs, I can observe a point where relative energy fraction starts to shifts from peptides to glycans.