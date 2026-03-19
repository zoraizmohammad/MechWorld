# PG Network Assembly Script
import numpy as np
from math import floor, ceil
from random import randrange, random, shuffle
from collections import defaultdict
from lammps_PG_objects import Atom, Bond, Angle, GlycanMolecule
from simulation_constants_settings import *
from lammps_PG_objects import peptide_energy_lammps, shortest_path_is_periodic_x, shortest_path_is_periodic_y
import matplotlib.pyplot as plt

rng = np.random.default_rng()

# Random Distribution Array
# Koch, A. L. (2000a). Length distribution of the peptidoglycan chains in the sacculus of
# escherichia coli. Journal of Theoretical Biology, 204(4), 533–541.

def create_FlorySchulz_distribution(min_DSU : int, max_DSU : int, p : float, entries : int):
    DSUs = range(min_DSU,max_DSU+1);
    distribution = list();
    for i,x in enumerate(DSUs):
        entries_for_this_length = floor( (x)*((1-p)**2)*(p**(x-1))*entries );
        distribution += [x] * entries_for_this_length;
    
    return distribution;

def create_top_hat_distribution(min_DSU : int, max_DSU : int):
    distribution = range(min_DSU, max_DSU+1);
    return distribution;

def process_distribution_string(distrib_str : str, size : int) -> list[int]:
    # Option #1: FS-{min}-{max}-{alpha}
    # i.e. FS-2-100-0.9

    # Option #2: UNI-{min}-{max}
    # i.e. UNI-20-30

    chunks : list[str] = distrib_str.split("-")

    if chunks[0] == "FS":
        assert len(chunks) == 4;
        return create_FlorySchulz_distribution(int(chunks[1]), int(chunks[2]), float(chunks[3]), 1E6)

    elif chunks[0] == "UNI":
        assert len(chunks) == 3;
        return create_top_hat_distribution(int(chunks[1]), int(chunks[2]));

    else:
        raise ValueError(f"Misconfigured distrib str: {distrib_str}")

def get_sample_of_DSU_lengths_simple(Ny : int, distribution : list[int]) -> list[int]:
    # Ny includes the gaps between glycans
    glycan_lengths_DSU = [];

    # Draw from the distribution until the total desired length is exceeded
    while (sum(glycan_lengths_DSU) + len(glycan_lengths_DSU)) < Ny:
        glycan_lengths_DSU.append(distribution[randrange(0,len(distribution))])

    glycan_lengths_DSU.pop(); # Remove the glycan that pushed it over the edge

    # Fill the deficit with a new glycan (or extend a random glycan if we need exactly 1 DSU)
    DSU_deficit = Ny - sum(glycan_lengths_DSU) - len(glycan_lengths_DSU);
    if (DSU_deficit == 1):
        glycan_lengths_DSU[0] += 1;
    else:
        glycan_lengths_DSU.append(DSU_deficit);

    shuffle(glycan_lengths_DSU)

    return glycan_lengths_DSU

def get_sample_of_DSU_lengths_no_gaps(Ny : int, distribution : list[int]) -> list[int]:
    # Ny excludes the gaps between glycans
    glycan_lengths_DSU = [];

    # Draw from the distribution until the total desired length is exceeded
    while (sum(glycan_lengths_DSU)) < Ny:
        glycan_lengths_DSU.append(distribution[randrange(0,len(distribution))])

    glycan_lengths_DSU.pop(); # Remove the glycan that pushed it over the edge

    # Fill the deficit with a new glycan (or extend a random glycan if we need exactly 1 DSU)
    DSU_deficit = Ny - sum(glycan_lengths_DSU);
    if (DSU_deficit == 1):
        glycan_lengths_DSU[0] += 1;
    else:
        glycan_lengths_DSU.append(DSU_deficit);

    shuffle(glycan_lengths_DSU)

    return glycan_lengths_DSU

def add_simple_glycan(atoms : dict[int,Atom], bonds : dict[int,Bond], angles : dict[int,Angle], glycans : dict[int,GlycanMolecule], cm_x, cm_y, numDSUs : int, orientation_override = None):
    if (numDSUs == 0):
        print("Warning: numDSU len of 0 was passed!")
        return;
    
    # Create add a new glycan object to the dictionary
    molecule_id = len(glycans)+1;
    glycans[molecule_id] = GlycanMolecule(molecule_id);
    glycans[molecule_id].set_cm(cm_x, cm_y)

    if orientation_override:
        orientation_randomizer = orientation_override;
    else:
        orientation_randomizer = randrange(1,4);

    # Add atoms, bonds, angles
    for i in range(0,numDSUs):
        # First atom (with lowest index) is placed at the 'bottom' of the glycan
        xA = cm_x
        yA = cm_y + (i - (numDSUs-1)/2)*DSU # nm

        ### Atom
        new_aid = len(atoms)+1;

        # Alternate Right-Reaching and Left-Reaching DSUs
        tmp = (orientation_randomizer + new_aid) % 4;
        if (tmp == 1 or tmp == 2):
            atoms[new_aid] = Atom(new_aid, molecule_id, ATOM_TYPE_POS_DSU, xA, yA, 0);
        else:
            atoms[new_aid] = Atom(new_aid, molecule_id, ATOM_TYPE_NEG_DSU, xA, yA, 0);
        
        # Set stem vector (it will change when rotating later)
        atoms[new_aid].set_stem_vector(0);
        
        # Tell the glycan object about this atom
        glycans[molecule_id].atom_ids.add(new_aid);

        ### Bond?
        if (i >= 1):
            bond_id = len(bonds)+1;
            bonds[bond_id] = Bond(bond_id, BOND_TYPE_GLYCAN, new_aid-1, new_aid);
            glycans[molecule_id].bond_ids.add(bond_id);

        ### Angle?
        if (i >= 2):
            angle_id = len(angles)+1;
            angles[angle_id] = Angle(angle_id, ANGLE_TYPE_GLYCAN, new_aid-2, new_aid-1, new_aid);
            glycans[molecule_id].angle_ids.add(angle_id);

def spatial_hash_coords(a : Atom, cell_size : float, simbox_lx, simbox_ly) -> tuple[int,int]:
    if   (a.x < 0):
        cx = floor( (a.x + simbox_lx) / cell_size);
    elif (a.x > simbox_lx):
        cx = floor( (a.x - simbox_lx) / cell_size);
    else:
        cx = floor( a.x / cell_size );

    if   (a.y < 0):
        cy = floor( (a.y + simbox_ly) / cell_size);
    elif (a.y > simbox_ly):
        cy = floor( (a.y - simbox_ly) / cell_size);
    else:
        cy = floor( a.y / cell_size );

    return cx, cy;

def verify_stem_alignment(a1 : Atom, a2 : Atom, COS_ALIGNMENT_TOL : float, simbox_lx, simbox_ly, check_PCB : bool):
    v_a2_to_a1 = np.array([a1.x - a2.x, a1.y - a2.y]);

    if check_PCB:
        if shortest_path_is_periodic_x(a1, a2, simbox_lx):
            if a1.x < a2.x:
                v_a2_to_a1[0] = (a1.x + simbox_lx) - a2.x;
            else:
                v_a2_to_a1[0] = a1.x - (a2.x  + simbox_lx);
        
        if shortest_path_is_periodic_y(a1, a2, simbox_ly):
            if a1.x < a2.x:
                v_a2_to_a1[1] = (a1.y + simbox_ly) - a2.y;
            else:
                v_a2_to_a1[1] = a1.y - (a2.y + simbox_ly);

    n_a2_to_a1 = v_a2_to_a1 / np.linalg.norm(v_a2_to_a1); # unit

    d1_unit = np.dot(a1.v_stem, -1*n_a2_to_a1);
    if (d1_unit < COS_ALIGNMENT_TOL):
        return False
    
    d2_unit = np.dot(a2.v_stem, n_a2_to_a1);
    if (d2_unit < COS_ALIGNMENT_TOL):
        return False

    return True

def create_peptide_with_nearby_neighbor(
        id_of_atom : int, grid : defaultdict[list], cell_size : float, molecule_bonding_matrix : defaultdict[int], 
        atoms : dict[int,Atom], bonds : dict[int,Bond], glycans : dict[int,GlycanMolecule], simbox_lx : float, simbox_ly : float, 
        override_energy = None):
    
    # cell_size = radius
    a : Atom = atoms[id_of_atom];

    # It could be ineligible because another bond was formed with it.
    # There is also a X% chance that the DSU is not eligible based on a Bernoulli trial, see constructor.
    if not a.is_eligible():
        return;

    neighbors_ids : list[int] = list()

    # 'max' cx and cy, useful to wrap around in PCB
    mcx = floor(simbox_lx / cell_size); 
    mcy = floor(simbox_ly / cell_size);

    # what cell is this atom in?
    cx, cy = spatial_hash_coords(a, cell_size, simbox_lx, simbox_ly);

    PERIODIC_RISK : bool = ((cx == 0) or (cy == 0) or (cx == mcx) or (cx == mcy));
    COS_ALIGNMENT_TOL = np.cos(np.deg2rad(PEPTIDE_ANG_TOL_DEGREES));
    SIN_ALIGNMENT_TOL = np.sin(np.deg2rad(PEPTIDE_ANG_TOL_DEGREES));

    dcx_set = {-1,0,1};
    dcy_set = {-1,0,1};

    # # Optimization to ignore cells that point away from the stem vector
    # if a.v_stem[0] < -SIN_ALIGNMENT_TOL:
    #     dcx_set.discard(1);
    # elif a.v_stem[0] > SIN_ALIGNMENT_TOL:
    #     dcx_set.discard(-1);
    
    # if a.v_stem[1] < -SIN_ALIGNMENT_TOL:
    #     dcy_set.discard(1);
    # elif a.v_stem[1] > SIN_ALIGNMENT_TOL:
    #     dcy_set.discard(-1);

    # look into the cells of the atom + (relevant) adjacent cells -> get a list of could-be neighbors
    for dcx in dcx_set:
        for dcy in dcy_set:
            if ((cx + dcx) < 0):
                cx += mcx;
            if ((cy + dcy) < 0):
                cy += mcy;
            if ((cx + dcx) > mcx):
                cx -= mcx;
            if ((cy + dcy) > mcy):
                cy -= mcy;
            
            if (cx+dcx,cy+dcy) not in grid:
                continue;

            neighbors_ids.extend(grid[(cx+dcx,cy+dcy)])

    # which could-be neighbor is the best?
    energy_ideal_neighbor = float("Inf");
    ideal_neighbor_id = None;

    if override_energy:
        max_allowed_energy = override_energy;
    else:
        max_allowed_energy = E_PEPTIDE_CUTOFF;

    # Speed date all the neighbors to see who's the best match
    for neighbor_id in neighbors_ids:
        print(f"Atom {a.id} is checking Atom {neighbor_id}")
        neighbor : Atom = atoms.get(neighbor_id)

        # Cannot form bond that connects to the same Glycan strand
        if (neighbor.mol_id == a.mol_id):
            print("> Failed: Same molecule")
            continue;
        
        # Cannot form bond if the neighbor is ineligible (e.g. it has a peptide already, failed Bernoulli trial)
        if (not neighbor.is_eligible()):
            print("> Failed: Neighbor is not eligible")
            continue;

        # Ensure that the stems are pointing toward each other, each stem must be aligned within 45 degrees of the new peptide
        if (not verify_stem_alignment(a, neighbor, COS_ALIGNMENT_TOL, simbox_lx, simbox_ly, PERIODIC_RISK)):
            print("> Failed: Stems not aligned")
            continue;
        
        # There are not any hard restrictions on the neighbor, so compute the energy to bond...
        r_neighbor : float = np.sqrt(periodic_distance_squared(neighbor.x, neighbor.y, a.x, a.y, simbox_lx, simbox_ly));
        E_neighbor = peptide_energy_lammps(r_neighbor);

        # if the energy is undefined (past singularity) or too high, no bond
        if (E_neighbor == None) or (E_neighbor > max_allowed_energy):
            print("> Failed: Energy too high")
            continue;

        # It is eligible, so see if it is the BEST neighbor
        if E_neighbor < energy_ideal_neighbor:
            energy_ideal_neighbor = E_neighbor;
            ideal_neighbor_id = neighbor_id;

    if (ideal_neighbor_id == None):
        # It's a sad lonely life for this DSU...
        pass
    else:
        # We have an ideal neighbor, form a bond!
        ideal_neighbor : Atom = atoms.get(ideal_neighbor_id);
        new_bond_id = len(bonds)+1;
        bonds[new_bond_id] = (Bond(new_bond_id, BOND_TYPE_PEPTIDE, a.id, ideal_neighbor.id))
        atoms[id_of_atom].has_peptide = True;
        atoms[ideal_neighbor_id].has_peptide = True;
    
        glycans[a.mol_id].bond_ids.add(new_bond_id);
        glycans[ideal_neighbor.mol_id].bond_ids.add(new_bond_id);
    
        # Update bonding matrix
        if (a.mol_id, ideal_neighbor.mol_id) not in molecule_bonding_matrix:
            molecule_bonding_matrix[(a.mol_id, ideal_neighbor.mol_id)] = 1;
            molecule_bonding_matrix[(ideal_neighbor.mol_id, a.mol_id)] = 1;
        else:
            molecule_bonding_matrix[(a.mol_id, ideal_neighbor.mol_id)] += 1;
            molecule_bonding_matrix[(ideal_neighbor.mol_id, a.mol_id)] += 1;

    return;

def periodic_distance_squared(x1,y1,x2,y2,simbox_lx,simbox_ly) -> float:
    # The 'aforementioned spaghetti' problem was also because of this
    if (x1 < 0):
        x1 += simbox_lx;
    elif (x1 > simbox_lx):
        x1 -= simbox_lx;

    if (x2 < 0):
        x2 += simbox_lx;
    elif (x2 > simbox_lx):
        x2 -= simbox_lx;

    if (y1 < 0):
        y1 += simbox_ly;
    elif (y1 > simbox_ly):
        y1 -= simbox_ly;

    if (y2 < 0):
        y2 += simbox_ly;
    elif (y2 > simbox_ly):
        y2 -= simbox_ly;

    return (x1 - x2)**2 + (y1 - y2)**2

def periodic_distance_test(x1,y1,x2,y2,r) -> bool:
    return periodic_distance_squared(x1,y1,x2,y2) < r**2

def put_the_atoms_into_a_spatial_hash_smh(atoms, cell_size, simbox_lx, simbox_ly): # Saw this in a yt video once
    grid = defaultdict(list)
    ids_of_eligible_atoms = list();

    for (a_id, a) in atoms.items():
        if a.is_eligible():
            # Slight change to fix potential rounding issue
            cx, cy = spatial_hash_coords(a, cell_size, simbox_lx, simbox_ly);

            ids_of_eligible_atoms.append(a_id)
            grid[(cx, cy)].append(a_id)
        else:
            continue
    
    return grid, ids_of_eligible_atoms

def form_peptide_bonds(atoms, bonds, glycans, simbox_lx, simbox_ly, override_radius = None, override_energy = None):
    
    if override_radius:
        peptide_bond_search_radius = override_radius;
    else:
        peptide_bond_search_radius = PEPTIDE_SEARCH_RADIUS; # nm, this is a greater length 
    
    print(PEPTIDE_SEARCH_RADIUS)
    (grid, ids_of_eligible_atoms) = put_the_atoms_into_a_spatial_hash_smh(atoms, peptide_bond_search_radius, simbox_lx, simbox_ly)

    if ids_of_eligible_atoms == []:
        return; # NOOP

    # Randomize the order of the eligible atoms so bonds don't form based on an arbitrary priority.
    shuffle(ids_of_eligible_atoms);

    # This symmetric matrix records how thoroughly bonded each molecule pair is
    molecule_bonding_matrix = defaultdict(int);

    # Each atom will search for neighbors to bond with
    for id in ids_of_eligible_atoms:
        create_peptide_with_nearby_neighbor(id, grid, peptide_bond_search_radius, molecule_bonding_matrix, atoms, bonds, glycans, simbox_lx, simbox_ly, override_energy)
    
    pairwise_list = list(molecule_bonding_matrix.values());
    histo = dict();
    if not len(pairwise_list) == 0:
        for i in range(1,max(pairwise_list)+1):
            histo[i] = floor(pairwise_list.count(i) / 2) # sym matrix => divide by 2
        print(f"Number of glycan pairs with _ connecting bonds: {histo}") # How many pairs have X crosslinks connecting them?

def write_to_laamps_datafile(filename, atoms, bonds, angles, simbox_lx, simbox_ly):
    with open(filename, "w") as f:
        f.write("LAMMPS Data File. PG System.")
        f.write("\n")
        f.write(f"{len(atoms)} atoms\n")
        f.write(f"{len(bonds)} bonds\n")
        f.write(f"{len(angles)} angles\n")
        f.write(f"2 atom types\n")
        f.write(f"2 bond types\n")
        f.write(f"1 angle types\n")
        f.write(f"3 extra bond per atom\n")
        f.write(f"2 extra angle per atom\n")
        f.write(f"{-simbox_lx/2} {simbox_lx/2} xlo xhi\n")
        f.write(f"{-simbox_ly/2} {simbox_ly/2} ylo yhi\n")
        f.write(f"-0.5 0.5 zlo zhi\n") # Recommended for 2D, https://docs.lammps.org/Howto_2d.html
        f.write(f"0 0 0 xy xz yz\n") # Restricted Triclinic Tilts, inc it makes this a triclinic instead of ortho box
        f.write("\n")

        f.write(f"Masses\n\n")
        f.write(f"1 {DSU_MASS_ATTOGRAM}\n")
        f.write(f"2 {DSU_MASS_ATTOGRAM}\n")

        f.write(f"\nAtoms\n\n")
        for a in atoms.values():
            a.to_datafile(f)

        f.write(f"\nBonds\n\n")
        for b in bonds.values():
            b.to_datafile(f)

        f.write(f"\nAngles\n\n")
        for c in angles.values():
            c.to_datafile(f)

def compute_crosslink_ratio(atoms : dict[int,Atom], bonds : dict[int,Bond], simbox_lx, simbox_ly):
    # Count number of cross-links formed
    number_of_atoms = len(atoms);

    #print(f"DEBUG: Total Atoms {len(atoms)}")
    #print(f"DEBUG: Total Bonds {len(bonds)}")

    peptide_crosslink_counter = 0;
    glycan_bond_counter = 0;
    for b in bonds.values():
        if b.bond_type == BOND_TYPE_PEPTIDE:
            peptide_crosslink_counter += 1;
        if b.bond_type == BOND_TYPE_GLYCAN:
            glycan_bond_counter += 1;

    ineligible_atom_counter = 0;
    for a in atoms.values():
        if not a.is_eligible():
            ineligible_atom_counter += 1;
    
    #print(f"DEBUG: Ineligible Atoms {ineligible_atom_counter}")
    #print(f"DEBUG: Peptide Bonds {peptide_crosslink_counter}")
    #print(f"DEBUG: Glycan Bonds {glycan_bond_counter}")
    
    rho_mesh = (number_of_atoms * DSU**2) / (simbox_lx * simbox_ly);

    crosslink_ratio = (2*peptide_crosslink_counter) / number_of_atoms;
    return rho_mesh, crosslink_ratio;

def populate_glycans_on_a_not_so_unitary_grid(atoms, bonds, angles, glycans, Nx : int, Ny : int, epsilon_x : float, epsilon_y : float, distribution : list[int]):
    for column_idx in range(0,Nx):
        glycan_lengths_for_this_column = get_sample_of_DSU_lengths_no_gaps(Ny, distribution);
        vertical_gap_between_glycans = (Ny*DSU*(1+epsilon_y) - sum(glycan_lengths_for_this_column)*DSU) \
            / len(glycan_lengths_for_this_column);

        cm_x = (DSU/2 + column_idx*DSU)         *(1+epsilon_x);
        cm_y = (vertical_gap_between_glycans/2 + rng.uniform(0,Ny*DSU/2))*(1+epsilon_y);

        for length_of_glycan_DSU in glycan_lengths_for_this_column:
            cm_y += DSU*(length_of_glycan_DSU/2);
            add_simple_glycan(atoms, bonds, angles, glycans, cm_x, cm_y, length_of_glycan_DSU)
            cm_y += DSU*(length_of_glycan_DSU/2) + vertical_gap_between_glycans;

#### DEBUG INSPECTION FUNCTIONS

def visualizeBonds(
        atoms : dict[int, Atom], 
        bonds : dict[int,Bond], 
        glycans : dict[int,GlycanMolecule], 
        xlo, xhi, ylo, yhi, 
        ax : plt.Axes = None, 
        draw_stems : bool = True):
    
    if ax == None:
        fig, ax = plt.subplots()
        show_now = True;
    else:
        show_now = False;

    #for g in glycans.values():
    #    plt.scatter(g.cm_x, g.cm_y, color='red');

    for b in bonds.values():
            
        a1 = atoms[b.atom_id_1];
        a2 = atoms[b.atom_id_2];

        if shortest_path_is_periodic_x(a1, a2, xhi-xlo) or shortest_path_is_periodic_y(a1, a2, yhi-ylo):
            continue;
            #pass

        #print(f"{b.atom_id_1} =?= {a1.id})");
        color_arr = ["","black","green"]
        linestyle_arr = ["","-","--"]

        # Big ol'd bonds
        ax.plot([a1.x,a2.x],[a1.y,a2.y], color=color_arr[b.bond_type],linestyle=linestyle_arr[b.bond_type]);

        # Cute lil' stems
        if draw_stems:
            ax.plot([a1.x,a1.x+a1.v_stem[0]*0.2],[a1.y,a1.y+a1.v_stem[1]*0.2], color="purple");
            ax.plot([a2.x,a2.x+a2.v_stem[0]*0.2],[a2.y,a2.y+a2.v_stem[1]*0.2], color="purple");
    
    ax.plot([xlo,xhi,xhi,xlo,xlo],[ylo,ylo,yhi,yhi,ylo],color='red',linestyle=":")
    ax.set_aspect('equal')

    if show_now:
        plt.show();

#### MAIN FUNCTION FOR MAKING NETWORKS

def generate_pg_network(
        Ny           : int   = 100,     # Total number of DSU in the y direction for the network
        mesh_density : float = 1.0,     # Target density, units of (number of DSU) / (DSU length scale)**2
        anisotropy   : float = 0.65,    # 0.0 => glycans are perfectly hoop-aligned (+y)
                                        # 1.0 => glycans orientation is completely random
        distribution : list[int] = None,
        filepath     : str  = None,          # If set, write file to this filepath. File is lammps-compatible.
        generate_figure_of_steps   : bool     = False, # Plot bonds for debug purposes?
        plot_network_on_these_axes : plt.Axes = None
        ):
    
    if distribution == None:
        distribution = create_FlorySchulz_distribution(2,30,0.9,1E8);
    
    # Input checks
    assert (Ny >= 10)
    assert (type(Ny) == int)
    assert (0 < mesh_density)
    assert (type(mesh_density) == float)
    assert (0 <= anisotropy) and (anisotropy <= 1.0)
    assert (type(anisotropy) == float)
    assert max(distribution) < Ny;
    assert (type(distribution) == list)
    assert (type(filepath) == str) or (filepath == None)
    assert (type(generate_figure_of_steps) == bool)

    # Map an id (1,2,3,...) to python object. These ids are used in lammps.
    atoms   : dict[int,Atom] = dict();
    bonds   : dict[int,Bond] = dict();
    angles  : dict[int,Angle] = dict();
    glycans : dict[int,GlycanMolecule] = dict();

    # Equations derived by Octavio give a starting point estimate for the spacing between glycans for a square patch
    mean_of_distribution = np.mean(distribution);
    epsilon_x = np.sqrt( (1 + (1/2)*mean_of_distribution)**2 + ((1/mesh_density) - 1)*(1 + mean_of_distribution) ) - (1+(1/2)*mean_of_distribution);
    epsilon_y = epsilon_x/(1+mean_of_distribution);
    Nx = floor((1+epsilon_y)/(1+epsilon_x)*Ny);

    # Box dimensions in nm
    simbox_ly = (1+epsilon_y) * DSU * Ny;
    simbox_lx = (1+epsilon_x) * DSU * Nx;

    # Place non-rotated glycans with equal horizontal spacing.
    # Vertical spacing is equal per-column, and on-average equal from column to column.
    populate_glycans_on_a_not_so_unitary_grid(atoms, bonds, angles, glycans, Nx, Ny, epsilon_x, epsilon_y, distribution);

    if generate_figure_of_steps:
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)
        ax1 : plt.Axes; ax2 : plt.Axes; ax3 : plt.Axes; ax4 : plt.Axes;
        visualizeBonds(atoms, bonds, glycans, 0, simbox_lx, 0, simbox_ly, ax1, draw_stems=False);

    # Jangle the glycans
    for g in glycans.values():
        dx = 0.8*(random()-1);
        dy = 0.8*(random()-1);
        g.displace_by_const(atoms, dx, dy)

    #if visuals:
    #    visualizeBonds(atoms, bonds, glycans, 0, DSU * Nx, 0, DSU * Ny, ax2);

    # Rotate the glycans randomly about their center of mass
    for g in glycans.values():
        alpha = (2*random()-1) * anisotropy * (np.pi)/2;
        g.rotate_wrt_cm(atoms, alpha)

    if generate_figure_of_steps:
        visualizeBonds(atoms, bonds, glycans, 0, simbox_lx, 0, simbox_ly, ax2, draw_stems=False);

    # Atoms and glycans will be outside the box b/c of rotation and
    # column start randomization. We're sticking them back into the box
    # at this point to simplify peptide-crosslink calculations
    for g in glycans.values():
        g.correct_orthogonal_PCB(atoms, 0, simbox_lx, 0, simbox_ly);

    if generate_figure_of_steps:
        visualizeBonds(atoms, bonds, glycans, 0, simbox_lx, 0, simbox_ly, ax3, draw_stems=False);

    # Form peptide crosslinks based on distance and angle criteria
    form_peptide_bonds(atoms, bonds, glycans, simbox_lx, simbox_ly);

    # Count Cross-Linking
    density_fraction, crosslink_ratio = compute_crosslink_ratio(atoms, bonds, simbox_lx, simbox_ly);

    if generate_figure_of_steps:
        print(f"Box Dimensions [nm] = ({simbox_lx}, {simbox_ly})")
        print(f"Density = {density_fraction}")
        print(f"Crosslink Ratio = {crosslink_ratio}")
        visualizeBonds(atoms, bonds, glycans, 0, simbox_lx, 0, simbox_ly, ax4, draw_stems=False);
        for a in [ax1,ax2,ax3,ax4]:
            a.set_xticks([]);
            a.set_yticks([]);
        
        ax1.set_title("#1: Populate Glycan")
        ax2.set_title("#2: Reorient Glycan")
        ax3.set_title("#3: Apply PCB")
        ax4.set_title("#4: Form Cross-Links")
        fig.set_size_inches(6,7)
        plt.show()

    if plot_network_on_these_axes:
        visualizeBonds(atoms, bonds, glycans, 0, simbox_lx, 0, simbox_ly, plot_network_on_these_axes, draw_stems=False);

    #Delete free-floating glycans
    #for g in glycans.values():
    #    g.delete_if_free(atoms, bonds, angles);

    # Transform coordinates of atoms so patch is centered on 0,0 in lammps
    for a in atoms.values():
        a.translate(-simbox_lx/2, -simbox_ly/2, 0);
    
    if not filepath == None:
        # Write everything to LAMMPS datafile
        write_to_laamps_datafile(filepath, atoms, bonds, angles, simbox_lx, simbox_ly);

    return density_fraction, crosslink_ratio, glycans, atoms, bonds, angles;

# Functions to compare network distribution to theory distribution
def normalized_length_distribution(distribution : list[int]):
    possible_glycan_lengths = list(range(min(distribution),max(distribution)+1));
    norm_distrib = [0]*len(possible_glycan_lengths)
    len_distrib = len(distribution)
    for i,x in enumerate(possible_glycan_lengths):
        norm_distrib[i] = distribution.count(x) / len_distrib;

    return possible_glycan_lengths, norm_distrib

def actual_length_distribution(glycans : dict[int,GlycanMolecule], distribution : list[int]):
    # 0, 1, 2, ..., 20 etc
    # We include smaller lengths because they can be generated with the 'filler glycans' 
    # added to meet the density criteria when the drawn glycan length is too large
    possible_glycan_lengths = list(range(0,(max(distribution)+1)+5)); # includes a bit of margin at the end

    # First contains the absolute numbers of each length, then the relative proportion
    actual_distrib = np.zeros(len(possible_glycan_lengths));

    # each index i of actual_distrib is a counter for length of i DSU
    for g in glycans.values():
        actual_distrib[len(g.atom_ids)] += 1;

    # abs # -> proportion
    actual_distrib = actual_distrib/len(glycans);

    return possible_glycan_lengths, actual_distrib