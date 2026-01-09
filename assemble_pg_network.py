# PG Network Assembly Script
import numpy as np
from math import sin, cos, floor
from random import randrange, random, shuffle
from collections import defaultdict
from lammps_PG_objects import Atom, Bond, Angle
from simulation_constants_settings import *
from lammps_PG_objects import peptide_energy_lammps

rng = np.random.default_rng()

# Random Distribution Array
# Koch, A. L. (2000a). Length distribution of the peptidoglycan chains in the sacculus of
# escherichia coli. Journal of Theoretical Biology, 204(4), 533–541.

p = 0.9;
DSUs = range(1,31); # 1-30
distribution = [];
for i,x in enumerate(DSUs):
    num_entries = (x)*((1-p)**2)*(p**(x-1))*100;
    num_entries = floor(num_entries*10);
    distribution += [x] * num_entries;

def get_DSU_lengths(SIMBOX_MAX_H) -> tuple[list[int], float]:
    DSU_lengths = [];
    while (sum(DSU_lengths)*DSU + (len(DSU_lengths))*glycan_gap <= SIMBOX_MAX_H):
        DSU_lengths.append(distribution[randrange(0,len(distribution))])

    DSU_lengths.pop(); # Remove the one that pushed it over the edge
    filler_glycan_length = floor((SIMBOX_MAX_H - sum(DSU_lengths)*DSU - (len(DSU_lengths))*glycan_gap)/DSU)
    DSU_lengths.append(filler_glycan_length)
    # Total gaps = number of glycan. (n-1 between them, then 1 that wraps the periodic box)
    
    # We don't want a bunch of space at the bottom, so we'll spread it evenly by increasing the glycan gap for this column
    new_glycan_gap = (SIMBOX_MAX_H - sum(DSU_lengths)*DSU)/(len(DSU_lengths));
    shuffle(DSU_lengths)

    return DSU_lengths, new_glycan_gap

def build_a_glycan(mol_id,x,y,dx=0,dy=0,numDSUs=1,alpha=0):
    # (x,y) is CENTER of the Molecule

    per_glycan_DSU_orientation_randomizer = randrange(1,4);

    for i in range(0,numDSUs):
        xA = x+((i+1)-(numDSUs/2))*DSU*sin(alpha)+dx # nm, Applies rotation to x values, rotation is centered on midpoint.
        yA = y+((i+1)-(numDSUs/2))*DSU*cos(alpha)+dy # nm, Applies rotation to x values, rotation is centered on midpoint.

        # Atoms
        atom_id = len(lst_of_atoms)+1;

        # Alternate Right-Reaching and Left-Reaching DSUs
        tmp = (per_glycan_DSU_orientation_randomizer + atom_id) % 4;
        
        if (tmp == 1 or tmp == 2):
            lst_of_atoms.append(Atom(atom_id, mol_id, ATOM_TYPE_NEG_DSU, xA, yA, 0))
        else:
            lst_of_atoms.append(Atom(atom_id, mol_id, ATOM_TYPE_POS_DSU, xA, yA, 0))

        # Bonds
        if (i >= 1):
            bond_id = len(lst_of_atoms)+1;
            lst_of_bonds.append(Bond(bond_id, BOND_TYPE_GLYCAN, lst_of_atoms[-2].id, lst_of_atoms[-1].id))

        # Angles
        if (i >= 2):
            angle_id = len(lst_of_atoms)+1;
            lst_of_angles.append(Angle(angle_id, ANGLE_TYPE_GLYCAN, lst_of_atoms[-3].id, lst_of_atoms[-2].id, lst_of_atoms[-1].id))

def row_trot(x):
    # Walk down a row and populate it with rotated glycans
    global molecule_counter;

    (lst_glycan_lengths, vertical_gap_between_glycans) = get_DSU_lengths(SIMBOX_MAX_H)

    # Experiment: patch the gaps with a new glycan and remove the gap
    # this causes rho_mesh -> rho_gap as size of mesh -> infinity.
    #lst_glycan_lengths.append(round((SIMBOX_MAX_H/DSU) - sum(lst_glycan_lengths)))
    #vertical_gap_between_glycans = 0;

    #print(f"Column {x}: new_glycan_gap = {new_glycan_gap}");
    #print(DSU_lengths, new_glycan_gap)

    y = (vertical_gap_between_glycans/2) + rng.uniform(-0.5*SIMBOX_MAX_H,0.5*SIMBOX_MAX_H); 
    # This shift is a little bit subtle, I am shifting the whole row so the breaks at the tops and bottoms aren't aligned
    # it is easiest to imagine this when there is no rotation
    for len_of_glycan_DSU in lst_glycan_lengths:
        len_of_glycan_nm = len_of_glycan_DSU * DSU;
        #print(y)
        y += len_of_glycan_nm/2; # Move y to the center of the new glycan strand. [nm]

        dx = rng.normal(0, random_displacement_stdev); # Shape should to be adjusted to match paper, 0.996
        dy = rng.normal(0, random_displacement_stdev);
        alpha = (2*random()-1) * isotropic_parameter * (np.pi)/2; # Uniform distribution

        #dx = 0; dy = 0; #alpha = 0;

        molecule_counter += 1;
        build_a_glycan(molecule_counter, x, y, dx, dy, len_of_glycan_DSU, alpha);

        y += len_of_glycan_nm/2 + vertical_gap_between_glycans # nm

def spatial_hash_coords(a : Atom, cell_size : float) -> tuple[int,int]:
    if   (a.x < 0):
        cx = floor( (a.x + simbox_actual_width) / cell_size);
    elif (a.x > simbox_actual_width):
        cx = floor( (a.x - simbox_actual_width) / cell_size);
    else:
        cx = floor( a.x / cell_size );

    if   (a.y < 0):
        cy = floor( (a.y + simbox_actual_height) / cell_size);
    elif (a.y > simbox_actual_height):
        cy = floor( (a.y - simbox_actual_height) / cell_size);
    else:
        cy = floor( a.y / cell_size );

    return cx, cy;

def put_the_atoms_into_a_spatial_hash_smh(cell_size): # Saw this in a yt video once
    grid = defaultdict(list)
    idxs_of_eligible_atoms = list();

    for idx, a in enumerate(lst_of_atoms):
        if a.is_eligible():
            # Slight change to fix potential rounding issue
            cx, cy = spatial_hash_coords(a, cell_size);

            idxs_of_eligible_atoms.append(idx)
            grid[(cx, cy)].append(idx) # Holds index, and thus id of the atom
        else:
            continue
    
    return grid, idxs_of_eligible_atoms

def create_bond_with_nearby_neighbor(idx_of_atom : int, grid : defaultdict[list], cell_size : float, molecule_bonding_matrix : defaultdict[int]):
    # cell_size = radius
    a : Atom = lst_of_atoms[idx_of_atom];

    global DEBUG_favored_bonds;

    # It could be ineligible because another bond was formed with it.
    if not a.is_eligible():
        return;

    mcx = floor(simbox_actual_width / cell_size); # This is the cell index of the furthest-right (thus non-periodic) atom. Searching one to the right should result in searching cx = 0;
    mcy = floor(simbox_actual_height / cell_size);

    cx, cy = spatial_hash_coords(a, cell_size);

    neighbors_idxs : list[int] = list()

    for dcx in [-1,0,1]:
        for dcy in [-1,0,1]:

            # Got to consider periodic bonds
            if ((cx + dcx) < 0):
                cx += mcx;
            if ((cy + dcy) < 0):
                cy += mcy;
            if ((cx + dcx) > mcx):
                cx -= mcx;
            if ((cy + dcy) > mcy):
                cy -= mcy;
            
            if (cx+dcx,cy+dcy) not in grid:
                #print(f"Indices {cx+dcx} {cy+dcy} are undefined")
                continue;

            neighbors_idxs.extend(grid[(cx+dcx,cy+dcy)])

    energy_ideal_neighbor = float("Inf");
    idx_ideal_neighbor = None;

    # Speed date all the neighbors to see who's the best match
    for idx_of_neighbor in neighbors_idxs:
        neighbor : Atom = lst_of_atoms[idx_of_neighbor]

        # Disregard if the orientations (+/-) are the same
        if (a.atom_type == neighbor.atom_type):
            continue;

        # Cannot form bond that connects to the same Glycan strand
        if (neighbor.mol_id == a.mol_id):
            continue;
        
        # Cannot form bond if the neighbor is ineligible (e.g. it has a peptide already)
        if (not neighbor.is_eligible()):
            continue;
        
        # There are not any hard restrictions on the neighbor, so compute the energy to bond...
        r_neighbor = np.sqrt(periodic_distance_squared(neighbor.x, neighbor.y, a.x, a.y));
        E_neighbor = peptide_energy_lammps(r_neighbor);

        # Are these molecules bonded to each other?
        if (a.mol_id, neighbor.mol_id) not in molecule_bonding_matrix:
            # NO
            # number_of_bonds_between_prospective_molecules = 0;
            if (r_neighbor < E_FIRST_PEPTIDE_MAX_EXTENSION * PEPTIDE_COEFFICIENTS[2]):
                idx_ideal_neighbor = idx_of_neighbor;

                if (E_neighbor > E_PEPTIDE_CUTOFF):
                    DEBUG_favored_bonds = DEBUG_favored_bonds + 1;

                break;
        else:
            # YES
            # number_of_bonds_between_prospective_molecules = molecule_bonding_matrix[(a.mol_id, neighbor.mol_id)];
            if (E_neighbor == None) or (E_neighbor > E_PEPTIDE_CUTOFF):
                continue;
    
            if E_neighbor < energy_ideal_neighbor:
                energy_ideal_neighbor = E_neighbor;
                idx_ideal_neighbor = idx_of_neighbor;

    if (idx_ideal_neighbor == None):
        # It's a sad lonely life for this DSU...
        pass
    else:
        ideal_neighbor = lst_of_atoms[idx_ideal_neighbor];

        # We have an ideal neighbor, form a bond!
        lst_of_bonds.append(Bond(len(lst_of_bonds)+1, BOND_TYPE_PEPTIDE, a.id, ideal_neighbor.id))
        lst_of_atoms[idx_of_atom].has_peptide = True;
        lst_of_atoms[idx_ideal_neighbor].has_peptide = True;

        # Update bonding matrix
        if (a.mol_id, ideal_neighbor.mol_id) not in molecule_bonding_matrix:
            molecule_bonding_matrix[(a.mol_id, ideal_neighbor.mol_id)] = 1;
            molecule_bonding_matrix[(ideal_neighbor.mol_id, a.mol_id)] = 1;
        else:
            molecule_bonding_matrix[(a.mol_id, ideal_neighbor.mol_id)] += 1;
            molecule_bonding_matrix[(ideal_neighbor.mol_id, a.mol_id)] += 1;

    return;

def periodic_distance_squared(x1,y1,x2,y2) -> float:
    # The 'aforementioned spaghetti' problem was also because of this
    if (x1 < 0):
        x1 += simbox_actual_width;
    elif (x1 > simbox_actual_width):
        x1 -= simbox_actual_width;

    if (x2 < 0):
        x2 += simbox_actual_width;
    elif (x2 > simbox_actual_width):
        x2 -= simbox_actual_width;

    if (y1 < 0):
        y1 += simbox_actual_height;
    elif (y1 > simbox_actual_height):
        y1 -= simbox_actual_height;

    if (y2 < 0):
        y2 += simbox_actual_height;
    elif (y2 > simbox_actual_height):
        y2 -= simbox_actual_height;

    return (x1 - x2)**2 + (y1 - y2)**2

def periodic_distance_test(x1,y1,x2,y2,r) -> bool:
    return periodic_distance_squared(x1,y1,x2,y2) < r**2

def go_go_gadget_peptide_bonds():
    peptide_bond_search_radius = PEPTIDE_SEARCH_RADIUS; # nm, this is a greater length 
    (grid, idxs_of_eligible_atoms) = put_the_atoms_into_a_spatial_hash_smh(peptide_bond_search_radius)

    if idxs_of_eligible_atoms == []:
        return; # NOOP

    # Randomize the order of the eligible atoms so bonds don't form based on an arbitrary priority.
    shuffle(idxs_of_eligible_atoms);

    # This symmetric matrix records how thoroughly bonded each molecule pair is
    molecule_bonding_matrix = defaultdict(int);

    # Each atom will search for neighbors to bond with
    for i in range(0, len(idxs_of_eligible_atoms)):
        create_bond_with_nearby_neighbor(idxs_of_eligible_atoms[i], grid, peptide_bond_search_radius, molecule_bonding_matrix)

    
    pairwise_list = list(molecule_bonding_matrix.values());
    histo = dict();
    for i in range(1,max(pairwise_list)+1):
        histo[i] = floor(pairwise_list.count(i) / 2) # sym matrix => divide by 2
    print(f"Number of glycan pairs with _ connecting bonds: {histo}") # How many pairs have X crosslinks connecting them?

    print(f"Number of unique molecule pairs: {floor(len(molecule_bonding_matrix)/2)}")
    print(f"Extra bonds created via First-Favored Policy: {DEBUG_favored_bonds} ({DEBUG_favored_bonds/len(lst_of_bonds)*100}% of total)")

# Output percentage of cross-linked polymers
# Plot that compares density to cross-linked polymers

def write_to_laamps_datafile(filename):
    with open(filename, "w") as f:
        f.write("LAMMPS Data File. PG System.")
        f.write("\n")
        f.write(f"{len(lst_of_atoms)} atoms\n")
        f.write(f"{len(lst_of_bonds)} bonds\n")
        f.write(f"{len(lst_of_angles)} angles\n")
        f.write(f"2 atom types\n")
        f.write(f"2 bond types\n")
        f.write(f"1 angle types\n")
        f.write(f"3 extra bond per atom\n")
        f.write(f"2 extra angle per atom\n")
        f.write(f"{-simbox_actual_width/2} {simbox_actual_width/2} xlo xhi\n")
        f.write(f"{-simbox_actual_height/2} {simbox_actual_height/2} ylo yhi\n")
        f.write(f"-1 1 zlo zhi\n")
        f.write(f"0 0 0 xy xz yz\n") # Restricted Triclinic Tilts, inc it makes this a triclinic instead of ortho box
        f.write("\n")

        f.write(f"Masses\n\n")
        f.write(f"1 {DSU_MASS_ATTOGRAM}\n")
        f.write(f"2 {DSU_MASS_ATTOGRAM}\n")

        f.write(f"\nAtoms\n\n")
        for a in lst_of_atoms:
            a.to_datafile(f)

        f.write(f"\nBonds\n\n")
        for b in lst_of_bonds:
            b.to_datafile(f)

        f.write(f"\nAngles\n\n")
        for c in lst_of_angles:
            c.to_datafile(f)

def compute_crosslink_ratio(number_of_atoms : int, lst_of_bonds : list[Bond]):
    # Count number of cross-links formed
    crosslink_cnt = 0;
    for b in lst_of_bonds:
        if b.bond_type == 2:
            crosslink_cnt += 1;
    
    rho_mesh = (number_of_atoms * DSU**2) / (simbox_actual_width * simbox_actual_height);
    crosslink_ratio = (2*crosslink_cnt) / number_of_atoms;
    return rho_mesh, crosslink_ratio;

# Note: Cells are typically rod-shaped, and are about 2.0 μm long and 0.25–1.0 μm in diameter, with a cell volume of 0.6–0.7 μm3. (from Wikipedia)
# 2um = 2000nm, 0.25-1.0um diameter = 785.40-3141.59nm in circumference.

# Globals
simbox_actual_width = 0; # TBD by population
simbox_actual_height = 0; # TBD by population
molecule_counter = 0;
DEBUG_favored_bonds = 0;
lst_of_atoms : list[Atom] = list(); # note to self: () are used when you have an iterable, use x : list[obj] = list() when type hinting
lst_of_bonds : list[Bond] = list();
lst_of_angles :  list[Angle] = list();

def generate_pg_network(box_size_DSU : float = 100, glycan_packing_factor : float = 1, X : float = 0.65, filename : str = None):

    # Std Deviation of Random Displacement
    global random_displacement_stdev; random_displacement_stdev = DSU*(1/(2*np.sqrt(2)));

    # Global constants for other functions
    global isotropic_parameter; isotropic_parameter = X;
    global glycan_gap; glycan_gap = DSU / glycan_packing_factor;
    global column_gap; column_gap = DSU / glycan_packing_factor;
    global SIMBOX_MAX_W; SIMBOX_MAX_W = box_size_DSU*DSU;
    global SIMBOX_MAX_H; SIMBOX_MAX_H = box_size_DSU*DSU;

    # Reset Globals
    global simbox_actual_height; simbox_actual_height = 0;
    global simbox_actual_width; simbox_actual_width = 0;
    global molecule_counter;    molecule_counter = 0;
    global DEBUG_favored_bonds; DEBUG_favored_bonds = 0;
    global lst_of_atoms;  lst_of_atoms = list(); # note to self: () are used when you have an iterable, use x : list[obj] = list() when type hinting
    global lst_of_bonds;  lst_of_bonds = list();
    global lst_of_angles; lst_of_angles = list();

    # Populate Glycans
    x = column_gap/2;
    while True:
        # Interating across the columns
        if (x + column_gap > SIMBOX_MAX_W):
            simbox_actual_height = SIMBOX_MAX_H;
            simbox_actual_width = x;
            break
        
        row_trot(x);

        x += column_gap;
    
    # Create Peptide Bonds
    go_go_gadget_peptide_bonds()

    # Count Cross-Linking
    density_fraction, crosslink_ratio = compute_crosslink_ratio(len(lst_of_atoms), lst_of_bonds)

    # Transform Coordinates of Atoms
    for a in lst_of_atoms:
        a.translate(-simbox_actual_width/2, -simbox_actual_height/2, 0);
    
    if not filename == None:
        # Write everything to LAMMPS datafile
        write_to_laamps_datafile(filename);

    return density_fraction, crosslink_ratio, lst_of_atoms, lst_of_bonds, lst_of_angles;