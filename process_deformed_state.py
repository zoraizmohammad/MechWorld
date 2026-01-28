from lammps_PG_objects import Atom, Bond, Angle;
from simulation_constants_settings import *;
import numpy as np;
import matplotlib.pyplot as plt;
import matplotlib as mpl;

def import_2D_triclinic_box_bounds_from_dump(filename : str) -> tuple[float, float, float, float, float]:
    """
    Expected format format:
        ITEM: TIMESTEP
        <int>
        ITEM: NUMBER OF ATOMS
        <int>
        ITEM: BOX BOUNDS ...
        <3 lines of floats>
        ITEM: ENTRIES index c_1[1] c_1[2] c_1[3] c_2[1] c_2[2] c_2[3] c_2[4]
        <n lines of floats>
        <EOF>
    """

    # Break into lines
    with open(filename,"r") as f:
        lines = [line.strip() for line in f]

    i = 4; # go to line number 5
    if not lines[i].startswith("ITEM: BOX BOUNDS"):
        raise ValueError("Unexpected format: BOX BOUNDS missing")

    i += 1;
    box_bounds = []
    for j in range(3):
        parts = list(map(float, lines[i+j].split()))
        box_bounds.append(parts)

    xlo = box_bounds[0][0]
    xhi = box_bounds[0][1]
    xy  = box_bounds[0][2]
    ylo = box_bounds[0][0]
    yhi = box_bounds[0][1]

    return (xlo, xhi, xy, ylo, yhi)

def import_atoms_from_dump(filename : str, triclinic_bounds) -> list[Atom]:
    """
    Expected format format:
        ITEM: TIMESTEP
        <int>
        ITEM: NUMBER OF ATOMS
        <int>
        ITEM: BOX BOUNDS ...
        <3 lines of floats>
        ITEM: ATOMS <columns...>
        <atom lines...>
        <EOF>
    """

    (xlo, xhi, xy, ylo, yhi) = triclinic_bounds;

    # Break into lines
    with open(filename,"r") as f:
        lines = [line.strip() for line in f]

    i = 2; # 3rd Line
    verify = "ITEM: NUMBER OF ATOMS";
    if not lines[i].startswith(verify):
        raise ValueError(f"Expected at line {i+1}: {verify}");
    n_atoms = int(lines[i+1]);

    i = 8; # 9th line
    verify = "ITEM: ATOMS id mol type x y";
    if not lines[i].startswith(verify):
        raise ValueError(f"Expected at line {i+1}: {verify}");

    lst_atoms : list[Atom] = list();
    for ai in range(n_atoms):
        atom_data = list(map(float, lines[i+1+ai].split()));
        a = Atom(id=int(atom_data[0]), mol_id=int(atom_data[1]), atom_type=int(atom_data[2]), x=atom_data[3], y=atom_data[4], z=0);
        a.correct_PCB(xlo, xhi, xy, ylo, yhi);
        lst_atoms.append(a);
    
    lst_atoms.sort(key=lambda Atom: Atom.id)

    return lst_atoms

def import_bonds_from_dump(filename : str) -> list[Atom]:
    """
    Expected format format:
        ITEM: TIMESTEP
        <int>
        ITEM: NUMBER OF ENTRIES
        <int>
        ITEM: BOX BOUNDS ...
        <3 lines of floats>
        ITEM: ENTRIES <columns...>
        <atom lines...>
        <EOF>
    """

    # Break into lines
    with open(filename,"r") as f:
        lines = [line.strip() for line in f]

    i = 2; # 3rd Line
    verify = "ITEM: NUMBER OF ENTRIES";
    if not lines[i].startswith(verify):
        raise ValueError(f"Expected at line {i+1}: {verify}");
    n_bonds = int(lines[i+1]);

    i = 8; # 9th line
    verify = "ITEM: ENTRIES index c_b1[1] c_b1[2] c_b1[3] c_b2[1] c_b2[2] c_b2[3] c_b2[4]";
    if not lines[i].startswith(verify):
        raise ValueError(f"Couldn't process {filename}: expected at line {i+1}: {verify}");

    lst_bonds : list[Bond] = list();
    for j in range(n_bonds):
        bond_data = list(map(float, lines[i+1+j].split()));
        b = Bond(id=int(bond_data[0]), bond_type=int(bond_data[1]), atom_id_1=int(bond_data[2]), atom_id_2=int(bond_data[3]));
        b.add_distance_and_forces(bond_data[4], bond_data[5], bond_data[6], bond_data[7]);
        lst_bonds.append(b);

    return lst_bonds

def assemble_boundary_sets(lst_atoms, consideration_depth, triclinic_bounds) -> tuple[set[int], set[int], set[int], set[int]]:
    
    # This is our 2D restricted triclinic box
    (xlo, xhi, xy, ylo, yhi) = triclinic_bounds;

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
        elif a.y > yhi - consideration_depth:
            upper_atom_ids.add(a.id);

        if (xy == 0):
            # The left and right side walls are not tilted
            if a.x < xlo + consideration_depth:
                left_atom_ids.add(a.id);
            elif a.x > xhi - consideration_depth:
                right_atom_ids.add(a.id);
        else:
            # The left and right side walls are tilted, can be represented by a slope
            triclinic_slope = (yhi - ylo) / (xy); # dy/dx
        
            if a.x < xlo + (a.y - ylo)/triclinic_slope + consideration_depth:
                left_atom_ids.add(a.id);
            elif a.x > xhi + (a.y - ylo)/triclinic_slope - consideration_depth:
                right_atom_ids.add(a.id);
    
    #print(f"Debug: IDs of atoms in each boundary region: \n Lower: {len(lower_atom_ids)} \n Upper: {len(upper_atom_ids)} \n Left: {len(left_atom_ids)} \n Right: {len(right_atom_ids)}")

    return (lower_atom_ids, upper_atom_ids, left_atom_ids, right_atom_ids);

def compute_stress_at_boundary(lst_bonds : list[Bond], boundary_sets_tuple, triclinic_bounds):

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
    
    boundary_bond_ids = set();
    for b in lst_bonds:
        if (b.atom_id_1 in upper_atom_ids) & (b.atom_id_2 in lower_atom_ids):
            # F is top -> bottom
            f_U2B += b.forces;
            boundary_bond_ids.add(b);
        if (b.atom_id_1 in lower_atom_ids) & (b.atom_id_2 in upper_atom_ids):
            # F is bottom -> top (must flip)
            f_U2B -= b.forces;
            boundary_bond_ids.add(b);
        if (b.atom_id_1 in left_atom_ids)  & (b.atom_id_2 in right_atom_ids):
            # F is left -> right (must flip)
            f_R2L -= b.forces;
            boundary_bond_ids.add(b);
        if (b.atom_id_1 in right_atom_ids) & (b.atom_id_2 in left_atom_ids):
            # F is right -> left
            f_R2L += b.forces;
            boundary_bond_ids.add(b);
    
    print(f"Debug: found {len(boundary_bond_ids)} bonds that cross the periodic boundary.")

    # Compute stresses
    (xlo, xhi, xy, ylo, yhi) = triclinic_bounds;

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

    Fn_R2L = (np.dot(f_R2L, n_right))*n_right;
    Ft_R2L = f_R2L - Fn_R2L;

    Fn_U2B = (np.dot(f_U2B, n_upper))*n_upper;
    Ft_U2B = f_U2B - Fn_U2B;

    #stress_tensor = np.array([
    #    [np.linalg.norm(Fn_R2L)/area_R2L, np.linalg.norm(Ft_R2L)/area_R2L], # forces on slanted surface
    #    [np.linalg.norm(Ft_U2B)/area_U2B, np.linalg.norm(Fn_U2B)/area_U2B]  # forces on aligned surface
    #]);

    euler_stress_tensor = np.array([
        [f_R2L[0]/area_R2L, f_R2L[1]/area_R2L],         # sigma_xx, tau_xy [Pa]
        [f_U2B[0]/area_U2B, f_U2B[1]/area_U2B]]) * 1E9; # sigma_yx, sigma_yy [Pa]
    
    # F has units of attogram-nanometer/nanosecond^2 = 1E-9 N
    # A has units of nm*2 = 1E-18 m**2
    # ... 1 attogram-nanometer/nanosecond^2 * 1/nm**2 = 1E9 Pa

    return euler_stress_tensor;

def visualizeForceHistogram(lst_bonds : list[Bond]):
    #https://matplotlib.org/stable/gallery/statistics/hist.html

    fmax = max(lst_bonds, key=lambda x: x.force_norm).force_norm;
    fmin = min(lst_bonds, key=lambda x: x.force_norm).force_norm;

    force_magnitudes_glycan = list()
    force_magnitudes_peptide = list()

    for b in lst_bonds: 
        if b.bond_type == BOND_TYPE_GLYCAN:
            force_magnitudes_glycan.append(b.force_norm);
        elif b.bond_type == BOND_TYPE_PEPTIDE:
            force_magnitudes_peptide.append(b.force_norm);
        else:
            continue;

    fig, ax = plt.subplots(2,1,tight_layout=True)

    # We can set the number of bins with the *bins* keyword argument.
    n_bins = 50;
    ax[0].hist(force_magnitudes_glycan, bins=n_bins)
    ax[1].hist(force_magnitudes_peptide, bins=n_bins)

    ax[0].set_xlim(fmin, fmax)
    ax[0].set_ylabel('Number of Bonds');
    ax[0].set_xlabel('Bond Force [nN]')
    ax[0].set_title("Glycan")

    ax[1].set_xlim(fmin, fmax)
    ax[1].set_ylabel('Number of Bonds');
    ax[1].set_xlabel('Bond Force [nN]')
    ax[1].set_title("Peptide")

    plt.show();

def visualizeForceChains(lst_atoms : list[Atom], lst_bonds : list[Bond], triclinic_bounds, boundary_sets_tuple):
    print(f"Total Number of Atoms: {len(lst_atoms)}")
    print(f"Total Number of Bonds: {len(lst_bonds)}")

    (lower_atom_ids, upper_atom_ids, left_atom_ids, right_atom_ids) = assemble_boundary_sets(lst_atoms, 0, triclinic_bounds)
    out_of_bound_count = len(lower_atom_ids) + len(upper_atom_ids) + len(left_atom_ids) + len(right_atom_ids)
    
    print(f"Debug: {out_of_bound_count} atoms were detected outside the bounding box.")

    (lower_atom_ids, upper_atom_ids, left_atom_ids, right_atom_ids) = boundary_sets_tuple;

    fmax = max(lst_bonds, key=lambda x: x.force_norm).force_norm;
    fmin = min(lst_bonds, key=lambda x: x.force_norm).force_norm;

    #norm = mpl.colors.LogNorm(vmin=fmin, vmax=fmax)
    norm = mpl.colors.Normalize(vmin=fmin, vmax=fmax)
    cmap = plt.cm.afmhot
    # list(colormaps)
    # https://matplotlib.org/stable/users/explain/colors/colormaps.html#colormaps
    # https://matplotlib.org/stable/users/explain/colors/colormapnorms.html
    # https://matplotlib.org/stable/users/explain/colors/colorbar_only.html#colorbar-attached-next-to-a-pre-existing-axes 

    fig, ax = plt.subplots()

    for b in lst_bonds:
        
        if b.atom_id_1 in lower_atom_ids and b.atom_id_2 in upper_atom_ids:
            continue;
        elif b.atom_id_1 in upper_atom_ids and b.atom_id_2 in lower_atom_ids:
            continue;
        
        if b.atom_id_1 in left_atom_ids and b.atom_id_2 in right_atom_ids:
            continue;
        elif b.atom_id_1 in right_atom_ids and b.atom_id_2 in left_atom_ids:
            continue;
            
        a1 = lst_atoms[b.atom_id_1-1];
        a2 = lst_atoms[b.atom_id_2-1];

        #print(f"{b.atom_id_1} =?= {a1.id})");

        ax.plot([a1.x,a2.x],[a1.y,a2.y],color=cmap(norm(b.force_norm)));

    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
             ax=ax, orientation='vertical', label='Force [nN]')
    plt.show();

def visualizeStrainHistogram(lst_bonds : list[Bond]):
    #https://matplotlib.org/stable/gallery/statistics/hist.html

    fmax = max(lst_bonds, key=lambda x: x.get_strain()).get_strain();
    fmin = min(lst_bonds, key=lambda x: x.get_strain()).get_strain();

    strain_glycan = list()
    strain_peptide = list()

    for b in lst_bonds: 
        if b.bond_type == BOND_TYPE_GLYCAN:
            strain_glycan.append(b.get_strain());
        elif b.bond_type == BOND_TYPE_PEPTIDE:
            strain_peptide.append(b.get_strain());
        else:
            continue;

    fig, ax = plt.subplots(2,1,tight_layout=True)

    # We can set the number of bins with the *bins* keyword argument.
    n_bins = 50;
    ax[0].hist(strain_glycan, bins=n_bins, log=True)
    ax[1].hist(strain_peptide, bins=n_bins, log=True)

    #ax[0].set_xlim(fmin, fmax)
    ax[0].set_ylabel('Number of Bonds');
    ax[0].set_xlabel('Bond Strain [a.u.]')
    ax[0].set_title("Glycan")

    ax[1].set_xlim(fmin, fmax)
    ax[1].set_ylabel('Number of Bonds');
    ax[1].set_xlabel('Bond Strain [a.u.]')
    ax[1].set_title("Peptide")

    plt.show();

def determineColor(f, fmax, fmin) -> tuple[float,float,float]:
    # https://matplotlib.org/stable/users/explain/colors/colors.html)
    fmean = (fmax + fmin) / 2
    red = (f - fmin)/(fmax-fmin); # Linear
    # red = np.log(((f - fmin)/(fmax-fmin) + 1)*np.exp(1) / 2) # Log
    return (red, 0, 0)
# 
#import argparse
#parser = argparse.ArgumentParser()
#parser.add_argument("atom_file")
#parser.add_argument("bond_file")
#args = parser.parse_args()

#if args.atom_file and args.bond_file:
#    atom_file = args.atom_file;
#    bond_file = args.bond_file;

# Read input
#triclinic_bounds = import_2D_triclinic_box_bounds_from_dump(atom_file);
#lst_atoms : list[Atom] = import_atoms_from_dump(atom_file, triclinic_bounds);
#lst_bonds : list[Bond] = import_bonds_from_dump(bond_file);

# Compute: 
#boundary_sets_tuple = assemble_boundary_sets(lst_atoms, 10, triclinic_bounds)
#stress_tensor = compute_stress_at_boundary(lst_bonds, boundary_sets_tuple, triclinic_bounds)
#visualizeForceChains(lst_atoms, lst_bonds, triclinic_bounds, boundary_sets_tuple)
#visualizeForceHistogram(lst_bonds)
#visualizeStrainHistogram(lst_bonds)

# Output:
#print(stress_tensor)

# Replicate 2.6B, see how our model differs
# Plot histogram of strain, instead of bond force for peptides, glycan

