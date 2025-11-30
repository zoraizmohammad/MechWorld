from lammps_PG_objects import Atom, Bond, Angle;
import numpy as np;

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

triclinic_bounds = import_2D_triclinic_box_bounds_from_dump("atom_state.dump");
lst_atoms : list[Atom] = import_atoms_from_dump("atom_state.dump");
lst_bonds : list[Bond] = import_bonds_from_dump("bond_state.dump");

#for i,a in enumerate(lst_atoms):
#    lst_bonds[i] = a.

# slope of the triclinic boundary box line (left / right edges)
(xlo, xhi, xy, ylo, yhi) = triclinic_bounds;
m = (yhi - ylo) / (xy); # dy/dx
# y = mx + b
# a.y = m*a.x + ylo
# a.x = (a.y - ylo)/m

def assemble_boundary_sets(lst_atoms, consideration_depth, triclinic_bounds) -> tuple[set[int], set[int], set[int], set[int]]:
    
    # This is our 2D restricted triclinic box
    (xlo, xhi, xy, ylo, yhi) = triclinic_bounds;
    triclinic_slope = (yhi - ylo) / (xy); # dy/dx

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

def compute_stress_at_boundary(lst_atoms, lst_bonds : list[Bond], boundary_sets_tuple):
    # Output order: 
    # (fx, fy) at lower interface
    #    ""       upper ""
    #    ""       left  ""
    #    ""       right ""

    f_lower = np.zeros(3);
    f_upper = np.zeros(3);
    f_left  = np.zeros(3);
    f_right = np.zeros(3);
    
    # Is there even a need to distinguish between upper/lower or left/right surfaces?

    for b in lst_bonds:
        if (b.id1 in upper_atom_ids) & (b.id2 in lower_atom_ids):
            f_upper += b.forces;
        if (b.id1 in lower_atom_ids) & (b.id2 in upper_atom_ids):
            f_lower += b.forces;
        if (b.id1 in left_atom_ids)  & (b.id2 in right_atom_ids):
            f_left += b.forces;
        if (b.id1 in right_atom_ids) & (b.id2 in left_atom_ids):
            f_right += b.forces;

    # Compute stresses


    (lower_atom_ids, upper_atom_ids, left_atom_ids, right_atom_ids) = boundary_sets_tuple;
    
    # Internal angle between x vector and y vector of the box.

    # Area
    area_left_right = ((yhi - ylo)**2 + (xy)**2)**(1/2)
    area_lower_upper = (xhi - xlo);

    # Normal unit vectors on each boundary
    xvect = np.array([xhi-xlo, 0      ,0]);
    yvect = np.array([   xy  , yhi-ylo,0]);
    zvect = np.array([0,0,1]);

    n_left = np.cross(yvect,zvect);
    n_left = n_left / np.linalg.norm(n_left);
    n_right = -1 * n_left;

    n_upper = np.array([0, 1, 0]);
    n_lower = -1 * n_upper;

    # Internal Angle
    cos_theta = np.dot(xvect, yvect) / (np.linalg.norm(xvect) * np.linalg.norm(yvect));
    angle_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0));
    angle_deg = np.degrees(angle_rad);

    normal_stress_left = np.dot([fx_left, fy_left, 0], n_left);
    shear


             
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