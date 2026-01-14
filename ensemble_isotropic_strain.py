# Imports
from dataclasses import dataclass, asdict
from os import makedirs, listdir
import os.path
import re
import pandas as pd
from stats_helper import get_confidence_intervals
from assemble_pg_network import generate_pg_network
import matplotlib.pyplot as plt

from run_lammps_isotropic_strain import run_isotropic_prestrain

from process_isotropic_prestrain import ThermoStruct, import_isotropic_prestrain_data

# Simple Helper Functions
def create_networks_in_groups_with_varying_isotropic_parameter(working_directory, isotropic_parameters, networks_per_group, rewrite : bool):
    size = 200;
    rho_gap = 0.5;
    for group_index, alpha in enumerate(isotropic_parameters):
        for network_index in range(0,networks_per_group):
            filename = os.path.join(f"{working_directory}",f"dsu{size}_rho{rho_gap}_a{int(alpha*100)}.network")
            if rewrite or not os.path.exists(filename):
                (density_fraction, crosslink_ratio, _, _, _, _) = generate_pg_network(size, 0.5, alpha, filename)
            else:
                print(f"[SKIPPED] Generating network {filename} b/c it already exists")
                continue;

def run_networks(dirpath, regex_pattern, rerun):
    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            expected_output_file = os.path.join(dirpath,os.path.splitext(filename)[0] + ".out")
            if rerun or not os.path.exists(expected_output_file):
                print(f"Running {filename}...")
                file_to_run = os.path.join(dirpath,filename)
                run_isotropic_prestrain(file_to_run, 0.3, False)
            else:
                print(f"[SKIPPED] Running {filename} b/c existing output file was found")
                continue;

def collect_list_of_dataframes(dirpath : str, regex_pattern : str) -> list[pd.DataFrame]:
    # Returns a list of dataframes, one from each file
    dfs = list();

    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            filepath = os.path.join(dirpath,filename)
            dataclasses_from_file = import_isotropic_prestrain_data(filepath)
            df = pd.DataFrame([asdict(n) for n in dataclasses_from_file])
            dfs.append(df)

    return dfs

def calc_stress_df_from_file_df(file_df : pd.DataFrame) -> pd.DataFrame:
    lx  = file_df['lx'].to_numpy()
    pxx = file_df['pxx'].to_numpy()
    pyy = file_df['pyy'].to_numpy()
    pxy = file_df['pxy'].to_numpy()

    strain   = (lx - lx[0]) / lx[0]
    sigma_xx = -(pxx - pxx[0]);
    sigma_yy = -(pyy - pyy[0]);
    sigma_xy = -(pxy - pxy[0]);

    d = {"strain":strain, "sigma_xx":sigma_xx, "sigma_yy":sigma_yy, "sigma_xy":sigma_xy}
    return pd.DataFrame(d)

def calc_energy_df_from_file_df(file_df : pd.DataFrame) -> pd.DataFrame:
    lx  = file_df['lx'].to_numpy()
    glycan_pe  = file_df['glycan_pe'].to_numpy()
    angle_pe   = file_df['angle_pe'].to_numpy()
    peptide_pe = file_df['peptide_pe'].to_numpy()

    strain   = (lx - lx[0]) / lx[0]
    total_pe = glycan_pe + angle_pe + peptide_pe;
    glycan_pe_frac  = glycan_pe  / total_pe;
    angle_pe_frac   = angle_pe   / total_pe;
    peptide_pe_frac = peptide_pe / total_pe;

    d = {"strain":strain, "glycan_pe_frac":glycan_pe_frac, "angle_pe_frac":angle_pe_frac, "peptide_pe_frac":peptide_pe_frac}
    return pd.DataFrame(d)

def add_energy_curves(df : pd.DataFrame, color_name : str, labelstr):
    # Elastic of Glycan
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'glycan_pe_frac');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle=":", label="Glycan Extension")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2, 
        label=f'95% Confidence (nSamples={n})'
    )

    # Bending of Glycan
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'angle_pe_frac');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="--", label="Glycan Bending")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2
    )

    # Elastic of Peptides
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'peptide_pe_frac');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="-", label="Peptide Extension")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2
    )

def finish_energy_curve():
    plt.legend();
    plt.title("Fraction of Potential Energy vs Strain")
    plt.ylabel("Energy Fraction [a.u.]")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.show();

def add_stress_curve(df : pd.DataFrame, color_name : str, labelstr):
    # Longitudinal (Lower)
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'sigma_xx');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="--")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2, 
        label=f'95% Confidence (nSamples={n})'
    )

    # Hoop (Higher)
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'sigma_yy');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="-", label = labelstr)
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2
    )

def finish_stress_curve():
    plt.ylabel("$\sigma$ [N/m]")
    plt.xlabel(r"$\mathcal{E}$, Strain")
    plt.legend()
    plt.show()

def finish_stress_ratio_curve():
    plt.ylabel("$\sigma$ [N/m]")
    plt.xlabel(r"$\mathcal{E}$, Strain")
    plt.show()

### START OF PROGRAM FOR TESTING
# Settings
working_dirpath = os.path.join(os.path.curdir,"isostrain2");
isotropic_parameters = [0.33, 0.72, 1.0];
number_networks_per_group = 3;

# Subfunction to create folder if it not found
makedirs(working_dirpath, exist_ok=True)

# Loop to create networks
#create_networks_in_groups_with_varying_isotropic_parameter(working_dirpath, isotropic_parameters, number_networks_per_group, False)

network_regex = r".*\.network$";
#run_networks(working_dirpath, network_regex, False)

lst_output_regex : list[str] = [r'.*_a33\.out',r'.*_a72\.out',r'.*_a100.out']
lst_colorname = ['blue','green','red'];
lst_label = ["a = 0.33", "a = 0.72", "a = 1.00"]

#dfs = collect_list_of_dataframes(working_dirpath, output_regex)

# Plot Stress vs. Strain...
for i in range(0,len(lst_output_regex)):
    output_regex = lst_output_regex[i]
    colorname = lst_colorname[i]
    labelstr = lst_label[i]
    dfs = collect_list_of_dataframes(working_dirpath,output_regex)
    stress_dfs = list()
    for file_df in dfs:
        stress_dfs.append(calc_stress_df_from_file_df(file_df));

    combined_stress_df = pd.concat(stress_dfs)
    print(combined_stress_df)

    add_stress_curve(combined_stress_df, colorname, labelstr);

finish_stress_curve()

# Plot Energy vs. Strain...
dfs = collect_list_of_dataframes(working_dirpath,r'.*\_a33\.out');
energy_dfs = list()
for file_df in dfs:
    energy_dfs.append(calc_energy_df_from_file_df(file_df));

combined_energy_df = pd.concat(energy_dfs)
print(combined_energy_df)
add_energy_curves(combined_energy_df, "black", "combined");
finish_energy_curve();