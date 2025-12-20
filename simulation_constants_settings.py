# Constants
DSU = 2; #nm # Should it be 1.03 or 2? Xioxuan 2024 vs. Nyugen 2015
BOND_TYPE_GLYCAN = 1;
BOND_TYPE_PEPTIDE = 2;
ANGLE_TYPE_GLYCAN = 1;
ATOM_TYPE_POS_DSU = 1; # + orientation
ATOM_TYPE_NEG_DSU = 2; # - orientation

# https://en.wikipedia.org/wiki/KT_(energy)
#E_PEPTIDE_CUTOFF = 4.11E-21 * 1E18; # 1 kT = 4.11E-21 J, 1 J = 1E18 attogram-nm2/ns2

# https://en.wikipedia.org/wiki/Peptidoglycan
# https://en.wikipedia.org/wiki/N-Acetylglucosamine
# https://en.wikipedia.org/wiki/N-Acetylmuramic_acid
DSU_MOLAR_MASS = (221.21 + 293.272)/2; # grams / mol
A_NUM = 6.02214076E23;                 # molecules / mol
DSU_MASS_GRAM = DSU_MOLAR_MASS / A_NUM; # grams / molecule
DSU_MASS_ATTOGRAM = DSU_MASS_GRAM * 1E18; # ag / molecule

GLYCAN_COEFFICIENTS = (5.570, 2.00);
PEPTIDE_COEFFICIENTS = (0.1709, 0.9065, 4.0878);