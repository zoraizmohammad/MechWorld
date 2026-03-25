# Imports
from dataclasses import dataclass, asdict
from simulation_constants_settings import *;
from os import listdir
import os.path
import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from utils_helpers import get_confidence_intervals, find_files, add_curve_with_ci
from assemble_pg_network import generate_pg_network
from run_lammps_isotropic_strain import run_isotropic_prestrain_nve, run_isotropic_prestrain_minimize
from lammps_PG_objects import Bond
from import_data_from_dumps import *
from dataclasses import dataclass

## ENSEMBLE NETWORK CREATION
def create_networks_in_groups_with_varying_isotropic_parameter(working_directory : str, size : int, rho_gap : float, isotropic_parameters : list[float], networks_per_group : int, rewrite : bool):
    for group_index, alpha in enumerate(isotropic_parameters):
        for network_index in range(0,networks_per_group):
            filename = os.path.join(f"{working_directory}",f"n{network_index}_dsu{size}_rho{int(rho_gap*100)}_a{int(alpha*100)}.network")
            if rewrite or not os.path.exists(filename):
                (density_fraction, crosslink_ratio, _, _, _, _) = generate_pg_network(size, rho_gap, alpha, filename)
            else:
                print(f"[SKIPPED] Generating network {filename} b/c it already exists")
                continue;

## ENSEMBLE REGEX-BASED NETWORK PROPAGATION
def run_networks_nve(dirpath, regex_pattern, rerun):
    for filepath in find_files(dirpath, regex_pattern):
        expected_output_filepath = os.path.splitext(filepath)[0] + ".out";
        if rerun or not os.path.exists(expected_output_filepath):
            print(f"Running {filepath}...")
            run_isotropic_prestrain_nve(filepath, 0.3, True, True)
        else:
            print(f"[SKIPPED] Running {filepath} b/c existing output file was found")
            continue;

def run_networks_minimize(dirpath, regex_pattern, rerun : bool = False, remap : bool = False):
    for filepath in find_files(dirpath, regex_pattern):
        expected_output_filepath = os.path.splitext(filepath)[0] + ".out";
        if rerun or not os.path.exists(expected_output_filepath):
            print(f"Running {filepath}...")
            run_isotropic_prestrain_minimize(filepath, 0.3, True, True, remap)
        else:
            print(f"[SKIPPED] Running {filepath} b/c existing output file was found")
            continue;

### ISOTROPIC PRESTRAIN FILE IO & DATAFRAME MANIPULATION
@dataclass
class ThermoStruct:
    step  : int; 
    temp  : float;
    pe    : float;
    press : float;
    pxx   : float;
    pyy   : float;
    pxy   : float;
    lx    : float;
    ly    : float;
    vol   : float;
    glycan_pe  : float;
    angle_pe   : float;
    peptide_pe : float;

def import_isotropic_prestrain_data(filename : str) -> list[ThermoStruct]:
    # Break into lines
    with open(filename,"r") as f:
        lines = [line.strip() for line in f]

    i = 0; # 1st Line
    verify = "step temp pe press pxx pyy pxy lx ly vol glycan_pe angle_pe peptide_pe";
    if not lines[i].startswith(verify):
        raise ValueError(f"Expected at line {i+1}: {verify}");

    lst_structs : list[ThermoStruct] = list();

    for i in range(1,len(lines)):
        if lines[i].startswith("#"): # ignore
            continue;
        
        data = lines[i].split();

        struct = ThermoStruct(
            step   = int(data[0]),
            temp   = float(data[1]),
            pe     = float(data[2]),
            press  = float(data[3]),
            pxx    = float(data[4]),
            pyy    = float(data[5]),
            pxy    = float(data[6]),
            lx     = float(data[7]),
            ly     = float(data[8]),
            vol    = float(data[9]),
            glycan_pe  = float(data[10]),
            angle_pe   = float(data[11]),
            peptide_pe = float(data[12])
        );

        lst_structs.append(struct);

    return lst_structs

def collect_list_of_prestrain_dataframes(dirpath : str, regex_pattern : str) -> list[pd.DataFrame]:
    # Returns a list of dataframes, one from each file
    dfs = list();

    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            filepath = os.path.join(dirpath,filename)
            dataclasses_from_file = import_isotropic_prestrain_data(filepath)
            df = pd.DataFrame([asdict(n) for n in dataclasses_from_file])
            dfs.append(df)

    return dfs

# TODO: Review units & names
def calculate_tension_df_from_file_df(file_df : pd.DataFrame) -> pd.DataFrame:
    lx  = file_df['lx'].to_numpy()
    pxx = file_df['pxx'].to_numpy()
    pyy = file_df['pyy'].to_numpy()
    pxy = file_df['pxy'].to_numpy()

    strain   = (lx - lx[0]) / lx[0];
    tension_xx = -(pxx - pxx[0]) * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
    tension_yy = -(pyy - pyy[0]) * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
    tension_xy = -(pxy - pxy[0]) * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
    ratio = tension_xx / tension_yy;
    ratio[0] = ratio[1];

    d = {"strain":strain, "tension_xx":tension_xx, "tension_yy":tension_yy, "tension_xy":tension_xy, "ratio":ratio}
    return pd.DataFrame(d)

def calc_energy_df_from_file_df(file_df : pd.DataFrame) -> pd.DataFrame:
    lx  = file_df['lx'].to_numpy()
    ly  = file_df['ly'].to_numpy()
    pe  = file_df['pe'].to_numpy()
    glycan_pe  = file_df['glycan_pe'].to_numpy()
    angle_pe   = file_df['angle_pe'].to_numpy()
    peptide_pe = file_df['peptide_pe'].to_numpy()

    strain   = (lx - lx[0]) / lx[0]
    total_pe = glycan_pe + angle_pe + peptide_pe;
    glycan_pe_frac  = glycan_pe  / total_pe;
    angle_pe_frac   = angle_pe   / total_pe;
    peptide_pe_frac = peptide_pe / total_pe;
    energy_density = pe / (lx * ly)

    d = {"strain":strain, "glycan_pe_frac":glycan_pe_frac, "angle_pe_frac":angle_pe_frac, "peptide_pe_frac":peptide_pe_frac,"energy_density":energy_density}
    return pd.DataFrame(d)

def file_dfs_to_combined_tension_df(file_dfs : pd.DataFrame) -> pd.DataFrame:
    tension_dfs = list()
    for file_df in file_dfs:
        tension_dfs.append(calculate_tension_df_from_file_df(file_df));

    if len(tension_dfs) == 0:
        return None;
    else:
        return pd.concat(tension_dfs)

## PLOTTING FUNCTIONS -- ENERGY RATIO
def add_energy_ratio_curves(df : pd.DataFrame, curves_color : str, extra_label_info : str):
    # Elastic of Glycan
    add_curve_with_ci(df, 'strain', 'glycan_pe_frac', 
                      curve_linestyle=":", curve_color=curves_color, curve_label_override="Glycan Extension"+extra_label_info)

    # Bending of Glycan
    add_curve_with_ci(df, 'strain', 'angle_pe_frac', 
                      curve_linestyle="--", curve_color=curves_color, curve_label_override="Glycan Bending")

    # Elastic of Peptides
    add_curve_with_ci(df, 'strain', 'peptide_pe_frac', 
                      curve_linestyle="-", curve_color=curves_color, curve_label_override="Peptide Extension")

def finish_energy_ratio_curve():
    plt.legend();
    plt.title("Fraction of Potential Energy vs Strain")
    plt.ylabel("Energy Fraction [a.u.]")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid(True);
    plt.show();

## PLOTTING FUNCTIONS -- ENERGY DENSITY
def add_PE_density_curve(df : pd.DataFrame, colorname : str, labelstr : str):
    ci_df = get_confidence_intervals(df, 0.95, "strain", "energy_density")

    plt.plot(
        ci_df.index, 
        ci_df['mean'], 
        label = labelstr,
        color = colorname
    )
    plt.fill_between(
        ci_df.index,
        ci_df['upper'],
        ci_df['lower'],
        color = colorname,
        alpha = 0.2
    )

def finish_PE_density_curve():
    plt.legend()
    plt.title("Potential Energy Density")
    plt.ylabel("Potential Energy Density [aJ/nm2]")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid(True);
    plt.show()

## PLOTTING FUNCTIONS -- TENSION
def add_tension_curve(df : pd.DataFrame, curves_color : str, extra_label_info):
    # Hoop (Higher)
    add_curve_with_ci(df, 'strain', 'tension_yy', 
                    curve_linestyle="-", curve_color=curves_color, curve_label_override=r"$\gamma_{Hoop}$"+extra_label_info)

    # Longitudinal (Lower)
    add_curve_with_ci(df, 'strain', 'tension_xx', 
                    curve_linestyle="--", curve_color=curves_color, curve_label_override=r"$\gamma_{Axial}$")

def finish_tension_curve():
    plt.title("Directional Tension during Isotropic Pre-Strain")
    plt.ylabel("$\gamma$ [N/m]")
    plt.xlabel(r"$\mathcal{E}$, Strain")
    plt.legend()
    plt.grid()
    plt.show()

## PLOTTING FUNCTIONS -- TENSION RATIO
def add_tension_ratio_curve(df : pd.DataFrame, curve_color : str, extra_label_info : str):
    add_curve_with_ci(df, 'strain', 'ratio', 
                curve_linestyle="-", curve_color=curve_color, curve_label_override="Tension Ratio"+extra_label_info)

    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'ratio')
    print(f"Mean Tension Ratio for {extra_label_info}: {np.mean(ci_df['mean'].to_numpy())}")

def finish_tension_ratio_curve():
    plt.title("Tension Ratio during Isotropic Pre-Strain")
    plt.ylabel(r"$\gamma_{Axial}$ / $\gamma_{Hoop}$ [a.u.]")
    plt.xlabel(r"$\mathcal{E}$, Strain")
    plt.ylim([0,1.6])
    plt.grid(True)
    plt.legend()
    plt.show()

## FULL FIGURE FUNCTIONS
def full_tension_figure(
        curves_information : list[tuple[str, str, str, str]],
        expected_strain_tuple : tuple[float,float] = None,
        expected_tension_xx_tuple : tuple[float,float] = None,
        expected_tension_yy_tuple : tuple[float,float] = None):
    
    for i in range(0,len(curves_information)):
        (working_dirpath, output_regex, colorname, labelstr) = curves_information[i];

        dfs = collect_list_of_prestrain_dataframes(working_dirpath, output_regex)

        tension_dfs = list()
        for file_df in dfs:
            tension_dfs.append(calculate_tension_df_from_file_df(file_df));

        if len(tension_dfs) == 0:
            continue;
        else:
            combined_tension_df = pd.concat(tension_dfs)

        add_tension_curve(combined_tension_df, colorname, labelstr);
    
    ci_df = get_confidence_intervals(combined_tension_df, 0.95, 'strain', 'tension_yy')
    ci_df = ci_df.loc[abs(ci_df.index-0.25)<=0.02]
    print(ci_df)
    
    print(expected_strain_tuple,expected_tension_xx_tuple,expected_tension_yy_tuple)
    if (expected_strain_tuple != None) and (expected_tension_xx_tuple != None):
        print("DEBUG: Drawing expected tension_xx region...")
        plt.fill_between([expected_strain_tuple[0],expected_strain_tuple[1]],
                         [expected_tension_xx_tuple[0],expected_tension_xx_tuple[0]],
                         [expected_tension_xx_tuple[1],expected_tension_xx_tuple[1]],
                         alpha=0.2,
                         color="purple")
        
    if expected_strain_tuple and expected_tension_yy_tuple:
        print("DEBUG: Drawing expected tension_yy region...")
        plt.fill_between([expected_strain_tuple[0],expected_strain_tuple[1]],
                         [expected_tension_yy_tuple[0],expected_tension_yy_tuple[0]],
                         [expected_tension_yy_tuple[1],expected_tension_yy_tuple[1]],
                         alpha=0.4,
                         color="purple")

    finish_tension_curve();

def full_tension_ratio_figure(curves_information : list[tuple[str, str, str, str]], ax : plt.Axes = None, show_laplace_region : bool = False):
    
    if ax == None:
        ax = plt.subplot();
    
    for i in range(0,len(curves_information)):
        (working_dirpath, output_regex, colorname, labelstr) = curves_information[i];

        dfs = collect_list_of_prestrain_dataframes(working_dirpath, output_regex)

        tension_dfs = list()
        for file_df in dfs:
            tension_dfs.append(calculate_tension_df_from_file_df(file_df));

        if len(tension_dfs) == 0:
            continue;
        else:
            combined_df = pd.concat(tension_dfs)

        add_tension_ratio_curve(combined_df, colorname, labelstr);
    
    if show_laplace_region:
        expected_ratio = 0.5;
        margin_ratio = 0.1;
        ylo = expected_ratio * (1-margin_ratio);
        yhi = expected_ratio * (1+margin_ratio);
        ax.fill_between([0,0.3],[ylo,ylo],[yhi,yhi], alpha=0.2, color="green", hatch="/", label="Expected Ratio for Cylindrical Shell")

    finish_tension_ratio_curve();

def full_energy_ratio_figure(curves_information : list[tuple[str, str, str, str]]):
    for i in range(0,len(curves_information)):
        (working_dirpath, output_regex, colorname, labelstr) = curves_information[i];

        dfs = collect_list_of_prestrain_dataframes(working_dirpath, output_regex)

        energy_ratio_dfs = list()
        for file_df in dfs:
            energy_ratio_dfs.append(calc_energy_df_from_file_df(file_df));

        if len(energy_ratio_dfs) == 0:
            continue;
        else:
            combined_energy_ratio_df = pd.concat(energy_ratio_dfs)

        add_energy_ratio_curves(combined_energy_ratio_df, colorname, labelstr);

    finish_energy_ratio_curve();

def full_PE_figure(curves_information : list[tuple[str, str, str, str]]):
    for i in range(0,len(curves_information)):
        (working_dirpath, output_regex, colorname, labelstr) = curves_information[i];

        dfs = collect_list_of_prestrain_dataframes(working_dirpath, output_regex)

        PE_dfs = list()
        for file_df in dfs:
            PE_dfs.append(calc_energy_df_from_file_df(file_df));

        if len(PE_dfs) == 0:
            continue;
        else:
            combined_PE_df = pd.concat(PE_dfs)

        add_PE_density_curve(combined_PE_df, colorname, labelstr);

    finish_PE_density_curve();

#### Peptide Strain Histograms
def full_bonds_strain_figure(working_dirpath : str, regex_pattern_no_extension : str):
    pass
    bonds_in_relaxed_state : list[Bond] = list()
    bonds_in_final_state : list[Bond] = list()
    regex_relaxed_bonds = regex_pattern_no_extension + r"\.relaxed.bonds"
    regex_final_bonds = regex_pattern_no_extension + r"\.final.bonds"
    for filename in os.listdir(working_dirpath):
        if re.match(regex_relaxed_bonds, filename):
            bonds_in_relaxed_state.extend(
                import_bonds_from_dump(os.path.join(working_dirpath,filename)))
        elif re.match(regex_final_bonds, filename):
            bonds_in_final_state.extend(
                import_bonds_from_dump(os.path.join(working_dirpath,filename)))
    
    # todo: make better function to overlay initial & final on one figure (transparency)
    plot_combined_histogram(bonds_in_relaxed_state, bonds_in_final_state)

def plot_combined_histogram(bonds_in_relaxed_state : list[Bond], bonds_in_final_state : list[Bond]):
    #https://matplotlib.org/stable/gallery/statistics/hist.html

    # Lists to keep track of strain in network initial state
    glycan_strain_0  : list[float] = list()
    peptide_strain_0 : list[float] = list()

    for b in bonds_in_relaxed_state: 
        if b.bond_type == BOND_TYPE_GLYCAN:
            glycan_strain_0.append(b.get_strain());
        elif b.bond_type == BOND_TYPE_PEPTIDE:
            peptide_strain_0.append(b.get_strain());
        else:
            continue;
    
    # Lists to keep track of strain in network final state
    glycan_strain_f  : list[float] = list()
    peptide_strain_f : list[float] = list()

    for b in bonds_in_final_state:
        if b.bond_type == BOND_TYPE_GLYCAN:
            glycan_strain_f.append(b.get_strain());
        elif b.bond_type == BOND_TYPE_PEPTIDE:
            peptide_strain_f.append(b.get_strain());
        else:
            continue;

    # Figure stuff
    fig, ax = plt.subplots(2,1,tight_layout=True)
    
    peptide_max = max(max(peptide_strain_f), max(peptide_strain_0))
    peptide_min = min(min(peptide_strain_f), min(peptide_strain_0))
    glycan_max =  max(max(glycan_strain_f),  max(glycan_strain_0))
    glycan_min =  min(min(glycan_strain_f),  min(glycan_strain_0))

    # We can set the number of bins with the *bins* keyword argument.
    n_bins = 100;
    alpha_setting = 0.5;
    print(len(glycan_strain_f) - len(glycan_strain_0))
    print(len(peptide_strain_f) - len(peptide_strain_0))

    ax[0].hist(
        glycan_strain_0, 
        bins  = n_bins, 
        range = (glycan_min, glycan_max),
        log   = True, 
        color = "green", 
        alpha = alpha_setting,
        label = "Relaxed State",
    )
    
    ax[0].hist(
        glycan_strain_f, 
        bins  = n_bins, 
        range = (glycan_min, glycan_max),
        log   = True, 
        color = "red", 
        alpha = alpha_setting,
        label = "Deformed State",
    )

    ax[1].hist(
        peptide_strain_0, 
        bins  = n_bins, 
        range = (peptide_min, peptide_max),
        log   = True, 
        color = "green", 
        alpha = alpha_setting,
        label = "Relaxed State",
    )

    ax[1].hist(
        peptide_strain_f, 
        bins  = n_bins, 
        range = (peptide_min, peptide_max),
        log   = True, 
        color = "red", 
        alpha = alpha_setting,
        label = "Deformed State",
    )

    ax[0].set_ylabel('Number of Bonds');
    ax[0].set_xlabel('Bond Strain [a.u.]')
    ax[0].set_title("Glycan")

    ax[1].set_ylabel('Number of Bonds');
    ax[1].set_xlabel('Bond Strain [a.u.]')
    ax[1].set_title("Peptide")

    # Print Some Stats
    print(f"(Mean, Std) of Glycan in relaxed network: ({np.mean(glycan_strain_0)}, {np.std(glycan_strain_0)})")
    print(f"(Mean, Std) of Peptide in relaxed network: ({np.mean(peptide_strain_0)}, {np.std(peptide_strain_0)})")
    print(f"(Mean, Std) of Glycan in deformed network: ({np.mean(peptide_strain_f)}, {np.std(peptide_strain_f)})")
    print(f"(Mean, Std) of Peptide in deformed network: ({np.mean(peptide_strain_f)}, {np.std(peptide_strain_f)})")

    plt.show();

#### Compare Two Networks of Different Sizes

def add_network_ratio(df, colornamestr, labelstr):
    # tension_xx
    ci_df = get_confidence_intervals(df, 0.95, "strain", "comparison_ratio_xx")
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=colornamestr, linestyle="-", label=labelstr+", $\tension_(xx)$")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=colornamestr, 
        alpha=0.2, 
        label=f'95% Confidence (nSamples={n})'
    )

    # tension_yy
    ci_df = get_confidence_intervals(df, 0.95, "strain", "comparison_ratio_yy")
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=colornamestr, linestyle="--", label=labelstr+", $\tension_(yy)$")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=colornamestr, 
        alpha=0.2, 
        label=f'95% Confidence (nSamples={n})'
    )

def finish_network_ratio():
    plt.title("Ratio of Tension Between Network Types")
    plt.legend()
    plt.grid(True)
    plt.ylabel("Ratio of Networks")
    plt.xlabel(r"$\mathcal{E}$, Strain")
    plt.show()

def plot_comparison_of_ensembles(working_dirpath : str, curves_info : list[tuple[str, str, str, str]]):
    # tuple = (regex_numer, regex_denom, colorname, labelstr)
    
    for i in range(0,len(curves_info)):
        (output_regex_A, output_regex_B, colornamestr, labelstr) = curves_info[i];
        
        dfs_A = collect_list_of_prestrain_dataframes(working_dirpath, output_regex_A)
        dfs_B = collect_list_of_prestrain_dataframes(working_dirpath, output_regex_B)

        tension_df_A = file_dfs_to_combined_tension_df(dfs_A)
        tension_df_B = file_dfs_to_combined_tension_df(dfs_B)

        if not isinstance(tension_df_A,pd.DataFrame) or not isinstance(tension_df_B,pd.DataFrame):
            continue;
        
        strain_A   = tension_df_A["strain"].to_numpy();
        tension_xx_A = tension_df_A["tension_xx"].to_numpy();
        tension_yy_A = tension_df_A["tension_yy"].to_numpy();

        strain_B   = tension_df_B["strain"].to_numpy();
        tension_xx_B = tension_df_B["tension_xx"].to_numpy();
        tension_yy_B = tension_df_B["tension_yy"].to_numpy();

        tension_xx_B_interp = np.interp(strain_A, strain_B, tension_xx_B)
        tension_yy_B_interp = np.interp(strain_A, strain_B, tension_yy_B)

        print(tension_xx_B_interp)

        comparison_ratio_xx = tension_xx_A / tension_xx_B_interp;
        comparison_ratio_yy = tension_yy_A / tension_yy_B_interp;

        print(strain_A)
        print(comparison_ratio_xx)

        tension_df_A["comparison_ratio_xx"] = comparison_ratio_xx;
        tension_df_A["comparison_ratio_yy"] = comparison_ratio_yy;
    
        add_network_ratio(tension_df_A, colornamestr, labelstr)

    finish_network_ratio();