from lammps_PG_objects import Atom, Bond, Angle, GlycanMolecule;
from simulation_constants_settings import *;
import numpy as np
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
    box_bounds_header = lines[i].split()
    box_bounds_fields = box_bounds_header[3:]
    if "abc" in box_bounds_fields or "origin" in box_bounds_fields:
        raise ValueError(
            "Unsupported general triclinic BOX BOUNDS header; "
            "this 2D reader accepts orthogonal or restricted triclinic dumps"
        )

    tilt_fields = {"xy", "xz", "yz"}.intersection(box_bounds_fields)
    if tilt_fields and box_bounds_fields[:3] != ["xy", "xz", "yz"]:
        raise ValueError("Malformed restricted triclinic BOX BOUNDS header")

    i += 1;
    box_bounds = []
    for j in range(3):
        parts = list(map(float, lines[i+j].split()))
        box_bounds.append(parts)

    is_restricted_triclinic = box_bounds_fields[:3] == ["xy", "xz", "yz"]
    if is_restricted_triclinic:
        xy = box_bounds[0][2]
        xz = box_bounds[1][2]
        yz = box_bounds[2][2]
        if xz != 0.0 or yz != 0.0:
            raise ValueError(
                "Unsupported 2D restricted triclinic BOX BOUNDS with nonzero xz/yz"
            )
    else:
        xy = 0.0

    # LAMMPS writes restricted-triclinic bounding extents to dump files. Convert
    # them back to the true box bounds used by the existing 2D return contract.
    xlo = box_bounds[0][0] - min(0.0, xy)
    xhi = box_bounds[0][1] - max(0.0, xy)
    ylo = box_bounds[1][0]
    yhi = box_bounds[1][1]

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
    atom_header = lines[i].split()
    if atom_header[:2] != ["ITEM:", "ATOMS"]:
        raise ValueError(f"Expected at line {i+1}: ITEM: ATOMS <columns...>");

    atom_columns = atom_header[2:]
    required_columns = {"id", "mol", "type", "x", "y"}
    missing_columns = required_columns.difference(atom_columns)
    if missing_columns:
        raise ValueError(
            f"Missing required atom dump columns: {', '.join(sorted(missing_columns))}"
        )
    if ("ix" in atom_columns) != ("iy" in atom_columns):
        raise ValueError("Atom dump must provide both ix and iy image columns or neither")

    column_index = {name: index for index, name in enumerate(atom_columns)}

    def parse_integer(column_name: str, values: list[str]) -> int:
        token = values[column_index[column_name]]
        try:
            return int(token)
        except ValueError:
            numeric_value = float(token)
            if not numeric_value.is_integer():
                raise ValueError(
                    f"Atom column {column_name} must contain an integer, got {token}"
                )
            return int(numeric_value)

    atoms : dict[int,Atom] = dict();
    for ai in range(n_atoms):
        atom_data = lines[i+1+ai].split();
        atom_id = parse_integer("id", atom_data)
        if atom_id in atoms:
            raise ValueError(f"Duplicate atom ID {atom_id} in {filename}")

        a = Atom(
            id=atom_id,
            mol_id=parse_integer("mol", atom_data),
            atom_type=parse_integer("type", atom_data),
            x=float(atom_data[column_index["x"]]),
            y=float(atom_data[column_index["y"]]),
            z=0,
        );
        if "ix" in column_index:
            a.image_shift = np.array(
                [parse_integer("ix", atom_data), parse_integer("iy", atom_data)],
                dtype=np.int64,
            )
        a.correct_triclinic_PCB(xlo, xhi, xy, ylo, yhi);
        atoms[a.id] = a;

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
