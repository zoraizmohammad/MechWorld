# PG Network Assembly Script
import numpy as np
import io
from math import sin, cos, floor
from random import randrange, random, shuffle
from collections import defaultdict

rng = np.random.default_rng()

# Constants
DSU = 2; #nm
BOND_TYPE_GLYCAN = 1;
BOND_TYPE_PEPTIDE = 2;
ANGLE_TYPE_GLYCAN = 1;
ATOM_TYPE_NOPEP_DSU = 1;
ATOM_TYPE_BINDING_DSU = 2;

# Note: Cells are typically rod-shaped, and are about 2.0 μm long and 0.25–1.0 μm in diameter, with a cell volume of 0.6–0.7 μm3. (from Wikipedia)
# 2um = 2000nm, 0.25-1.0um diameter = 785.40-3141.59nm in circumference.

# Options
rho = 1;                    # float; Higher = More Dense
isotropic_parameter = 0.65; # 0-1; Higher = Orientation is More Random
random_displacement_stdev = DSU*(1/(2*np.sqrt(2)));
probability_that_DSU_can_bind = 0.4; # 0.4 - 0.6
proportion_of_binding_DSU_simple = 2; # 1 of X DSU will have the ability to bind, spaced evenly not randomly
glycan_gap = DSU / rho;
column_gap = DSU / rho;
SIMBOX_MAX_W = 50*DSU;
SIMBOX_MAX_H = 50*DSU;

# Classes, yada
class Molecule:
    def __init__(self, id : int, num_DSU : int, x : float, y : float, z : float):
        pass

class Atom:
    def __init__(self, id : int, mol_id : int, atom_type : int, x : float, y : float, z : float):
        self.id = id;
        self.mol_id = mol_id;
        self.atom_type = atom_type;
        self.x = x;
        self.y = y;
        self.z = z;
        self.has_peptide = False;

    def translate(self, dx, dy, dz):
        self.x += dx;
        self.y += dy;
        self.z += dz;

    def to_datafile(self, f):
        f.write(f"{self.id} {self.mol_id} {self.atom_type} {self.x:.2f} {self.y:.2f} {self.z:.2f}\n")

    def is_eligible(self) -> bool:
        if self.atom_type != ATOM_TYPE_BINDING_DSU:
            return False;
    
        if self.has_peptide:
            return False;

        return True;

class Bond:
    def __init__(self, id : int, bond_type : int, atom_id_1 : int, atom_id_2 : int):
        self.id = id;
        self.bond_type = bond_type;
        self.atom_id_1 = atom_id_1;
        self.atom_id_2 = atom_id_2;

    def to_datafile(self, f):
        f.write(f"{self.id} {self.bond_type} {self.atom_id_1} {self.atom_id_2}\n")

class Angle:
    def __init__(self, id : int, angle_type : int, atom_id_1 : int, atom_id_2 : int, atom_id_3 : int):
        self.id = id;
        self.angle_type = angle_type;
        self.atom_id_1 = atom_id_1;
        self.atom_id_2 = atom_id_2;
        self.atom_id_3 = atom_id_3;

    def to_datafile(self, f):
        f.write(f"{self.id} {self.angle_type} {self.atom_id_1} {self.atom_id_2} {self.atom_id_3}\n");

# Globals
simbox_actual_width = 0; # TBD by population
simbox_actual_height = 0; # TBD by population
molecule_counter = 0;
lst_of_atoms : list[Atom] = list(); # note to self: () are used when you have an iterable, use x : list[obj] = list() when type hinting
lst_of_bonds : list[Bond] = list();
lst_of_angles :  list[Angle] = list();

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

#


# print(distribution)

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

    for i in range(0,numDSUs):
        xA = x+((i+1)-(numDSUs/2))*DSU*sin(alpha)+dx # nm, Applies rotation to x values, rotation is centered on midpoint.
        yA = y+((i+1)-(numDSUs/2))*DSU*cos(alpha)+dy # nm, Applies rotation to x values, rotation is centered on midpoint.

        # Atoms
        atom_id = len(lst_of_atoms)+1;

        #if (random() <= probability_that_DSU_can_bind):
        #    lst_of_atoms.append(Atom(atom_id, mol_id, 2, xA, yA, 0))
        #else:
        #    lst_of_atoms.append(Atom(atom_id, mol_id, 1, xA, yA, 0))

        if (atom_id % proportion_of_binding_DSU_simple == 0):
            lst_of_atoms.append(Atom(atom_id, mol_id, 2, xA, yA, 0))
        else:
            lst_of_atoms.append(Atom(atom_id, mol_id, 1, xA, yA, 0))

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

    (DSU_lengths, new_glycan_gap) = get_DSU_lengths(SIMBOX_MAX_H)
    n = len(DSU_lengths)
    #print(f"Column {x}: new_glycan_gap = {new_glycan_gap}");
    #print(DSU_lengths, new_glycan_gap)

    y = (new_glycan_gap/2) + rng.uniform(-0.5*SIMBOX_MAX_H,0.5*SIMBOX_MAX_H); 
    # This shift is a little bit subtle, I am shifting the whole row so the breaks at the tops and bottoms aren't aligned
    # it is easiest to imagine this when there is no rotation
    for DSU_length in DSU_lengths:
        #print(y)
        y += (DSU_length/2)*DSU # nm

        # To-DO: randomly select rotation and displacement
        dx = rng.normal(0, random_displacement_stdev); # Shape should to be adjusted to match paper, 0.996
        dy = rng.normal(0, random_displacement_stdev);
        # This shift in y is a bit subtle: I am shifting the 
        alpha = (2*random()-1) * isotropic_parameter * (np.pi)/2; # Uniform distribution

        #dx = 0; dy = 0; 
        #alpha = 0;

        molecule_counter += 1;
        build_a_glycan(molecule_counter, x, y, dx, dy, DSU_length, alpha);

        y += (DSU_length/2)*DSU + new_glycan_gap # nm

x = column_gap/2;
while True:
    # Interating across the columns
    if (x + column_gap > SIMBOX_MAX_W):
        simbox_actual_height = SIMBOX_MAX_H;
        simbox_actual_width = x;
        break
    
    row_trot(x);

    x += column_gap;

def put_the_atoms_into_a_spatial_hash_smh(cell_size): # Saw this in a yt video once
    grid = defaultdict(list)
    is_of_eligible_atoms = list();

    mcx = floor(simbox_actual_width / cell_size);
    mcy = floor(simbox_actual_height / cell_size);

    for idx, a in enumerate(lst_of_atoms):
        if a.is_eligible():
            cx = floor(a.x / cell_size)
            cy = floor(a.y / cell_size)

            # Got to consider periodic bonds
            # When I forgor to add this, the edges pulled apart like delicious spaghetti
            if ((cx) < 0):
                cx += mcx;
            if ((cy) < 0):
                cy += mcy;
            if ((cx) > mcx):
                cx -= mcx;
            if ((cy) > mcy):
                cy -= mcy;

            is_of_eligible_atoms.append(idx)
            grid[(cx, cy)].append(idx) # Holds index, and thus id of the atom
        else:
            continue
    return grid, is_of_eligible_atoms

def create_bond_with_nearby_neighbor(idx_of_atom : int, grid : defaultdict[list], cell_size : float):
    # cell_size = radius
    a : Atom = lst_of_atoms[idx_of_atom];

    # It could be ineligible because another bond was formed with it.
    if not a.is_eligible():
        return;

    mcx = floor(simbox_actual_width / cell_size);
    mcy = floor(simbox_actual_height / cell_size);

    cx = floor(a.x / cell_size)
    cy = floor(a.y / cell_size)

    neighbors_idxs : list[int] = list()

    for dcx in [-1,0,1]:
        for dcy in [-1,0,1]:

            # Got to consider periodic bonds
            if ((cx + dcx) < 0):
                cx += mcx;
                #print(cx)
            if ((cy + dcy) < 0):
                cy += mcy;
            if ((cx + dcx) > mcx):
                cx -= mcx;
                #print(cx)
            if ((cy + dcy) > mcy):
                cy -= mcy;
            
            if (cx+dcx,cy+dcy) not in grid:
                #print(f"Indices {cx+dcx} {cy+dcy} are undefined")
                continue;

            neighbors_idxs.extend(grid[(cx+dcx,cy+dcy)])

    # I'm retrieving the entire list so we can implement more complex bonding criteria in the future
    # print(f"{a.id} -> {neighbors_idxs}");

    for idx_of_neighbor in neighbors_idxs:
        neighbor : Atom = lst_of_atoms[idx_of_neighbor]

        if (not neighbor.is_eligible()):
            continue;

        if (neighbor.mol_id == a.mol_id):
            #print(a.mol_id)
            continue;

        if not periodic_distance_test(neighbor.x, neighbor.y, a.x, a.y, cell_size):
            continue;

        lst_of_bonds.append(Bond(len(lst_of_bonds)+1, BOND_TYPE_PEPTIDE, a.id, neighbor.id))
        lst_of_atoms[idx_of_atom].has_peptide = True;
        lst_of_atoms[idx_of_neighbor].has_peptide = True;
        #print(f"Created bond between {a.id} <> {neighbor.id}")
        return;

def periodic_distance_test(x1,y1,x2,y2,r) -> bool:

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

    return (x1 - x2)**2 + (y1 - y2)**2 < r**2

def go_go_gadget_peptide_bonds():
    peptide_bonding_radius = 4.5; # nm, This is the limit of Peptide length with model we use
    (grid, idxs_of_eligible_atoms) = put_the_atoms_into_a_spatial_hash_smh(peptide_bonding_radius)

    #print(grid)

    # We're going to form the bonds randomly so certain atoms don't have priority
    #print(idxs_of_eligible_atoms)

    if idxs_of_eligible_atoms == []:
        return; # None

    shuffle(idxs_of_eligible_atoms)
    for i in range(0, len(idxs_of_eligible_atoms)):
        create_bond_with_nearby_neighbor(idxs_of_eligible_atoms[i], grid, peptide_bonding_radius)

# Create Peptide Bonds
go_go_gadget_peptide_bonds()

# Transform Coordinates of Atoms
for a in lst_of_atoms:
    a.translate(-simbox_actual_width/2, -simbox_actual_height/2, 0);

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
        f.write(f"1 1.0\n")
        f.write(f"2 1.0\n")

        f.write(f"\nAtoms\n\n")
        for a in lst_of_atoms:
            a.to_datafile(f)

        f.write(f"\nBonds\n\n")
        for b in lst_of_bonds:
            b.to_datafile(f)

        f.write(f"\nAngles\n\n")
        for c in lst_of_angles:
            c.to_datafile(f)

# Write everything to LAMMPS datafile
write_to_laamps_datafile("file.data");
