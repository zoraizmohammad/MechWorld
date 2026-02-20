# What level of pre-strain on the PG network is biologically representative?

import numpy as np

# Literature:
# Octavio's continuum paper cites an observed pre-strain of 0.13 +- 0.08 
# https://www.biorxiv.org/content/10.1101/2025.01.20.633943v1.full.pdf

# https://pubmed.ncbi.nlm.nih.gov/1938964/
nm2_per_DSU = 2.5;
DSU_per_nm2 = 1/nm2_per_DSU
DSU_length = 1.1; # nm
observed_density_under_pre_strain = DSU_per_nm2*(DSU_length**2) # number_of_DSU / DSU_length**2
pre_strain = np.array([0.13-0.08, 0.13, 0.13+0.08, 0.30]);
relaxed_density = observed_density_under_pre_strain * (1+pre_strain)**2

print("Relaxed Density (LB,MEAN,UB): ", relaxed_density)

# To a 1st-order estimate, we have a few approaches:

# Pressure Vessel Model
# sigma_yy = PR          # Stress Per Unit of Wall Depth
# sigma_xx = PR/2        # Stress Per Unit of Wall Depth

P = np.array([0.3, 2.0]) * 101325            # atm -> Pa N/m2
V = np.array([0.6, 0.7]) * (1E-6)**3         # 0.6-0.7 um3
R = np.array([0.25,1.0]) * (1/2) * 1E-6      # D is 0.25 - 1.0 um https://en.wikipedia.org/wiki/Escherichia_coli
t = 4 * 1E-9 # m

# Lower Bound
sigma_yy = P[0]*R[0];   # N/m
sigma_xx = P[0]*R[0]/2; # N/m
print("Lower Bound for Stress: ", sigma_xx, sigma_yy)

# Upper Bound
sigma_yy = P[1]*R[1];   # N/m
sigma_xx = P[1]*R[1]/2; # N/m
print("Upper Bound for Stress: ", sigma_xx, sigma_yy)

# Interestingly, our simulations seem to be in the right ballpark before pre-strains of about 0.2

# Literature

# Energy Model
Energy_done_by_gas = P[0]*V[0]