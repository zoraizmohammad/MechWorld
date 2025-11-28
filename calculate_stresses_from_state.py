from lammps_PG_objects import Atom, Bond, Angle;

def import_2D_triclinic_box_bounds_from_dump(filename : str) -> tuple[float, float, float, float, float]:
    with open(filename,"r") as f:
        pass

def import_atoms_from_dump(filename : str) -> list[Atom]:
    lst_atoms : list[Atom] = list();
    with open(filename,"r") as f:
        pass

def import_bonds_from_dump(filename : str) -> list[Atom]:
    lst_bonds : list[Bond] = list();
    with open(filename,"r") as f:
        pass

(xlo, xhi, xy, ylo, yhi) = import_2D_triclinic_box_bounds_from_dump("atom_state.dump");
lst_atoms : list[Atom] = import_atoms_from_dump("atom_state.dump");
lst_bonds : list[Bond] = import_bonds_from_dump("bond_state.dump");

# slope of the triclinic boundary box line (left / right edges)
m = xy / (xlo, ylo); 
# y = mx + b
# a.y = m*a.x + ylo
# a.x = (a.y - ylo)/m

def assemble_boundary_sets(lst_atoms, consideration_depth, triclinic_slope) -> tuple[set[int], set[int], set[int], set[int]]:
    # Output order: Lower, Upper, Left, Right
    lower_atom_ids : set[int] = set();
    upper_atom_ids : set[int] = set();
    left_atom_ids  : set[int] = set();
    right_atom_ids : set[int] = set();

    for a in lst_atoms:
        # object function to correct periodic boundary conditions (lammps warn bout this)

        # Perform up to four checks, only two are independent (opposite sides)

        # Top and bottom of the boundary box aren't tilted
        if a.y < ylo + consideration_depth:
            lower_atom_ids.add(a.id);
        elif a.y > yhi + consideration_depth:
            upper_atom_ids.add(a.id);

        # The left and right side walls are tilted, can be represented by a slope
        if a.x < xlo + (a.y - ylo)/triclinic_slope + consideration_depth:
            left_atom_ids.add(a.id);
        elif a.x > xhi + (a.y - ylo)/triclinic_slope - consideration_depth:
            right_atom_ids.add(a.id);

    return (lower_atom_ids, upper_atom_ids, left_atom_ids, right_atom_ids);

boundary_sets_tuple = assemble_boundary_sets(lst_atoms, consideration_depth=5, triclinic_slope=m)

def compute_force_at_boundary(lst_atoms, lst_bonds, boundary_sets_tuple) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    # Output order: 
    # (fx, fy) at lower interface
    #    ""       upper ""
    #    ""       left  ""
    #    ""       right ""
    
    pass
# la plan

# Get list of atoms from atom_state.dump
# Read list of bonds from bond_state.dump 

# Compute 4 sets: upper atoms, lower atoms, left atoms, right atoms

# Loop through the list of bonds

# for bond in lst_bonds:
# if (bond.id1 in upper_atom_ids) && (bond.id2 in lower_atom_ids)
# if (bond.id1 in lower_atom_ids) && (bond.id2 in upper_atom_ids)
# if (bond.id1 in left_atom_ids)  && (bond.id2 in right_atom_ids)
# if (bond.id1 in right_atom_ids) && (bond.id2 in left_atom_ids)