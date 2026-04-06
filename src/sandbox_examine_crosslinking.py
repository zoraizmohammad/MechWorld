from assemble_pg_network import visualize_bonds, compute_crosslink_ratio, form_peptide_bonds, add_simple_glycan, create_peptide_with_nearby_neighbor
from lammps_PG_objects import GlycanMolecule
from math import pi
import matplotlib.pyplot as plt

from simulation_constants_settings import E_PEPTIDE_CUTOFF, PEPTIDE_SEARCH_RADIUS, inv_lammps_nonlinear, PEPTIDE_COEFFICIENTS

custom_energy = E_PEPTIDE_CUTOFF * 10;
(_,custom_radius) = inv_lammps_nonlinear(custom_energy, PEPTIDE_COEFFICIENTS[0], PEPTIDE_COEFFICIENTS[1], PEPTIDE_COEFFICIENTS[2])

atoms = dict()
bonds = dict()
angles = dict()
glycans : dict[int,GlycanMolecule] = dict()

xlo =  0; # must be 0 for peptide formation
xhi =  8;
ylo =  0; # must be 0 for peptide formation
yhi =  11;

cx = 3
cy = 7

add_simple_glycan(atoms, bonds, angles, glycans,  cx-0.7,  cy-2, 6, 1)
add_simple_glycan(atoms, bonds, angles, glycans,  cx+0,  cy+1, 5, 1)
add_simple_glycan(atoms, bonds, angles, glycans,  cx+2.5,  cy-2, 5, 1)
add_simple_glycan(atoms, bonds, angles, glycans,  cx+1,  cy-4, 6, 1)
add_simple_glycan(atoms, bonds, angles, glycans,  cx+2,   cy+0, 4, 1)

glycans[1].rotate_wrt_cm(atoms, pi/6)
glycans[2].rotate_wrt_cm(atoms, pi/9)
glycans[3].rotate_wrt_cm(atoms, -pi/12)
glycans[4].rotate_wrt_cm(atoms, pi/8)
glycans[5].rotate_wrt_cm(atoms, 0)

form_peptide_bonds(atoms, bonds, glycans, xhi-xlo, yhi-ylo, override_radius=custom_radius, override_energy=custom_energy)

_, cr = compute_crosslink_ratio(atoms, bonds, xhi-xlo, yhi-ylo);
print(cr);

fig, ax = plt.subplots(1,1)

#ax.scatter([atoms[15].x,atoms[24].x],[atoms[15].y,atoms[24].y])

visualize_bonds(atoms, bonds, glycans, xlo, xhi, ylo, yhi, ax=ax, draw_stems=True)
fig.set_size_inches(xhi/2,yhi/2)
plt.show()