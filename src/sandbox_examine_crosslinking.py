from assemble_pg_network import visualizeBonds, compute_crosslink_ratio, form_peptide_bonds, add_simple_glycan

atoms = dict()
bonds = dict()
angles = dict()
glycans = dict()

xlo =  0;
xhi =  20;
ylo =  0;
yhi =  20;

add_simple_glycan(atoms, bonds, angles, glycans,   9, 10, 10)
add_simple_glycan(atoms, bonds, angles, glycans,  10, 10, 10)
add_simple_glycan(atoms, bonds, angles, glycans,  11, 10, 10)
form_peptide_bonds(atoms, bonds, glycans, xhi-xlo, yhi-ylo)

visualizeBonds(atoms, bonds, glycans, xlo, xhi, ylo, yhi)

_, cr = compute_crosslink_ratio(atoms, bonds, xhi-xlo, yhi-ylo);

print(cr);