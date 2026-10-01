# Imports
from dataclasses import dataclass, asdict
from simulation_constants_settings import *;
from os import listdir
import os.path
import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from utils_helpers import get_confidence_intervals, find_files, add_curve_with_ci, get_initial_density_from_filename, get_crosslinkage_from_filename, bucket_round, apply_band_filters_to_df
from assemble_pg_network import generate_pg_network
from run_lammps_isotropic_strain import run_isotropic_prestrain_nve, run_isotropic_prestrain_minimize
from lammps_PG_objects import Bond
from import_data_from_dumps import *
from dataclasses import dataclass

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
            run_isotropic_prestrain_minimize(
                network_filepath=filepath,
                max_strain=0.3,
                number_strain_steps=None,
                write_debug_images=True,
                dump_specs=[("INITIAL", None, None), ("FINAL", None, None)],
                restart_specs=None,
                remap=remap,
            )
        else:
            print(f"[SKIPPED] Running {filepath} b/c existing output file was found")
            continue;

### ISOTROPIC PRE-STRAIN FILE IO & DATAFRAME MANIPULATION
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

def import_isotropic_prestrain_dataframe(filename : str) -> list[ThermoStruct]:
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

    # List of Structs -> Dataframe
    df = pd.DataFrame([asdict(n) for n in lst_structs])

    # The file's name contains some information about the network, include it in df
    rho_0 = get_initial_density_from_filename(filename);
    if rho_0: df['rho_0'] = [rho_0] * len(df);

    linkage = get_crosslinkage_from_filename(filename);
    if linkage: df['linkage'] = [linkage] * len(df);

    return df

def collect_list_of_prestrain_dataframes(dirpath : str, regex_pattern : str) -> list[pd.DataFrame]:
    # Returns a list of dataframes, one from each file
    dfs = list();

    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            filepath = os.path.join(dirpath,filename)
            df = import_isotropic_prestrain_dataframe(filepath)
            dfs.append(df)

    return dfs

# def calculate_tension_df_from_file_df(file_df : pd.DataFrame) -> pd.DataFrame:
#     lx  = file_df['lx'].to_numpy()
#     pxx = file_df['pxx'].to_numpy()
#     pyy = file_df['pyy'].to_numpy()
#     pxy = file_df['pxy'].to_numpy()
#     rho_0 = file_df['rho_0'].to_numpy();

#     strain   = (lx - lx[0]) / lx[0];
#     rho_f = rho_0 / (1+strain)**2;
#     tension_xx = -(pxx - pxx[0]) * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
#     tension_yy = -(pyy - pyy[0]) * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
#     tension_xy = -(pxy - pxy[0]) * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
#     ratio = tension_xx / tension_yy;
#     ratio[0] = np.nan;

#     d = {"strain":strain, "tension_xx":tension_xx, "tension_yy":tension_yy, "tension_xy":tension_xy, "ratio":ratio, "rho_f":rho_f, "rho_0":rho_0}
#     return pd.DataFrame(d)

def calculate_tension_df_from_file_df(file_df : pd.DataFrame) -> pd.DataFrame:
    # Ask Jeff which is preferred...
    lx  = file_df['lx'].to_numpy()
    pxx = file_df['pxx'].to_numpy()
    pyy = file_df['pyy'].to_numpy()
    pxy = file_df['pxy'].to_numpy()
    rho_0 = file_df['rho_0'].to_numpy();

    strain   = (lx - lx[0]) / lx[0];
    rho_f = rho_0 / (1+strain)**2;
    tension_xx = -pxx * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
    tension_yy = -pyy * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
    tension_xy = -pxy * u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER;
    ratio = tension_xx / tension_yy;

    d = {"strain":strain, "tension_xx":tension_xx, "tension_yy":tension_yy, "tension_xy":tension_xy, "ratio":ratio, "rho_f":rho_f, "rho_0":rho_0}
    return pd.DataFrame(d)

def calc_energy_df_from_file_df(file_df : pd.DataFrame) -> pd.DataFrame:
    lx  = file_df['lx'].to_numpy()
    ly  = file_df['ly'].to_numpy()
    pe  = file_df['pe'].to_numpy()
    glycan_pe  = file_df['glycan_pe'].to_numpy()
    angle_pe   = file_df['angle_pe'].to_numpy()
    peptide_pe = file_df['peptide_pe'].to_numpy()
    rho_0 = file_df['rho_0'].to_numpy();

    strain   = (lx - lx[0]) / lx[0];
    rho_f = rho_0 / (1+strain)**2;
    total_pe = glycan_pe + angle_pe + peptide_pe;
    glycan_pe_frac  = glycan_pe  / total_pe;
    angle_pe_frac   = angle_pe   / total_pe;
    peptide_pe_frac = peptide_pe / total_pe;
    energy_density = pe / (lx * ly)

    d = {"strain":strain, "glycan_pe_frac":glycan_pe_frac, "angle_pe_frac":angle_pe_frac, "peptide_pe_frac":peptide_pe_frac,"energy_density":energy_density, "rho_f":rho_f, "rho_0":rho_0}
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
    #plt.legend();
    #plt.title("Fraction of Potential Energy vs Strain")
    plt.ylabel("Energy Fraction [a.u.]")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid(True);
    plt.show();

## PLOTTING FUNCTIONS -- ENERGY DENSITY
def add_PE_density_curve(df : pd.DataFrame, colorname : str, labelstr : str):
    add_curve_with_ci(df, "strain", "energy_density", curve_color=colorname, curve_label_override=labelstr)

def finish_PE_density_curve():
    plt.legend()
    #plt.title("Potential Energy Density")
    plt.ylabel(r"$e$, Energy Density [aJ / $\text{nm}^2$]")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid(True);
    plt.show();

## PLOTTING FUNCTIONS -- TENSION
def add_tension_curve(df : pd.DataFrame, curves_color : str, extra_label_info):
    # Hoop (Higher)
    add_curve_with_ci(df, 'strain', 'tension_yy', 
                    curve_linestyle="-", curve_color=curves_color, curve_label_override=r"$\gamma_{Hoop}$"+extra_label_info)

    # Longitudinal (Lower)
    add_curve_with_ci(df, 'strain', 'tension_xx', 
                    curve_linestyle="--", curve_color=curves_color, curve_label_override=r"$\gamma_{Axial}$")

## PLOTTING FUNCTIONS -- TENSION RATIO
def add_tension_ratio_curve(df : pd.DataFrame, curve_color : str, extra_label_info : str):
    add_curve_with_ci(df, 'strain', 'ratio', 
                curve_linestyle="-", curve_color=curve_color, curve_label_override=extra_label_info)

    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'ratio')
    print(f"Mean Tension Ratio for {extra_label_info}: {np.mean(ci_df['mean'].to_numpy())}")



## FULL FIGURE FUNCTIONS
def full_tension_figure(
        curves_information : list[tuple[str, str, str, str]],
        expected_strain_tuple : tuple[float,float] = None,
        expected_tension_xx_tuple : tuple[float,float] = None,
        expected_tension_yy_tuple : tuple[float,float] = None,
        ax : plt.Axes = None):
    
    was_axis_provided = (ax != None);
    if not was_axis_provided:
        ax = plt.subplot();
    
    for i in range(0,len(curves_information)):
        (working_dirpath, output_regex, curve_color, extra_label_info) = curves_information[i];

        dfs = collect_list_of_prestrain_dataframes(working_dirpath, output_regex)

        tension_dfs = list()
        for file_df in dfs:
            tension_dfs.append(calculate_tension_df_from_file_df(file_df));

        if len(tension_dfs) == 0:
            continue;
        else:
            combined_tension_df = pd.concat(tension_dfs)

        # Hoop (Higher)
        #add_curve_with_ci(combined_tension_df, 'strain', 'tension_yy',  "-", curve_color, r"$\gamma_{Hoop}$, "+extra_label_info, ax)
        add_curve_with_ci(combined_tension_df, 'strain', 'tension_yy',  "-", curve_color, extra_label_info, ax)

        # Longitudinal (Lower)
        #add_curve_with_ci(combined_tension_df, 'strain', 'tension_xx', "--", curve_color, r"$\gamma_{Axial}$", ax)
        add_curve_with_ci(combined_tension_df, 'strain', 'tension_xx', "--", curve_color, None, ax)
    
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

    ax.set_ylabel(r"$\gamma$ [N/m]")
    ax.set_xlabel(r"$\mathcal{E}$, Strain")
    ax.legend(prop={'size': 15})
    ax.grid()
    ax.set_title(r"Total Tension, $\gamma$")

    if not was_axis_provided:
        plt.title("Total Tension")
        plt.show()

def full_tension_ratio_figure(curves_information : list[tuple[str, str, str, str]], ax : plt.Axes = None, show_laplace_region : bool = False, add_legend = True):
    
    was_axis_provided = (ax != None);
    if not was_axis_provided:
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
        ax.plot([0,0.3],[0.5,0.5], linestyle="--", color="green", label="Expected Ratio for Cylindrical Shell")
    
    ax.set_ylabel(r"$\gamma_{Axial}$ / $\gamma_{Hoop}$ [a.u.]")
    ax.set_xlabel(r"$\mathcal{E}$, Strain")
    ax.set_ylim([0,1.6])
    ax.grid(True)
    if add_legend: ax.legend();
    ax.set_title("Tension Ratio")

    if not was_axis_provided:
        plt.title("Tension Ratio")
        plt.show()

def full_energy_ratio_figure(curves_information : list[tuple[str, str, str, str]], bsize = None, ax = None):
    for i in range(0,len(curves_information)):
        (working_dirpath, output_regex, colorname, labelstr, curve_filters) = curves_information[i];

        dfs = collect_list_of_prestrain_dataframes(working_dirpath, output_regex)

        energy_ratio_dfs = list()
        for file_df in dfs:
            energy_ratio_dfs.append(calc_energy_df_from_file_df(file_df));

        if len(energy_ratio_dfs) == 0:
            continue;
        else:
            combined_energy_ratio_df = pd.concat(energy_ratio_dfs)

            combined_energy_ratio_df = apply_band_filters_to_df(combined_energy_ratio_df, curve_filters)

            # Group nearby x values together with confidence interval analysis
            if bsize:
                combined_energy_ratio_df['strain'] = bucket_round(combined_energy_ratio_df['strain'],bsize);

        add_energy_ratio_curves(combined_energy_ratio_df, colorname, labelstr);

    if not ax:
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

def full_turgor_strain_figure(
        curves_information : list[tuple[str, str, str, str]],
        diameter_bounds_m : tuple[float, float] = (0.99*1E-6,1.01*1E-6),
        density_filter : tuple[float,float] = None,
        pressure_filter_atm : tuple[float,float] = (0.3,3.0),
        ):
    
    # Loop through each curve, add them to figure one by one
    for i in range(0,len(curves_information)):
        (working_dirpath, output_regex, curve_color, curve_label, curve_filters) = curves_information[i];

        dfs = collect_list_of_prestrain_dataframes(working_dirpath, output_regex)
        print(f"Curve #{i}: collected {len(dfs)} output files from regex pattern")

        tension_dfs = list()
        for file_df in dfs:
            new_tension_df = calculate_tension_df_from_file_df(file_df);

            if len(new_tension_df) != 0:
                tension_dfs.append(new_tension_df);

        # If we filtered all the data point away, skip the curve
        if len(tension_dfs) == 0:
            continue;
        else:
            # Place results from each file into one big dataframe
            combined_tension_df : pd.DataFrame = pd.concat(tension_dfs)

            if density_filter:
                combined_tension_df = apply_band_filters_to_df(combined_tension_df, [(density_filter[0],"rho_f",density_filter[1])])
            
            combined_tension_df = apply_band_filters_to_df(combined_tension_df, curve_filters)

            # Group nearby x values together with confidence interval analysis
            bsize = 1E-2; # 1% strain
            combined_tension_df['strain'] = bucket_round(combined_tension_df['strain'],bsize);
        
        # Correct for density variation in the range we are examining. Assuming linear tension relation for small values.
        if density_filter:
            target_density = np.mean(density_filter);
            combined_tension_df['tension_yy'] = combined_tension_df['tension_yy'].to_numpy() * (target_density/combined_tension_df['rho_f'].to_numpy());

        ci_pyy_df = get_confidence_intervals(combined_tension_df, 0.95, "strain", "tension_yy")

        # estimate pressure from tension in the y direction
        turgor_pressure_df = pd.DataFrame();
        turgor_pressure_df['strain'] = ci_pyy_df.index;
        turgor_pressure_df['upper'] = ci_pyy_df['upper'].to_numpy() / (min(diameter_bounds_m)/2 * u_ATM_to_PASCAL);
        turgor_pressure_df['mean']  = ci_pyy_df['mean'].to_numpy()  / (np.mean(diameter_bounds_m)/2 * u_ATM_to_PASCAL);
        turgor_pressure_df['lower'] = ci_pyy_df['lower'].to_numpy() / (max(diameter_bounds_m)/2 * u_ATM_to_PASCAL);

        # restrict plot to a region that is relevant to E.Coli
        turgor_pressure_df = apply_band_filters_to_df(turgor_pressure_df, [(pressure_filter_atm[0],"mean",pressure_filter_atm[1])]);

        plt.plot(turgor_pressure_df['strain'], turgor_pressure_df['mean'], color=curve_color, linestyle="-", label=curve_label)
        plt.fill_between(
            turgor_pressure_df['strain'],
            turgor_pressure_df['lower'],
            turgor_pressure_df['upper'],
            color=curve_color, 
            alpha=0.2
        )

        # Print the reference_strain at 1 atm of turgor pressure
        ref_pressure = 1.0;
        ref_strain = np.interp(ref_pressure, turgor_pressure_df["mean"], turgor_pressure_df["strain"])
        print(f"For curve '{curve_label}', epsilon_0 = {round(ref_strain,3)} at P_t = {ref_pressure}")

    title_str = r"Turgor Pressure; $D = "+str(round(np.mean(diameter_bounds_m)*1E6,1))+r" \mu m $"
    if density_filter:
        title_str += r", $\rho_{f} = "+str(round(density_filter[0]/(DSU**2),2))+r"-"+str(round(density_filter[1]/(DSU**2),2))+r"$ $\frac{DSU}{nm^2}$"
    else:
        title_str += r", all $\rho_{f}$"

    plt.title(title_str);
    plt.legend()
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.ylabel(r"Equivalent Turgor [atm]")
    plt.grid()
    plt.show()


#### Compare Two Networks of Different Sizes

def add_network_ratio(df, colornamestr, labelstr):
    # tension_xx
    ci_df = get_confidence_intervals(df, 0.95, "strain", "comparison_ratio_xx")
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=colornamestr, linestyle="-", label=labelstr+r", $\tension_(xx)$")
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
