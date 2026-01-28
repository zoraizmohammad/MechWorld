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
#PEPTIDE_COEFFICIENTS = (0.1709, 0.9065, 4.0878);
PEPTIDE_COEFFICIENTS = (0.185328520541486, 1.0, 4.034069292365436); # Another curve fit with prescribed slack length instead of best fit to WLC
PROBABILITY_DSU_CAN_ATTEMPT_TO_FORM_PEPTIDE = 0.8; # Improves percolation of the network for a given cross-linking ratio by nudging density up.

# https://en.wikipedia.org/wiki/KT_(energy)
# 1 kT = 4.11E-21 J at 298K
E_PEPTIDE_CUTOFF = 1 * 4.11E-21 * 1E18; # kT -> 
PEPTIDE_SEARCH_RADIUS = 2; # nm

INITIAL_MINIMIZATION_ITERATIONS = 10E3;
RUNITER = 200E3;