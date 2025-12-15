import numpy as np;
import numpy.typing as npt;
from dataclasses import dataclass;

# Constants
DSU = 1.03; #nm # Should it be 1.03 or 2? Xioxuan 2024 vs. Nyugen 2015
BOND_TYPE_GLYCAN = 1;
BOND_TYPE_PEPTIDE = 2;
ANGLE_TYPE_GLYCAN = 1;
ATOM_TYPE_POS_DSU = 1; # + orientation
ATOM_TYPE_NEG_DSU = 2; # - orientation

# https://en.wikipedia.org/wiki/KT_(energy)
#E_PEPTIDE_CUTOFF = 4.11E-21 * 1E18; # 1 kT = 4.11E-21 J, 1 J = 1E18 attogram-nm2/ns2

# https://en.wikipedia.org/wiki/Peptidoglycan
# https://en.wikipedia.org/wiki/N-Acetylglucosamine
# https://en.wikipedia.org/wiki/N-Acetylmuramic_acid
DSU_MOLAR_MASS = (221.21 + 293.272)/2; # g/mol
A_NUM = 6.02214076E23;
DSU_MASS_NANOGRAM = DSU_MOLAR_MASS / A_NUM * 1E9;

@dataclass
class TriclinicBounds:
    xlo : float
    xhi : float
    xy  : float
    ylo : float
    yhi : float

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
        if self.has_peptide:
            return False;
        else:
            return True;

    def correct_PCB(self, xlo, xhi, xy, ylo, yhi):
        # Transforms the atom's position to be within the boundary of the original periodic box
        w = (xhi-xlo);
        h = (yhi-ylo);

        if self.y > yhi:
            self.y -= h;
        elif self.y < ylo:
            self.y += h;
        
        if (xy == 0):
            if self.x < xlo:
                self.x += w;
            elif self.x > xhi:
                self.x -= w;
        else:
            triclinic_slope = (h) / (xy);
            if self.x < xlo + (self.y - ylo)/triclinic_slope:
                self.x += w;
            elif self.x > xhi + (self.y - ylo)/triclinic_slope:
                self.x -= w;

class Bond:
    def __init__(self, id : int, bond_type : int, atom_id_1 : int, atom_id_2 : int):
        self.id = id;
        self.bond_type = bond_type;
        self.atom_id_1 = atom_id_1;
        self.atom_id_2 = atom_id_2;
        self.dist : float | None = None;
        self.forces : npt.NDArray[np.float64] | None = None;
        self.force_norm : np.float64 | None = None;

    def to_datafile(self, f):
        f.write(f"{self.id} {self.bond_type} {self.atom_id_1} {self.atom_id_2}\n")

    def add_distance_and_forces(self,dist,fx,fy,fz):
        self.dist = dist;
        self.forces = np.array([fx,fy,fz]);
        self.force_norm = np.linalg.norm(self.forces);

class Angle:
    def __init__(self, id : int, angle_type : int, atom_id_1 : int, atom_id_2 : int, atom_id_3 : int):
        self.id = id;
        self.angle_type = angle_type;
        self.atom_id_1 = atom_id_1;
        self.atom_id_2 = atom_id_2;
        self.atom_id_3 = atom_id_3;

    def to_datafile(self, f):
        f.write(f"{self.id} {self.angle_type} {self.atom_id_1} {self.atom_id_2} {self.atom_id_3}\n");

    def correct_pcb(self, triclinic_bounds):
        (xlo, xhi, xy, ylo, yhi) = triclinic_bounds;
        w = xhi - xlo;
        h = yhi - ylo;

        # Top and bottom of the boundary box aren't tilted
        if self.y < ylo:
            self.y += h;
        elif self.y > yhi:
            self.y -= h;

        if (xy == 0):
            # The left and right side walls are not tilted
            if self.y < xlo:
                self.x += w;
            elif self.y > xhi:
                self.x -= w;
        else:
            # The left and right side walls are tilted, can be represented by a slope
            triclinic_slope = (yhi - ylo) / (xy); # dy/dx
        
            if self.x < xlo + (self.y - ylo)/triclinic_slope:
                self.x += w;
            elif self.x > xhi + (self.y - ylo)/triclinic_slope:
                self.x -= w;