import numpy as np;
import numpy.typing as npt;
from typing import Union;
from dataclasses import dataclass;
from random import random;
from math_helpers import get_angle_between_vectors;

from simulation_constants_settings import *

# Hoffman supports up to python 3.9.6, must use union
def peptide_energy_lammps(bond_distance) -> Union[float,None]:
    return lammps_nonlinear(bond_distance, PEPTIDE_COEFFICIENTS[0], PEPTIDE_COEFFICIENTS[1], PEPTIDE_COEFFICIENTS[2])

def glycan_energy_lammps(bond_distance) -> Union[float,None]:
    return lammps_linear(bond_distance, GLYCAN_COEFFICIENTS[0], GLYCAN_COEFFICIENTS[1])

def lammps_nonlinear(r, esp, r0, lambd) -> Union[float,None]:
    if ((r-r0) >= lambd):
        return None
    else:
        return esp*(r-r0)**2 / (lambd**2 - (r-r0)**2);

def lammps_linear(r, K, r0) -> Union[float,None]:
    return K*(r-r0)**2;

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
        self.is_inclined_to_peptide = True;
        self.has_peptide = False;

        # Can be set by set_stem_vector()
        self.v_glycan = None;
        self.v_stem = None;
    
    def run_bernoulli_trial(self, p : float):
        self.is_inclined_to_peptide = (random() < p);
    
    def set_stem_vector(self, glycan_angle : float):
        self.v_glycan = np.array([-np.sin(glycan_angle), np.cos(glycan_angle)]);

        if self.atom_type == ATOM_TYPE_POS_DSU:
            # Right-Reaching, rotate by -90 degrees k
            rot_k = -np.pi/2
        else:
            # Left-Reaching, rotate by +90 degrees k
            rot_k = np.pi/2

        cos_r = np.cos(rot_k);
        sin_r = np.sin(rot_k);

        self.v_stem = np.matmul(np.array([[cos_r, -sin_r], [sin_r, cos_r]]), self.v_glycan);

    def translate(self, dx, dy, dz):
        self.x += dx;
        self.y += dy;
        self.z += dz;

    def to_datafile(self, f):
        f.write(f"{self.id} {self.mol_id} {self.atom_type} {self.x:.2f} {self.y:.2f} {self.z:.2f}\n")

    def is_eligible(self) -> bool:
        if self.is_inclined_to_peptide and not self.has_peptide:
            return True;
        else:
            return False;

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
        self.dist : Union[float,None] = None;
        self.forces : Union[npt.NDArray[np.float64], None] = None;
        self.force_norm : Union[np.float64, None] = None;

    def to_datafile(self, f):
        f.write(f"{self.id} {self.bond_type} {self.atom_id_1} {self.atom_id_2}\n")

    def add_distance_and_forces(self,dist,fx,fy,fz):
        self.dist = dist;
        self.forces = np.array([fx,fy,fz]);
        self.force_norm = np.linalg.norm(self.forces);

    def get_strain(self):
        if self.bond_type == BOND_TYPE_GLYCAN:
            return (self.dist - GLYCAN_COEFFICIENTS[1]) / GLYCAN_COEFFICIENTS[1]
        elif self.bond_type == BOND_TYPE_PEPTIDE:
            return (self.dist - PEPTIDE_COEFFICIENTS[1]) / PEPTIDE_COEFFICIENTS[1]
        else:
            return None;

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

class GlycanMolecule:
    def __init__(self, id : int): # Important lesson, don't mut set() in default arguments or it gets shared
        self.id = id;
        self.atom_ids = set();
        self.bond_ids = set();
        self.angle_ids = set();

    def delete_components(self, atoms : dict[int,Atom], bonds : dict[int,Bond], angles : dict[int,Angle]):
        pass
        [atoms.pop(x) for x in self.atom_ids];
        [bonds.pop(x) for x in self.bond_ids];
        [angles.pop(x) for x in self.angle_ids];
    
    def add_atom_id(self, atom_id : int):
        self.atom_ids.add(atom_id);

    def add_bond_id(self, bond_id : int):
        self.bond_ids.add(bond_id);

    def delete_if_free(self, atoms : dict[int,Atom], bonds : dict[int,Bond], angles : dict[int,Angle]) -> bool:
        if len(self.bond_ids) == (len(self.atom_ids)-1):
            self.delete_components(atoms, bonds, angles)
            #print(f"Deleted free glycan with id = {self.id}")

    def get_orientation_vector(self, atoms : dict[int,Atom]):
        dx = atoms[max(self.atom_ids)].x - atoms[min(self.atom_ids)].x;
        dy = atoms[max(self.atom_ids)].y - atoms[min(self.atom_ids)].y;
        glycan_vector = np.array([dx,dy])
        return glycan_vector;

    def get_orientation_with_respect_to_hoop(self, atoms : dict[int,Atom]) -> float:
        hoop_vector = np.array([0,1])
        glycan_vector = self.get_orientation_vector(atoms)
        angle = get_angle_between_vectors(hoop_vector, (glycan_vector[0], np.abs(glycan_vector[1])));
        if glycan_vector[0] > 0: 
            return -1 * angle;
        else:
            return angle; # If (Top_x - Bottom_x) > 0 -> Flip angle b/c glycan is tilted in -Z direction

    def displace_by_const(self, atoms : dict[int,Atom], dx, dy):
        for aid in self.atom_ids:
            atoms[aid].x += dx;
            atoms[aid].y += dy;
    
    def set_cm(self, x, y):
        self.cm_x = x;
        self.cm_y = y;
    
    def displace_by_strain(self, atoms : dict[int,Atom], strain_x, strain_y, simbox_lx, simbox_ly):
        dx = (self.cm_x % simbox_lx) * (strain_x);
        dy = (self.cm_y % simbox_ly) * (strain_y);
        self.displace_by_const(atoms, dx,dy);
    
    def rotate_wrt_cm(self, atoms : dict[int,Atom], alpha):
        cosa = np.cos(alpha);
        sina = np.sin(alpha);
        rotation_matrix = np.array([[cosa, -sina],[sina, cosa]])

        for aid in self.atom_ids:
            r_relative = np.array([atoms[aid].x, atoms[aid].y]) - np.array([self.cm_x, self.cm_y])
            r_rotated_relative = np.matmul(rotation_matrix, r_relative)
            r_abs_new = r_rotated_relative + np.array([self.cm_x, self.cm_y])
            atoms[aid].x = r_abs_new[0];
            atoms[aid].y = r_abs_new[1];
            atoms[aid].set_stem_vector(alpha);

    def get_length(self) -> int:
        return len(self.atom_ids);