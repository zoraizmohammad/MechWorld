# What level of pre-strain on the PG network is biologically representative?

import numpy as np
from simulation_constants_settings import *

# Literature:
# Octavio's continuum paper cites an observed pre-strain of 0.13 +- 0.08 
# https://www.biorxiv.org/content/10.1101/2025.01.20.633943v1.full.pdf

# https://pubmed.ncbi.nlm.nih.gov/1938964/
nm2_per_DSU = 2.5;
DSU_per_nm2 = 1/nm2_per_DSU;
DSU_length = 1.1; # nm
observed_density_under_pre_strain = DSU_per_nm2*(DSU_length**2); # number_of_DSU / DSU_length**2
pre_strain = np.array([0.13-0.08, 0.13, 0.13+0.08, 0.30]);
relaxed_density = observed_density_under_pre_strain * (1+pre_strain)**2

print("Relaxed Density (LB,MEAN,UB): ", relaxed_density)

# To a 1st-order estimate, we have a few approaches:
# Pressure Vessel Model
# sigma_yy = PR          # Stress Per Unit of Wall Depth
# sigma_xx = PR/2        # Stress Per Unit of Wall Depth

P = np.array([0.9, 1.2]) * 101325            # atm -> Pa N/m2
#V = np.array([0.6, 0.7]) * (1E-6)**3         # 0.6-0.7 um3
R = np.array([0.7,1.0]) * (1/2) * 1E-6      # D is 0.25 - 1.0 um https://en.wikipedia.org/wiki/Escherichia_coli
t = 4 * 1E-9 # m

# Lower Bound
sigma_yy = P[0]*R[0];   # N/m
sigma_xx = P[0]*R[0]/2; # N/m
print("Lower Bound: sigma_xx = ", sigma_xx, ", sigma_yy = ", sigma_yy)

# Upper Bound
sigma_yy = P[1]*R[1];   # N/m
sigma_xx = P[1]*R[1]/2; # N/m
print("Upper Bound: sigma_xx = ", sigma_xx, ", sigma_yy = ", sigma_yy)

# This is about 3-5 times higher than what is observed in the simulations (as of 2/25/2026)

### ENERGY METHOD
# If we imagine the PG layer as an inflated balloon, 
# we would expect it to store potential energy equal to the work done on it by the internal fluid?

# So the entire sacculus would have a potential energy of (P-P0)*(V-V0). We can scale that to a energy/area metric and compare it against the patch.

# We have estimations on these values from the work of Cayley et al, 2000
# https://www.cell.com/biophysj/fulltext/S0006-3495(00)76726-9?_returnURL=https%3A%2F%2Flinkinghub.elsevier.com%2Fretrieve%2Fpii%2FS0006349500767269%3Fshowall%3Dtrue

V0 = 1.4 * u_FEMTOLITER_to_NANOMETER_CUBED;
P0 = 0;
V1 = 2.0 * u_FEMTOLITER_to_NANOMETER_CUBED;
P1 = 1.5 * u_ATM_to_NANO_PRESSURE;

# E = int(Vf,V0,P_cell(V)dV - [P_atm * (Vf - V0)]
# E = int(Vf,V0,(P_cell(V)-P_atm)dV

# Trapezoidal Approximation
# E ~ (1/2)*((Pf-Patm) + (P0-Patm))*(Vf-V0)

# Better Approximation
# Better approximation of this integral: fit a polynomial to the data points given, then integrate on that

sacculus_energy = (1/2)*(P1+P0)*(V1 - V0);
sacculus_surface_area = 8.1 * u_MICROMETER_to_NANOMETER**2; #nm2
patch_relaxed_length_DSU = 300;
patch_strained_surface_area = (patch_relaxed_length_DSU * pre_strain[1] * DSU)**2; # nm2

expected_patch_energy = (sacculus_energy/sacculus_surface_area) * patch_strained_surface_area;
print(expected_patch_energy);

# THESE VALUES SEEM WAY TOO HIGH by ~100x