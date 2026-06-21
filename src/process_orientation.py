from lammps_PG_objects import Atom, Bond, Angle, GlycanMolecule;
from simulation_constants_settings import *;
import numpy as np;
import pandas as pd;
import re;
import matplotlib.pyplot as plt;
import os;
from utils_helpers import get_angle_between_vectors, bucket_round, get_confidence_intervals;
from import_data_from_dumps import import_all_from_dump;

def calculate_length_of_glycan_molecules(molecules : dict[int,GlycanMolecule]):
    list_lengths = list();
    for m in molecules.values():
        list_lengths.append(m.get_length())

    return list_lengths;

def calculate_absolute_orientation_of_glycan_molecules(atoms, molecules : dict[int,GlycanMolecule], triclinic_bounds):
    return [m.get_orientation_with_respect_to_hoop(atoms, triclinic_bounds) for m in molecules.values()];

def calculate_tension_of_glycan_molecules(bonds : dict[int,Bond], molecules : dict[int,GlycanMolecule]):
    return [m.get_tension(bonds) for m in molecules.values()];

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
def full_orientation_delta_figure(curves : list[tuple[str,str]]):
    
    # Skeleton of figure
    fig, ax = plt.subplots(2,len(curves));
    # https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes

    for i, curve_tuple in enumerate(curves):
        curve_dir, curve_filename_no_ext, curve_title  = curve_tuple;

        bounds, atoms, bonds, molecules = import_all_from_dump(curve_dir, curve_filename_no_ext)
        abs_orientations_0 = calculate_absolute_orientation_of_glycan_molecules(atoms, molecules, bounds)
        lengths_0 = calculate_length_of_glycan_molecules(molecules)
        [rel_orientations_0, strains_0] = calculate_strain_and_relative_glycan_orientation(atoms, bonds, molecules, bounds)

        # Upper: Orientation vs. Length
        ax[0, i].scatter(abs_orientations_0, lengths_0, alpha=1E-2, color="black");
        ax[0, i].set_xlim(-100, 100)
        ax[0, i].set_xticks([-90,-60,-30,0,30,60,90])
        ax[0, i].set_title(curve_title)
        ax[0, i].set_xlabel("Deviation from Hoop Direction [degrees]")
        ax[0, i].set_ylabel("Length [DSU]")

        # Bottom: Relaxed Strain vs Relative Orientation
        ax[1, i].scatter(rel_orientations_0, strains_0, alpha=1E-2, color="black");
        ax[1, i].set_xlim(-10, 190)
        ax[1, i].set_ylim(-0.2, 3.5)
        ax[1, i].set_xticks([0,30,60,90,120,150,180])
        #ax[1, i].set_title("Initial Peptide Attachment Angle & Strain")
        ax[1, i].set_xlabel("Attachment Angle [degrees]")
        ax[1, i].set_ylabel("Peptide Strain [a.u.]")

    plt.show()

def collect_combined_orientations_array(dirpath : str, regex_pattern : str) -> np.ndarray:
    combined_orientations = 0;
    matches_counter = 0;

    for filename in os.listdir(dirpath):
        if re.search(regex_pattern, filename):
            (filename_without_ext, _) = os.path.splitext(filename);
            bounds, atoms, _, molecules = import_all_from_dump(dirpath, filename_without_ext)
            gly_orientation = calculate_absolute_orientation_of_glycan_molecules(atoms, molecules, bounds);

            if type(combined_orientations) == int:
                combined_orientations = gly_orientation;
            else:
                combined_orientations = np.append(combined_orientations, gly_orientation)

            matches_counter += 1;

    if matches_counter == 0:
        raise FileNotFoundError()
    else:
        print(f"Debug: Imported orientation data from {matches_counter} dumps that matched regex")

    return combined_orientations

def collect_combined_tensions_array(dirpath : str, regex_pattern : str) -> np.ndarray:
    combined_tensions = 0;
    matches_counter = 0;

    for filename in os.listdir(dirpath):
        if re.search(regex_pattern, filename):
            (filename_without_ext, _) = os.path.splitext(filename);
            _, _, bonds, molecules = import_all_from_dump(dirpath, filename_without_ext)
            gly_tension = calculate_tension_of_glycan_molecules(bonds, molecules);

            if type(combined_tensions) == int:
                combined_tensions = gly_tension;
            else:
                combined_tensions = np.append(combined_tensions, gly_tension)

            matches_counter += 1;

    if matches_counter == 0:
        raise FileNotFoundError()
    else:
        print(f"Debug: Imported tension data from {matches_counter} dumps that matched regex")

    return combined_tensions

def draw_tension_by_orientation(gly_orient_deg, gly_tensions, ax = None):
    # Convert deg->rad, numpy arrays
    gly_orient = np.deg2rad(gly_orient_deg);
    gly_tensions = np.array(gly_tensions);

    # Stack indices together into buckets
    N = 180;
    bucket_size = (2*np.pi)/N;
    gly_orient = [bucket_round(g,bucket_size) for g in gly_orient]

    # Combine data points with same index
    df = pd.DataFrame({"orientation" : gly_orient, "tension" : gly_tensions})
    ci_df = get_confidence_intervals(df, 0.95, "orientation", "tension")

    if ax == None:
        ax = plt.subplot(111, polar=True);
        ax.set_theta_zero_location("N");

    max_tension = np.max(ci_df["mean"]); # Net, Average

    theta = ci_df.index;
    radii = (ci_df["mean"] / max_tension);

    bottom = 0.0;
    cmap = plt.get_cmap('plasma')

    bars = ax.bar(theta, radii, width=bucket_size, bottom=bottom)
    for r, bar in zip(radii, bars):
        bar.set_facecolor(cmap(r))

    # The tension acts in both directions so it needs to be mirrored
    bars_mirrored = ax.bar(theta+(np.pi), radii, width=bucket_size, bottom=bottom)
    for r, bar in zip(radii, bars_mirrored):
        bar.set_facecolor(cmap(r))

    #ax.set_rlabel(r"$\bar{\gamma}$, Normalized Tension")

    plt.show()

def full_oriented_stress_figure(working_directory : str, regex_pattern : str):

    gly_abs_orient = collect_combined_orientations_array(working_directory, regex_pattern);
    gly_tensions = collect_combined_tensions_array(working_directory, regex_pattern);

    draw_tension_by_orientation(gly_abs_orient, gly_tensions, None);

    plt.show()


