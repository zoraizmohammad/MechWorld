from assemble_pg_network import visualizeBonds, compute_crosslink_ratio, form_peptide_bonds, add_simple_glycan

atoms = dict()
bonds = dict()
angles = dict()
glycans = dict()

xlo =  0;
xhi =  4;
ylo =  0;
yhi =  29;

add_simple_glycan(atoms, bonds, angles, glycans, xhi/2-0.5, yhi/2, 25)
add_simple_glycan(atoms, bonds, angles, glycans, xhi/2+0.5, yhi/2, 25)

form_peptide_bonds(atoms, bonds, glycans, xhi-xlo, yhi-ylo)

_, cr = compute_crosslink_ratio(atoms, bonds, xhi-xlo, yhi-ylo);
print(cr);

visualizeBonds(atoms, bonds, glycans, xlo, xhi, ylo, yhi)