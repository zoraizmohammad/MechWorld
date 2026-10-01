import numpy as np;
import numpy.typing as npt;
from typing import Union; # P3.9 on Hoffman2
from dataclasses import dataclass;
import random as python_random;
from utils_helpers import get_angle_between_vectors;
from math import floor, ceil

from simulation_constants_settings import *

DATAFILE_SIGNIFICANT_DIGITS = 17


def format_datafile_float(value, significant_digits=DATAFILE_SIGNIFICANT_DIGITS):
    """Format a finite scalar for a round-trippable LAMMPS text data file."""
    if isinstance(significant_digits, bool) or not isinstance(significant_digits, int):
        raise ValueError("significant_digits must be an integer")
    if significant_digits < 1 or significant_digits > 17:
        raise ValueError("significant_digits must be between 1 and 17")
    value = float(value)
    if not np.isfinite(value):
        raise ValueError("LAMMPS data-file values must be finite")
    return format(value, f".{significant_digits}g")

# LAAMPS ENERGY (& TENSION) FUNCTIONS
def peptide_energy_lammps(bond_distance) -> Union[float,None]:
    return lammps_energy_nonlinear(bond_distance, PEPTIDE_COEFFICIENTS[0], PEPTIDE_COEFFICIENTS[1], PEPTIDE_COEFFICIENTS[2])

def peptide_tension_lammps(bond_distance) -> Union[float,None]:
    return lammps_tension_nonlinear(bond_distance, PEPTIDE_COEFFICIENTS[0], PEPTIDE_COEFFICIENTS[1], PEPTIDE_COEFFICIENTS[2])

def glycan_energy_lammps(bond_distance) -> Union[float,None]:
    return lammps_energy_linear(bond_distance, GLYCAN_COEFFICIENTS[0], GLYCAN_COEFFICIENTS[1])

def glycan_tension_lammps(bond_distance) -> Union[float,None]:
    return lammps_tension_linear(bond_distance, GLYCAN_COEFFICIENTS[0], GLYCAN_COEFFICIENTS[1])

def lammps_energy_linear(r, K, r0) -> Union[float,None]:
    return K*(r-r0)**2;

def lammps_tension_linear(r, K, r0) -> Union[float,None]:
    return 2*K*(r-r0);

def lammps_energy_nonlinear(r, epsil, r0, lambd) -> Union[float,None]:
    if ((r-r0) >= lambd):
        return None
    else:
        return epsil*(r-r0)**2 / (lambd**2 - (r-r0)**2);

def lammps_tension_nonlinear(r, epsil, r0, lambd) -> Union[float,None]:
    if ((r-r0) >= lambd):
        return None
    else:
        return (2 * lambd**2 * epsil * (r-r0)) / (r**2 - (2*r0*r) + r0**2 - lambd**2)**2

###
@dataclass
class TriclinicBounds:
    xlo : float
    xhi : float
    xy  : float
    ylo : float
    yhi : float

def _validate_2d_cell(xlo, xhi, xy, ylo, yhi):
    cell_values = np.array([xlo, xhi, xy, ylo, yhi], dtype=float)
    if not np.all(np.isfinite(cell_values)):
        raise ValueError("Periodic cell bounds and tilt must be finite")
    if xhi <= xlo or yhi <= ylo:
        raise ValueError("Periodic cell lengths must be positive")

def _wrap_position_2d(x, y, xlo, xhi, xy, ylo, yhi):
    """Wrap a Cartesian point and return its LAMMPS-style lattice image shift.

    The returned integer shift ``n`` follows ``unwrapped = wrapped + H @ n``,
    where ``H = [[xhi - xlo, xy], [0, yhi - ylo]]``.
    """
    _validate_2d_cell(xlo, xhi, xy, ylo, yhi)
    lx = xhi - xlo
    ly = yhi - ylo
    fractional_y = (y - ylo) / ly
    fractional_x = (x - xlo - xy * fractional_y) / lx
    image_x = floor(fractional_x)
    image_y = floor(fractional_y)
    wrapped_x = x - lx * image_x - xy * image_y
    wrapped_y = y - ly * image_y
    return (wrapped_x, wrapped_y), (image_x, image_y)

def minimum_image_displacement_2d(a1, a2, triclinic_bounds):
    """Return the shortest ``a1 -> a2`` vector and its lattice image offset.

    The offset ``n_12`` follows ``r_12 = x_2 - x_1 + H @ n_12``. For each
    candidate y image, the best x image is solved exactly; the finite y range
    is bounded by the best distance already found, avoiding fractional-rounding
    assumptions for skew or non-square cells.
    """
    (xlo, xhi, xy, ylo, yhi) = triclinic_bounds
    _validate_2d_cell(xlo, xhi, xy, ylo, yhi)
    lx = xhi - xlo
    ly = yhi - ylo
    dx = a2.x - a1.x
    dy = a2.y - a1.y

    image_y = int(round(-dy / ly))
    image_x = int(round(-(dx + xy * image_y) / lx))
    best_offset = (image_x, image_y)
    best_vector = np.array(
        [dx + lx * image_x + xy * image_y, dy + ly * image_y],
        dtype=float,
    )
    best_distance_squared = float(np.dot(best_vector, best_vector))

    vertical_limit = np.sqrt(best_distance_squared)
    image_y_min = ceil((-vertical_limit - dy) / ly)
    image_y_max = floor((vertical_limit - dy) / ly)
    for candidate_y in range(image_y_min, image_y_max + 1):
        ideal_x = -(dx + xy * candidate_y) / lx
        for candidate_x in {floor(ideal_x), ceil(ideal_x)}:
            candidate_vector = np.array(
                [
                    dx + lx * candidate_x + xy * candidate_y,
                    dy + ly * candidate_y,
                ],
                dtype=float,
            )
            candidate_distance_squared = float(
                np.dot(candidate_vector, candidate_vector)
            )
            if candidate_distance_squared < best_distance_squared:
                best_distance_squared = candidate_distance_squared
                best_vector = candidate_vector
                best_offset = (candidate_x, candidate_y)

    return best_vector, np.array(best_offset, dtype=np.int64)

class Atom:
    def __init__(self, id : int, mol_id : int, atom_type : int, x : float, y : float, z : float):
        self.id = id;
        self.mol_id = mol_id;
        self.atom_type = atom_type;
        self.x = x;
        self.y = y;
        self.z = z;
        self.image_shift = np.zeros(2, dtype=np.int64)
        self.is_inclined_to_peptide = True;
        self.has_peptide = False;

        # Can be set by set_stem_vector()
        self.v_glycan = None;
        self.v_stem = None;
    
    def run_bernoulli_trial(self, p : float, random_source=None):
        """Draw material eligibility from an injected stream when supplied."""
        source = python_random if random_source is None else random_source
        self.is_inclined_to_peptide = (source.random() < p);
    
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

    def to_datafile(self, f, significant_digits=DATAFILE_SIGNIFICANT_DIGITS):
        """Write one atom and return absolute coordinate round-trip errors."""
        coordinates = (self.x, self.y, self.z)
        tokens = tuple(
            format_datafile_float(value, significant_digits) for value in coordinates
        )
        f.write(
            f"{self.id} {self.mol_id} {self.atom_type} "
            f"{' '.join(tokens)}\n"
        )
        return tuple(
            abs(float(token) - float(value))
            for token, value in zip(tokens, coordinates)
        )

    def is_eligible(self) -> bool:
        if self.is_inclined_to_peptide and not self.has_peptide:
            return True;
        else:
            return False;

    def correct_triclinic_PCB(self, xlo, xhi, xy, ylo, yhi):
        # Keep the mutation used by legacy callers while exposing image changes.
        (self.x, self.y), applied_shift = _wrap_position_2d(
            self.x, self.y, xlo, xhi, xy, ylo, yhi
        )
        self.image_shift += np.array(applied_shift, dtype=np.int64)
        return applied_shift

    def correct_orthogonal_PCB(self, xlo, xhi, ylo, yhi):
        return self.correct_triclinic_PCB(xlo, xhi, 0.0, ylo, yhi)

### PCB HANDLING
def shortest_path_is_periodic_x(a1 : Atom, a2 : Atom, simbox_lx : float):
    return abs(a1.x - a2.x) > (simbox_lx/2)

def shortest_path_is_periodic_y(a1 : Atom, a2 : Atom, simbox_ly : float):
    return abs(a1.y - a2.y) > (simbox_ly/2)

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

    def get_tension(self):
        if self.bond_type == BOND_TYPE_GLYCAN:
            return glycan_tension_lammps(self.dist);
        elif self.bond_type == BOND_TYPE_PEPTIDE:
            return peptide_tension_lammps(self.dist);
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

    def delete_components(self, atoms : dict[int,Atom], bonds : dict[int,Bond], angles : dict[int,Angle] = None):
        [atoms.pop(x) for x in self.atom_ids];
        [bonds.pop(x) for x in self.bond_ids];
        
        # Angles is optional, will be deleted if provided
        if (angles != None):
            [angles.pop(x) for x in self.angle_ids];
    
    def add_atom_id(self, atom_id : int):
        self.atom_ids.add(atom_id);

    def add_bond_id(self, bond_id : int):
        self.bond_ids.add(bond_id);

    def delete_if_free(self, atoms : dict[int,Atom], bonds : dict[int,Bond], angles : dict[int,Angle]) -> bool:
        if len(self.bond_ids) == (len(self.atom_ids)-1):
            self.delete_components(atoms, bonds, angles)

    def get_orientation_vector(self, atoms : dict[int,Atom], triclinic_bounds):
        a0 = atoms[min(self.atom_ids)] # First atom placed. It is 'top' of glycan before rotation.
        af = atoms[max(self.atom_ids)] # It is 'bottom' glycan before rotation.
        glycan_vector, _ = minimum_image_displacement_2d(
            a0, af, triclinic_bounds
        )
        return glycan_vector;

    def get_orientation_with_respect_to_hoop(self, atoms : dict[int,Atom], triclinic_bounds) -> float:
        hoop_vector = np.array([0,1])
        glycan_vector = self.get_orientation_vector(atoms, triclinic_bounds)
        angle = get_angle_between_vectors(hoop_vector, glycan_vector);

        if (angle > 90):
            angle = angle - 180;

        # If (Top_x - Bottom_x) > 0 -> Flip angle b/c glycan is tilted in -Z direction
        if glycan_vector[0] > 0:
            return -1 * angle;
        else:
            return angle;

    def displace_by_const(self, atoms : dict[int,Atom], dx, dy):
        for aid in self.atom_ids:
            atoms[aid].x += dx;
            atoms[aid].y += dy;
    
        self.cm_x += dx;
        self.cm_y += dy;
    
    def set_cm(self, x, y):
        self.cm_x = x;
        self.cm_y = y;
    
    def recalculate_cm(self, atoms : dict[int,Atom], xlo, xhi, ylo, yhi):

        w = xhi - xlo;
        h = yhi - ylo;
    
        median_aid = np.median(list(self.atom_ids))

        tmp_x = self.cm_x;
        tmp_y = self.cm_y;

        #print(self.id, self.atom_ids, median_aid)

        if (median_aid % 1 == 0):
            # Length is odd, there's a single atom at cm
            self.cm_x = atoms[median_aid].x;
            self.cm_y = atoms[median_aid].y;
        else:
            # The length is even, need to average two glycans and account for PCB
            a1 = atoms[floor(median_aid)]
            a2 = atoms[ceil(median_aid)]

            if abs(a1.x - a2.x) > w/2:
                # Periodic across the left/right sides of the box
                self.cm_x = (a1.x + a2.x + w)/2;     
                while (self.cm_x > xhi): self.cm_x -= w;
                print(f"cm is periodic in x: ({self.cm_x},{self.cm_y})")
            else:
                self.cm_x = (a1.x + a2.x)/2;
            
            if abs(a1.y - a2.y) > h/2:
                # Periodic across the top/bottom sides of the box
                self.cm_y = (a1.y + a2.y + h)/2;     
                while (self.cm_y > yhi): self.cm_y -= h;
                print(f"cm is periodic in y: ({self.cm_x},{self.cm_y})")
            else:
                self.cm_y = (a1.y + a2.y)/2;
    
            if tmp_x != self.cm_x:
                print(f"cm x changed: {tmp_x} -> {self.cm_x}")

            if tmp_y != self.cm_y:
                print(f"cm y changed: {tmp_y} -> {self.cm_y}")
    
    def rotate_wrt_cm(self, atoms : dict[int,Atom], alpha : float):
        # alpha has units radians
        cosa = np.cos(alpha);
        sina = np.sin(alpha);
        rotation_matrix = np.array([[cosa, -sina],[sina, cosa]])
        r_cm = np.array([self.cm_x, self.cm_y]);

        for aid in self.atom_ids:
            a = atoms[aid];
            r_relative = np.array([a.x, a.y]) - r_cm
            r_rotated_relative = np.matmul(rotation_matrix, r_relative)
            r_rotated_absolute = r_rotated_relative + r_cm

            a.x, a.y = r_rotated_absolute;
            a.set_stem_vector(alpha);

    def get_length(self) -> int:
        return len(self.atom_ids);

    def get_tension(self, bonds : dict[int,Bond]):
        return np.mean([b.get_tension() for b in [bonds.get(bid) for bid in self.bond_ids]])

    def correct_orthogonal_PCB(self, atoms : dict[int,Atom], xlo, xhi, ylo, yhi):
        
        for id in self.atom_ids:
            atoms[id].correct_orthogonal_PCB(xlo, xhi, ylo, yhi)

        while (self.cm_x < xlo):
            self.cm_x += (xhi - xlo);
        
        while (self.cm_x > xhi):
            self.cm_x -= (xhi - xlo);

        while (self.cm_y < ylo):
            self.cm_y += (yhi - ylo);
        
        while (self.cm_y > yhi):
            self.cm_y -= (yhi - ylo);
