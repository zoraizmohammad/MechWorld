# Get list of atoms from atom_state.dump
# Read list of bonds from bond_state.dump 

# Compute 4 sets: upper atoms, lower atoms, left atoms, right atoms

# Loop through the list of bonds

# for bond in lst_bonds:
# if (bond.id1 in upper_atom_ids) && (bond.id2 in lower_atom_ids)
# if (bond.id1 in lower_atom_ids) && (bond.id2 in upper_atom_ids)
# if (bond.id1 in left_atom_ids)  && (bond.id2 in right_atom_ids)
# if (bond.id1 in right_atom_ids) && (bond.id2 in left_atom_ids)