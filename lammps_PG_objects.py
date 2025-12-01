import numpy as np;
import numpy.typing as npt;
from dataclasses import dataclass;

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

    def is_eligible(self,ATOM_TYPE_BINDING_DSU) -> bool:
        if self.atom_type != ATOM_TYPE_BINDING_DSU:
            return False;
    
        if self.has_peptide:
            return False;

        return True;

    def correct_PCB(self, xlo, xhi, xy, ylo, yhi):
        # Transforms the atom's position to be within the boundary of the original periodic box
        w = (xhi-xlo);
        h = (yhi-ylo);

        if self.y > yhi:
            self.y -= h;
        elif self.y < ylo:
            self.y += h;

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

    def to_datafile(self, f):
        f.write(f"{self.id} {self.bond_type} {self.atom_id_1} {self.atom_id_2}\n")

    def add_distance_and_forces(self,dist,fx,fy,fz):
        self.dist = dist;
        self.forces = np.array([fx,fy,fz]);

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