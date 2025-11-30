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

    # Because we are using PBC, only two sets of forces need to be tracked: left/right (surface is slanted), upper/lower (surface || to x-axis)
    f_U2B = np.zeros(3); # Upper Surface -> Bottom Surface (normal points +y)
    f_R2L = np.zeros(3); # Right Surface -> Left Surface (normal points +x ISH)
    
    # Normalization might have to occur, check the signs of the bonds, fx, fy components
    # https://docs.lammps.org/compute_bond_local.html
    # The sign of the forces is determined by the locations of the atoms:
    # Fx, Fy, Fz is the force on atom #1 due to atom #2.
    # (a1.x < a2.x) -> Fx is positive
    # (a1.y < a2.y) -> Fy is positive
    # Fz is zero for these 2D simulations
    # how to account for this = enforce direction like left2right, = multiply right2left * -1

    (lower_atom_ids, upper_atom_ids, left_atom_ids, right_atom_ids) = boundary_sets_tuple;
 
    for b in lst_bonds:
        if (b.id1 in upper_atom_ids) & (b.id2 in lower_atom_ids):
            # F is top -> bottom
            f_U2B += b.forces;
        if (b.id1 in lower_atom_ids) & (b.id2 in upper_atom_ids):
            # F is bottom -> top (must flip)
            f_U2B -= b.forces;
        if (b.id1 in left_atom_ids)  & (b.id2 in right_atom_ids):
            # F is left -> right (must flip)
            f_R2L -= b.forces;
        if (b.id1 in right_atom_ids) & (b.id2 in left_atom_ids):
            # F is right -> left
            f_R2L += b.forces;

    # Compute stresses

    # Area
    area_R2L = ((yhi - ylo)**2 + (xy)**2)**(1/2)
    area_U2B = (xhi - xlo);

    # Normal unit vectors on each boundary (that we can about)
    xvect = np.array([xhi-xlo, 0      ,0]);
    yvect = np.array([   xy  , yhi-ylo,0]);
    zvect = np.array([0,0,1]);

    n_right = np.cross(yvect,zvect);
    n_right = n_right / np.linalg.norm(n_right);

    n_upper = np.array([0, 1, 0]);

    # Internal angle of box
    cos_theta = np.dot(xvect, yvect) / (np.linalg.norm(xvect) * np.linalg.norm(yvect));
    angle_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0));
    angle_deg = np.degrees(angle_rad);

    normal_stress_R2L = np.dot(f_R2L, n_right)/area_R2L;
    shear_stress_R2L = f_R2L/area_R2L - normal_stress_R2L;

    normal_stress_U2B = np.dot(f_U2B, n_upper)/area_U2B;
    shear_stress_U2B = f_U2B/area_U2B - normal_stress_U2B;