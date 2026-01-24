# Imports
from dataclasses import dataclass, asdict
from os import makedirs, listdir
import os.path
import re
import numpy as np
import pandas as pd
from stats_helper import get_confidence_intervals
from assemble_pg_network import generate_pg_network
import matplotlib.pyplot as plt
from run_lammps_isotropic_strain import run_isotropic_prestrain_nve, run_isotropic_prestrain_minimize

from process_isotropic_prestrain import ThermoStruct, import_isotropic_prestrain_data

# Simple Helper Functions
def create_networks_in_groups_with_varying_isotropic_parameter(working_directory : str, size : int, rho_gap : float, isotropic_parameters : list[float], networks_per_group : int, rewrite : bool):
    for group_index, alpha in enumerate(isotropic_parameters):
        for network_index in range(0,networks_per_group):
            filename = os.path.join(f"{working_directory}",f"n{network_index}_dsu{size}_rho{int(rho_gap*100)}_a{int(alpha*100)}.network")
            if rewrite or not os.path.exists(filename):
                (density_fraction, crosslink_ratio, _, _, _, _) = generate_pg_network(size, rho_gap, alpha, filename)
            else:
                print(f"[SKIPPED] Generating network {filename} b/c it already exists")
                continue;

def run_networks_nve(dirpath, regex_pattern, rerun):
    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            expected_output_file = os.path.join(dirpath,os.path.splitext(filename)[0] + ".out")
            if rerun or not os.path.exists(expected_output_file):
                print(f"Running {filename}...")
                file_to_run = os.path.join(dirpath,filename)
                run_isotropic_prestrain_nve(file_to_run, 0.3, True, True)
                #run_isotropic_prestrain_minimize(file_to_run, 0.3, 50, True, True)
            else:
                print(f"[SKIPPED] Running {filename} b/c existing output file was found")
                continue;

def run_networks_minimize(dirpath, regex_pattern, rerun : bool = False, remap : bool = False):
    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            expected_output_file = os.path.join(dirpath,os.path.splitext(filename)[0] + ".out")
            if rerun or not os.path.exists(expected_output_file):
                print(f"Running {filename}...")
                file_to_run = os.path.join(dirpath,filename)
                run_isotropic_prestrain_minimize(file_to_run, 0.3, None, True, True, remap)
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
    ratio = sigma_xx / sigma_yy;

    d = {"strain":strain, "sigma_xx":sigma_xx, "sigma_yy":sigma_yy, "sigma_xy":sigma_xy, "ratio":ratio}
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

def add_potential_energy_curve(df : pd.DataFrame, labelstr : str):
    ci_df = get_confidence_intervals(df, 0.95, "strain", "pe")

    plt.plot(
        ci_df.index, 
        ci_df['mean'], 
        label = labelstr
    )
    plt.fill_between(
        ci_df.index,
        ci_df['upper'],
        ci_df['lower'],
    )

def add_stress_curve(df : pd.DataFrame, color_name : str, labelstr):
    # Longitudinal (Lower)
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'sigma_xx');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="--", label = labelstr+", Axial Stress")
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
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="-", label = labelstr+", Hoop Stress")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2
    )

def finish_stress_curve():
    plt.title("Directional Stress during Pre-Strain")
    plt.ylabel("$\sigma$ [N/m]")
    plt.xlabel(r"$\mathcal{E}$, Strain")
    plt.legend()
    plt.show()

def add_stress_ratio_curve(df : pd.DataFrame, color_name : str, labelstr):
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'ratio');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="-", label = labelstr)
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2,
        label=f'95% Confidence (nSamples={n})'
    )

    print(f"Mean Stress Ratio for {labelstr}: {np.mean(ci_df['mean'].to_numpy())}")

def finish_stress_ratio_curve():
    plt.title("Stress Ratio during Pre-Strain")
    plt.ylabel("$\sigma_(xx) / \sigma_(yy)$ [a.u.]")
    plt.xlabel(r"$\mathcal{E}$, Strain")
    plt.ylim([0,1.5])
    plt.grid(True)
    plt.legend()
    plt.show()