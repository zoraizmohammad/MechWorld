from lammps_PG_objects import Atom, Bond, Angle, GlycanMolecule;
from simulation_constants_settings import *;
import os;

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

def import_atoms_from_dump(filename : str, triclinic_bounds = None) -> dict[int,Atom]:
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

    if not triclinic_bounds:
        triclinic_bounds = import_2D_triclinic_box_bounds_from_dump(filename)

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

    atoms : dict[int,Atom] = dict();
    for ai in range(n_atoms):
        atom_data = list(map(float, lines[i+1+ai].split()));
        a = Atom(id=int(atom_data[0]), mol_id=int(atom_data[1]), atom_type=int(atom_data[2]), x=atom_data[3], y=atom_data[4], z=0);
        a.correct_triclinic_PCB(xlo, xhi, xy, ylo, yhi);
        atoms[atom_data[0]] = a;

    return atoms

def import_bonds_from_dump(filename : str) -> dict[int,Bond]:
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

    bonds : dict[int,Bond] = dict();
    for j in range(n_bonds):
        bond_data = list(map(float, lines[i+1+j].split()));
        b = Bond(id=int(bond_data[0]), bond_type=int(bond_data[1]), atom_id_1=int(bond_data[2]), atom_id_2=int(bond_data[3]));
        b.add_distance_and_forces(bond_data[4], bond_data[5], bond_data[6], bond_data[7]);
        bonds[bond_data[0]] = b;

    return bonds

def reconstruct_molecule_objects(atoms : dict[int,Atom], bonds : dict[int,Bond]) -> dict[int,GlycanMolecule]:
    molecules : dict[int,GlycanMolecule] = dict()

    # Add all the atoms to the molecules
    for a in atoms.values():
        molecule_id = a.mol_id;

        # create molecule if needed...
        if molecule_id not in molecules.keys():
            molecules[molecule_id] = GlycanMolecule(molecule_id)

        # add atom id
        molecules[molecule_id].add_atom_id(a.id)

    # Add all the bonds to the molecules (which should all be created by now)
    for b in bonds.values():
        for a in (atoms[b.atom_id_1], atoms[b.atom_id_2]):
            molecule_id = a.mol_id;
            molecules[molecule_id].add_bond_id(b.id)

    return molecules;

def import_all_from_dump(working_directory : str, filename_no_extension : str) -> tuple[tuple, dict[int,Atom], dict[int,Bond], dict[int,GlycanMolecule]]:
    filepath_initial_atoms = os.path.join(working_directory, filename_no_extension + ".atoms");
    filepath_initial_bonds = os.path.join(working_directory, filename_no_extension + ".bonds");

    bounds = import_2D_triclinic_box_bounds_from_dump(filepath_initial_bonds)
    atoms = import_atoms_from_dump(filepath_initial_atoms, bounds);
    bonds = import_bonds_from_dump(filepath_initial_bonds);
    molecules = reconstruct_molecule_objects(atoms, bonds);

    return bounds, atoms, bonds, molecules;