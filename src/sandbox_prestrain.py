# What level of pre-strain on the PG network is biologically representative?

import numpy as np
from simulation_constants_settings import *

# Literature:
# Octavio's continuum paper cites an observed pre-strain of 0.13 +- 0.08 
# https://www.biorxiv.org/content/10.1101/2025.01.20.633943v1.full.pdf

# https://pubmed.ncbi.nlm.nih.gov/1938964/
# Wientjes 1991
nm2_per_DSU = 2.5;
DSU_per_nm2 = 1/nm2_per_DSU;
nm_per_DSU = 1.1; # nm
rho_under_prestrain = DSU_per_nm2*(nm_per_DSU**2); # number_of_DSU / DSU_length**2

# Rojas 2018
a = 0.25;
b = 0.05;
prestrain = np.array([a-b, a, a+b, 0.30]);
rho_relaxed = rho_under_prestrain * (1+prestrain)**2

print("Relaxed Density (LB,MEAN,UB): ", rho_relaxed)

# To a 1st-order estimate, we have a few approaches:
# Laplace Pressure Vessel Model
# tension_yy = PR          # Stress Per Unit of Wall Depth
# tension_xx = PR/2        # Stress Per Unit of Wall Depth

turgor_pressure_Pa = np.array([0.9, 1.2]) * u_ATM_to_PASCAL # atm -> Pa N/m2
#turgor_pressure_Pa = np.array([0.28, 0.32]) * u_ATM_to_PASCAL # atm -> Pa N/m2
diameter_um = np.array([0.7,1.0])
radius_m = (diameter_um/2) * 1E-6 # D is 0.25 - 1.0 um https://en.wikipedia.org/wiki/Escherichia_coli
t = 6 * 1E-9 # m

# Lower Bound
tension_yy = turgor_pressure_Pa[0]*radius_m[0];   # [N/m]
tension_xx = turgor_pressure_Pa[0]*radius_m[0]/2; # [N/m]
print("Lower Bound: sigma_xx = ", tension_xx, ", sigma_yy = ", tension_yy)

# Upper Bound
tension_yy = turgor_pressure_Pa[1]*radius_m[1];   # [N/m]
tension_xx = turgor_pressure_Pa[1]*radius_m[1]/2; # [N/m]
print("Upper Bound: sigma_xx = ", tension_xx, ", sigma_yy = ", tension_yy)

# stress = tension / thickness

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
P1 = 1.5 * u_ATM_to_LAMMPS_PRESSURE;

# E = int(Vf,V0,P_cell(V)dV - [P_atm * (Vf - V0)]
# E = int(Vf,V0,(P_cell(V)-P_atm)dV

# Trapezoidal Approximation
# E ~ (1/2)*((Pf-Patm) + (P0-Patm))*(Vf-V0)

# Better Approximation
# Better approximation of this integral: fit a polynomial to the data points given, then integrate on that

sacculus_energy = (1/2)*(P1+P0)*(V1 - V0);
sacculus_surface_area = 8.1 * u_MICROMETER_to_NANOMETER**2; #nm2
patch_relaxed_length_DSU = 300;
patch_strained_surface_area = (patch_relaxed_length_DSU * prestrain[1] * DSU)**2; # nm2

expected_patch_energy = (sacculus_energy/sacculus_surface_area) * patch_strained_surface_area;
print(f"Estimated PE of network (size = {patch_relaxed_length_DSU}, strain = {prestrain[1]}): ",expected_patch_energy);

# Local Deformation for Size Increase with Constant Aspect Ratio

def total_patch_dimensions(total_rod_length, aspect_ratio):
    width = total_rod_length / aspect_ratio;       # diameter
    cylinder_axial_length = total_rod_length - width;
    cylinder_hoop_length = np.pi*width;

    return cylinder_axial_length, cylinder_hoop_length;

w0, h0 = total_patch_dimensions(1, 4);
w1, h1 = total_patch_dimensions(2, 4);

patch_strain_x = (w1-w0)/w0
patch_strain_y = (h1-h0)/h0

print(patch_strain_x,patch_strain_y)

# Okay, so the patch experiences isotropic deformation as the cell expands with a constant aspect ratio
# just needed to double check that