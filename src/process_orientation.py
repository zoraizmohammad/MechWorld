from lammps_PG_objects import Atom, Bond, Angle, GlycanMolecule;
from simulation_constants_settings import *;
import numpy as np;
import matplotlib.pyplot as plt;
import os;
from math_helpers import get_angle_between_vectors;
from import_data_from_dumps import import_2D_triclinic_box_bounds_from_dump, import_atoms_from_dump, import_bonds_from_dump, reconstruct_molecule_objects

def calculate_length_and_orientation_of_glycan_molecules(atoms : dict[int,GlycanMolecule], molecules : dict[int,GlycanMolecule], triclinic_bounds : tuple):
    
    list_orientations = list();
    list_lengths = list();

    for m in molecules.values():
        list_orientations.append(m.get_orientation_with_respect_to_hoop(atoms, triclinic_bounds))
        list_lengths.append(m.get_length())

    return list_orientations, list_lengths;

def calculate_strain_and_relative_glycan_orientation(atoms : dict[int,Atom], bonds : dict[int,Bond], molecules : dict[int,GlycanMolecule], triclinic_bounds : tuple):

    list_rel_orientation = list();
    list_peptide_strain = list();
    
    for b in bonds.values():
        if not b.bond_type == BOND_TYPE_PEPTIDE:
            continue;

        m1 = molecules[atoms[b.atom_id_1].mol_id];
        m2 = molecules[atoms[b.atom_id_2].mol_id];

        o1 = m1.get_orientation_vector(atoms, triclinic_bounds);
        o2 = m2.get_orientation_vector(atoms, triclinic_bounds);

        relative_orientation = get_angle_between_vectors(o1, o2);
        list_rel_orientation.append(relative_orientation);
        list_peptide_strain.append(b.get_strain());

    return list_rel_orientation, list_peptide_strain;

def calculate_strain_and_attachment_orientation(atoms : dict[int,Atom], bonds : dict[int,Bond], molecules : dict[int,GlycanMolecule], triclinic_bounds : tuple):

    list_rel_orientation = list();
    list_peptide_strain = list();
    
    for b in bonds.values():
        if not b.bond_type == BOND_TYPE_PEPTIDE:
            continue;

        a1 = atoms[b.atom_id_1];
        a2 = atoms[b.atom_id_2];

        peptide_vector = np.array([a2.x - a1.x, a2.y - a1.y])
        o1 = molecules[a1.mol_id].get_orientation_vector(atoms, triclinic_bounds);
        o2 = molecules[a2.mol_id].get_orientation_vector(atoms, triclinic_bounds);

        list_rel_orientation.append(get_angle_between_vectors(peptide_vector, o1));
        list_rel_orientation.append(get_angle_between_vectors(peptide_vector, o2));
        list_peptide_strain.append(b.get_strain());
        list_peptide_strain.append(b.get_strain());
    
    return list_rel_orientation, list_peptide_strain;

#### Produce a figure comparing the initial and final state of orientation, like Xaoxuan Figure 4B-D
def full_orientation_delta_figure(working_directory, filename_no_extension):
    # skeleton of figure
    fig, ax = plt.subplots(2,2);
    # https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes

    # relaxed data
    filepath_initial_atoms = os.path.join(working_directory, filename_no_extension + ".relaxed.atoms");
    filepath_initial_bonds = os.path.join(working_directory, filename_no_extension + ".relaxed.bonds");

    bounds = import_2D_triclinic_box_bounds_from_dump(filepath_initial_bonds)
    atoms = import_atoms_from_dump(filepath_initial_atoms, bounds);
    bonds = import_bonds_from_dump(filepath_initial_bonds);
    molecules = reconstruct_molecule_objects(atoms, bonds);
    [abs_orientations_0, lengths_0] = calculate_length_and_orientation_of_glycan_molecules(atoms, molecules, bounds)
    [rel_orientations_0, strains_0] = calculate_strain_and_relative_glycan_orientation(atoms, bonds, molecules, bounds)

    del filepath_initial_atoms, filepath_initial_bonds, bounds, atoms, bonds, molecules;

    # strained data
    filepath_final_atoms = os.path.join(working_directory, filename_no_extension + ".final.atoms");
    filepath_final_bonds = os.path.join(working_directory, filename_no_extension + ".final.bonds");

    bounds = import_2D_triclinic_box_bounds_from_dump(filepath_final_bonds)
    atoms = import_atoms_from_dump(filepath_final_atoms, bounds);
    bonds = import_bonds_from_dump(filepath_final_bonds);
    molecules = reconstruct_molecule_objects(atoms, bonds);
    [abs_orientations_f, lengths_f] = calculate_length_and_orientation_of_glycan_molecules(atoms, molecules, bounds)
    [rel_orientations_f, strains_f] = calculate_strain_and_attachment_orientation(atoms, bonds, molecules, bounds)

    del filepath_final_atoms, filepath_final_bonds, bounds, atoms, bonds, molecules;

    #### Plots
    # add labels and titles
    
    # Top-Left Plot: Relaxed Length vs Glycan Orientation
    ax[0, 0].scatter(abs_orientations_0, lengths_0, alpha=1E-2, color="black");
    ax[0, 0].set_xlim(-100, 100)
    ax[0, 0].set_xticks([-90,-60,-30,0,30,60,90])
    ax[0, 0].set_title("Initial Glycan Orientation, by Length")
    ax[0, 0].set_xlabel("Deviation from Hoop Direction [degrees]")
    ax[0, 0].set_ylabel("Length [DSU]")


    # Top-Right Plot: Final Length vs Glycan Orientation
    ax[0, 1].scatter(abs_orientations_f, lengths_f, alpha=1E-2, color="black");
    ax[0, 1].set_xlim(-100, 100)
    ax[0, 1].set_xticks([-90,-60,-30,0,30,60,90])
    ax[0, 1].set_title("Final Glycan Orientation & Length")
    ax[0, 1].set_xlabel("Deviation from Hoop Direction [degrees]")
    ax[0, 1].set_ylabel("Length [DSU]")

    # Bottom-Left: Relaxed Strain vs Relative Orientation
    ax[1, 0].scatter(rel_orientations_0, strains_0, alpha=1E-2, color="black");
    ax[1, 0].set_xlim(-10, 190)
    ax[1, 0].set_ylim(-0.2, 3.5)
    ax[1, 0].set_xticks([0,30,60,90,120,150,180])
    ax[1, 0].set_title("Initial Peptide Attachment Angle & Strain")
    ax[1, 0].set_xlabel("Attachment Angle [degrees]")
    ax[1, 0].set_ylabel("Peptide Strain [a.u.]]")

    # Bottom-Right: Final Strain vs Relative Orientation
    ax[1, 1].scatter(rel_orientations_f, strains_f, alpha=1E-2, color="black");
    ax[1, 1].set_xlim(-10, 190)
    ax[1, 1].set_ylim(-0.2, 3.5)
    ax[1, 1].set_xticks([0,30,60,90,120,150,180])
    ax[1, 1].set_title("Final Peptide Attachment Angle & Strain")
    ax[1, 1].set_xlabel("Attachment Angle [degrees]")
    ax[1, 1].set_ylabel("Peptide Strain [a.u.]]")

    plt.show()