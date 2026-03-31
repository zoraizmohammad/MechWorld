from utils_helpers import find_files, get_confidence_intervals, add_curve_with_ci, get_initial_density_from_filename, get_crosslinkage_from_filename, bandpass_df
import os
import re
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from os import listdir
import matplotlib.pyplot as plt

@dataclass
class ElasticTensorStruct:
    strain : float;
    C11 : float;
    C22 : float;
    C33 : float;
    C12 : float;
    C13 : float;
    C23 : float;
    Ex   : float = None;
    Ey   : float = None;
    Gxy  : float = None;
    Vxy  : float = None;
    Vyx  : float = None;
    units : str = "MPa*nm";

    def calculate_orthotropic_moduli(self) -> None:
        # Theory of Plates & Shells, Colorado State University, 2006 -> Reduced Stiffness Matrix
        # Note that C in this struct is the STIFFNESS matrix [Q] in that document's notation 
        self.Gxy = self.C33;
        self.Vxy = self.C12 / self.C22;
        self.Vyx = self.C12 / self.C11;
        denominator = 1 - (self.C12**2)/(self.C11 * self.C22);
        self.Ex = self.C11 * denominator;
        self.Ey = self.C22 * denominator;
    
    def calculate_orthotropic_moduli_compliance(self) -> None:
        M = np.array([[self.C11, self.C12, 0],
                      [self.C12, self.C22, 0],
                      [0,        0,        self.C33]]);
        Minv = np.linalg.inv(M)
        self.Ex = 1 / Minv[0,0];
        self.Ey = 1 / Minv[1,1];
        self.Gxy = 1 / Minv[2,2];
        self.Vxy = -1 * Minv[1,0] * self.Ex;
        self.Vyx = -1 * Minv[1,0] * self.Ey;

    def print_comparison_of_two_moduli_methods(self) -> None:
        self.calculate_orthotropic_moduli();
        print(self.line_data());
        self.calculate_orthotropic_moduli_compliance();
        print(self.line_data());
    
    def expected_stress_ratio_xx_over_yy(self) -> float:
        return (self.C11+self.C12)/(self.C12+self.C22)

    def line_data(self) -> str:
        return f"{self.strain} {self.C11} {self.C22} {self.C33} {self.C12} {self.C13} {self.C23} {self.Ex} {self.Ey} {self.Gxy} {self.Vxy} {self.Vyx} {self.units}\n"

def combine_elastic_constant_files_into_one_file_per_network(working_dir : str):
    set_of_unique_basepaths = set();
    regex_individual_constants = r".+_prestr\d\.\d+\.elastic_constants";
    regex_capture_basepaths = r"(.+)_prestr\d\.\d+\.elastic_constants";

    filepaths_to_individual_lines : set[str] = find_files(working_dir, regex_individual_constants);

    #print(filepaths_to_individual_lines);

    for filepath in filepaths_to_individual_lines:
        match = re.match(regex_capture_basepaths, filepath);
        if match:
            basepath = match.group(1);
            set_of_unique_basepaths.add(basepath);

    #print(set_of_unique_basepaths);

    for basepath in set_of_unique_basepaths:
        combined_filepath = basepath + ".moduli"

        if not os.path.exists(combined_filepath):
            with open(combined_filepath, "w+") as f:
                f.write("strain C11 C22 C33 C12 C13 C23 Ex Ey Gxy Vxy Vyx units\n");

        for filepath in sorted(list(filepaths_to_individual_lines)):
            if not filepath.startswith(basepath):
                continue;
            
            line : str = "";
            with open(filepath, "r") as f:
                line = f.readline();
            
            line_data = line.split(" ")
            struct = ElasticTensorStruct(
                strain= float(line_data[0]), 
                C11   = float(line_data[1]),
                C22   = float(line_data[2]),
                C33   = float(line_data[3]),
                C12   = float(line_data[4]),
                C13   = float(line_data[5]),
                C23   = float(line_data[6]),
                Ex = None,
                Ey = None,
                Gxy = None,
                Vxy = None,
                Vyx = None,
                units = str(line_data[7]).strip(),
            )
            print(struct.line_data())
            struct.calculate_orthotropic_moduli()

            with open(combined_filepath, "a+") as f:
                f.write(struct.line_data());

            os.remove(filepath);

def import_ElasticTensorStructs_from_file(filepath : str) -> list[ElasticTensorStruct]:
    structs = list()
    with open(filepath,"r") as f:
        lines = f.readlines();
        for i,line in enumerate(lines):
            
            if i == 0: continue;

            line_data = line.split(" ")
            struct = ElasticTensorStruct(
                strain= float(line_data[0]), 
                C11   = float(line_data[1]),
                C22   = float(line_data[2]),
                C33   = float(line_data[3]),
                C12   = float(line_data[4]),
                C13   = float(line_data[5]),
                C23   = float(line_data[6]),
                Ex    = float(line_data[7]),
                Ey    = float(line_data[8]),
                Gxy   = float(line_data[9]),
                Vxy   = float(line_data[10]),
                Vyx   = float(line_data[11]),
                units = str(line_data[12]).strip(),
            )

            assert struct.units == "MPa*nm"

            structs.append(struct);

    return structs

def collect_combined_elastic_dataframe(dirpath : str, regex_pattern : str) -> list[pd.DataFrame]:
    combined_df : pd.DataFrame = "-";
    
    # Returns a list of dataframes, one from each file
    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            #print(f"{filename} is a match")
            filepath = os.path.join(dirpath,filename)
            dataclasses_from_file = import_ElasticTensorStructs_from_file(filepath)
            df = pd.DataFrame([asdict(n) for n in dataclasses_from_file])
            df['rho_0'] = [get_initial_density_from_filename(filename)] * len(df);
            df['rho_f'] = df["rho_0"] / (1+df["strain"])**2;

            linkage = get_crosslinkage_from_filename(filename);
            if linkage: df['linkage'] = [linkage] * len(df);

            if type(combined_df) == str:
                combined_df = df;
            else:
                combined_df = pd.concat([combined_df,df]);
            
    if (type(combined_df) == str):
        raise FileNotFoundError(f"No files were found in: {dirpath} matching regex: {regex_pattern}");

    return combined_df;

## TODO: Check reduced stiffness matrix for unstable modes, look at eigenvalues

## PLOTTING FUNCTIONS -- Ex,Ey,Gxy
def full_moduli_figure(curves_information : list[tuple[str, str, str, str]], density_filter = None, thickness_nm = None):

    for curve_tuple in curves_information:
        working_dir, regex_pattern, color_name, extra_label_info = curve_tuple;
        df = collect_combined_elastic_dataframe(working_dir, regex_pattern)
        df = bandpass_df(df, 'rho_f', density_filter);

        # convert to MPa if thickness is specified
        if thickness_nm:
            df['Ex'] = df["Ex"]/thickness_nm;
            df['Ey'] = df["Ey"]/thickness_nm;
            df['Gxy'] = df["Gxy"]/thickness_nm;

        add_curve_with_ci(df, 'strain', 'Ex', curve_color=color_name, curve_linestyle="-", curve_label_override="$E_{xx}$"+extra_label_info)
        add_curve_with_ci(df, 'strain', 'Ey', curve_color=color_name, curve_linestyle="--", curve_label_override="$E_{yy}$")
        add_curve_with_ci(df, 'strain', 'Gxy', curve_color=color_name, curve_linestyle=":", curve_label_override="$G_{xy}$")

    plt.legend();

    title_str = "Extensional and Shear Moduli"

    if thickness_nm:
        title_str += "; $t = "+str(thickness_nm)+"nm$"

    plt.title(title_str);

    if thickness_nm:
        plt.ylabel("MPa")
    else:
        plt.ylabel("MPa*nm")

    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid(True);
    plt.show();

## PLOTTING FUNCTIONS -- Vxy,Vyx
def full_poisson_ratios_figure(curves_information : list[tuple[str, str, str, str]], density_filter = None):

    for curve_tuple in curves_information:
        working_dir, regex_pattern, color_name, extra_label_info = curve_tuple;
        df = collect_combined_elastic_dataframe(working_dir, regex_pattern)
        df = bandpass_df(df, 'rho_f', density_filter); 
        add_curve_with_ci(df, 'strain', 'Vxy',"--", curve_label_override="$V_{xy}$"+extra_label_info,curve_color=color_name)
        add_curve_with_ci(df, 'strain', 'Vyx',":", curve_label_override="$V_{yx}$",curve_color=color_name)
    
    plt.legend()
    plt.title("Poisson Ratios")
    plt.ylabel("Poisson Ratio [a.u.]")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid()
    plt.show()

## PLOTTING FUNCTIONS -- Predicted Stress Ratio & Actual Stress Ratio
from process_network_ensembles import add_tension_ratio_curve

def add_expected_tension_ratio(df : pd.DataFrame):
    df["xx_yy_ratio"] = (df["Ex"] + df['Vxy']*df['Ey']) / (df["Ey"] + df['Vyx']*df['Ex']);
    pass

def full_ratios_figure(working_dir, regex_pattern):
    df = collect_combined_elastic_dataframe(working_dir, regex_pattern)
    #add_moduli_curves(df, "black", "a = 0.925")
    #finish_moduli_curve()