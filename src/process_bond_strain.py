from import_data_from_dumps import import_atoms_from_dump, import_bonds_from_dump, import_2D_triclinic_box_bounds_from_dump
from assemble_pg_network import visualize_bonds
from simulation_constants_settings import BOND_TYPE_GLYCAN, BOND_TYPE_PEPTIDE
from lammps_PG_objects import Bond
import re
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mplc
import numpy as np

#### Force Chain Visualization w/ Histogram
def sequential_force_chain_figure(curves_info : list[tuple[str,str,float]], ax = None):

    if type (curves_info) == tuple:
        return

    fig, ax = plt.subplots(2,len(curves_info),tight_layout=True,height_ratios=[5,1], sharex="row", sharey="row")

    glycan_tensions : list[np.ndarray] = list();
    max_glycan_tension = 0;
    min_glycan_tension = 0;

    for i, curve_info in enumerate(curves_info):
        curve_filepath, curve_title, curve_prestrain = curve_info;

        bonds = import_bonds_from_dump(curve_filepath+".bonds").values();
        glycan_tension, peptide_tension = split_tension_by_type(bonds);

        if max(glycan_tension) > max_glycan_tension:
            gnorm = mplc.PowerNorm(1,0,np.percentile(glycan_tension,98),True)
            pnorm = mplc.PowerNorm(1,0,np.percentile(peptide_tension,98),True)
            max_glycan_tension = max(glycan_tension)

        min_glycan_tension = min(min_glycan_tension, min(glycan_tension))

    cmap = plt.get_cmap('plasma')

    for i, curve_info in enumerate(curves_info):
        curve_filepath, curve_title, curve_prestrain = curve_info
        force_chain_and_histogram_combo(ax[0,i],ax[1,i], curve_filepath, 
                                        max_glycan_tension, min_glycan_tension,
                                        None, None, cmap, gnorm, pnorm)
        ax[0,i].set_title(curve_title)
        ax[1,i].set_title("Tension Distribution")

    plt.show()

def full_chain_figure(filepath_0, title_0, filepath_f = None, title_f = None):

    if filepath_f:
        fig, ax = plt.subplots(2,2,tight_layout=True,height_ratios=[5,1], sharex="row", sharey="row")
    else:
        fig, ax = plt.subplots(2,1,tight_layout=True,height_ratios=[5,1])

    bonds0 = import_bonds_from_dump(filepath_0+".bonds").values();
    g0_ten, p0_ten = split_tension_by_type(bonds0);
    
    if filepath_f:
        gf_ten, pf_ten = split_tension_by_type(import_bonds_from_dump(filepath_f+".bonds").values());
        max_glycan_tension = max(max(g0_ten),max(gf_ten)); min_glycan_tension = min(min(g0_ten),min(gf_ten));
        max_peptide_tension = max(max(p0_ten),max(pf_ten)); min_peptide_tension = min(min(p0_ten),min(pf_ten));
        gnorm = mplc.PowerNorm(1,0,np.percentile(gf_ten,98),True)
        pnorm = mplc.PowerNorm(1,0,np.percentile(pf_ten,98),True)
    else:
        max_glycan_tension = max(g0_ten); min_glycan_tension = min(g0_ten);
        max_peptide_tension = max(p0_ten); min_peptide_tension = min(p0_ten);
        gnorm = mplc.PowerNorm(1,0,np.percentile(g0_ten,98),True)
        pnorm = mplc.PowerNorm(1,0,np.percentile(p0_ten,98),True)

    cmap = plt.get_cmap('plasma')

    if filepath_f:
        force_chain_and_histogram_combo(ax[0,0],ax[1,0],filepath_0, max_glycan_tension, min_glycan_tension, max_peptide_tension, min_peptide_tension, cmap, gnorm, pnorm)
        force_chain_and_histogram_combo(ax[0,1],ax[1,1],filepath_f, max_glycan_tension, min_glycan_tension, max_peptide_tension, min_peptide_tension, cmap, gnorm, pnorm)
        ax[0,0].set_title(title_0);
        ax[0,1].set_title(title_f);
        ax[1,0].set_title("Tension Distribution")
        ax[1,1].set_title("Tension Distribution")
    else:
        force_chain_and_histogram_combo(ax[0],ax[1],filepath_0, max_glycan_tension, min_glycan_tension, max_peptide_tension, min_peptide_tension, cmap, gnorm, pnorm)
        ax[0].set_title(title_0);
        ax[1].set_title("Tension Distribution")

    plt.show()

def force_chain_and_histogram_combo(ax1, ax2, filename_wo_ext, gmax, gmin, pmax, pmin, cmap, gnorm, pnorm):
    triclinic_bounds = import_2D_triclinic_box_bounds_from_dump(filename_wo_ext+".atoms")
    atoms = import_atoms_from_dump(filename_wo_ext+".atoms", triclinic_bounds)
    bonds = import_bonds_from_dump(filename_wo_ext+".bonds")
    
    visualize_bonds(atoms, bonds, None, triclinic_bounds[0], triclinic_bounds[1], triclinic_bounds[3], triclinic_bounds[4], 
                    ax=ax1, strain_colormap=cmap, strain_colormap_norm_glycan=gnorm, strain_colormap_norm_peptide=pnorm,draw_stems=False);
    
    g, p = split_tension_by_type(bonds.values());
    
    #strain_histogram(ax2, p, "", pmin, pmax, colormap=cmap, colormap_norm=pnorm, alpha_setting=1)
    strain_histogram(ax2, g, "", gmin, gmax, colormap=cmap, colormap_norm=gnorm, alpha_setting=1, use_log=True)
    
    ax1.set_facecolor('black')
    ax2.set_facecolor('black')

#### Peptide Strain Histograms
def full_bonds_strain_figure(working_dirpath : str, initial_file_regex_pattern : str, final_file_regex_pattern : str, relaxed_label : str, final_label : str):
    bonds_in_relaxed_state : list[Bond] = list()
    bonds_in_final_state   : list[Bond] = list()
    regex_relaxed_bonds = initial_file_regex_pattern + r"\.bonds"
    regex_final_bonds = final_file_regex_pattern + r"\.bonds"

    for filename in os.listdir(working_dirpath):
        if re.match(regex_relaxed_bonds, filename):
            bonds_in_relaxed_state.extend(
                import_bonds_from_dump(os.path.join(working_dirpath,filename)).values())
        elif re.match(regex_final_bonds, filename):
            bonds_in_final_state.extend(
                import_bonds_from_dump(os.path.join(working_dirpath,filename)).values())
    
    # print(bonds_in_relaxed_state)
    # todo: make better function to overlay initial & final on one figure (transparency)

    fig, ax = plt.subplots(2,1,tight_layout=True)

    #cmap = plt.get_cmap('plasma')

    g0, p0 = split_strain_by_type(bonds_in_relaxed_state);
    gf, pf = split_strain_by_type(bonds_in_final_state);

    gmax = max(max(g0),max(gf)); gmin = min(min(g0),min(gf));
    pmax = max(max(p0),max(pf)); pmin = min(min(p0),min(pf));

    #gnorm = mplc.Normalize(gmin,gmax)
    #pnorm = mplc.Normalize(pmin,pmax)

    # Glycan, 0 -> f
    strain_histogram(ax[0], g0, relaxed_label, gmin, gmax, uniform_color="green")
    strain_histogram(ax[0], gf, final_label, gmin, gmax, uniform_color="red")
    ax[0].set_ylabel('Number of Bonds');
    ax[0].set_xlabel('Bond Strain [a.u.]')
    ax[0].set_title("Glycan")
    ax[0].legend()

    # Peptides, 0 -> f
    strain_histogram(ax[1], p0, relaxed_label, pmin, pmax, uniform_color="green")
    strain_histogram(ax[1], pf, final_label, pmin, pmax, uniform_color="red")
    ax[1].set_ylabel('Number of Bonds');
    ax[1].set_xlabel('Bond Strain [a.u.]')
    ax[1].set_title("Peptide")
    ax[1].legend()
    plt.show()

def split_strain_by_type(mixed_bonds : list[Bond]) -> tuple[list[float],list[float]]:
       # Lists to keep track of strain in network initial state
    glycan_strains  : list[float] = list()
    peptide_strains  : list[float] = list()

    for b in mixed_bonds: 
        if b.bond_type == BOND_TYPE_GLYCAN:
            glycan_strains.append(b.get_strain());
        elif b.bond_type == BOND_TYPE_PEPTIDE:
            peptide_strains.append(b.get_strain());
        else:
            continue;

    return glycan_strains, peptide_strains

def split_tension_by_type(mixed_bonds : list[Bond]) -> tuple[list[float],list[float]]:
    # Lists to keep track of strain in network initial state
    glycan_tension  : list[float] = list()
    peptide_tension  : list[float] = list()

    for b in mixed_bonds: 
        if b.bond_type == BOND_TYPE_GLYCAN:
            glycan_tension.append(b.get_tension());
        elif b.bond_type == BOND_TYPE_PEPTIDE:
            peptide_tension.append(b.get_tension());
        else:
            continue;

    return glycan_tension, peptide_tension

def strain_histogram(
        ax : plt.Axes, 
        strains : list[float], 
        label : str, 
        min_x : float, 
        max_x : float,
        uniform_color = "green",
        alpha_setting = 0.5,
        colormap = None, 
        colormap_norm = None,
        use_log = True,
        use_density = True):

    # We can set the number of bins with the *bins* keyword argument.
    n_bins = 100;

    n, bins, patches = ax.hist(
        strains, 
        bins  = n_bins, 
        range = (min_x, max_x),
        log   = use_log, 
        color = uniform_color,
        alpha = alpha_setting,
        label = label,
        density = use_density,
    )

    # if a colormap and normalization function is provided, then we will recolor our bins to match
    if (colormap and colormap_norm):
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        for c, p in zip(bin_centers, patches):
            plt.setp(p, 'facecolor', colormap(colormap_norm(c)))

