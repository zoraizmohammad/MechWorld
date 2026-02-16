# Constants
from math import sqrt

def inv_lammps_nonlinear(energy, epsil, r0, lambd) -> tuple[float, float]:
    # epsil*(r-r0)**2 / (lambd**2 - (r-r0)**2) = ENERGY
    # epsil*(r-r0)**2 = ENERGY * (lambd**2 - (r-r0)**2)
    # epsil*(r-r0)**2 = ENERGY*lambd**2 - ENERGY*(r-r0)**2
    # (epsil+ENERGY)*(r-r0)**2 - ENERGY*lambd**2 = 0;
    # This is quadratic in (r-r0), as others are constants
    # a =  (epsil+ENERGY)
    # c = -(ENERGY*lamd**2)
    # x = +-sqrt(-4*a*c) / 2a
    # r = x + r0
    a =  (energy+epsil);
    c = -(energy*lambd**2);
    r1 = r0 - sqrt(-4*a*c) / (2*a);
    r2 = r0 + sqrt(-4*a*c) / (2*a);
    return (r1, r2)

def inv_peptide_energy_lammps(energy):
    return inv_lammps_nonlinear(energy, PEPTIDE_COEFFICIENTS[0], PEPTIDE_COEFFICIENTS[1], PEPTIDE_COEFFICIENTS[2])

# Constants
DSU = 1.03; #nm # Should it be 1.03 or 2? Xioxuan 2024 vs. Nyugen 2015

# CHECK CURVE FIT FOR DIMENSIONAL ACCURACY
# Nyugen 2015 says that the DSU length should be 2 nm
# Xaoxuan uses 1.03 nm for this value
#  -> what should we proceed with?

BOND_TYPE_GLYCAN = 1;
BOND_TYPE_PEPTIDE = 2;
ANGLE_TYPE_GLYCAN = 1;
ATOM_TYPE_POS_DSU = 1; # + orientation
ATOM_TYPE_NEG_DSU = 2; # - orientation

# https://en.wikipedia.org/wiki/Peptidoglycan
# https://en.wikipedia.org/wiki/N-Acetylglucosamine
# https://en.wikipedia.org/wiki/N-Acetylmuramic_acid
DSU_MOLAR_MASS = (221.21 + 293.272)/2;    # grams / mol
A_NUM = 6.02214076E23;                    # molecules / mol
DSU_MASS_GRAM = DSU_MOLAR_MASS / A_NUM;   # grams / molecule
DSU_MASS_ATTOGRAM = DSU_MASS_GRAM * 1E18; # ag / molecule

GLYCAN_COEFFICIENTS = (5.570, DSU);
PEPTIDE_COEFFICIENTS = (0.185328520541486, 1.0, 4.034069292365436); # Another curve fit with prescribed slack length instead of best fit to WLC
PROBABILITY_DSU_CAN_ATTEMPT_TO_FORM_PEPTIDE = 1.1; # Improves percolation of the network for a given cross-linking ratio by nudging density up.

# https://en.wikipedia.org/wiki/KT_(energy)
# 1 kT = 4.11E-21 J at 298K
E_PEPTIDE_CUTOFF = 1.5 * 4.11E-21 * 1E18; # kT
PEPTIDE_ANG_TOL_DEGREES = 90; # degrees
PEPTIDE_SEARCH_RADIUS = inv_peptide_energy_lammps(E_PEPTIDE_CUTOFF)[1] + 0.2; # nm

INITIAL_MINIMIZATION_ITERATIONS = 10E3;
RUNITER = 200E3;